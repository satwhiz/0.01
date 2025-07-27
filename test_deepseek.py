#!/usr/bin/env python3
"""
Show the first 30 lines of gmail_setup_agent.py to see the imports
"""
import os

filename = 'gmail_setup_agent.py'

if os.path.exists(filename):
    print(f"📄 First 30 lines of {filename}:")
    print("=" * 60)
    
    with open(filename, 'r') as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines[:30], 1):
        prefix = "❌" if "openai" in line.lower() else "✅" if "deepseek" in line.lower() else "  "
        print(f"{prefix} {i:2}: {line.rstrip()}")
        
    print("=" * 60)
    
    # Check for specific problem lines
    content = ''.join(lines)
    
    print("\n🔍 Analysis:")
    if 'from agno.models.openai import OpenAIChat' in content:
        print("❌ Found: from agno.models.openai import OpenAIChat")
    if 'OpenAIChat' in content:
        print("❌ Found: OpenAIChat references")
    if 'get_ai_model' in content:
        print("❌ Found: get_ai_model function")
    if 'get_deepseek_model' in content:
        print("✅ Found: get_deepseek_model function")
    if 'base_url="https://api.deepseek.com"' in content:
        print("✅ Found: DeepSeek base URL")
        
else:
    print(f"❌ {filename} not found")