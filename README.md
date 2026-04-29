# Expert Platform OS

![License](https://img.shields.io/badge/license-MIT-blue)
![GitHub stars](https://img.shields.io/github/stars/sLeep133/expert-platform-os?style=social)
![GitHub forks](https://img.shields.io/github/forks/sLeep133/expert-platform-os?style=social)

Expert Platform OS 是一个基于 OpenWebUI 二次开发的**企业级 AI 专家平台**，支持知识库管理、专家智能体、工作空间协作等功能，完全离线部署，支持任意 OpenAI 兼容 API。

## 核心功能

### 🧠 专家智能体
- 创建 AI 专家角色，配置角色设定和大模型
- 关联知识库，让专家具备专业领域知识
- 支持私有/共享模式，团队共享专家资源

### 📚 知识库
- 上传文档、网页、文本等多种格式
- 基于 **Karpathy llm-wiki 方法论**，LLM 自动分析并生成结构化 Wiki 页面
- 页面分类：实体、概念、主题、对比、查询等，便于系统化知识管理
- Wiki 页面自动同步到专家知识库，增强检索能力

### 👥 工作空间
- 知识库 / 专家 / 技能三大模块
- 细粒度权限控制，管理员统一管理
- 响应式设计，支持 PC / 平板 / 手机

### 🔗 API 兼容
- 支持任意 OpenAI 兼容 API（智谱、海螺、MiniMax 等）
- 支持本地 Ollama 模型
- 无需显卡，纯 CPU 即可运行

## 快速部署

### 环境要求
- Docker & Docker Compose
- 1核2G内存以上

### 一键部署
```bash
git clone https://github.com/sLeep133/expert-platform-os.git
cd expert-platform-os
docker compose -f docker-compose.webui-only.yaml up -d
```

访问 `http://localhost:3000`

### 更新版本
```bash
cd expert-platform-os
git pull origin main
docker compose -f docker-compose.webui-only.yaml up -d --build
```

## 配置大模型

1. 进入「专家」页面，创建或编辑专家
2. 在「LLM 配置」中填写：
   - **API Base**: 如 `https://api.minimaxi.com/v1`
   - **API Key**: 你的 API Key
   - **Model**: 模型名称，如 `abab6.5s-chat`

## 项目结构

```
expert-platform-os/
├── backend/              # 后端 API
├── src/                  # 前端源码
├── docs/                 # 文档
├── Dockerfile            # Docker 构建文件
├── docker-compose.webui-only.yaml  # 简化部署配置
└── deploy-simple.sh      # 一键部署脚本
```

## 技术栈

- **前端**: SvelteKit + TailwindCSS
- **后端**: Python FastAPI + SQLAlchemy
- **数据库**: SQLite（默认）/ PostgreSQL
- **向量库**: 支持 ChromaDB、PGVector 等

## License

MIT License
