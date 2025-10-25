from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class HttpStat:
    """HTTP 请求各阶段耗时统计（单位：毫秒）
    
    参考 httpstat 和 curl -w 的时间指标：
    - namelookup: DNS 解析完成时间点
    - connect: TCP 连接完成时间点
    - pretransfer: TLS 握手完成时间点（HTTP 则等于 connect）
    - starttransfer: 接收到第一个字节的时间点
    - total: 请求总耗时
    
    各阶段耗时计算：
    - dns_lookup = namelookup
    - tcp_connection = connect - namelookup
    - tls_handshake = pretransfer - connect
    - server_processing = starttransfer - pretransfer
    - content_transfer = total - starttransfer
    """
    
    # 累计时间点（毫秒）
    namelookup: float = 0.0
    connect: float = 0.0
    pretransfer: float = 0.0
    starttransfer: float = 0.0
    total: float = 0.0
    
    # 各阶段耗时（毫秒）- 自动计算
    dns_lookup: float = field(init=False, default=0.0)
    tcp_connection: float = field(init=False, default=0.0)
    tls_handshake: float = field(init=False, default=0.0)
    server_processing: float = field(init=False, default=0.0)
    content_transfer: float = field(init=False, default=0.0)
    
    def __post_init__(self) -> None:
        """根据时间点自动计算各阶段耗时"""
        self.calculate()
    
    def calculate(self) -> None:
        """计算各阶段耗时"""
        self.dns_lookup = max(0.0, self.namelookup)
        self.tcp_connection = max(0.0, self.connect - self.namelookup)
        self.tls_handshake = max(0.0, self.pretransfer - self.connect)
        self.server_processing = max(0.0, self.starttransfer - self.pretransfer)
        self.content_transfer = max(0.0, self.total - self.starttransfer)
    
    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式（用于 JSON 序列化）"""
        return {
            "dns_lookup": round(self.dns_lookup, 2),
            "tcp_connection": round(self.tcp_connection, 2),
            "tls_handshake": round(self.tls_handshake, 2),
            "server_processing": round(self.server_processing, 2),
            "content_transfer": round(self.content_transfer, 2),
            "total": round(self.total, 2),
            # 包含原始时间点（用于调试）
            "namelookup": round(self.namelookup, 2),
            "connect": round(self.connect, 2),
            "pretransfer": round(self.pretransfer, 2),
            "starttransfer": round(self.starttransfer, 2),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> HttpStat:
        """从字典创建实例"""
        return cls(
            namelookup=float(data.get("namelookup", 0.0)),
            connect=float(data.get("connect", 0.0)),
            pretransfer=float(data.get("pretransfer", 0.0)),
            starttransfer=float(data.get("starttransfer", 0.0)),
            total=float(data.get("total", 0.0)),
        )
    
    def is_connection_reused(self) -> bool:
        """判断是否复用了已有连接（Keep-Alive）
        
        如果 DNS、TCP、TLS 都为 0，说明复用了连接
        """
        return self.dns_lookup == 0.0 and self.tcp_connection == 0.0 and self.tls_handshake == 0.0
    
    def is_https(self) -> bool:
        """判断是否为 HTTPS 请求（有 TLS 握手）"""
        return self.tls_handshake > 0.0
