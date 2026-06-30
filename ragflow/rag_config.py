import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Tuple, Optional

def _load_ragflow_env() -> Tuple[Optional[str], Optional[str]]:
    """
    加载 RAGFlow 环境变量（从项目根目录 .env 加载）
    返回值：(api_key, base_url) → 缺失则返回 None
    """
    # 从当前文件向上查找项目根目录的 .env
    current_dir = Path(__file__).resolve().parent  # ragflow/
    project_root = current_dir.parent              # 项目根目录
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()  # 回退：从当前工作目录或系统环境变量加载

    api_key = os.getenv("RAGFLOW_API_KEY")
    base_url = os.getenv("RAGFLOW_API_URL")
    return api_key, base_url