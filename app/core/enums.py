"""
项目全局枚举

消除魔术字符串 — 所有事件类型、消息类型、智能体角色均从此处引用。

Usage:
    from app.core.enums import EventType, AgentRole
    if event == EventType.TOOL_START: ...
"""
from enum import StrEnum


class EventType(StrEnum):
    """WebSocket / Monitor 事件类型"""
    TOOL_START = "tool_start"
    ASSISTANT_CALL = "assistant_call"
    TASK_RESULT = "task_result"
    SESSION_CREATED = "session_created"
    ERROR = "error"
    PONG = "pong"


class MessageType(StrEnum):
    """WebSocket 消息类型"""
    MONITOR_EVENT = "monitor_event"


class AgentRole(StrEnum):
    """LangGraph 节点名称"""
    MODEL = "model"
    TOOLS = "tools"


class ToolName(StrEnum):
    """DeepAgents 框架保留工具名"""
    TASK = "task"
