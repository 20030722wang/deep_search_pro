"""
主智能体 (Team Leader) — 任务拆解、并行调度与结果汇总

基于 LangGraph + DeepAgents，协调三个专家子智能体：
- 数据库查询助手 (MySQL)
- RAGFlow 知识库助手 (私有文档)
- 网络搜索助手 (Tavily)

使用懒加载避免 import 时 LLM 连接阻塞，首次调用 run_deep_agent 时创建实例。
"""
import asyncio
import shutil
from pathlib import Path

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import AIMessage

from agent.subagents.knowledge_base_agent import knowledge_base_agent
from agent.subagents.database_query_agent import database_query_agent
from agent.subagents.network_search_agent import network_search_agent
from agent.llm import model
from agent.prompts import main_agent_content

from tools.markdown_tools import generate_markdown
from tools.pdf_tools import convert_md_to_pdf
from tools.upload_file_read_tool import read_file_content

from api.context import (
    set_session_context, reset_session_context, set_thread_context,
)
from api.monitor import monitor

from app.core import get_logger, AgentRole, ToolName

logger = get_logger(__name__)

# ============================================================
# 主智能体懒加载
# ============================================================
_main_agent = None


def _get_main_agent():
    """获取主智能体实例（首次调用时创建，避免 import 阻塞）"""
    global _main_agent
    if _main_agent is None:
        _main_agent = create_deep_agent(
            model=model,
            system_prompt=main_agent_content['system_prompt'],
            tools=[generate_markdown, convert_md_to_pdf, read_file_content],
            checkpointer=InMemorySaver(),
            subagents=[
                database_query_agent,
                network_search_agent,
                knowledge_base_agent,
            ],
        )
    return _main_agent


# ============================================================
# 路径常量
# ============================================================
_project_root = Path(__file__).parents[1].resolve()


# ============================================================
# 主执行函数
# ============================================================

async def run_deep_agent(task_query: str, session_id: str) -> None:
    """流式异步执行主智能体，通过 WebSocket 实时推送进度。

    Args:
        task_query: 用户提问的完整问题文本
        session_id: 前端会话唯一标识（UUID）

    Raises:
        异常通过 WebSocket error 事件推送，不向调用方传播。
    """
    main_agent = _get_main_agent()
    logger.info("Agent execution started", extra={"session_id": session_id})

    # ---------- 工作目录准备 ----------
    session_dir = _project_root / "output" / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_dir_str = str(session_dir).replace("\\", "/")
    relative_session_dir_str = (
        str(session_dir.relative_to(_project_root)).replace("\\", "/")
    )

    # ---------- 上传文件处理 ----------
    updated_dir_path = _project_root / "updated" / f"session_{session_id}"
    updated_info_prompt = ""
    if updated_dir_path.exists():
        files = [f.name for f in updated_dir_path.iterdir() if f.is_file()]
        if files:
            for filename in files:
                shutil.copy2(updated_dir_path / filename, session_dir / filename)
            updated_info_prompt = (
                f"\n    [已上传文件] 已加载到工作目录:\n"
                + "\n".join([f"    - {f}" for f in files])
                + "\n    请优先使用工具（read_file_content）读取并参考这些文件。"
            )

    # ---------- 上下文绑定 ----------
    session_dir_token = set_session_context(session_dir_str)
    session_id_token = set_thread_context(session_id)
    monitor.report_session_dir(session_dir_str)

    # ---------- 路径指引提示词 ----------
    path_instruction = f"""
    【工作环境指令】
    工作目录: {relative_session_dir_str}
    {updated_info_prompt}

    规则：
    1. 新生成文件必须保存到工作目录：'{relative_session_dir_str}/filename'
    2. 读取已上传的文件时，直接使用文件名作为 filename 参数传入 read_file_content 工具，不带目录前缀
    3. 使用相对路径，禁止使用绝对路径
    4. 若存在上传文件，请先分析内容
    """

    # ---------- 流式执行 ----------
    config = {"configurable": {"thread_id": session_id}}

    try:
        async for chunk in main_agent.astream({
            "messages": [{
                "role": "user",
                "content": task_query + "\n" + path_instruction,
            }]
        }, config=config):
            for node_name, state in chunk.items():
                if not state or "messages" not in state:
                    continue
                messages = state["messages"]
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    if node_name == AgentRole.MODEL:
                        if last_msg.tool_calls:
                            for tool_call in last_msg.tool_calls:
                                if tool_call.name == ToolName.TASK:
                                    monitor.report_assistant(
                                        tool_call.args['subagent_type'],
                                        {'description': tool_call.args['description']},
                                    )
                        elif last_msg.content:
                            logger.debug(
                                "Agent result preview: %s",
                                last_msg.content[:100],
                            )
                            monitor.report_task_result(last_msg.content)

    except Exception:
        logger.exception("Agent execution failed")
        monitor._emit("error", "执行主智能体发生异常，请查看服务端日志")
    finally:
        reset_session_context(session_dir_token, session_id_token)
