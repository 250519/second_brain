"""Graph router — knowledge graph analysis and visualization."""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse, JSONResponse

from ...graph import analyze, visualize
from ..models import GraphResponse

router = APIRouter()


@router.post("/analyze", response_model=GraphResponse)
def graph_analyze() -> GraphResponse:
    """
    Run knowledge graph analysis on the ontology.

    Computes betweenness centrality, isolated clusters, and bridge concepts
    using networkx. An LLM generates 7–10 research questions targeting the
    most important knowledge gaps. Results are saved to data/todos/gaps.md.
    """
    try:
        report = analyze()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return GraphResponse(report=report)


@router.get("/data")
def graph_data() -> JSONResponse:
    """
    Return the knowledge graph as JSON (nodes + edges).

    Suitable for custom D3.js / Cytoscape.js visualizations.
    Each node includes centrality score and connection count.
    Each edge includes the relation label.
    """
    import networkx as nx
    from ...graph import _load_existing_triples, ensure_graph_dirs, TRIPLE_RE

    ensure_graph_dirs()
    existing = _load_existing_triples()

    if not existing:
        raise HTTPException(status_code=404, detail="Ontology is empty — ingest some sources first.")

    G: nx.DiGraph = nx.DiGraph()
    for triple in existing:
        m = TRIPLE_RE.match(triple)
        if m:
            G.add_edge(m.group("a"), m.group("b"), relation=m.group("rel"))

    centrality = nx.betweenness_centrality(G)

    nodes = [
        {
            "id": n,
            "centrality": round(centrality.get(n, 0), 4),
            "degree": G.degree(n),
            "in_degree": G.in_degree(n),
            "out_degree": G.out_degree(n),
        }
        for n in G.nodes()
    ]
    edges = [
        {"source": u, "target": v, "relation": d.get("relation", "")}
        for u, v, d in G.edges(data=True)
    ]

    return JSONResponse({"nodes": nodes, "edges": edges})


@router.get("/view")
def graph_view() -> FileResponse:
    """
    Serve an interactive pyvis HTML visualization of the knowledge graph.

    Open in any browser. Nodes are colour-coded by centrality (red = hub,
    orange = medium, blue = peripheral). Hover for details; drag to explore.
    """
    try:
        path = visualize()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return FileResponse(str(path), media_type="text/html")
