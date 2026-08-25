#!/usr/bin/env python3
"""
测试 LLM 连接的脚本
"""
import requests
import json

# 测试 health 端点
print("=" * 50)
print("1. 检查 LLM 是否启用...")
print("=" * 50)
response = requests.get("http://localhost:8010/health")
health = response.json()
print(json.dumps(health, indent=2, ensure_ascii=False))

if not health.get("llm_enabled"):
    print("\n❌ LLM 未启用！可能的原因：")
    print("  - 环境变量未正确设置")
    print("  - Flask 进程未重启")
    exit(1)

print("\n✅ LLM 已启用！现在测试 API 调用...")
print()

# 测试 /api/analyze 端点
print("=" * 50)
print("2. 测试 /api/analyze 端点...")
print("=" * 50)
payload = {
    "user_input": "我们需要优化库存管理"
}

response = requests.post("http://localhost:8010/api/analyze", json=payload)
result = response.json()

print(f"状态码: {response.status_code}")
print(f"\n返回数据:")
print(json.dumps(result, indent=2, ensure_ascii=False))

# 检查是否成功调用了 LLM
if "llm_error" in result:
    print(f"\n❌ LLM 调用失败！")
    print(f"错误信息: {result['llm_error']}")
elif result.get("mode") == "llm":
    print(f"\n✅ LLM 调用成功！")
    print(f"业务域: {result.get('business_domain')}")
    print(f"痛点: {result.get('pain_point')}")
elif result.get("mode") == "mock":
    print(f"\n⚠️  使用 Mock 模式（模拟数据）")
else:
    print(f"\n⚠️  无法确定运行模式")
    print(f"返回的 mode 字段: {result.get('mode')}")
