from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.deps import engine
from app.models import Base
from app.routers import audit as audit_router
from app.routers import auth as auth_router
from app.routers import evaluate as evaluate_router
from app.routers import flags as flags_router
from app.routers import health as health_router
from app.routers import segments as segments_router
from app.utils.logging import setup_logging

# Logging
setup_logging(settings.log_level)

app = FastAPI(title="Feature Flag Service", version="0.1.0")

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["path", "method", "status"]
)


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            status = getattr(response, "status_code", 500)
            REQUEST_COUNT.labels(
                path=request.url.path, method=request.method, status=status
            ).inc()


@app.on_event("startup")
async def on_startup():
    # Create tables (simple approach for starter)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


app.add_middleware(MetricsMiddleware)

# Routers
app.include_router(health_router.router)
app.include_router(auth_router.router)
app.include_router(flags_router.router)
app.include_router(segments_router.router)
app.include_router(evaluate_router.router)
app.include_router(audit_router.router)


@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
