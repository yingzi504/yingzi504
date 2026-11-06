#!/usr/bin/env python3
"""
测试配置加载
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


def test_config_loading():
    """测试配置加载"""
    print("=" * 60)
    print("  测试配置加载")
    print("=" * 60)
    print()
    
    print("[1] 配置信息:")
    print(f"  环境: {settings.environment}")
    print(f"  端口: {settings.port}")
    print()
    
    print("[2] LLM 配置:")
    print(f"  模型: {settings.llm_model}")
    print(f"  API Endpoint: {settings.llm_api_endpoint or '未设置'}")
    print(f"  API Key: {'已设置' if settings.llm_api_key else '未设置'}")
    print(f"  API Base: {settings.llm_api_base or '未设置'}")
    print()
    
    if not settings.llm_api_key:
        print("[!] 警告: LLM_API_KEY 未设置，请在 .env 文件中配置")
        print()
    
    print("[3] .env 文件检查:")
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        print(f"  ✓ .env 文件存在: {env_path}")
        with open(env_path, 'r', encoding='utf-8') as f:
            content = f.read()
            print("  文件内容预览:")
            for line in content.strip().split('\n')[:10]:
                if 'API_KEY' in line:
                    key_part = line.split('=')[1].strip() if '=' in line else ''
                    if key_part:
                        print(f"    {line.split('=')[0]}=***")
                    else:
                        print(f"    {line}")
                else:
                    print(f"    {line}")
    else:
        print(f"  ✗ .env 文件不存在: {env_path}")
        print("  请从 .env.example 复制创建")
    
    print()
    print("=" * 60)
    print("  测试完成!")
    print("=" * 60)


if __name__ == "__main__":
    test_config_loading()
