import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import debug, firecrawl, health

app = FastAPI(
    title="Action Debug Runner",
    description=(
        "Debug Firecrawl action sequences step-by-step.\n\n"
        "When a multi-step scrape fails, find exactly which step broke and "
        "what the page looked like at failure time."
    ),
    version="0.2.0",
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
app.include_router(debug.router, tags=["debug"])


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Action Debug Runner API",
        "version": "0.2.0",
        "docs": "/docs",
    }
