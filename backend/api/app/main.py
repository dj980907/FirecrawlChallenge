from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import debug, health

app = FastAPI(
    title="Action Debug Runner",
    description=(
        "Debug Firecrawl action sequences step-by-step.\n\n"
        "When a multi-step scrape fails, find exactly which step broke and "
        "what the page looked like at failure time."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(debug.router, prefix="/debug", tags=["debug"])


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Action Debug Runner API",
        "version": "0.2.0",
        "docs": "/docs",
    }
