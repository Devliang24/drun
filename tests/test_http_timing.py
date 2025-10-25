"""
集成测试：HTTP 时间采集功能
"""

import pytest
from drun.engine.http import HTTPClient
from drun.models.httpstat import HttpStat


def test_http_client_with_httpstat_enabled():
    """测试启用 http_stat 的 HTTP 客户端"""
    client = HTTPClient(
        base_url="https://httpbin.org",
        enable_http_stat=True
    )
    
    try:
        response = client.request({
            "method": "GET",
            "path": "/get",
            "params": {"test": "value"}
        })
        
        # 验证基本响应
        assert response["status_code"] == 200
        assert "httpstat" in response
        
        # 验证 httpstat 数据结构
        httpstat_data = response["httpstat"]
        assert "total" in httpstat_data
        assert "dns_lookup" in httpstat_data
        assert "tcp_connection" in httpstat_data
        assert "tls_handshake" in httpstat_data
        assert "server_processing" in httpstat_data
        assert "content_transfer" in httpstat_data
        
        # 验证时间值合理性
        assert httpstat_data["total"] > 0
        
        # 可以反序列化为 HttpStat 对象
        httpstat = HttpStat.from_dict(httpstat_data)
        assert httpstat.total > 0
        
    finally:
        client.close()


def test_http_client_without_httpstat():
    """测试未启用 http_stat 的 HTTP 客户端（默认行为）"""
    client = HTTPClient(base_url="https://httpbin.org")
    
    try:
        response = client.request({
            "method": "GET",
            "path": "/get"
        })
        
        # 验证基本响应
        assert response["status_code"] == 200
        
        # 不应该包含 httpstat
        assert "httpstat" not in response
        
        # 但应该有 elapsed_ms（原有功能）
        assert "elapsed_ms" in response
        assert response["elapsed_ms"] > 0
        
    finally:
        client.close()


def test_httpstat_https_request():
    """测试 HTTPS 请求的时间统计"""
    client = HTTPClient(
        base_url="https://httpbin.org",
        enable_http_stat=True
    )
    
    try:
        response = client.request({
            "method": "GET",
            "path": "/delay/1"  # 1 秒延迟
        })
        
        assert response["status_code"] == 200
        httpstat_data = response["httpstat"]
        
        # HTTPS 请求应该有 TLS 握手时间（首次连接）
        # 注意：由于连接复用，可能为 0
        assert httpstat_data["total"] >= 1000  # 至少 1 秒（因为有 delay）
        
        # 服务器处理时间应该占大部分
        assert httpstat_data["server_processing"] > 0
        
    finally:
        client.close()


def test_httpstat_http_request():
    """测试 HTTP 请求的时间统计（如果有可用的 HTTP 端点）"""
    client = HTTPClient(
        base_url="http://httpbin.org",
        enable_http_stat=True
    )
    
    try:
        response = client.request({
            "method": "GET",
            "path": "/get"
        })
        
        assert response["status_code"] == 200
        httpstat_data = response["httpstat"]
        
        # HTTP 请求可能没有 TLS 握手时间
        assert httpstat_data["total"] > 0
        
        # 验证可以创建 HttpStat 对象
        httpstat = HttpStat.from_dict(httpstat_data)
        
        # HTTP 请求的 is_https() 应该返回 False（如果没有 TLS）
        # 注意：由于估算算法，可能不准确
        
    finally:
        client.close()


def test_httpstat_post_request():
    """测试 POST 请求的时间统计"""
    client = HTTPClient(
        base_url="https://httpbin.org",
        enable_http_stat=True
    )
    
    try:
        response = client.request({
            "method": "POST",
            "path": "/post",
            "body": {"test": "data", "number": 123}
        })
        
        assert response["status_code"] == 200
        assert "httpstat" in response
        
        httpstat_data = response["httpstat"]
        assert httpstat_data["total"] > 0
        
    finally:
        client.close()


@pytest.mark.parametrize("method", ["GET", "POST", "PUT", "DELETE"])
def test_httpstat_different_methods(method):
    """测试不同 HTTP 方法的时间统计"""
    client = HTTPClient(
        base_url="https://httpbin.org",
        enable_http_stat=True
    )
    
    try:
        path_map = {
            "GET": "/get",
            "POST": "/post",
            "PUT": "/put",
            "DELETE": "/delete"
        }
        
        response = client.request({
            "method": method,
            "path": path_map[method],
            "body": {"test": "data"} if method != "GET" else None
        })
        
        assert response["status_code"] == 200
        assert "httpstat" in response
        assert response["httpstat"]["total"] > 0
        
    finally:
        client.close()
