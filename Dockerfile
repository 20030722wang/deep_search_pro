# ============================================================
# Deep Search Pro - 多智能体深度搜索系统
# 基于 Python 3.12 + FastAPI + LangChain/LangGraph
# ============================================================

FROM python:3.12-slim

LABEL maintainer="whw24151258@gmail.com"
LABEL description="智析协同助手 | 多智能体协作分析系统 - Multi-Agent Deep Search System"

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    # markdown 转 PDF 替代方案 (取代 Windows Word COM)
    weasyprint \
    # 清理缓存
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml requirements.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    # 安装 weasyprint 的 Python 包 (用于 MD -> PDF)
    && pip install --no-cache-dir weasyprint

# 复制项目代码（.dockerignore 会排除不需要的文件）
COPY . .

# 创建必要的目录
RUN mkdir -p output updated

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs')" || exit 1

# 启动服务
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
