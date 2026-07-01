"""
应用生命周期管理

- 启动时：配置日志 → 校验配置 → 绑定 WebSocket 事件循环
- 关闭时：断开 WebSocket 连接 → 清理资源
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import ConfigurationError

logger = get_logger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """FastAPI 生命周期管理器"""

    # ========== 启动阶段 ==========
    setup_logging(
        log_level=settings.app.log_level,
        json_format=not settings.app.debug,
    )

    logger.info(
        "Application starting",
        extra={
            "app_name": settings.app.name,
            "version": settings.app.version,
            "host": settings.app.host,
            "port": settings.app.port,
        },
    )

    # 校验必填配置
    try:
        SettingsClass = settings.__class__
        SettingsClass.validate_critical_config(settings)
    except ValueError as e:
        logger.critical("Configuration validation failed: %s", e)
        raise ConfigurationError(str(e))

    # 绑定 WebSocket 事件循环
    from api.monitor import manager
    loop = asyncio.get_running_loop()
    manager.set_loop(loop)
    logger.info("WebSocket Manager bound to event loop")

    logger.info("Application started successfully")
    yield

    # ========== 关闭阶段 ==========
    logger.info("Application shutting down...")

    # 给正在执行的任务一个宽限期
    await asyncio.sleep(2)

    # 清理 WebSocket 连接
    for thread_id in list(manager.active_connections.keys()):
        try:
            manager.disconnect(manager.active_connections[thread_id], thread_id)
        except Exception:
            pass

    logger.info("Application shut down complete")
