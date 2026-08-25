#!/bin/bash

# 从 .env 文件加载环境变量
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
fi

# 确认变量已加载
echo "=== 启动 Flask，LLM 配置如下 ==="
echo "LLM_API_KEY: ${LLM_API_KEY:0:20}..."
echo "LLM_BASE_URL: $LLM_BASE_URL"
echo "LLM_MODEL: $LLM_MODEL"
echo ""

# 启动 Flask
export PORT=8010
python3 app.py
