# #!/usr/bin/env python3
# """
# Script to check which files are being used and their content
# """
# import os

# print("🔍 Checking Current Files...")
# print("=" * 60)

# # Check if files exist and show their key content
# files_to_check = [
#     'gmail_setup_agent.py',
#     'config.py',
#     '.env'
# ]

# for filename in files_to_check:
#     print(f"\n📄 Checking {filename}:")
#     if os.path.exists(filename):
#         print(f"✅ {filename} exists")
        
#         # Check key content
#         with open(filename, 'r') as f:
#             content = f.read()
            
#             if filename == 'gmail_setup_agent.py':
#                 if 'from agno.models.openai import OpenAIChat' in content:
#                     print("❌ Still imports OpenAI!")
#                 if 'from agno.models.deepseek import DeepSeek' in content:
#                     print("✅ Imports DeepSeek")
#                 if 'get_ai_model()' in content:
#                     print("❌ Still uses get_ai_model() - OLD VERSION")
#                 if 'get_deepseek_model()' in content:
#                     print("✅ Uses get_deepseek_model() - NEW VERSION")
                    
#             elif filename == 'config.py':
#                 if 'OPENAI_API_KEY' in content:
#                     print("❌ Still has OPENAI_API_KEY")
#                 if 'AI_PROVIDER' in content:
#                     print("❌ Still has AI_PROVIDER switching")
#                 if 'class Config' in content and 'DEEPSEEK_API_KEY' in content:
#                     if content.count('OPENAI') == 0:
#                         print("✅ DeepSeek-only config")
#                     else:
#                         print("❌ Mixed config")
                        
#             elif filename == '.env':
#                 lines = content.strip().split('\n')
#                 print(f"Has {len(lines)} lines")
#                 if any('OPENAI_API_KEY' in line for line in lines):
#                     print("❌ Still has OPENAI_API_KEY")
#                 if any('DEEPSEEK_API_KEY' in line for line in lines):
#                     print("✅ Has DEEPSEEK_API_KEY")
#                 if any('AI_PROVIDER' in line for line in lines):
#                     print("❌ Still has AI_PROVIDER")
#     else:
#         print(f"❌ {filename} does not exist")

# print(f"\n📍 Current working directory: {os.getcwd()}")
# print(f"📂 All .py files in directory:")
# for f in os.listdir('.'):
#     if f.endswith('.py'):
#         print(f"  - {f}")

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