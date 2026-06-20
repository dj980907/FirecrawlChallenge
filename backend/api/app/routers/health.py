from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint"""
    return {"status": "healthy", "service": "api"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    """Readiness check endpoint"""
    return {"status": "ready", "service": "api"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    """Liveness check endpoint"""
    return {"status": "alive", "service": "api"}
