from __future__ import annotations

import contextlib

try:
    from opentelemetry import trace as _trace
except Exception:
    class _NoOpSpan:
        def set_attribute(self, *args, **kwargs) -> None:
            pass

        def record_exception(self, *args, **kwargs) -> None:
            pass

        def set_status(self, *args, **kwargs) -> None:
            pass

    class _NoOpTracer:
        def start_span(self, *args, **kwargs):
            return _NoOpSpan()

        def start_as_current_span(self, *args, **kwargs):
            return contextlib.nullcontext(_NoOpSpan())

    class _NoOpTrace:
        def get_tracer(self, *args, **kwargs):
            return _NoOpTracer()

        def get_current_span(self, *args, **kwargs):
            return _NoOpSpan()

    _trace = _NoOpTrace()

trace = _trace
