"""
控制台 HTTP 耗时统计展示

参考 httpstat 和 HttpRunner 的输出格式
"""

from __future__ import annotations

from typing import Dict, Optional
from drun.models.httpstat import HttpStat


def format_httpstat(httpstat_data: Dict[str, float], url: str = "", protocol: str = "HTTPS") -> str:
    """格式化 httpstat 数据为可视化时间轴
    
    Args:
        httpstat_data: HttpStat.to_dict() 返回的字典
        url: 请求的 URL
        protocol: 协议类型（HTTP/HTTPS）
    
    Returns:
        格式化的字符串，包含时间轴和统计信息
    """
    # 从字典创建 HttpStat 对象
    stat = HttpStat.from_dict(httpstat_data)
    
    # 判断协议
    is_https = stat.is_https()
    is_reused = stat.is_connection_reused()
    
    # 构建输出
    lines = []
    
    # 连接信息
    if url:
        lines.append(f"\nConnected to: {url}")
    
    if is_reused:
        lines.append("(Connection reused - Keep-Alive)")
    else:
        proto_str = "HTTPS (TLS)" if is_https else "HTTP"
        lines.append(f"Protocol: {proto_str}")
    
    # 时间轴
    lines.append("")
    lines.append(_build_timeline(stat, is_https))
    lines.append("")
    
    # 统计信息
    lines.append(_build_stats_summary(stat))
    
    return "\n".join(lines)


def _build_timeline(stat: HttpStat, is_https: bool) -> str:
    """构建时间轴图形
    
    类似 httpstat 的输出：
      DNS Lookup   TCP Connection   TLS Handshake   Server Processing   Content Transfer
    [     40ms  |         284ms  |        579ms  |            359ms  |             0ms  ]
             |                |               |                   |                  |
    namelookup:40ms           |               |                   |                  |
                        connect:325ms         |                   |                  |
                                    pretransfer:905ms             |                  |
                                                      starttransfer:1264ms           |
                                                                                 total:1264ms
    """
    lines = []
    
    # 各阶段名称和耗时
    if is_https:
        stages = [
            ("DNS Lookup", stat.dns_lookup),
            ("TCP Connection", stat.tcp_connection),
            ("TLS Handshake", stat.tls_handshake),
            ("Server Processing", stat.server_processing),
            ("Content Transfer", stat.content_transfer),
        ]
    else:
        stages = [
            ("DNS Lookup", stat.dns_lookup),
            ("TCP Connection", stat.tcp_connection),
            ("Server Processing", stat.server_processing),
            ("Content Transfer", stat.content_transfer),
        ]
    
    # 第一行：阶段名称
    stage_names = "  ".join(f"{name:^18}" for name, _ in stages)
    lines.append(stage_names)
    
    # 第二行：时间条（简化版）
    time_bars = "  |  ".join(f"{dur:>8.0f}ms" for _, dur in stages)
    lines.append(f"[  {time_bars}  ]")
    
    # 第三行：分隔符
    sep_line = "  " + "  |  ".join("         " for _ in stages)
    lines.append(sep_line)
    
    # 累计时间点
    indent = "   "
    lines.append(f"{indent}namelookup:{stat.namelookup:.0f}ms")
    
    indent += "         "
    lines.append(f"{indent}connect:{stat.connect:.0f}ms")
    
    indent += "         "
    lines.append(f"{indent}pretransfer:{stat.pretransfer:.0f}ms")
    
    indent += "         "
    lines.append(f"{indent}starttransfer:{stat.starttransfer:.0f}ms")
    
    indent += "         "
    lines.append(f"{indent}total:{stat.total:.0f}ms")
    
    return "\n".join(lines)


def _build_stats_summary(stat: HttpStat) -> str:
    """构建简洁的统计摘要"""
    return (
        f"HTTP Timing (ms): "
        f"DNS={stat.dns_lookup:.0f}, "
        f"TCP={stat.tcp_connection:.0f}, "
        f"TLS={stat.tls_handshake:.0f}, "
        f"Server={stat.server_processing:.0f}, "
        f"Transfer={stat.content_transfer:.0f}, "
        f"Total={stat.total:.0f}"
    )


def format_httpstat_rich(httpstat_data: Dict[str, float], url: str = "") -> str:
    """使用 Rich 库增强的格式化输出
    
    添加颜色和更好的视觉效果
    """
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text
        
        stat = HttpStat.from_dict(httpstat_data)
        
        # 创建时间轴文本
        timeline = _build_timeline_rich(stat)
        summary = _build_stats_summary(stat)
        
        # 使用 Panel 展示
        content = timeline + "\n\n" + summary
        
        # 根据总耗时添加颜色标记
        if stat.total < 500:
            border_style = "green"
            title_emoji = "✓"
        elif stat.total < 2000:
            border_style = "yellow"
            title_emoji = "⚠"
        else:
            border_style = "red"
            title_emoji = "⚠"
        
        panel = Panel(
            content,
            title=f"{title_emoji} HTTP Request Timing",
            border_style=border_style,
            padding=(1, 2)
        )
        
        # 渲染到字符串
        console = Console(record=True, width=100)
        console.print(panel)
        return console.export_text()
        
    except ImportError:
        # Rich 库不可用时回退到简单版本
        return format_httpstat(httpstat_data, url)


def _build_timeline_rich(stat: HttpStat) -> str:
    """构建带颜色的时间轴"""
    try:
        from rich.text import Text
        
        is_https = stat.is_https()
        
        # 构建简单的文本时间轴
        lines = []
        lines.append(f"DNS Lookup:        {stat.dns_lookup:>7.1f} ms")
        lines.append(f"TCP Connection:    {stat.tcp_connection:>7.1f} ms")
        if is_https:
            lines.append(f"TLS Handshake:     {stat.tls_handshake:>7.1f} ms")
        lines.append(f"Server Processing: {stat.server_processing:>7.1f} ms")
        lines.append(f"Content Transfer:  {stat.content_transfer:>7.1f} ms")
        lines.append("─" * 40)
        lines.append(f"Total Time:        {stat.total:>7.1f} ms")
        
        return "\n".join(lines)
        
    except ImportError:
        return _build_timeline(stat, stat.is_https())


# 简单的打印函数（用于测试）
def print_httpstat(httpstat_data: Dict[str, float], url: str = "", use_rich: bool = True) -> None:
    """打印 httpstat 到控制台
    
    Args:
        httpstat_data: HttpStat 数据字典
        url: 请求 URL
        use_rich: 是否使用 rich 库增强输出
    """
    if use_rich:
        try:
            from rich.console import Console
            console = Console()
            output = format_httpstat_rich(httpstat_data, url)
            print(output)
            return
        except ImportError:
            pass
    
    # 回退到简单输出
    output = format_httpstat(httpstat_data, url)
    print(output)
