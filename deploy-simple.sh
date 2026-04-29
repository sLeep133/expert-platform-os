#!/bin/bash
# Expert Platform OS 简化部署脚本（无需 Ollama，使用外部 API）

# 拉取最新代码（如果有更新）
# git pull origin main

# 启动服务（使用预构建镜像，不 build）
docker compose -f docker-compose.simple.yaml up -d

echo "部署完成！访问 http://服务器IP:3000"
