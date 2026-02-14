#!/usr/bin/env python3
"""
配置文件转换工具
将 test_multi_accounts.py 中的配置转换为 GitHub Actions 需要的 JSON 格式
"""
import json
from test_multi_accounts import ACCOUNTS

def convert_config():
    """转换配置为 GitHub Actions 格式"""
    print("="*70)
    print("🔄 配置转换工具")
    print("="*70)
    print()
    
    # 转换为 JSON
    config_json = json.dumps(ACCOUNTS, indent=2, ensure_ascii=False)
    
    # 保存到文件
    output_file = "github_actions_config.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(config_json)
    
    print(f"✅ 配置已转换并保存到: {output_file}")
    print()
    print("📋 配置内容预览（前100个字符）：")
    print("-"*70)
    print(config_json[:100] + "...")
    print("-"*70)
    print()
    print("📝 使用说明：")
    print("1. 打开 github_actions_config.json 文件")
    print("2. 复制全部内容")
    print("3. 在 GitHub 仓库的 Settings → Secrets → Actions")
    print("4. 创建新的 Secret：")
    print("   - Name: ANYROUTER_ACCOUNTS")
    print("   - Value: 粘贴复制的内容")
    print()
    print("⚠️  重要：")
    print("- 这个文件包含敏感信息，不要提交到 Git")
    print("- 已自动添加到 .gitignore")
    print()
    
    # 更新 .gitignore
    gitignore_file = ".gitignore"
    gitignore_entry = "github_actions_config.json"
    
    try:
        # 读取现有 .gitignore
        if os.path.exists(gitignore_file):
            with open(gitignore_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 检查是否已存在
            if gitignore_entry not in content:
                with open(gitignore_file, 'a', encoding='utf-8') as f:
                    f.write(f"\n{gitignore_entry}\n")
                print(f"✅ 已添加到 .gitignore")
        else:
            # 创建新的 .gitignore
            with open(gitignore_file, 'w', encoding='utf-8') as f:
                f.write(f"{gitignore_entry}\n")
            print(f"✅ 已创建 .gitignore")
    except Exception as e:
        print(f"⚠️  无法更新 .gitignore: {e}")
    
    print()
    print("="*70)
    print("🎉 转换完成！")
    print("="*70)
    
    return output_file

if __name__ == '__main__':
    import os
    convert_config()
