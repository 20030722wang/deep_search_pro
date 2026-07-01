"""
集中配置管理 — 基于 Pydantic BaseSettings

取代项目中所有散落的 load_dotenv() + os.getenv() 调用。
.env 文件在 Settings 类实例化时自动加载，仅此一次。

Usage:
    from app.core.config import settings
    print(settings.llm.openai_api_key)       # 获取 LLM API Key
    print(settings.mysql.model_dump())       # 获取 MySQL 配置字典
"""
from pathlib import Path
from typing import Optional, List
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# ============================================================
# 领域配置模型
# ============================================================

class LLMSettings(BaseSettings):
    """大模型服务配置 (OpenAI 兼容接口)"""
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="LLM API 地址"
    )
    openai_api_key: str = Field(
        default="",
        min_length=1,
        description="LLM API 密钥"
    )
    model_name: str = Field(
        default="qwen-max",
        alias="LLM_QWEN_MAX",
        description="模型名称 (兼容阿里云百炼)"
    )

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def check_api_key(cls, v: str) -> str:
        if not v or v.startswith("sk-your-") or v == "your-api-key-here":
            raise ValueError("OPENAI_API_KEY 未配置或将占位值替换为真实 Key")
        return v


class RAGFlowSettings(BaseSettings):
    """RAGFlow 知识库服务配置"""
    api_url: str = Field(
        default="http://localhost:9380",
        alias="RAGFLOW_API_URL",
        description="RAGFlow 服务地址"
    )
    api_key: str = Field(
        default="",
        alias="RAGFLOW_API_KEY",
        description="RAGFlow API 密钥"
    )
    request_timeout: int = Field(
        default=30,
        description="请求超时 (秒)"
    )


class TavilySettings(BaseSettings):
    """Tavily 网络搜索配置"""
    api_key: str = Field(
        default="",
        alias="TAVILY_API_KEY",
        description="Tavily API 密钥"
    )
    request_timeout: int = Field(
        default=30,
        description="请求超时 (秒)"
    )


class MySQLSettings(BaseSettings):
    """MySQL 数据库连接配置"""
    host: str = Field(default="localhost", alias="MYSQL_HOST")
    port: int = Field(default=3306, alias="MYSQL_PORT")
    user: str = Field(default="root", alias="MYSQL_USER")
    password: str = Field(default="", alias="MYSQL_PASSWORD")
    database: str = Field(default="", alias="MYSQL_DATABASE")
    charset: str = Field(default="utf8mb4", alias="MYSQL_CHARSET")
    collation: str = Field(default="utf8mb4_unicode_ci", alias="MYSQL_COLLATION")
    sql_mode: str = Field(default="TRADITIONAL", alias="MYSQL_SQL_MODE")
    connect_timeout: int = Field(default=10, description="连接超时 (秒)")
    autocommit: bool = Field(default=True)

    def to_conn_dict(self) -> dict:
        """返回 mysql.connector.connect() 所需的参数字典"""
        return {
            "host": self.host,
            "port": self.port,
            "user": self.user,
            "password": self.password,
            "database": self.database,
            "charset": self.charset,
            "collation": self.collation,
            "autocommit": self.autocommit,
            "sql_mode": self.sql_mode,
            "connection_timeout": self.connect_timeout,
        }


class AppSettings(BaseSettings):
    """应用基础配置"""
    name: str = Field(default="智析协同助手")
    version: str = Field(default="2.0.0")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    cors_origins: List[str] = Field(
        default=["*"],
        description="CORS 允许的域名列表"
    )
    project_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[2],
        description="项目根目录绝对路径"
    )


# ============================================================
# 全局配置单例
# ============================================================

class Settings(BaseSettings):
    """全局配置聚合根"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app: AppSettings = Field(default_factory=AppSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    ragflow: RAGFlowSettings = Field(default_factory=RAGFlowSettings)
    tavily: TavilySettings = Field(default_factory=TavilySettings)
    mysql: MySQLSettings = Field(default_factory=MySQLSettings)

    @model_validator(mode="after")
    def validate_critical_config(self):
        """启动时集中校验，输出所有缺失配置"""
        errors: list[str] = []

        if not self.llm.openai_api_key:
            errors.append("OPENAI_API_KEY: 未配置")

        # 可选服务仅警告
        missing_optional: list[str] = []
        if not self.ragflow.api_key:
            missing_optional.append("RAGFLOW_API_KEY (知识库功能不可用)")
        if not self.tavily.api_key:
            missing_optional.append("TAVILY_API_KEY (网络搜索功能不可用)")
        if not self.mysql.password or not self.mysql.database:
            missing_optional.append("MySQL 配置不完整 (数据库查询功能不可用)")

        if errors:
            raise ValueError(
                "缺少必填配置:\n  " + "\n  ".join(errors)
            )

        if missing_optional:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning("可选服务未配置:\n  %s", "\n  ".join(missing_optional))

        return self


# 全局单例 — 导入此模块时自动加载 .env 并校验
settings = Settings()
