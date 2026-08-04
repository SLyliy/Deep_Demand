#!/bin/bash

# ? .env ????????
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | grep -v '^$' | xargs)
fi

# ???????
echo "=== ?? Flask?LLM ???? ==="
echo "LLM_API_KEY: ${LLM_API_KEY:0:20}..."
echo "LLM_BASE_URL: $LLM_BASE_URL"
echo "LLM_MODEL: $LLM_MODEL"
echo ""

# ?? Flask
export PORT=8010
python3 app.py
