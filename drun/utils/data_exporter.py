from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional


def export_to_csv(
    data: List[Dict[str, Any]],
    file_path: str,
    columns: Optional[List[str]] = None,
    encoding: str = "utf-8",
    mode: str = "overwrite",
    delimiter: str = ",",
    base_dir: Optional[Path] = None,
) -> int:
    """
    导出数组数据到 CSV 文件
    
    Args:
        data: 要导出的数组数据（字典列表）
        file_path: 输出文件路径（相对或绝对）
        columns: 要导出的列名列表（None=全部）
        encoding: 文件编码（默认：utf-8）
        mode: 写入模式 "overwrite" 或 "append"
        delimiter: CSV 分隔符（默认：逗号）
        base_dir: 基准目录（用于解析相对路径）
    
    Returns:
        导出的数据行数
        
    Raises:
        ValueError: 数据格式错误
        OSError: 文件写入失败
    """
    # 1. 数据验证
    if not isinstance(data, list):
        raise ValueError(
            f"export.csv.data 必须返回数组，实际类型：{type(data).__name__}"
        )
    
    # 2. 路径解析（与 CSV 参数化路径解析保持一致）
    path = Path(file_path).expanduser()
    if not path.is_absolute() and base_dir:
        path = base_dir / path
    
    # 确保父目录存在
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 3. 列名处理
    if data:
        first_row = data[0]
        if not isinstance(first_row, dict):
            raise ValueError(
                f"export.csv.data 数组元素必须是对象，实际类型：{type(first_row).__name__}"
            )
        
        available_columns = list(first_row.keys())
        
        if columns:
            # 验证指定的列是否存在
            missing = set(columns) - set(available_columns)
            if missing:
                raise ValueError(
                    f"export.csv.columns 指定的列不存在：{missing}\n"
                    f"可用列：{available_columns}"
                )
            fieldnames = columns
        else:
            # 使用所有列
            fieldnames = available_columns
    else:
        # 空数组：使用指定的 columns 或空 header
        fieldnames = columns or []
    
    # 4. 写入 CSV
    write_mode = "a" if mode == "append" else "w"
    file_exists = path.exists() and mode == "append"
    
    with path.open(write_mode, newline="", encoding=encoding) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            delimiter=delimiter,
            extrasaction="ignore",  # 忽略不在 fieldnames 中的列
        )
        
        # 写入 header（追加模式且文件已存在时跳过）
        if not file_exists:
            writer.writeheader()
        
        # 写入数据行
        writer.writerows(data)
    
    return len(data)
