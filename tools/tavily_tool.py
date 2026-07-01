"""Tavily 网络搜索工具 — 1 个 LangChain Tool"""
from typing import Literal
from langchain_core.tools import tool
from tavily import TavilyClient

from app.core import settings, get_logger
from api.monitor import monitor

logger = get_logger(__name__)

# 延迟初始化
_tavily_client: TavilyClient | None = None


def _get_tavily_client() -> TavilyClient:
    """获取 TavilyClient 实例（懒加载）"""
    global _tavily_client
    if _tavily_client is None:
        _tavily_client = TavilyClient(api_key=settings.tavily.api_key)
    return _tavily_client


@tool
def internet_search(
    query: str,
    topic: Literal["news", "finance", "general"] = "general",
    max_results: int = 5,
    include_raw_content: bool = False,
) -> str:
    """
    根据用户问题进行网络信息搜索。仅搜索公开网络信息，
    如果指定查询数据库或 RAGFlow 不能使用此工具。

    Args:
        query: 用户的查询信息
        topic: 查询类型 (news/finance/general)
        max_results: 返回的最大条数
        include_raw_content: 是否返回原始内容 (False=精简, True=详细)

    Returns:
        搜索结果文本
    """
    monitor.report_tool(
        tool_name="网络搜索工具",
        args={
            "query": query,
            "topic": topic,
            "max_results": max_results,
            "include_raw_content": include_raw_content,
        },
    )

    try:
        return str(_get_tavily_client().search(
            query=query,
            topic=topic,
            max_results=max_results,
            include_raw_content=include_raw_content,
        ))
    except Exception as e:
        logger.exception("Tavily search failed for query: %s", query)
        return f"网络搜索失败：{str(e)}"
