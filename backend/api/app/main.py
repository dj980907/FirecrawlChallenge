import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import SupabaseNotConfiguredError, verify_supabase_connection
from app.routers import extractors, firecrawl, health

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        try:
            await verify_supabase_connection()
            logger.info("Supabase connection verified")
        except SupabaseNotConfiguredError:
            logger.warning("Supabase env vars incomplete; database features disabled")
        except Exception:
            logger.exception(
                "Supabase connection failed. Run supabase/migrations/001_initial_schema.sql "
                "in your Supabase project if tables do not exist yet."
            )
            raise
    else:
        logger.warning(
            "SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not set; database features disabled"
        )

    yield


app = FastAPI(
    title="Managed Extractors API",
    description=(
        "Self-maintaining extraction pipelines powered by Firecrawl.\n\n"
        "Define extractors with a prompt and JSON schema; the API handles "
        "persistence, extraction, validation, drift detection, and auto-repair.\n\n"
        "See `backend/api/API.md` for endpoint reference and curl examples."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",")]
else:
    allowed_origins = [
        "http://app.localhost",
        "http://localhost:3000",
        "http://localhost",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(firecrawl.router, prefix="/firecrawl", tags=["firecrawl"])
app.include_router(extractors.router, prefix="/extractors", tags=["extractors"])


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Welcome to Firecrawl Challenge API",
        "version": "0.1.0",
    }
