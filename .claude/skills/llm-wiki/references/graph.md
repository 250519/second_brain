# Knowledge Graph Reference — graph.py

Three functions: `extract_triples` (called by compiler), `analyze` (called by CLI/API), `visualize` (called by CLI --view and API /graph/view).

```python
"""Knowledge graph: extract triples from wiki pages, analyze structure, detect gaps."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx

from .config import (
    GAPS_FILE, INFRANODUS_DIR, MAX_SOURCE_CHARS, MODEL,
    ONTOLOGY_FILE, OUTPUT_DIR, TODOS_DIR, WIKI_DIR,
)
from .llm import get_client

# Canonical triple format
TRIPLE_RE = re.compile(
    r"^\[\[(?P<a>[^\]]+)\]\]\s+--(?P<rel>[^-]+)-->\s+\[\[(?P<b>[^\]]+)\]\]$"
)


def ensure_graph_dirs() -> None:
    INFRANODUS_DIR.mkdir(parents=True, exist_ok=True)
    TODOS_DIR.mkdir(parents=True, exist_ok=True)
    if not ONTOLOGY_FILE.exists():
        ONTOLOGY_FILE.write_text("# Wiki Ontology\n\n")
    if not GAPS_FILE.exists():
        GAPS_FILE.write_text("# Knowledge Gaps\n\n")


def _load_existing_triples() -> set[str]:
    if not ONTOLOGY_FILE.exists():
        return set()
    triples = set()
    for line in ONTOLOGY_FILE.read_text().splitlines():
        line = line.strip()
        if TRIPLE_RE.match(line):
            triples.add(line)
    return triples


def _slug(title: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    return re.sub(r"[-\s]+", "-", slug)


def extract_triples(pages_written: list[str], wiki_dir: Path = WIKI_DIR) -> int:
    """Extract entity→relation→entity triples from newly written pages.

    Called by compiler after every ingest. Append-only — never rewrites the ontology.
    Returns count of new triples appended.
    """
    ensure_graph_dirs()
    existing = _load_existing_triples()

    pages_content_parts: list[str] = []
    total_chars = 0
    for entry in pages_written:
        if "/" not in entry:
            continue
        page_type, title = entry.split("/", 1)
        path = wiki_dir / page_type / f"{_slug(title)}.md"
        if not path.exists():
            continue
        text = path.read_text()
        if total_chars + len(text) > MAX_SOURCE_CHARS:
            break
        pages_content_parts.append(f"### {entry}\n{text}")
        total_chars += len(text)

    if not pages_content_parts:
        return 0

    # Provide existing entity names so LLM uses consistent spelling
    entity_names: list[str] = []
    for triple in existing:
        m = TRIPLE_RE.match(triple)
        if m:
            entity_names.extend([m.group("a"), m.group("b")])
    unique_entities = sorted(set(entity_names))[:100]

    prompt = (
        "You are an ontology extractor. Extract entity→relation→entity triples from these wiki pages.\n\n"
        + (
            "Existing entity names — use EXACTLY these spellings if the entity appears:\n"
            + ", ".join(unique_entities) + "\n\n"
            if unique_entities else ""
        )
        + "Rules:\n"
        "- Each triple must be: a factual relationship between two named concepts\n"
        "- Keep relation labels short (2-5 words, no arrows or special chars)\n"
        "- Return ONLY a raw JSON array, no markdown fences, no explanation\n"
        '- Example: [{"a": "RAG", "rel": "is a type of", "b": "Retrieval System"}]\n\n'
        "Pages:\n" + "---\n".join(pages_content_parts)
    )

    client = get_client()
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
        items = json.loads(raw)
    except Exception:
        return 0

    new_triples: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        a = str(item.get("a", "")).strip()
        rel = str(item.get("rel", "")).strip()
        b = str(item.get("b", "")).strip()
        if not a or not rel or not b:
            continue
        if "-->" in rel:
            continue
        formatted = f"[[{a}]] --{rel}--> [[{b}]]"
        if formatted not in existing:
            new_triples.append(formatted)
            existing.add(formatted)

    if not new_triples:
        return 0

    with ONTOLOGY_FILE.open("a") as f:
        for triple in new_triples:
            f.write(triple + "\n")

    return len(new_triples)


def analyze() -> str:
    """Run graph analysis: centrality, gaps, research questions.

    Writes gap questions to data/todos/gaps.md. Returns full report string.
    """
    ensure_graph_dirs()
    existing = _load_existing_triples()

    if not existing:
        return "Ontology is empty — ingest some sources first, then run `graph`."

    G: nx.DiGraph = nx.DiGraph()
    for triple in existing:
        m = TRIPLE_RE.match(triple)
        if m:
            G.add_edge(m.group("a"), m.group("b"), label=m.group("rel"))

    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()

    centrality = nx.betweenness_centrality(G)
    top_central = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10]
    wccs = sorted(nx.weakly_connected_components(G), key=len, reverse=True)
    isolated = [c for c in wccs if len(c) <= 3]
    main_cluster_size = len(wccs[0]) if wccs else 0

    try:
        bridge_edges = list(nx.bridges(G.to_undirected()))
    except Exception:
        bridge_edges = []
    bridge_nodes = {n for e in bridge_edges for n in e}

    in_degree = sorted(G.in_degree(), key=lambda x: x[1], reverse=True)[:5]   # type: ignore
    out_degree = sorted(G.out_degree(), key=lambda x: x[1], reverse=True)[:5]  # type: ignore

    lines = [
        "# Knowledge Graph Analysis\n",
        f"**Nodes:** {total_nodes}  **Edges:** {total_edges}  "
        f"**Components:** {len(wccs)}  **Main cluster:** {main_cluster_size} nodes\n",
        "## Central Concepts (highest betweenness)\n",
    ]
    for node, score in top_central:
        lines.append(f"- **{node}** — {score:.4f}")

    lines += ["\n## Hub Concepts (most incoming connections)\n"]
    for node, deg in in_degree:
        lines.append(f"- **{node}** — {deg} incoming")

    if bridge_nodes:
        lines += ["\n## Bridge Concepts (single points connecting clusters)\n"]
        for node in sorted(bridge_nodes):
            lines.append(f"- **{node}**")

    if isolated:
        lines += ["\n## Isolated Clusters (disconnected from main graph)\n"]
        for cluster in isolated[:10]:
            lines.append(f"- {', '.join(sorted(cluster))}")

    report = "\n".join(lines)

    # LLM generates research questions from the analysis
    ontology_sample = "\n".join(list(existing)[-150:])
    gap_prompt = (
        "Based on this knowledge graph analysis, generate 7-10 concrete research questions "
        "that would fill the most important knowledge gaps.\n\n"
        "Focus on:\n"
        "- Isolated clusters that should connect to the main graph\n"
        "- Central concepts that likely need deeper exploration\n"
        "- Missing bridges between major topic areas\n\n"
        f"Analysis:\n{report}\n\n"
        f"Recent ontology triples (sample):\n{ontology_sample}\n\n"
        "Return ONLY a raw JSON array of strings, no markdown fences."
    )

    client = get_client()
    research_questions: list[str] = []
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": gap_prompt}],
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw, flags=re.DOTALL).strip()
        research_questions = json.loads(raw)
        if not isinstance(research_questions, list):
            research_questions = []
    except Exception:
        research_questions = []

    if research_questions:
        report += "\n\n## Suggested Research Questions (Knowledge Gaps)\n"
        for q in research_questions:
            report += f"\n- {q}"
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        with GAPS_FILE.open("a") as f:
            f.write(f"\n## [{ts}] Gap Analysis\n")
            for q in research_questions:
                f.write(f"- {q}\n")

    return report


def visualize(output_path: Path | None = None) -> Path:
    """Render the knowledge graph as an interactive pyvis HTML file.

    Nodes coloured by betweenness centrality:
      red/large  → high-centrality hubs
      orange     → medium centrality
      blue/small → peripheral concepts

    Hover a node: name, centrality score, connection count.
    Hover an edge: relation label.
    Returns the path to the saved HTML file.
    """
    try:
        from pyvis.network import Network
    except ImportError:
        raise RuntimeError("pyvis not installed — run: uv add pyvis")

    ensure_graph_dirs()
    existing = _load_existing_triples()

    if not existing:
        raise ValueError("Ontology is empty — ingest some sources first.")

    G: nx.DiGraph = nx.DiGraph()
    for triple in existing:
        m = TRIPLE_RE.match(triple)
        if m:
            G.add_edge(m.group("a"), m.group("b"), title=m.group("rel"))

    centrality = nx.betweenness_centrality(G)

    net = Network(
        height="920px",
        width="100%",
        directed=True,
        bgcolor="#0f0f23",
        font_color="#e0e0e0",
        notebook=False,
        cdn_resources="in_line",   # fully self-contained HTML
    )
    net.from_nx(G)

    for node in net.nodes:
        nid = node["id"]
        c = centrality.get(nid, 0)
        deg = G.degree(nid)
        node["title"] = f"<b>{nid}</b><br>Centrality: {c:.3f}<br>Connections: {deg}"

        if c > 0.08:
            node["color"] = "#ff6b6b"
            node["size"] = 42
            node["font"] = {"size": 17, "bold": True, "color": "#ffffff"}
        elif c > 0.02:
            node["color"] = "#ffa94d"
            node["size"] = 26
            node["font"] = {"size": 13, "color": "#ffffff"}
        else:
            node["color"] = "#74c0fc"
            node["size"] = 14
            node["font"] = {"size": 10, "color": "#cccccc"}

    for edge in net.edges:
        edge["color"] = {"color": "#44445a", "highlight": "#aaaaff", "hover": "#8888ff"}
        edge["smooth"] = {"type": "curvedCW", "roundness": 0.15}
        edge["arrows"] = "to"

    net.set_options("""{
      "physics": {
        "enabled": true,
        "solver": "forceAtlas2Based",
        "forceAtlas2Based": {
          "gravitationalConstant": -60,
          "centralGravity": 0.008,
          "springLength": 160,
          "springConstant": 0.06,
          "damping": 0.6
        },
        "stabilization": {"iterations": 200, "fit": true}
      },
      "interaction": {
        "hover": true,
        "navigationButtons": true,
        "keyboard": {"enabled": true},
        "tooltipDelay": 100
      }
    }""")

    out = output_path or OUTPUT_DIR / "graph.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    net.save_graph(str(out))
    return out
```
