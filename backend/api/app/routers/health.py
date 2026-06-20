from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    return {"status": "ready"}
