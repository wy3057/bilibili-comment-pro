from __future__ import annotations

from time import perf_counter
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.router import api_router
from app.core.config import settings
from app.core.metrics import HTTP_ACTIVE_REQUESTS, HTTP_REQUEST_COUNT, HTTP_REQUEST_LATENCY
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.bootstrap import bootstrap_defaults


def _build_cors_origins() -> list[str]:
    origins = {
        settings.frontend_origin,
        "http://localhost:5173",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:4173",
    }
    parsed = urlparse(settings.frontend_origin)
    if parsed.scheme and parsed.port:
        if parsed.hostname == "localhost":
            origins.add(f"{parsed.scheme}://127.0.0.1:{parsed.port}")
        if parsed.hostname == "127.0.0.1":
            origins.add(f"{parsed.scheme}://localhost:{parsed.port}")
    return sorted(origin for origin in origins if origin)


app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_build_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    HTTP_ACTIVE_REQUESTS.inc()
    started = perf_counter()
    try:
        response = await call_next(request)
        return response
    finally:
        duration = perf_counter() - started
        path = request.url.path
        status_code = getattr(locals().get("response"), "status_code", 500)
        HTTP_REQUEST_COUNT.labels(request.method, path, str(status_code)).inc()
        HTTP_REQUEST_LATENCY.labels(request.method, path).observe(duration)
        HTTP_ACTIVE_REQUESTS.dec()


@app.on_event("startup")
def on_startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_defaults(db)
    finally:
        db.close()


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    return PlainTextResponse(generate_latest().decode("utf-8"), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.include_router(api_router, prefix=settings.api_prefix)
