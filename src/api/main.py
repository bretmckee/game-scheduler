"""FastAPI web service main module."""

import logging

from fastapi import FastAPI

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Game Scheduler API",
    description="Discord Game Scheduling System API",
    version="0.1.0"
)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Game Scheduler API"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
