"""
Prometheus metrics for monitoring
"""
from prometheus_client import Counter, Gauge, Histogram, generate_latest, REGISTRY
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

# Counters
INGEST_COUNT = Counter('ingest_documents_total', 'Total documents ingested')
INGEST_PAGES = Counter('ingest_pages_total', 'Total pages ingested')
EXTRACT_COUNT = Counter('extract_requests_total', 'Total extraction requests')
ASK_COUNT = Counter('ask_requests_total', 'Total ask/QA requests')
AUDIT_COUNT = Counter('audit_requests_total', 'Total audit requests')
CHUNK_COUNT = Counter('chunks_created_total', 'Total chunks created')

# Gauges
ACTIVE_REQUESTS = Gauge('active_requests', 'Number of active requests')

# Histograms
REQUEST_DURATION = Histogram(
    'request_duration_seconds',
    'Request duration in seconds',
    ['method', 'endpoint', 'status']
)

LLM_CALLS = Counter(
    'llm_calls_total',
    'Total LLM API calls',
    ['status']  # success/failure
)

# Registry
metrics_registry = REGISTRY


def get_metrics_text() -> str:
    """Get metrics in Prometheus text format"""
    return generate_latest(metrics_registry).decode('utf-8')


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to track request metrics"""
    
    async def dispatch(self, request: Request, call_next):
        # Skip metrics endpoint itself
        if request.url.path == "/metrics":
            return await call_next(request)
        
        # Track active requests
        ACTIVE_REQUESTS.inc()
        
        # Track duration
        start_time = time.time()
        
        try:
            response = await call_next(request)
            
            # Record duration
            duration = time.time() - start_time
            REQUEST_DURATION.labels(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code
            ).observe(duration)
            
            return response
            
        finally:
            ACTIVE_REQUESTS.dec()
            
# Webhook metrics
WEBHOOK_CALLS = Counter(
    'webhook_calls_total',
    'Total webhook calls emitted',
    ['event_type']
)