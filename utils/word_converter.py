"""
Markdown → PDF 转换模块

支持两种后端：
1. Word COM (Windows) — 需要安装 Microsoft Word + pywin32
2. WeasyPrint (跨平台) — Docker / Linux 环境默认方案
"""
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------- 按需导入 ----------

# Word COM 后端 (仅 Windows)
try:
    import markdown
    import win32com.client
    import pythoncom
    _WORD_AVAILABLE = True
except ImportError:
    _WORD_AVAILABLE = False

# WeasyPrint 后端 (跨平台)
try:
    import weasyprint
    _WEASYPRINT_AVAILABLE = True
except ImportError:
    _WEASYPRINT_AVAILABLE = False

# markdown 库 (HTML 转换共用)
try:
    import markdown as _md
    _MD_AVAILABLE = True
except ImportError:
    _MD_AVAILABLE = False


def _md_to_html(md_abs_path: Path) -> str:
    """将 Markdown 文件转为完整 HTML 字符串"""
    with open(md_abs_path, 'r', encoding='utf-8') as f:
        md_content = f.read()

    html_body = _md.markdown(md_content, extensions=['tables', 'fenced_code'])
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: "Microsoft YaHei", "SimHei", "Noto Sans SC", sans-serif;
               margin: 20px; line-height: 1.6; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #333; padding: 8px; text-align: left; }}
        th {{ background-color: #f0f0f0; }}
        pre {{ background-color: #f5f5f5; padding: 12px; border-radius: 4px;
              overflow-x: auto; }}
        code {{ font-family: "Consolas", "Monaco", "Courier New", monospace; }}
        h1, h2, h3 {{ color: #1a1a1a; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 10px 0; padding: 5px 15px;
                      color: #555; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""


def _convert_via_word(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """通过 Word COM 转换 (Windows only)"""
    temp_html_path = md_abs_path.with_suffix('.temp.html')
    word_app = None

    try:
        html_content = _md_to_html(md_abs_path)
        temp_html_path.write_text(html_content, encoding='utf-8')

        pythoncom.CoInitialize()
        word_app = win32com.client.Dispatch('Word.Application')
        word_app.Visible = False
        word_app.DisplayAlerts = False

        doc = word_app.Documents.Open(str(temp_html_path.resolve()))
        doc.SaveAs(str(pdf_abs_path.resolve()), FileFormat=17)  # wdFormatPDF
        doc.Close(SaveChanges=0)

        if pdf_abs_path.exists():
            return f"成功转换: {pdf_abs_path} (Word引擎)"
        else:
            return f"转换完成但未生成文件: {pdf_abs_path}"

    except Exception as e:
        logger.error("Word转换PDF失败: %s", e, exc_info=True)
        return f"转换失败: {str(e)}"

    finally:
        if word_app:
            try:
                word_app.Quit()
            except Exception:
                pass
        if temp_html_path.exists():
            try:
                temp_html_path.unlink()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def _convert_via_weasyprint(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """通过 WeasyPrint 转换 (跨平台)"""
    try:
        html_content = _md_to_html(md_abs_path)
        weasyprint.HTML(string=html_content).write_pdf(str(pdf_abs_path))

        if pdf_abs_path.exists():
            return f"成功转换: {pdf_abs_path} (WeasyPrint引擎)"
        else:
            return f"转换完成但未生成文件: {pdf_abs_path}"

    except Exception as e:
        logger.error("WeasyPrint转换PDF失败: %s", e, exc_info=True)
        return f"转换失败: {str(e)}"


def convert_md_to_pdf_via_word(md_abs_path: Path, pdf_abs_path: Path) -> str:
    """
    将 Markdown 文件转换为 PDF（自动选择可用后端）。

    优先级：WeasyPrint (跨平台) > Word COM (Windows only)
    """
    if not _MD_AVAILABLE:
        return "错误：缺少 markdown 库，请安装: pip install markdown"

    # 优先使用 WeasyPrint（跨平台，Docker 友好）
    if _WEASYPRINT_AVAILABLE:
        return _convert_via_weasyprint(md_abs_path, pdf_abs_path)

    # 回退到 Word COM（仅 Windows）
    if _WORD_AVAILABLE:
        return _convert_via_word(md_abs_path, pdf_abs_path)

    # 两种后端都不可用
    return (
        "错误：PDF 转换不可用。"
        "Windows 环境请安装: pip install pywin32 markdown；"
        "Linux/Docker 环境请安装: pip install weasyprint markdown"
    )
