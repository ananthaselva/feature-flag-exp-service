import time
import logging
from fastapi import FastAPI, Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import settings
from app.deps import engine
from app.models import Base
from app.routers import health as health_router
from app.routers import auth as auth_router
from app.routers import flags as flags_router
from app.routers import segments as segments_router
from app.routers import evaluate as evaluate_router
from app.routers import audit as audit_router
from app.utils.logging import setup_logging, get_request_context
from app.utils import metrics

# ---------- Logging ----------
setup_logging(settings.log_level)
logger = logging.getLogger("feature-flag-service")

# ---------- FastAPI App ----------
app = FastAPI(title="Feature Flag Service", version="0.1.0")

# ---------- Middleware ----------
app.add_middleware(metrics.MetricsMiddleware)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Structured logging for all requests/responses."""
    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Only log errors with duration
        if response.status_code >= 400:
            ctx = get_request_context(request, duration_ms=duration_ms)
            ctx["status"] = response.status_code
            logger.info("Request completed with error", extra=ctx)
        return response
    except Exception:
        duration_ms = (time.time() - start_time) * 1000
        ctx = get_request_context(request, duration_ms=duration_ms)
        logger.exception("Unhandled exception during request", extra=ctx)
        raise


# ---------- Startup Event ----------
@app.on_event("startup")
async def on_startup():
    """Create DB tables for development/demo."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# ---------- Routers ----------
app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(flags_router.router)
app.include_router(segments_router.router)
app.include_router(evaluate_router.router)
app.include_router(audit_router.router)


# ---------- Prometheus Metrics Endpoint ----------
@app.get("/metrics")
async def metrics_endpoint():
    """Expose Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
