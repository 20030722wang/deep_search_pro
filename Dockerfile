# ============================================================
# 智析协同助手 | 多智能体协作分析系统
# 多阶段构建 — 后端 FastAPI 服务
# ============================================================

# ---------- 构建阶段 ----------
FROM python:3.12-slim AS builder

WORKDIR /app

# 安装编译依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc curl \
    # WeasyPrint 系统依赖
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
    libffi-dev libgdk-pixbuf2.0-0 libgdk-pixbuf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --target=/deps -r requirements.txt

# ---------- 运行阶段 ----------
FROM python:3.12-slim

# 创建非 root 用户
RUN addgroup --system app && adduser --system --group app

WORKDIR /app

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    # WeasyPrint 运行时 (PDF 生成)
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 \
    libgdk-pixbuf2.0-0 libgdk-pixbuf-2.0-0 \
    # 清理
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制 Python 依赖
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages

# 创建数据目录并设置权限
RUN mkdir -p /app/output /app/updated \
    && chown -R appuser:appuser /app

# 复制应用代码
COPY --chown=appuser:appuser . .

# 入口脚本
COPY --chown=appuser:appuser entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 切换到非 root 用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
