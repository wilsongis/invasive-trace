"""API v1 router wiring."""

from fastapi import APIRouter

from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.observations import router as observations_router
from app.api.v1.predictions import router as predictions_router
from app.api.v1.rois import router as rois_router
from app.api.v1.scenes import router as scenes_router

router = APIRouter()

router.include_router(rois_router)
router.include_router(observations_router)
router.include_router(scenes_router)
router.include_router(predictions_router)
router.include_router(dashboard_router)


@router.get("/")
async def v1_root() -> dict[str, str]:
    """Simple API v1 root endpoint."""
    return {"status": "ok", "version": "v1"}
