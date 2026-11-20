"""Application factory: builds the FastAPI app and registers the v1 router, middleware,
exception handlers, CORS and /metrics.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from returnright.api.exception_handlers import register_exception_handlers
from returnright.api.v1.router import api_router
from returnright.core.config import get_settings
from returnright.db.session import dispose_engine


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    yield
    dispose_engine()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="ReturnRight API",
        version="0.1.0",
        summary="Returns, eligibility, inspection, finance approval, idempotent refunds and audit.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    register_exception_handlers(app)
    # Still to register as their stories land: request-id middleware, /metrics.
    return app


app = create_app()
