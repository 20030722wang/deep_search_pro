#!/bin/bash
set -euo pipefail

echo "============================================"
echo "  智析协同助手 | 多智能体协作分析系统"
echo "============================================"
echo ""

# 检查 .env 文件
if [ ! -f /app/.env ]; then
    echo "[WARNING] .env file not found, using environment variables"
else
    echo "[OK] .env file found"
fi

# 等待 MySQL 就绪 (如果配置了)
if [ -n "${MYSQL_HOST:-}" ] && [ -n "${MYSQL_PASSWORD:-}" ]; then
    echo -n "[*] Waiting for MySQL (${MYSQL_HOST}:${MYSQL_PORT:-3306})..."
    for i in $(seq 1 30); do
        if python -c "
from mysql.connector import connect
try:
    c = connect(
        host='${MYSQL_HOST}',
        port=${MYSQL_PORT:-3306},
        user='${MYSQL_USER:-root}',
        password='${MYSQL_PASSWORD}',
    )
    c.close()
    exit(0)
except Exception:
    exit(1)
" 2>/dev/null; then
            echo " ready"
            break
        fi
        sleep 2
        echo -n "."
    done
fi

echo ""
echo "[*] Starting application..."
echo ""

exec uvicorn api.server:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-1}" \
    --log-config /dev/null
