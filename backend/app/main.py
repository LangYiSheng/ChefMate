from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.config import settings
from app.infra.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging(settings.app_debug)
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.2.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    app.mount(settings.asset_url_prefix, StaticFiles(directory=settings.upload_path), name="assets")
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
