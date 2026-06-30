# 智析协同助手 | 多智能体协作分析系统

基于 **LangGraph + DeepAgents** 的多智能体深度搜索平台，由三个专家子智能体协作完成复杂的企业数据查询与分析任务。

## 🏗 系统架构

```
用户浏览器 (Vue 3)
       │
       ▼
┌─────────────┐     ┌──────────────────────────────────┐
│   前端 Nginx │────▶│   FastAPI 后端 (Port 8000)         │
│  (Port 8080) │     │                                  │
│  静态文件服务 │     │  ┌────────────────────────────┐  │
│  API 反向代理 │     │  │   主智能体 (Team Leader)    │  │
└─────────────┘     │  │   LangGraph + DeepAgents   │  │
                    │  └────┬───────┬───────┬───────┘  │
                    │       │       │       │           │
                    │  ┌────▼──┐ ┌──▼───┐ ┌─▼───────┐  │
                    │  │数据库 │ │RAGFlow│ │网络搜索 │  │
                    │  │查询   │ │知识库 │ │助手     │  │
                    │  │助手   │ │助手   │ │(Tavily) │  │
                    │  └──┬───┘ └──┬───┘ └───┬─────┘  │
                    └─────┼───────┼─────────┼─────────┘
                          │       │         │
                    ┌─────▼──┐ ┌──▼────┐ ┌──▼──────┐
                    │ MySQL  │ │RAGFlow│ │ Tavily  │
                    │ 数据库 │ │ 服务  │ │ 搜索API │
                    └────────┘ └───────┘ └─────────┘
```

- **主智能体**：协调任务拆解、委派子智能体、汇总结果并生成报告
- **数据库查询助手**：查询 MySQL 中的结构化业务数据
- **RAGFlow 助手**：从企业知识库检索非结构化文档信息
- **网络搜索助手**：通过 Tavily API 查询互联网公开信息

## ⚡ 快速开始

### 前置条件

- **Docker 模式**：Docker Desktop / Docker Engine
- **本地开发模式**：Python 3.12+、Node.js 22+、npm

### 方式一：Docker 一键启动（推荐）

```bash
# 1. 克隆项目
git clone <your-gitee-repo-url>
cd deep_search_pro

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 API Key（LLM、Tavily、RAGFlow 等）

# 3. 启动
docker compose up -d

# 4. 访问
# 前端: http://localhost:8080
# 后端 API 文档: http://localhost:8000/docs
```

### 方式二：本地开发运行

```bash
# 1. 克隆并进入项目
git clone <your-gitee-repo-url>
cd deep_search_pro

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的配置

# 3. 安装 Python 依赖
pip install -r requirements.txt

# 4. 启动后端 (终端1)
python main.py
# 后端运行在 http://localhost:8000

# 5. 启动前端 (终端2)
cd ui
npm install
npm run dev
# 前端运行在 http://localhost:5173
```

## ⚙ 环境变量配置

复制 `.env.example` 为 `.env`，按需配置：

| 变量 | 说明 | 必填 |
|------|------|------|
| `OPENAI_BASE_URL` | LLM API 地址（阿里云百炼 / OpenAI 兼容） | ✅ |
| `OPENAI_API_KEY` | LLM API 密钥 | ✅ |
| `LLM_QWEN_MAX` | 模型名称（默认 qwen-max） | - |
| `TAVILY_API_KEY` | Tavily 搜索 API Key | ✅ |
| `RAGFLOW_API_URL` | RAGFlow 服务地址 | - |
| `RAGFLOW_API_KEY` | RAGFlow API 密钥 | - |
| `MYSQL_HOST/PORT/USER/PASSWORD/DATABASE` | MySQL 数据库连接 | - |

> **注意**：RAGFlow 和 MySQL 是可选服务。如果不需要知识库或数据库查询，对应的子智能体在运行时会被跳过。

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 + TypeScript + Vite + Axios + Marked |
| **后端框架** | FastAPI + WebSocket + Uvicorn |
| **智能体编排** | LangGraph + DeepAgents |
| **LLM 接入** | LangChain + langchain-openai (兼容阿里云百炼) |
| **工具集成** | Tavily API / RAGFlow SDK / MySQL Connector |
| **文件处理** | WeasyPrint (MD→PDF) / pypdf / python-docx / Pandas |
| **容器化** | Docker + Docker Compose |

## 📁 项目结构

```
deep_search_pro/
├── agent/                      # 智能体核心
│   ├── main_agent.py           # 主智能体 (Team Leader)
│   ├── llm.py                  # LLM 模型初始化
│   ├── prompts.py              # 提示词加载
│   └── subagents/              # 子智能体定义
│       ├── database_query_agent.py   # 数据库查询助手
│       ├── knowledge_base_agent.py   # RAGFlow 知识库助手
│       └── network_search_agent.py   # 网络搜索助手
├── api/                        # Web API 层
│   ├── server.py               # FastAPI 服务器 + REST/WebSocket 接口
│   ├── context.py              # 协程级上下文变量 (ContextVar)
│   └── monitor.py              # 工具调用监控 + WebSocket 推送
├── tools/                      # LangChain 工具集
│   ├── db_tools.py             # MySQL 查询工具 (3个)
│   ├── ragflow_tools.py        # RAGFlow 知识库工具 (2个)
│   ├── tavily_tool.py          # 网络搜索工具
│   ├── markdown_tools.py       # Markdown 文件生成
│   ├── pdf_tools.py            # Markdown → PDF 转换
│   └── upload_file_read_tool.py # 多格式文件读取 (.docx/.pdf/.xlsx/.md)
├── utils/                      # 工具函数
│   ├── path_utils.py           # 路径安全解析
│   └── word_converter.py       # MD→PDF 转换引擎 (WeasyPrint/Word COM)
├── ragflow/                    # RAGFlow 集成
│   └── rag_config.py           # RAGFlow 环境配置加载
├── prompt/
│   └── prompts.yaml            # 智能体提示词配置
├── ui/                         # 前端 (Vue 3 + Vite)
│   ├── src/
│   │   ├── App.vue             # 主聊天界面
│   │   └── main.ts             # Vue 应用入口
│   ├── nginx.conf              # Nginx 配置 (Docker)
│   ├── Dockerfile              # 前端 Docker 构建
│   └── vite.config.ts          # Vite 配置 (含 API 代理)
├── output/                     # 生成文件输出 (运行时创建)
├── updated/                    # 用户上传文件 (运行时创建)
├── docker-compose.yml          # Docker 编排配置
├── Dockerfile                  # 后端 Docker 构建
├── .env.example                # 环境变量模板
├── main.py                     # 入口脚本
├── pyproject.toml              # Python 项目元数据
└── requirements.txt            # Python 依赖清单
```

## 📝 License

MIT
