"""Application factory: builds the FastAPI app and registers the v1 router, middleware,
exception handlers, CORS and /metrics.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from returnright.api.exception_handlers import register_exception_handlers
from returnright.api.v1.router import api_router
from returnright.core.config import get_settings
from returnright.db.session import dispose_engine
from returnright.mappers.return_mapper import UPLOADS_PATH


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
    # Customer photos, served under the API prefix so the web app's /api proxy reaches them.
    # File names are random, so a URL can't be guessed from another one.
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    app.mount(UPLOADS_PATH, StaticFiles(directory=upload_dir), name="uploads")
    # Still to register as their stories land: request-id middleware, /metrics.
    return app


app = create_app()
