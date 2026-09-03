from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import uuid
from contextvars import ContextVar
from typing import Optional

_request_id_ctx_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

def get_request_id() -> Optional[str]:
    return _request_id_ctx_var.get()

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = _request_id_ctx_var.set(req_id)
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        
        _request_id_ctx_var.reset(token)
        return response
