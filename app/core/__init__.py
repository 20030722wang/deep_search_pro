"""
app.core — 基础设施层

提供集中配置、结构化日志、异常层次、枚举、中间件和生命周期管理。
"""
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import (
    AppException,
    ConfigurationError,
    DatabaseError,
    ExternalServiceError,
    RAGFlowError,
    TavilyError,
    FileOperationError,
    ValidationError,
)
from app.core.enums import EventType, MessageType, AgentRole, ToolName
from app.core.middleware import (
    RequestIDMiddleware,
    RequestTimingMiddleware,
    create_cors_middleware,
)
from app.core.lifespan import app_lifespan

__all__ = [
    "settings",
    "setup_logging",
    "get_logger",
    "AppException",
    "ConfigurationError",
    "DatabaseError",
    "ExternalServiceError",
    "RAGFlowError",
    "TavilyError",
    "FileOperationError",
    "ValidationError",
    "EventType",
    "MessageType",
    "AgentRole",
    "ToolName",
    "RequestIDMiddleware",
    "RequestTimingMiddleware",
    "create_cors_middleware",
    "app_lifespan",
]
