#!/usr/bin/env python3
"""
批量修复 Agent 文件，添加 custom_openai provider 支持
"""

import os
import re
from pathlib import Path

def fix_agent_file(file_path):
    """修复单个 Agent 文件"""
    print(f"修复文件: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 查找需要替换的模式
    pattern = r'(# 根据 provider 路由 API 调用\s+if self\.exp_config\.provider == "evolink":.*?)\s+else:\s+(from google\.genai import types)'

    replacement = r'''\1
        elif self.exp_config.provider == "custom_openai":
            response_list = await generation_utils.call_custom_openai_text_with_retry_async(
                model_name=self.model_name,
                contents=content_list,
                config={
                    "system_prompt": self.system_prompt,
                    "temperature": self.exp_config.temperature,
                    "max_output_tokens": 50000,
                },
                max_attempts=5,
                retry_delay=5,
            )
        else:
            \2'''

    # 执行替换
    new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"✓ 已修复: {file_path}")
        return True
    else:
        print(f"- 无需修复: {file_path}")
        return False

def main():
    """主函数"""
    agents_dir = Path("agents")

    # 需要修复的文件列表
    agent_files = [
        "critic_agent.py",
        "stylist_agent.py",
        "vanilla_agent.py"
    ]

    fixed_count = 0
    for filename in agent_files:
        file_path = agents_dir / filename
        if file_path.exists():
            if fix_agent_file(file_path):
                fixed_count += 1
        else:
            print(f"⚠️ 文件不存在: {file_path}")

    print(f"\n修复完成！共修复 {fixed_count} 个文件。")

if __name__ == "__main__":
    main()