from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app import __version__
from app.core.config import Environment, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok"]
    environment: Environment
    version: str


@router.get("/healthz", response_model=HealthResponse, summary="Health check")
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", environment=settings.environment, version=__version__)
