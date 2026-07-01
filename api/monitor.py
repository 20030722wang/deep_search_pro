"""
工具调用监控与 WebSocket 消息推送

ToolMonitor: 在工具执行过程中上报进度和状态的单例
ConnectionManager: WebSocket 连接管理器，支持会话级消息隔离
"""
import datetime
import asyncio
import threading
from typing import Any, Dict, Optional

from fastapi import WebSocket

from app.core import get_logger, EventType, MessageType
from api.context import get_thread_context

logger = get_logger(__name__)


# ============================================================
# ToolMonitor — 单例工具监控
# ============================================================

class ToolMonitor:
    """工具监控 — 上报工具执行进度和状态到前端。

    使用示例:
        from api.monitor import monitor
        monitor.report_tool("my_tool", {"arg1": val1})
    """

    _instance: Optional["ToolMonitor"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "ToolMonitor":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.websocket_manager = None
        return cls._instance

    def set_websocket_manager(self, manager: "ConnectionManager") -> None:
        """设置 WebSocket 管理器"""
        self.websocket_manager = manager

    def _emit(
        self,
        event_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """内部发送方法 — 构建消息体并推送到前端"""
        payload = {
            "type": MessageType.MONITOR_EVENT,
            "event": event_type,
            "message": message,
            "data": data or {},
            "timestamp": datetime.datetime.now().isoformat(),
        }

        # 优先通过 WebSocket 定向推送
        if self.websocket_manager:
            try:
                thread_id = get_thread_context()
                manager_loop = self.websocket_manager.loop
                if not manager_loop:
                    return

                if thread_id:
                    try:
                        current_loop = asyncio.get_running_loop()
                    except RuntimeError:
                        current_loop = None

                    if current_loop and current_loop == manager_loop:
                        current_loop.create_task(
                            self.websocket_manager.send_to_thread(payload, thread_id)
                        )
                    else:
                        asyncio.run_coroutine_threadsafe(
                            self.websocket_manager.send_to_thread(payload, thread_id),
                            manager_loop,
                        )
            except Exception:
                logger.warning("WebSocket send failed", exc_info=True)

        # 控制台保底输出
        logger.debug("Monitor event: %s — %s", event_type, message)

    # ---- 公共上报方法 ----

    def report_tool(
        self, tool_name: str, args: Optional[Dict[str, Any]] = None
    ) -> None:
        """报告工具开始执行"""
        self._emit(
            EventType.TOOL_START,
            f"开始执行工具: {tool_name}",
            {"tool_name": tool_name, "args": args},
        )

    def report_assistant(
        self, assistant_name: str, args: Optional[Dict[str, Any]] = None
    ) -> None:
        """报告子智能体调用进度"""
        self._emit(
            EventType.ASSISTANT_CALL,
            f"正在调用助手: {assistant_name}",
            {"assistant_name": assistant_name, "args": args},
        )

    def report_task_result(self, result: str) -> None:
        """报告任务最终结果"""
        self._emit(EventType.TASK_RESULT, "任务执行完成", {"result": result})

    def report_session_dir(self, path: str) -> None:
        """报告任务工作目录"""
        self._emit(
            EventType.SESSION_CREATED,
            f"工作目录已创建: {path}",
            {"path": path},
        )


# 全局单例
monitor = ToolMonitor()


# ============================================================
# ConnectionManager — WebSocket 连接管理
# ============================================================

class ConnectionManager:
    """WebSocket 连接管理器 — 支持会话级消息隔离"""

    def __init__(self) -> None:
        self.active_connections: Dict[str, WebSocket] = {}
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """显式设置事件循环"""
        self.loop = loop
        monitor.set_websocket_manager(self)
        logger.info("ConnectionManager bound to event loop")

    async def connect(self, websocket: WebSocket, thread_id: str) -> None:
        """接受 WebSocket 连接并注册"""
        await websocket.accept()
        self.active_connections[thread_id] = websocket
        logger.info("WebSocket client connected", extra={"thread_id": thread_id})

    def disconnect(self, websocket: WebSocket, thread_id: str) -> None:
        """移除 WebSocket 连接"""
        if thread_id in self.active_connections:
            del self.active_connections[thread_id]
        logger.info("WebSocket client disconnected", extra={"thread_id": thread_id})

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """发送文本消息到指定连接"""
        await websocket.send_text(message)

    async def send_to_thread(self, message: dict, thread_id: str) -> None:
        """发送 JSON 消息到指定会话"""
        if thread_id in self.active_connections:
            websocket = self.active_connections[thread_id]
            await websocket.send_json(message)


manager = ConnectionManager()
