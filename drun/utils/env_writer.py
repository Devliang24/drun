from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml


def to_env_var_name(name: str) -> str:
    """将变量名转为环境变量格式（大写+下划线）
    
    示例：
        token -> TOKEN
        user_id -> USER_ID  
        apiKey -> API_KEY
        refreshToken -> REFRESH_TOKEN
    """
    # 处理驼峰：apiKey -> api_Key -> api_key
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name)
    # 转大写
    return s.upper()


def write_env_variable(file_path: str, key: str, value: Any) -> None:
    """更新或追加 .env 文件中的变量
    
    特性：
    - key 存在则原地更新
    - key 不存在则追加到末尾
    - 保留注释和空行
    - 原子写入（临时文件+rename）
    """
    env_key = to_env_var_name(key)
    path = Path(file_path)
    
    # 确保父目录存在
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 读取现有内容
    lines = []
    key_found = False
    key_line_index = -1
    
    if path.exists():
        lines = path.read_text(encoding='utf-8').splitlines()
    
    # 查找是否已存在该 key
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and '=' in stripped:
            existing_key = stripped.split('=', 1)[0].strip()
            if existing_key == env_key:
                key_found = True
                key_line_index = i
                break
    
    # 更新或追加
    new_line = f"{env_key}={value}"
    if key_found:
        lines[key_line_index] = new_line
    else:
        # 追加到末尾（不添加额外空行）
        lines.append(new_line)
    
    # 原子写入
    temp_path = path.parent / f".{path.name}.tmp"
    temp_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    temp_path.replace(path)


def write_yaml_variable(file_path: str, key: str, value: Any) -> None:
    """更新 YAML 环境文件的 variables 部分
    
    文件结构示例：
    base_url: https://api.example.com
    variables:
      TOKEN: xxx
      USER_ID: 123
    """
    env_key = to_env_var_name(key)
    path = Path(file_path)
    
    # 确保父目录存在
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 读取现有 YAML
    if path.exists():
        content = path.read_text(encoding='utf-8')
        data = yaml.safe_load(content) or {}
    else:
        data = {}
    
    # 确保 variables 字段存在
    if 'variables' not in data:
        data['variables'] = {}
    
    # 更新变量
    data['variables'][env_key] = value
    
    # 原子写入
    temp_path = path.parent / f".{path.name}.tmp"
    temp_path.write_text(
        yaml.dump(data, allow_unicode=True, sort_keys=False, default_flow_style=False),
        encoding='utf-8'
    )
    temp_path.replace(path)
