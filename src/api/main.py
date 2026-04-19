import logging
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parents[2] / ".env")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import research, stream, runs, hackernews
from src.config import settings

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="Genie AI — MARRE",
    description="Multi-Agent Research & Reporting Engine",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research.router)
app.include_router(stream.router)
app.include_router(runs.router)
app.include_router(hackernews.router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}
