from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRoute

from app import __version__
from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.errors import ErrorResponse, register_exception_handlers
from app.core.logging import configure_logging


def _operation_id(route: APIRoute) -> str:
    tag = str(route.tags[0]) if route.tags else "default"
    return f"{tag}_{route.name}"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="Lyre API",
        version=__version__,
        lifespan=lifespan,
        generate_unique_id_function=_operation_id,
        responses={
            422: {"model": ErrorResponse, "description": "Validation Error"},
            500: {"model": ErrorResponse, "description": "Internal Error"},
        },
    )

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
