"""多格式文件读取工具 — 支持 .md / .docx / .pdf / .xlsx / .txt"""
from pathlib import Path
from typing import Annotated, Optional

from langchain_core.tools import tool

from app.core import get_logger
from api.monitor import monitor
from api.context import get_session_context
from utils.path_utils import resolve_path

logger = get_logger(__name__)

# 按需导入可选依赖
try:
    import docx as _docx
except ImportError:
    _docx = None

try:
    import pypdf as _pypdf
except ImportError:
    _pypdf = None

try:
    import pandas as pd
except ImportError:
    pd = None

_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@tool
def read_file_content(
    filename: Annotated[str, "要读取的文件名或路径（支持 .md, .docx, .pdf, .xlsx, .xls）"],
    instruction: Annotated[str, "对提取内容的具体指令（例如：'提取摘要', '统计数据'）"] = "提取全部内容",
) -> str:
    """
    读取指定文件的内容。支持 Markdown(.md)、Word(.docx)、PDF(.pdf) 和 Excel(.xlsx/.xls)。
    对于 Excel 文件，会自动提供数据统计信息（head 和 describe）。

    Args:
        filename: 文件名或路径
        instruction: 提取指令

    Returns:
        文件文本内容（Excel 返回格式化摘要）
    """
    monitor.report_tool("文件内容读取工具", {"filename": filename, "instruction": instruction})

    # 路径解析
    session_dir = get_session_context()
    file_path = Path(resolve_path(filename, session_dir))

    if not file_path.exists():
        return f"错误：文件 '{filename}' 不存在 (解析路径: {file_path})"

    # 文件大小检查
    try:
        file_size = file_path.stat().st_size
        if file_size > _MAX_FILE_SIZE:
            return (
                f"错误：文件过大 ({file_size / 1024 / 1024:.1f}MB)，"
                f"最大支持 {_MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
            )
    except OSError:
        pass

    ext = file_path.suffix.lower()

    try:
        if ext in ('.md', '.txt'):
            return file_path.read_text(encoding='utf-8')

        elif ext == '.docx':
            if _docx is None:
                return "错误：未安装 'python-docx' 库，无法读取 Word 文件"
            doc = _docx.Document(str(file_path))
            full_text = [para.text for para in doc.paragraphs]
            return '\n'.join(full_text)

        elif ext == '.pdf':
            if _pypdf is None:
                return "错误：未安装 'pypdf' 库，无法读取 PDF 文件"
            reader = _pypdf.PdfReader(str(file_path))
            pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(pages)

        elif ext in ('.xlsx', '.xls'):
            if pd is None:
                return "错误：未安装 'pandas' 库，无法读取 Excel 文件"
            try:
                df = pd.read_excel(str(file_path))
            except Exception:
                logger.exception("Excel read failed: %s", filename)
                return f"读取 Excel 失败: {filename}"

            return "\n".join([
                f"文件: {filename}",
                f"行数: {len(df)}, 列数: {len(df.columns)}",
                f"列名: {', '.join(df.columns.astype(str))}",
                "\n[前5行数据预览]:",
                df.head().to_string(index=False),
                "\n[统计描述]:",
                df.describe().to_string(),
            ])

        else:
            # 尝试作为纯文本读取
            try:
                return file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                return f"错误：不支持的文件格式 '{ext}'，且无法作为文本读取"

    except Exception as e:
        logger.exception("File read failed: %s", filename)
        return f"读取文件出错: {str(e)}"
