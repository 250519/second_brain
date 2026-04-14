"""BM25 full-text search over wiki pages."""

from rank_bm25 import BM25Okapi

from .wiki import read_all_pages


def bm25_search(question: str, top_k: int = 10) -> list[str]:
    """Return top_k page paths most relevant to the question using BM25.

    Indexes full page content so synonym-rich pages rank well even when
    exact query terms are absent from the page title.
    """
    pages = read_all_pages()
    if not pages:
        return []

    paths = list(pages.keys())
    # Include the path slug in each doc so title tokens contribute to ranking
    corpus = [
        path.replace("/", " ").replace("-", " ") + " " + content
        for path, content in pages.items()
    ]

    tokenized_corpus = [doc.lower().split() for doc in corpus]
    tokenized_query = question.lower().split()

    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(tokenized_query)

    ranked = sorted(zip(paths, scores), key=lambda x: x[1], reverse=True)
    return [path for path, _ in ranked[:top_k]]
