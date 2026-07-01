"""
FastAPI 服务入口 — REST API + WebSocket

路由:
    POST /api/task       — 提交分析任务
    POST /api/upload     — 上传文件
    GET  /api/download   — 下载生成文件
    GET  /api/files      — 列出生成文件
    GET  /api/version    — 应用版本信息
    GET  /health         — Liveness 探针
    GET  /ready          — Readiness 探针
    WS   /ws/{thread_id} — 实时通信通道
"""
import uuid
import asyncio
import uvicorn
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI, WebSocket, WebSocketDisconnect,
    UploadFile, File, Form, HTTPException,
)
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.core import (
    settings, app_lifespan, get_logger,
    EventType, MessageType,
    RequestIDMiddleware, RequestTimingMiddleware, create_cors_middleware,
)

logger = get_logger(__name__)

# ============================================================
# 路径常量
# ============================================================
_project_root = settings.app.project_root
_output_dir = _project_root / "output"
_updated_dir = _project_root / "updated"

# ============================================================
# App 初始化
# ============================================================
app = FastAPI(
    title=settings.app.name,
    version=settings.app.version,
    lifespan=app_lifespan,
)

# 挂载静态文件目录（前端通过 /outputs/... 直接访问生成文件）
_output_dir.mkdir(exist_ok=True)
_updated_dir.mkdir(exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(_output_dir)), name="outputs")

# 中间件栈（按添加顺序逆序执行）
app.add_middleware(RequestTimingMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    type(create_cors_middleware(settings.app.cors_origins)),
    **create_cors_middleware(settings.app.cors_origins).__dict__,
) if False else None  # no-op guard

# 手动注册 CORS（避免 CORSMiddleware __init__ 中 app=None 的问题）
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 请求/响应模型
# ============================================================

class TaskRequest(BaseModel):
    """任务请求体"""
    query: str
    thread_id: Optional[str] = None


class TaskResponse(BaseModel):
    """任务启动响应体"""
    status: str = "started"
    thread_id: str


class UploadResponse(BaseModel):
    """文件上传响应体"""
    status: str = "uploaded"
    files: list[str]


class FileInfo(BaseModel):
    """文件元数据"""
    name: str
    type: str = "file"
    path: str
    size: int
    mtime: float


class FileListResponse(BaseModel):
    """文件列表响应体"""
    files: list[dict]


class HealthResponse(BaseModel):
    """健康检查响应体"""
    status: str = "healthy"
    timestamp: str


class ReadyResponse(BaseModel):
    """就绪检查响应体"""
    status: str
    checks: dict
    timestamp: str


class VersionResponse(BaseModel):
    """版本信息响应体"""
    name: str
    version: str


# ============================================================
# 内部辅助
# ============================================================

def _handle_task_exception(task: asyncio.Task) -> None:
    """捕获后台任务未处理异常，写入日志"""
    try:
        task.result()
    except Exception:
        logger.exception("Background task failed")


# ============================================================
# 健康检查端点
# ============================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Liveness 探针 — 仅验证进程存活"""
    from datetime import datetime, timezone
    return HealthResponse(timestamp=datetime.now(timezone.utc).isoformat())


@app.get("/ready", response_model=ReadyResponse)
async def readiness_check():
    """Readiness 探针 — 验证核心依赖是否可达"""
    from datetime import datetime, timezone
    checks: dict[str, str] = {}

    # MySQL 连通性检查 (2s 超时)
    try:
        import asyncio as _asyncio
        from mysql.connector import connect as _mysql_connect, Error as _MySQLError
        mysql_config = settings.mysql.to_conn_dict()
        mysql_config["connection_timeout"] = 2
        await _asyncio.to_thread(
            lambda: _mysql_connect(**mysql_config).close()
        )
        checks["mysql"] = "ok"
    except Exception as e:
        checks["mysql"] = f"error: {e}"

    # RAGFlow 连通性检查
    try:
        if settings.ragflow.api_key:
            import requests as _requests
            resp = await asyncio.to_thread(
                lambda: _requests.get(
                    f"{settings.ragflow.api_url}/api/v1/version",
                    timeout=5,
                    headers={"Authorization": f"Bearer {settings.ragflow.api_key}"},
                )
            )
            checks["ragflow"] = "ok" if resp.status_code < 500 else f"error: HTTP {resp.status_code}"
        else:
            checks["ragflow"] = "skipped (not configured)"
    except Exception as e:
        checks["ragflow"] = f"error: {e}"

    all_ok = all(v == "ok" or v.startswith("skipped") for v in checks.values())
    status_code = 200 if all_ok else 503

    if not all_ok:
        raise HTTPException(status_code=status_code, detail={"checks": checks})

    return ReadyResponse(
        status="ready" if all_ok else "not_ready",
        checks=checks,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@app.get("/api/version", response_model=VersionResponse)
async def api_version():
    """返回应用版本信息"""
    return VersionResponse(name=settings.app.name, version=settings.app.version)


# ============================================================
# 任务端点
# ============================================================

@app.post("/api/task", response_model=TaskResponse)
async def run_task(request: TaskRequest):
    """提交分析任务 — 异步执行，立即返回"""
    thread_id = request.thread_id or str(uuid.uuid4())

    from agent.main_agent import run_deep_agent
    task = asyncio.create_task(run_deep_agent(request.query, thread_id))
    task.add_done_callback(_handle_task_exception)

    return TaskResponse(thread_id=thread_id)


@app.post("/api/upload", response_model=UploadResponse)
async def upload_files(
    files: list[UploadFile] = File(...),
    thread_id: str = Form(...),
):
    """文件上传接口"""
    target_dir = _updated_dir / f"session_{thread_id}"
    target_dir.mkdir(parents=True, exist_ok=True)

    saved: list[str] = []
    for file in files:
        file_path = target_dir / file.filename
        with file_path.open("wb") as buffer:
            import shutil
            shutil.copyfileobj(file.file, buffer)
        saved.append(file.filename)

    return UploadResponse(files=saved)


@app.get("/api/download")
async def download_file(path: str):
    """文件下载接口 — 安全路径校验"""
    try:
        abs_path = Path(path).resolve()
        output_abs = _output_dir.resolve()
        if not abs_path.is_relative_to(output_abs):
            raise HTTPException(status_code=403, detail="拒绝访问")
    except Exception:
        raise HTTPException(status_code=400, detail="无效路径")

    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    return FileResponse(abs_path, filename=abs_path.name)


@app.get("/api/files", response_model=FileListResponse)
async def list_files(path: str):
    """文件列表查询接口"""
    logger.debug("File list request", extra={"path": path})

    try:
        abs_path = Path(path).resolve()
        if not abs_path.is_relative_to(_output_dir.resolve()):
            raise HTTPException(status_code=403, detail="拒绝访问")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"路径无效: {e}")

    if not abs_path.exists():
        return FileListResponse(files=[])

    files_data: list[dict] = []
    try:
        for file_path in abs_path.rglob("*"):
            if file_path.is_file():
                stat = file_path.stat()
                files_data.append({
                    "name": file_path.name,
                    "type": "file",
                    "path": str(file_path),
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    files_data.sort(key=lambda x: x.get("mtime", 0), reverse=True)
    logger.debug("File list result", extra={"count": len(files_data)})
    return FileListResponse(files=files_data)


# ============================================================
# WebSocket 端点
# ============================================================

@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """WebSocket 实时通信 — 会话级消息推送"""
    from api.monitor import manager

    await manager.connect(websocket, thread_id)
    logger.info("WebSocket connected", extra={"thread_id": thread_id})

    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({
                "type": EventType.PONG,
                "message": f"已收到: {data}",
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket, thread_id)
        logger.info("WebSocket disconnected", extra={"thread_id": thread_id})
    except Exception:
        manager.disconnect(websocket, thread_id)
        logger.exception("WebSocket error", extra={"thread_id": thread_id})


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "api.server:app",
        host=settings.app.host,
        port=settings.app.port,
        reload=settings.app.debug,
    )
