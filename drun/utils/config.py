"""
配置工具模块
提供统一的配置访问接口
"""
from __future__ import annotations

import os
import re
from typing import Optional

_INLINE_COMMENT_PATTERN = re.compile(r"[ \t]+#.*$")


def get_env_clean(key: str, default: Optional[str] = None, *, allow_empty: bool = False) -> Optional[str]:
    """读取环境变量并移除尾随注释/空白。

    允许用户在 .env 中写入 ``VALUE  # comment``，同时保持默认值回退逻辑。
    """

    raw = os.environ.get(key)
    if raw is None:
        return default
    first_line = raw.splitlines()[0]
    cleaned = _INLINE_COMMENT_PATTERN.sub("", first_line).strip()
    if cleaned == "" and not allow_empty:
        return default
    return cleaned


def get_system_name() -> str:
    """获取系统名称，优先级：SYSTEM_NAME > PROJECT_NAME > "Drun"""

    return get_env_clean("SYSTEM_NAME") or get_env_clean("PROJECT_NAME", "Drun") or "Drun"
