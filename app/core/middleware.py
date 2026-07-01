"""
FastAPI 中间件栈

- RequestIDMiddleware: 为每个请求生成唯一 ID，注入 ContextVar 和响应头
- RequestTimingMiddleware: 记录每个 HTTP 请求的耗时
- create_cors_middleware: 从配置生成 CORS 中间件
"""
import time
import uuid
from typing import Callable
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个 HTTP/WebSocket 请求分配唯一 Request ID

    生成 UUID → 存入 ContextVar → 写入 X-Request-ID 响应头
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        from api.context import set_request_context_id, reset_request_context_id

        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = set_request_context_id(request_id)

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            reset_request_context_id(token)
            raise


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """记录每个 HTTP 请求的耗时

    跳过 WebSocket 端点（长连接）
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # WebSocket 升级请求由 lifespan 处理，不在此处计时
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "Request completed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(elapsed_ms, 2),
            },
        )
        response.headers["X-Response-Time"] = f"{elapsed_ms:.1f}ms"
        return response


def create_cors_middleware(allow_origins: list[str] | str = "*") -> CORSMiddleware:
    """创建 CORS 中间件（配置从 settings 读取）

    Args:
        allow_origins: 允许的域名列表，默认为 ["*"]

    Returns:
        已配置的 CORSMiddleware 实例
    """
    if isinstance(allow_origins, str):
        allow_origins = [allow_origins]

    return CORSMiddleware(
        app=None,  # type: ignore — FastAPI add_middleware 会注入
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
