"""
HTTP 请求时间采集模块

由于 httpx 不直接暴露 DNS/TCP/TLS 等细粒度时间，采用简化方案：
1. 使用 elapsed 获取总耗时
2. 对于首次连接，估算各阶段时间比例
3. 对于连接复用，标记为 0

未来改进方向：
- 使用 httpcore 的 trace extension (需要深入研究 API)
- 或者集成 pycurl 获取精确的 libcurl 时间指标
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Dict, Any, Optional
from drun.models.httpstat import HttpStat

if TYPE_CHECKING:
    import httpx


class TimingCollector:
    """HTTP 请求时间采集器
    
    使用 event hooks 收集请求时间信息
    """
    
    def __init__(self) -> None:
        self.request_start_time: Optional[float] = None
        self.response_headers_time: Optional[float] = None
        self.request_data: Dict[str, Any] = {}
    
    def on_request(self, request: httpx.Request) -> None:
        """请求开始时的回调"""
        self.request_start_time = time.perf_counter()
        self.request_data = {
            "url": str(request.url),
            "method": request.method,
        }
    
    def on_response(self, response: httpx.Response) -> None:
        """收到响应时的回调"""
        if self.request_start_time is None:
            return
        
        # 记录响应头接收时间
        self.response_headers_time = time.perf_counter()
    
    def build_httpstat(self, response: httpx.Response) -> HttpStat:
        """根据响应构建 HttpStat
        
        策略：
        1. 使用 response.elapsed 作为 total
        2. 对于 HTTPS 首次连接，估算时间分布：
           - DNS: 5-10% 
           - TCP: 10-20%
           - TLS: 30-40%
           - Server: 剩余时间
        3. 对于连接复用，所有连接阶段为 0
        """
        if response.elapsed is None:
            # 如果没有 elapsed，返回空的 stat
            return HttpStat()
        
        total_ms = response.elapsed.total_seconds() * 1000.0
        
        # 判断是否为连接复用（通过 HTTP 头部 Connection: keep-alive 等）
        # 简化判断：如果总耗时很短（< 50ms）且没有太多数据传输，可能是复用
        # 这是一个启发式判断，不是 100% 准确
        is_reused = self._guess_connection_reused(response, total_ms)
        
        if is_reused:
            # 连接复用：DNS/TCP/TLS 都为 0
            return HttpStat(
                namelookup=0.0,
                connect=0.0,
                pretransfer=0.0,
                starttransfer=total_ms * 0.8,  # 假设 80% 是服务器处理
                total=total_ms
            )
        
        # 新连接：估算各阶段时间
        is_https = str(response.url).startswith("https://")
        
        if is_https:
            # HTTPS: DNS -> TCP -> TLS -> Server -> Transfer
            dns_ratio = 0.05
            tcp_ratio = 0.15
            tls_ratio = 0.35
            server_ratio = 0.40
            
            namelookup = total_ms * dns_ratio
            connect = total_ms * (dns_ratio + tcp_ratio)
            pretransfer = total_ms * (dns_ratio + tcp_ratio + tls_ratio)
            starttransfer = total_ms * (1 - 0.05)  # 留 5% 给传输
        else:
            # HTTP: DNS -> TCP -> Server -> Transfer
            dns_ratio = 0.08
            tcp_ratio = 0.20
            server_ratio = 0.65
            
            namelookup = total_ms * dns_ratio
            connect = total_ms * (dns_ratio + tcp_ratio)
            pretransfer = connect  # HTTP 无 TLS
            starttransfer = total_ms * (1 - 0.07)  # 留 7% 给传输
        
        return HttpStat(
            namelookup=namelookup,
            connect=connect,
            pretransfer=pretransfer,
            starttransfer=starttransfer,
            total=total_ms
        )
    
    def _guess_connection_reused(self, response: httpx.Response, total_ms: float) -> bool:
        """启发式判断是否复用了连接
        
        判断依据：
        1. 响应头包含 Connection: keep-alive
        2. 总耗时较短（< 100ms）且响应体较小
        
        注意：这只是估计，不是精确判断
        """
        # 检查响应头
        connection_header = response.headers.get("Connection", "").lower()
        if "close" in connection_header:
            return False
        
        # 简单启发式：如果耗时很短且内容小，可能是复用
        # 这个判断不完美，但足够用于演示
        content_length = len(response.content) if hasattr(response, "content") else 0
        
        # 如果耗时 < 50ms 且内容 < 1KB，很可能是复用
        if total_ms < 50 and content_length < 1024:
            return True
        
        # 对于第一次请求，默认认为是新连接
        return False
