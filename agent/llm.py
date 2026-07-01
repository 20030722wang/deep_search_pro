"""LLM 模型初始化 — 通过集中配置获取连接参数"""
from langchain.chat_models import init_chat_model
from app.core import settings

model = init_chat_model(
    model=settings.llm.model_name,
    model_provider="openai",
    openai_api_key=settings.llm.openai_api_key,
    openai_api_base=settings.llm.openai_base_url,
)
