"""
配置工具模块
提供统一的配置访问接口
"""
import os


def get_system_name():
    """
    获取系统名称，优先级：SYSTEM_NAME > PROJECT_NAME > "Drun"

    Returns:
        str: 系统名称
    """
    return os.environ.get("SYSTEM_NAME") or os.environ.get("PROJECT_NAME", "Drun")