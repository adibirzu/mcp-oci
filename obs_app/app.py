import os
from fastapi import FastAPI, HTTPException
from prometheus_client import make_asgi_app, Counter, Histogram
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from time import perf_counter

app = FastAPI()

# Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

request_counter = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'http_status'])
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration', ['method', 'endpoint'])

# Metrics middleware to record request count and latency
@app.middleware("http")
async def metrics_middleware(request, call_next):
    method = request.method
    endpoint = request.url.path
    start = perf_counter()
    response = await call_next(request)
    duration = perf_counter() - start
    try:
        request_counter.labels(method=method, endpoint=endpoint, http_status=str(response.status_code)).inc()
        request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    except Exception:
        # Prevent metrics errors from affecting request handling
        pass
    return response

# OpenTelemetry setup (consistent with MCP servers)
os.environ.setdefault("OTEL_SERVICE_NAME", "mcp-obs-app")
from mcp_oci_common.observability import init_tracing as _init_tracing, init_metrics as _init_metrics
_init_tracing(service_name=os.getenv("OTEL_SERVICE_NAME", "mcp-obs-app"))
_init_metrics()
if FastAPIInstrumentor:
    try:
        FastAPIInstrumentor.instrument_app(app)
    except Exception:
        try:
            FastAPIInstrumentor().instrument()
        except Exception:
            pass

# Health endpoint
@app.get("/health")
async def health():
    return {"status": "healthy"}

# Dashboard JSON endpoint
@app.get("/dashboard")
async def dashboard():
    # Summarize health of MCP servers (stub for now; implement pings if needed)
    servers = ["compute", "db", "network", "security", "observability", "cost"]
    health_summary = {server: {"status": "up", "last_check": "now"} for server in servers}
    return health_summary

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
