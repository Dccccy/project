#!/usr/bin/env python3
# =============================================================================
# Commit SHA Verification Script for Neural Network Architectures Entry
# 适配仓库: tech-docs-repository
# =============================================================================

import sys
import os
import requests
import base64
import re
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv

# -----------------------------
# 1) 配置参数（针对tech-docs-repository仓库）
# -----------------------------
CONFIG = {
    # 环境配置
    "ENVIRONMENT": {
        "env_file_path": ".env",           # 环境变量文件路径
        "github_token_var": "GITHUB_TOKEN",     # 存储GitHub令牌的环境变量名
        "github_owner_var": "GITHUB_OWNER",     # 存储仓库所有者的环境变量名
        "target_repo_var": "TARGET_REPO",       # 存储目标仓库名的环境变量名
        "target_branch_var": "TARGET_BRANCH",   # 存储目标分支名的环境变量名
        "default_repo": "tech-docs-repository", # 仓库名
        "default_branch": "main"                # 默认分支
    },
    
    # 任务配置
    "TASK": {
        "name": "Find Neural Network Architectures commit SHA",
        "expected_sha_var": "EXPECTED_NN_ARCH_SHA",
        "answer_file": {
            "name_var": "ANSWER_FILE_NAME",
            "default_name": "ANSWER.md"   # 答案文件
        },
        "target": {
            "entry_name_var": "TARGET_ENTRY",         # 目标条目
            "section_name_var": "TARGET_SECTION"      # 目标章节
        },
        "validation_strategy": {
            "verify_commit_details": "true",
            "allow_partial_match": "true"  # 允许部分匹配，降低难度
        }
    }
}

# -----------------------------
# 2) 工具函数
# -----------------------------
def _get_github_api(
    endpoint: str, 
    headers: Dict[str, str], 
    owner: str, 
    repo: str = CONFIG["ENVIRONMENT"]["default_repo"]
) -> Tuple[bool, Optional[Dict]]:
    """调用GitHub API获取数据"""
    url = f"https://api.github.com/repos/{owner}/{repo}/{endpoint}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            return True, response.json()
        elif response.status_code == 404:
            return False, None
        else:
            print(f"API错误 {endpoint}: {response.status_code}", file=sys.stderr)
            return False, None
    except Exception as e:
        print(f"API请求异常 {endpoint}: {e}", file=sys.stderr)
        return False, None


def _get_file_content(
    file_path: str,
    headers: Dict[str, str],
    owner: str,
    repo: str = CONFIG["ENVIRONMENT"]["default_repo"],
    ref: str = CONFIG["ENVIRONMENT"]["default_branch"],
) -> Optional[str]:
    """获取指定文件内容"""
    success, result = _get_github_api(
        f"contents/{file_path}?ref={ref}", headers, owner, repo
    )
    if not success or not result:
        return None

    try:
        content = base64.b64decode(result.get("content", "")).decode("utf-8")
        return content
    except Exception as e:
        print(f"文件解码错误 {file_path}: {e}", file=sys.stderr)
        return None


def _validate_required_env_vars(required_vars: list) -> bool:
    """验证必要的环境变量是否存在"""
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        print(f"错误: 缺少必要的环境变量: {missing}", file=sys.stderr)
        return False
    return True


def _verify_single_sha(content: str, expected_sha: str) -> bool:
    """验证单个SHA是否匹配"""
    content = content.strip()
    if content != expected_sha:
        print(f"错误: SHA不匹配。预期 {expected_sha}，实际: {content}", file=sys.stderr)
        return False
    return True


def _verify_commit_details(commit_data: Dict, target_entry: str, target_section: str) -> bool:
    """验证提交详情是否包含目标条目和章节信息（宽松验证）"""
    commit_message = commit_data.get('commit', {}).get('message', '').lower()
    target_entry_lower = target_entry.lower() if target_entry else ""
    target_section_lower = target_section.lower() if target_section else ""
    
    # 宽松验证：检查提交是否修改了任何Markdown文档
    modified_files = [f.get('filename') for f in commit_data.get('files', [])]
    md_files = [f for f in modified_files if f.endswith('.md')]
    
    if not md_files:
        print(f"警告: 提交未修改任何Markdown文档", file=sys.stderr)
        # 不强制要求，只是警告
    
    # 宽松验证：检查提交信息是否包含关键词（部分匹配即可）
    if target_entry and target_entry_lower not in commit_message:
        print(f"警告: 提交信息未提及目标条目: {target_entry}", file=sys.stderr)
        # 不强制要求，只是警告
        
    if target_section and target_section_lower not in commit_message:
        print(f"警告: 提交信息未提及目标章节: {target_section}", file=sys.stderr)
        # 不强制要求，只是警告
        
    return True


def _find_target_file(headers: Dict[str, str], owner: str, repo: str, branch: str) -> Optional[str]:
    """查找包含目标章节的Markdown文件"""
    # 尝试搜索包含目标章节的文件
    target_section = os.environ.get(CONFIG["TASK"]["target"]["section_name_var"], "Deep Learning Fundamentals")
    
    # 常见的可能文件路径
    possible_paths = [
        "docs/deep_learning.md",
        "articles/ai_basics.md",
        "docs/neural_networks.md",
        "tutorials/deep_learning_fundamentals.md",
        "docs/ai_fundamentals.md"
    ]
    
    for file_path in possible_paths:
        content = _get_file_content(file_path, headers, owner, repo, branch)
        if content and target_section.lower() in content.lower():
            print(f"找到目标文件: {file_path}")
            return file_path
    
    print(f"警告: 未找到明确包含'{target_section}'章节的文件")
    return None

# -----------------------------
# 3) 主验证流程
# -----------------------------
def verify_task() -> bool:
    """主验证流程"""
    # 加载环境变量
    env_file = CONFIG["ENVIRONMENT"]["env_file_path"]
    load_dotenv(env_file)

    # 获取配置信息
    github_token = os.environ.get(CONFIG["ENVIRONMENT"]["github_token_var"])
    github_owner = os.environ.get(CONFIG["ENVIRONMENT"]["github_owner_var"])
    target_repo = os.environ.get(
        CONFIG["ENVIRONMENT"]["target_repo_var"], 
        CONFIG["ENVIRONMENT"]["default_repo"]
    )
    target_branch = os.environ.get(
        CONFIG["ENVIRONMENT"]["target_branch_var"], 
        CONFIG["ENVIRONMENT"]["default_branch"]
    )
    
    # 任务特定配置
    expected_sha = os.environ.get(CONFIG["TASK"]["expected_sha_var"])
    answer_file = os.environ.get(
        CONFIG["TASK"]["answer_file"]["name_var"],
        CONFIG["TASK"]["answer_file"]["default_name"]
    )
    target_entry = os.environ.get(CONFIG["TASK"]["target"]["entry_name_var"], "Neural Network Architectures")
    target_section = os.environ.get(CONFIG["TASK"]["target"]["section_name_var"], "Deep Learning Fundamentals")
    
    # 验证策略
    verify_details = os.environ.get(
        CONFIG["TASK"]["validation_strategy"]["verify_commit_details"], 
        "true"
    ).lower() == "true"

    # 验证必要的环境变量
    required_vars = [
        CONFIG["ENVIRONMENT"]["github_token_var"],
        CONFIG["ENVIRONMENT"]["github_owner_var"],
        CONFIG["TASK"]["expected_sha_var"]
    ]
    if not _validate_required_env_vars(required_vars):
        return False

    # 准备GitHub API请求头
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    print(f"正在验证 {CONFIG['TASK']['name']} 任务...")

    # 1. 检查答案文件是否存在
    print(f"1. 检查 {answer_file} 是否存在...")
    content = _get_file_content(answer_file, headers, github_owner, target_repo, target_branch)
    if not content:
        print(f"错误: 仓库中未找到 {answer_file}", file=sys.stderr)
        return False
    print(f"✓ 找到 {answer_file}")

    # 2. 检查文件内容是否匹配预期SHA
    print(f"2. 检查 {answer_file} 内容...")
    content = content.strip()
    
    if not _verify_single_sha(content, expected_sha):
        return False
    print(f"✓ {answer_file} 内容正确")

    # 3. 验证提交是否存在且有效
    print(f"3. 验证提交是否存在...")
    
    # 验证SHA格式是否正确（40位十六进制）
    if not (len(content) == 40 and all(c in '0123456789abcdefABCDEF' for c in content)):
        print(f"错误: 无效的SHA格式 {content}，必须是40位十六进制字符", file=sys.stderr)
        return False
        
    success, commit_data = _get_github_api(f"commits/{content}", headers, github_owner, target_repo)
    if not success or not commit_data:
        print(f"错误: 仓库中未找到提交 {content}", file=sys.stderr)
        return False
        
    # 验证提交详情（宽松验证）
    if verify_details:
        if not _verify_commit_details(commit_data, target_entry, target_section):
            # 宽松模式下，验证失败只输出警告，不终止流程
            print("⚠ 提交详情验证有警告，但继续执行...")
    
    print(f"✓ 提交 {content} 存在且有效")

    # 所有检查通过
    print("\n✅ 所有验证检查通过!")
    print(f"任务 {CONFIG['TASK']['name']} 成功完成:")
    print(f"  - 已创建 {answer_file}，内容正确: {content}")
    print(f"  - 提交在仓库中存在且有效")

    return True

# -----------------------------
# 入口
# -----------------------------
if __name__ == "__main__":
    success = verify_task()
    sys.exit(0 if success else 1)