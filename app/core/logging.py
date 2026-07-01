"""
结构化日志配置

- 开发模式：彩色 Console 输出
- 生产模式 (DEBUG=false)：JSON 行格式，便于日志采集

Usage:
    from app.core.logging import setup_logging, get_logger
    setup_logging()
    logger = get_logger(__name__)
    logger.info("服务启动", extra={"request_id": "abc123"})
"""
import logging
import logging.config
import sys
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

# ContextVar 引用 — 由 api/context.py 提供
try:
    from api.context import get_request_context_id
except ImportError:
    get_request_context_id = lambda: None  # type: ignore


# ============================================================
# JSON 格式化器 (生产模式)
# ============================================================

class JsonFormatter(logging.Formatter):
    """输出 JSON 行格式日志"""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # 注入 request_id
        try:
            request_id = get_request_context_id()
            if request_id:
                log_entry["request_id"] = request_id
        except Exception:
            pass

        # 注入额外字段
        if hasattr(record, "request_id") and record.request_id:  # type: ignore
            log_entry["request_id"] = record.request_id  # type: ignore

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


# ============================================================
# 彩色 Console 格式化器 (开发模式)
# ============================================================

class ColorFormatter(logging.Formatter):
    """带颜色的控制台日志"""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    GREY = "\033[90m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.RESET)
        request_id = ""
        try:
            rid = get_request_context_id()
            if rid:
                request_id = f" {self.GREY}[{rid[:8]}]"
        except Exception:
            pass

        return (
            f"{self.GREY}{datetime.now().strftime('%H:%M:%S')}{self.RESET} "
            f"{color}{record.levelname:<7}{self.RESET} "
            f"{record.name}{request_id} "
            f"{record.getMessage()}"
        )


# ============================================================
# 初始化函数
# ============================================================

_logging_initialized = False


def setup_logging(log_level: str = "INFO", json_format: bool = False) -> None:
    """配置全局日志系统（幂等操作，仅首次调用生效）"""
    global _logging_initialized
    if _logging_initialized:
        return

    formatter = JsonFormatter() if json_format else ColorFormatter()

    # 根日志
    root_handler = logging.StreamHandler(sys.stdout)
    root_handler.setFormatter(formatter)
    root_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    root_logger.handlers.clear()
    root_logger.addHandler(root_handler)

    # 降低第三方库日志噪音
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _logging_initialized = True


def get_logger(name: str) -> logging.Logger:
    """获取 Logger 实例"""
    return logging.getLogger(name)
