"""
MCX Natural Gas Strategist — FastAPI web application.

Endpoints:
  GET  /          → serve the browser UI
  POST /api/analyze → stream SSE analysis from Claude
  GET  /api/health  → liveness check
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from strategist import stream_analysis

app = FastAPI(title="MCX Natural Gas Strategist", version="1.0.0")

TEMPLATES_DIR = Path(__file__).parent / "templates"


@app.get("/", include_in_schema=False)
async def serve_ui() -> FileResponse:
    return FileResponse(TEMPLATES_DIR / "index.html")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/analyze")
async def analyze() -> StreamingResponse:
    return StreamingResponse(
        stream_analysis(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
