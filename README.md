# Expert Platform OS

![License](https://img.shields.io/badge/license-MIT-blue)
![GitHub stars](https://img.shields.io/github/stars/sLeep133/expert-platform-os?style=social)
![GitHub forks](https://img.shields.io/github/forks/sLeep133/expert-platform-os?style=social)

Expert Platform OS 是一个基于 OpenWebUI 二次开发的**企业级 AI 专家平台**，支持知识库管理、专家智能体、工作空间协作等功能。基于 **Karpathy llm-wiki 方法论**构建知识图谱，实现"一次编译，处处使用"。

## 核心功能

### 🧠 专家智能体
- 创建 AI 专家角色，配置角色设定和大模型
- 关联知识库，让专家具备专业领域知识
- 支持私有/共享模式，团队共享专家资源
- 基于知识图谱的语义检索，理解实体关系

### 📚 知识库（Obsidian 兼容）
- 上传文档、网页、文本等多种格式
- LLM 自动分析并生成结构化 Wiki 页面
- **自动生成 `[[wikilinks]]` 双向链接**，构建知识网络
- **Obsidian 直接导入使用**，无需二次转换
- 页面分类：实体、概念、主题、对比、查询等
- **跨文档综合**，自动生成知识索引和关系总览
- Entity-Concept 关系图谱，支持图遍历检索

### 👥 工作空间
- 知识库 / 专家 / 技能三大模块
- 细粒度权限控制，管理员统一管理
- 响应式设计，支持 PC / 平板 / 手机

### 🔗 API 兼容
- 支持任意 OpenAI 兼容 API（智谱、海螺、MiniMax 等）
- 支持本地 Ollama 模型
- 无需显卡，纯 CPU 即可运行

## 设计理念

**一次编译，处处使用**：
- Wiki 编译产出的就是 Obsidian 直接能用的 vault
- Expert Platform 直接读取 Wiki 目录，无需二次导入
- 摈弃传统 RAG，拥抱知识图谱

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
├── backend/
│   └── open_webui/
│       └── knowledge/
│           ├── compiler.py    # Karpathy llm-wiki 编译器
│           ├── wiki.py       # Wiki 读写和检索
│           └── llm.py        # LLM 调用
├── src/                     # 前端源码
├── docs/                    # 文档
├── Dockerfile
├── docker-compose.webui-only.yaml  # 简化部署配置
└── deploy-simple.sh         # 一键部署脚本
```

## 技术栈

- **前端**: SvelteKit + TailwindCSS
- **后端**: Python FastAPI + SQLAlchemy
- **数据库**: SQLite（默认）/ PostgreSQL
- **知识图谱**: 原生 Markdown + Wikilinks（Obsidian 兼容）

## License

MIT License
