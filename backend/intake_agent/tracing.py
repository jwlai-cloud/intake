"""Export ADK's spans to Cloud Trace.

ADK already instruments itself with OpenTelemetry — `google.adk.telemetry`
emits a span per LLM call. Nothing collects them by default, so they go
nowhere. Twenty lines of exporter turns that into a waterfall in the Google
Cloud console: one trace per turn, with `transcriber`, `route`, the fanned-out
`adjudicate` calls side by side, and `coach`.

Two reasons that is worth having:

- **Operationally**, it is the only view that shows *where* a slow turn went.
  A chunk takes 12-21s and the split between transcription and adjudication is
  otherwise invisible.
- **As evidence**, it shows the ADK pipeline running on Google Cloud, per call,
  with real timings — which is a stronger claim than a request-count graph.

**Not working yet, and off by default.** With `INTAKE_TRACING=1` the provider
installs cleanly and `force_flush` returns, but no span has ever appeared in
Cloud Trace — not from the deployed service, and not from a local probe span
created and flushed by hand with credentials that have `roles/editor`. The
export is failing silently somewhere inside the gRPC exporter.

It stays off until a span is actually observed arriving. A `/health` field
reporting `tracing: true` while nothing is exported is precisely the kind of
flag that lies, and this codebase has already been bitten twice by exactly that
shape of bug — an overlay that never installed, and a gate that failed open.

The Cloud Run logs carry the same evidence today and are verified: they name the
ADK stage, the model, the number of parallel Gemini calls and the timings.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


def setup() -> bool:
    """Wire ADK's spans to Cloud Trace. False if tracing is off or unavailable."""
    if os.environ.get("INTAKE_TRACING") != "1":
        return False

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        log.warning("INTAKE_TRACING=1 but GOOGLE_CLOUD_PROJECT is unset")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as exc:
        # Tracing is a nicety. A missing extra must not stop the service.
        log.warning("tracing requested but not installed (%s)", exc)
        return False

    provider = TracerProvider(
        resource=Resource.create({"service.name": "intake-agent"}))
    provider.add_span_processor(
        BatchSpanProcessor(CloudTraceSpanExporter(project_id=project)))
    trace.set_tracer_provider(provider)

    # Cloud Run stops an idle instance without warning; an unflushed batch is a
    # lost trace, and the last turn is usually the interesting one.
    import atexit
    atexit.register(provider.shutdown)

    log.info("Cloud Trace enabled for project %s", project)
    return True
