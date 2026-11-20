"""Request id and timing middleware. Uses the caller's X-Request-ID when it is a safe value,
otherwise makes one; returns it in the response header and writes one JSON log line per request.
"""

import logging
import re
import time
import uuid

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from returnright.core.constants import REQUEST_ID_HEADER
from returnright.core.logging import request_id_var

logger = logging.getLogger("returnright.request")

SAFE_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


def _request_id(scope: Scope) -> str:
    header = REQUEST_ID_HEADER.lower().encode()
    for name, value in scope["headers"]:
        if name == header:
            candidate = value.decode("latin-1")
            if SAFE_REQUEST_ID.fullmatch(candidate):
                return candidate
    return uuid.uuid4().hex


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        request_id = _request_id(scope)
        token = request_id_var.set(request_id)
        # The 500 handler runs outside this middleware, after the context variable is reset.
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status_code = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self._app(scope, receive, send_with_id)
        finally:
            logger.info(
                "request",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
            request_id_var.reset(token)
