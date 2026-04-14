"""Query router — ask questions against the wiki."""

from fastapi import APIRouter, HTTPException, status

from ...agents import query as query_agent
from ..models import QueryRequest, QueryResponse

router = APIRouter()


@router.post("", response_model=QueryResponse)
def query(body: QueryRequest) -> QueryResponse:
    """
    Answer a question using the wiki.

    BM25 retrieves the most relevant pages; Claude synthesizes the answer.
    If `file_back` is true (default), non-trivial answers are auto-filed
    back into the wiki as qa/ or insight/ pages, compounding knowledge over time.
    """
    try:
        answer = query_agent.answer(body.question, file_back=body.file_back)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return QueryResponse(answer=answer)
