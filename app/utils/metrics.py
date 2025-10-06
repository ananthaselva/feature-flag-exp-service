from prometheus_client import Counter
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# Prometheus HTTP request counter with tenant/request context
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["path", "method", "status", "tenant", "request_id"],
)

class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track HTTP requests and attach tenant/request_id labels."""
    async def dispatch(self, request: Request, call_next):
        tenant = request.headers.get("X-Tenant-ID", "unknown")
        request_id = request.headers.get("X-Request-ID", "none")
        response = None
        try:
            response = await call_next(request)
            return response
        finally:
            status = getattr(response, "status_code", 500)
            REQUEST_COUNT.labels(
                path=request.url.path,
                method=request.method,
                status=status,
                tenant=tenant,
                request_id=request_id,
            ).inc()
