import time
from fastapi import FastAPI, Request
from prometheus_client import Counter, Histogram, Gauge, REGISTRY
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import structlog

logger = structlog.get_logger("app.observability")

# Custom Prometheus Metrics
TENDER_PROCESSING_TIME = Histogram(
    "tender_processing_duration_seconds",
    "Time taken to fully process, parse, and ingest a tender",
    labelnames=["status"],
    registry=REGISTRY
)

DOWNLOAD_FAILURES = Counter(
    "tender_download_failures_total",
    "Total number of tender document download failures",
    labelnames=["error_class", "host_domain"],
    registry=REGISTRY
)

EXTRACTION_ACCURACY = Gauge(
    "tender_extraction_accuracy_ratio",
    "Confidence ratio of extracted fields",
    labelnames=["field_name", "tender_id"],
    registry=REGISTRY
)

RECOMMENDATION_LATENCY = Histogram(
    "recommendation_latency_seconds",
    "Time taken to compute bid recommendation verdict",
    labelnames=["verdict"],
    registry=REGISTRY
)

QDRANT_SEARCH_TIME = Histogram(
    "qdrant_search_duration_seconds",
    "Duration of semantic vector searches in Qdrant",
    labelnames=["collection"],
    registry=REGISTRY
)

GEMINI_RESPONSE_TIME = Histogram(
    "gemini_response_duration_seconds",
    "FastAPI integration call duration for Gemini LLM completions",
    labelnames=["prompt_type"],
    registry=REGISTRY
)


def setup_observability(app: FastAPI):
    from app.core.config import settings

    # 1. Initialize Sentry if configured
    if settings.SENTRY_DSN:
        try:
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                integrations=[FastApiIntegration()],
                traces_sample_rate=1.0,
                environment=settings.ENV
            )
            logger.info("Sentry SDK integration initialized successfully")
        except Exception as e:
            logger.warn("Sentry initialization failed, running without Sentry", error=str(e))

    # 2. Setup OpenTelemetry
    try:
        provider = TracerProvider()
        processor = BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.OTLP_ENDPOINT)
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        
        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
        logger.info("OpenTelemetry FastAPI Instrumentation active", endpoint=settings.OTLP_ENDPOINT)
    except Exception as e:
        logger.warn("OpenTelemetry SDK initialization failed, running without distributed tracing", error=str(e))

    # 3. Add Custom Latency Request Middleware for general requests metric logging
    @app.middleware("http")
    async def log_request_metrics(request: Request, call_next):
        start_time = time.time()
        
        # Inject Trace ID into structlog context if present
        current_span = trace.get_current_span()
        trace_id = "UNKNOWN"
        if current_span and current_span.get_span_context().is_valid:
            trace_id = format(current_span.get_span_context().trace_id, "032x")
            structlog.contextvars.bind_contextvars(trace_id=trace_id)

        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        response.headers["X-Trace-ID"] = trace_id
        
        return response
