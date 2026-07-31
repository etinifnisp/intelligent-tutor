import logging

from fastapi import APIRouter, Request

router = APIRouter()
logger = logging.getLogger("tutor.api")


@router.get("/graph")
async def get_knowledge_graph_topology(request: Request):
    """Serves full NetworkX link topology for the concept map frontend."""
    logger.debug("GET /graph")
    return request.app.state.graph.export_subgraph()
