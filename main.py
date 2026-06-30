"""
智析协同助手 | 多智能体协作分析系统
基于 LangGraph + DeepAgents 的多智能体深度搜索平台

启动方式:
  docker compose up -d        # Docker 一键启动
  python -m api.server        # 本地开发启动后端
"""
import uvicorn


def main():
    """启动 API 服务"""
    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
