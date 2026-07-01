"""
应用异常层次结构

所有业务异常继承自 AppException，按领域分层。
Exception 消息用于日志记录，用户面消息由调用方决定。

Usage:
    from app.core.exceptions import ConfigurationError, DatabaseError
    raise ConfigurationError("OPENAI_API_KEY 未设置")
    raise DatabaseError("查询失败", detail="connection timeout", status_code=503)
"""
from typing import Optional


class AppException(Exception):
    """应用根异常"""
    def __init__(
        self,
        message: str,
        detail: Optional[str] = None,
        status_code: int = 500,
    ):
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)


class ConfigurationError(AppException):
    """配置错误 — 启动时抛出，阻止应用运行"""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=500)


class DatabaseError(AppException):
    """数据库错误"""
    def __init__(self, message: str, detail: Optional[str] = None, status_code: int = 500):
        super().__init__(message, detail, status_code)


class ExternalServiceError(AppException):
    """外部服务通用错误"""
    def __init__(self, message: str, detail: Optional[str] = None, status_code: int = 502):
        super().__init__(message, detail, status_code)


class RAGFlowError(ExternalServiceError):
    """RAGFlow 服务错误"""
    pass


class TavilyError(ExternalServiceError):
    """Tavily 搜索服务错误"""
    pass


class FileOperationError(AppException):
    """文件操作错误"""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=500)


class ValidationError(AppException):
    """输入校验错误"""
    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(message, detail, status_code=400)
