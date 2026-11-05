"""Application factory. The three transports and the clock are injectable so tests simulate only outbound HTTP."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api.v1.routes import Api, fallback_response
from .clients.rpc import RpcClient
from .core.config import Settings
from .core.security import JwtVerifier
from .nlu.extractor import DeepSeekExtractor, UnavailableExtractor


def create_app(settings: Settings | None = None, *, rpc_transport: httpx.BaseTransport | None = None,
               llm_transport: httpx.BaseTransport | None = None, jwks_transport: httpx.BaseTransport | None = None,
               clock=None, extractor=None) -> FastAPI:
    settings = settings or Settings.from_env()
    clock = clock or (lambda: datetime.now(timezone.utc))
    app = FastAPI(title="StudyFlow F1 API", docs_url=None, redoc_url=None, openapi_url=None)
    if extractor is None:
        extractor = (DeepSeekExtractor(settings.deepseek_base_url, settings.deepseek_api_key, settings.deepseek_model, llm_transport)
                     if settings.deepseek_api_key else UnavailableExtractor())
    api = Api(settings, RpcClient(settings, rpc_transport, clock), JwtVerifier(settings, jwks_transport, clock), clock, extractor)
    app.state.llm_transport = llm_transport  # used by the extraction stage
    api.register(app)

    @app.exception_handler(StarletteHTTPException)
    async def _not_found(request, exc):  # catalog envelope instead of the framework default
        return fallback_response(request, exc.status_code)

    app.add_middleware(
        CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Idempotency-Key", "Content-Type"],
        expose_headers=["X-Request-ID", "Idempotency-Replayed", "Retry-After"], max_age=600)
    return app
