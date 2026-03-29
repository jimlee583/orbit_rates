"""Satellite body-rate calculator — FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routers import body_rates

app = FastAPI(
    title="Satellite Body-Rate Calculator",
    description=(
        "Computes required spacecraft body rates for a satellite in low Earth orbit. "
        "Supports nadir, velocity-vector, and sun-nadir pointing modes."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(body_rates.router, prefix="/api")


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    """Return a simple health-check response."""
    return {"status": "ok"}
