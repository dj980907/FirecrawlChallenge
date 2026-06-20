from fastapi import APIRouter

from app.db import SupabaseNotConfiguredError, verify_supabase_connection

router = APIRouter()


@router.get("/")
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def readiness_check() -> dict[str, str]:
    try:
        await verify_supabase_connection()
    except SupabaseNotConfiguredError as exc:
        return {"status": "not_ready", "reason": str(exc)}
    except Exception as exc:
        return {"status": "not_ready", "reason": str(exc)}

    return {"status": "ready"}
