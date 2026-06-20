import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import firecrawl, health

app = FastAPI(
    title="Firecrawl Challenge API",
    description="Backend API for the Firecrawl 72-hour challenge",
    version="0.1.0",
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


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Welcome to Firecrawl Challenge API",
        "version": "0.1.0",
    }
