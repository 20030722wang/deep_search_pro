from agent.subagents.knowledge_base_agent import knowledge_base_agent
from agent.subagents.database_query_agent import database_query_agent
from agent.subagents.network_search_agent import network_search_agent
from langgraph.checkpoint.memory import InMemorySaver

# main_agent tool导入
from tools.markdown_tools import generate_markdown
from tools.pdf_tools import convert_md_to_pdf
from tools.upload_file_read_tool import read_file_content

from deepagents import create_deep_agent

from agent.llm import model
from agent.prompts import main_agent_content

from api.monitor import monitor
import asyncio
import uuid
import shutil
from pathlib import Path

from api.context import set_session_context, reset_session_context, set_thread_context

from langchain_core.messages import AIMessage


# 延迟初始化：避免 import 时因 LLM 连接失败导致服务无法启动
_main_agent = None


def _get_main_agent():
    """获取主智能体实例（懒加载，首次调用时创建）"""
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
                knowledge_base_agent
            ]
        )
    return _main_agent


project_root_path = Path(__file__).parents[1].resolve()


async def run_deep_agent(task_query, session_id):
    """
    流式+异步执行主智能体
    执行过程中通过 WebSocket 向客户端推送：子智能体调用、任务结果、文件地址

    task_query: 前端提问的问题
    session_id: 每个前端会话对应的唯一标识
    """
    main_agent = _get_main_agent()

    print(f"当前会话的main_agent开始执行了！ 会话id:{session_id}")

    # 准备工作：创建会话专属输出目录
    session_dir = project_root_path / "output" / f"session_{session_id}"
    session_dir.mkdir(parents=True, exist_ok=True)
    session_dir_str = str(session_dir).replace("\\", "/")
    relative_session_dir_str = str(session_dir.relative_to(project_root_path)).replace("\\", "/")

    # 处理上传文件
    updated_dir_path = project_root_path / "updated" / f"session_{session_id}"
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

    # 存储会话上下文（供工具函数和 WebSocket 推送使用）
    session_dir_token = set_session_context(session_dir_str)
    session_id_token = set_thread_context(session_id)

    monitor.report_session_dir(session_dir_str)

    config = {
        "configurable": {
            "thread_id": session_id
        }
    }

    path_instruction = f"""
    【工作环境指令】
    工作目录: {relative_session_dir_str}
    {updated_info_prompt}

    规则：
    1. 新生成文件必须保存到工作目录：'{relative_session_dir_str}/filename'
    2. 读取已上传的文件时，请直接将文件名（例如：'开篇.txt'）作为 filename 参数传入（read_file_content）读取工具，不要带上任何目录前缀。
    3. 使用相对路径，禁止使用绝对路径
    4. 若存在上传文件，请先分析内容
    """

    try:
        async for chunk in main_agent.astream({
            "messages": [
                {
                    "role": "user",
                    "content": task_query + "\n" + path_instruction
                }
            ]
        }, config=config):
            for node_name, state in chunk.items():
                if not state or "messages" not in state:
                    continue
                messages = state["messages"]
                if messages and isinstance(messages, list):
                    last_msg = messages[-1]
                    if node_name == 'model':
                        if last_msg.tool_calls:
                            for tool_call in last_msg.tool_calls:
                                if tool_call.name == 'task':
                                    monitor.report_assistant(
                                        tool_call.args['subagent_type'],
                                        {'description': tool_call.args['description']}
                                    )
                        elif last_msg.content:
                            print(f"主智能体执行结果，最终结果：{last_msg.content[:100]}")
                            monitor.report_task_result(last_msg.content)

    except Exception as e:
        monitor._emit("error", f"执行主智能体发生异常：{str(e)}")
    finally:
        reset_session_context(session_dir_token, session_id_token)
