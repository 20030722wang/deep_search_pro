"""RAGFlow 环境配置 — 兼容旧版调用方的薄包装

新版代码应直接从 app.core.config import settings 获取配置。
此模块保留供 demo 文件及其他旧引用使用。
"""
from app.core import settings


def _load_ragflow_env() -> tuple[str, str]:
    """获取 RAGFlow API 配置（兼容旧接口）

    Returns:
        (api_key, base_url) 元组
    """
    return settings.ragflow.api_key, settings.ragflow.api_url
