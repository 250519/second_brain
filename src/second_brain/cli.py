import re
from datetime import datetime, timezone
from pathlib import Path

import click

from .agents import compiler, query, review
from .config import RAW_DIR, ISSUES_FILE
from .reader import read_source
from .wiki import read_index


@click.group()
def main() -> None:
    """second-brain — personal knowledge wiki powered by Claude."""


@main.command()
@click.argument("source")
def ingest(source: str) -> None:
    """Ingest a file or URL into the wiki.

    SOURCE can be a local file path or a URL.
    """
    click.echo(f"Reading {source} ...")
    try:
        content, name = read_source(source)
    except Exception as e:
        raise click.ClickException(str(e))

    click.echo(f"Compiling into wiki ({len(content):,} chars) ...")
    pages = compiler.ingest(content, name, read_index())

    click.echo(f"\nDone. {len(pages)} page(s) written:")
    for p in pages:
        click.echo(f"  + {p}")


@main.command("ingest-list")
@click.argument("file", type=click.Path(exists=True))
def ingest_list(file: str) -> None:
    """Ingest all URLs found in a file, one by one.

    FILE should be a markdown or text file containing URLs (one per line or inline).
    """
    text = Path(file).read_text()
    urls = re.findall(r"https?://\S+", text)

    if not urls:
        raise click.ClickException(f"No URLs found in {file}")

    click.echo(f"Found {len(urls)} URLs in {file}\n")

    issues: list[str] = []

    for i, url in enumerate(urls, 1):
        # Strip trailing punctuation/markdown artifacts
        url = url.rstrip(")>.,\n")
        click.echo(f"[{i}/{len(urls)}] {url}")
        try:
            content, name = read_source(url)
            if len(content.strip()) < 300:
                msg = f"Very short content ({len(content)} chars) — may be incomplete"
                click.echo(f"  ⚠ {msg}")
                issues.append(f"- [{url}] {msg}")
            pages = compiler.ingest(content, name, read_index())
            click.echo(f"  ✓ {len(pages)} page(s) written")
        except Exception as e:
            msg = str(e)
            click.echo(f"  ✗ {msg}")
            issues.append(f"- [{url}] ERROR: {msg}")

    if issues:
        _append_issues(issues, file)
        click.echo(f"\n⚠ {len(issues)} issue(s) logged to ISSUES.md")
    else:
        click.echo("\nAll URLs ingested successfully.")


@main.command()
@click.argument("question")
@click.option("--no-file", is_flag=True, default=False, help="Don't file the answer back into the wiki.")
def query_cmd(question: str, no_file: bool) -> None:
    """Ask a question against the wiki."""
    result = query.answer(question, file_back=not no_file)
    click.echo(result)

    searches = _extract_search_suggestions(result)
    if searches:
        _web_search_followup(question, searches, file_back=not no_file)


main.add_command(query_cmd, name="query")


def _extract_search_suggestions(text: str) -> list[str]:
    """Parse backtick-quoted queries from a '## To explore' section."""
    match = re.search(r"##\s+To explore\n(.*?)(?:\n##|\Z)", text, re.DOTALL)
    if not match:
        return []
    return re.findall(r"`([^`]+)`", match.group(1))


def _web_search_followup(question: str, searches: list[str], file_back: bool = True) -> None:
    """Interactive flow: search web → pick results to ingest → optionally re-run query."""
    click.echo("\n" + "─" * 60)
    click.echo("The wiki doesn't fully cover this. Options:")
    click.echo("  [s] Search the web and pick results to ingest")
    click.echo("  [u] Paste a URL to ingest directly")
    click.echo("  [n] Skip")

    choice = click.prompt("Choice", default="n").strip().lower()

    if choice == "u":
        url = click.prompt("URL to ingest").strip()
        if url:
            _ingest_url(url)
            _maybe_requery(question, file_back)
        return

    if choice != "s":
        return

    # Run DuckDuckGo with the first suggested query
    search_query = searches[0]
    click.echo(f"\nSearching: {search_query}")
    try:
        from duckduckgo_search import DDGS
        results = list(DDGS().text(search_query, max_results=5))
    except Exception as e:
        click.echo(f"Search failed: {e}")
        return

    if not results:
        click.echo("No results found.")
        return

    click.echo("\nTop results:")
    for i, r in enumerate(results, 1):
        click.echo(f"  [{i}] {r.get('title', '?')}")
        click.echo(f"      {r.get('href', '')}")

    raw = click.prompt(
        "\nIngest which? (comma-separated numbers, or Enter to skip)",
        default="",
    ).strip()

    if not raw:
        return

    indices: list[int] = []
    for part in raw.split(","):
        try:
            idx = int(part.strip()) - 1
            if 0 <= idx < len(results):
                indices.append(idx)
        except ValueError:
            pass

    if not indices:
        return

    for idx in indices:
        url = results[idx].get("href", "")
        if url:
            _ingest_url(url)

    _maybe_requery(question, file_back)


def _ingest_url(url: str) -> None:
    from .agents import compiler as _compiler
    from .reader import read_source
    from .wiki import read_index as _read_index

    click.echo(f"\nIngesting {url} ...")
    try:
        content, name = read_source(url)
        pages = _compiler.ingest(content, name, _read_index())
        click.echo(f"  ✓ {len(pages)} page(s) written")
    except Exception as e:
        click.echo(f"  ✗ {e}")


def _maybe_requery(question: str, file_back: bool) -> None:
    if not click.confirm("\nRe-run your question with the updated wiki?", default=True):
        return
    click.echo("\n" + "─" * 60)
    click.echo(query.answer(question, file_back=file_back))


@main.command()
@click.option("--view", is_flag=True, default=False, help="Open interactive graph visualization in the browser.")
def graph(view: bool) -> None:
    """Analyze the knowledge graph: centrality, gaps, research questions."""
    from .graph import analyze, visualize
    click.echo(analyze())
    if view:
        import webbrowser
        try:
            path = visualize()
            url = f"file://{path.resolve()}"
            click.echo(f"\nGraph saved → {path}")
            webbrowser.open(url)
        except Exception as e:
            click.echo(f"\nVisualization failed: {e}", err=True)


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Bind address.")
@click.option("--port", default=8000, show_default=True, type=int, help="Port to listen on.")
@click.option("--reload", is_flag=True, default=False, help="Auto-reload on code changes (dev only).")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the FastAPI API server."""
    import uvicorn
    click.echo(f"Starting Second Brain API on http://{host}:{port}  (docs: /docs)")
    uvicorn.run("second_brain.api.main:app", host=host, port=port, reload=reload)


@main.command()
def lint() -> None:
    """Run a health check on the wiki."""
    click.echo(review.lint())


@main.command()
def status() -> None:
    """Show wiki statistics."""
    from .wiki import read_all_pages
    from .config import WIKI_DIR, IDEAS_FILE

    pages = read_all_pages()
    if not pages:
        click.echo("Wiki is empty. Run: second-brain ingest <file_or_url>")
        return

    by_type: dict[str, int] = {}
    for path in pages:
        t = path.split("/")[0]
        by_type[t] = by_type.get(t, 0) + 1

    click.echo(f"Wiki: {len(pages)} pages")
    for t, count in sorted(by_type.items()):
        click.echo(f"  {t}: {count}")

    raw_files = [f for f in RAW_DIR.glob("*") if f.name != ".gitkeep"] if RAW_DIR.exists() else []
    click.echo(f"Raw sources: {len(raw_files)}")

    if IDEAS_FILE.exists():
        ideas = [l for l in IDEAS_FILE.read_text().splitlines() if l.startswith("- ")]
        click.echo(f"Ideas: {len(ideas)}")


def _append_issues(issues: list[str], source: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    header = f"\n## [{ts}] Issues from: {source}\n"
    entry = header + "\n".join(issues) + "\n"
    with ISSUES_FILE.open("a") as f:
        f.write(entry)
