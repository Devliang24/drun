"""
测试控制台 httpstat 展示
"""

import pytest
from drun.reporter.console_reporter import (
    format_httpstat,
    format_httpstat_rich,
    _build_timeline,
    _build_stats_summary,
    print_httpstat
)
from drun.models.httpstat import HttpStat


def test_format_httpstat_basic():
    """测试基本的 httpstat 格式化"""
    httpstat_data = {
        "namelookup": 40.0,
        "connect": 325.0,
        "pretransfer": 905.0,
        "starttransfer": 1264.0,
        "total": 1264.0,
        "dns_lookup": 40.0,
        "tcp_connection": 285.0,
        "tls_handshake": 580.0,
        "server_processing": 359.0,
        "content_transfer": 0.0,
    }
    
    output = format_httpstat(httpstat_data, url="example.com:443")
    
    # 验证输出包含关键信息
    assert "Connected to: example.com:443" in output
    assert "DNS Lookup" in output
    assert "TCP Connection" in output
    assert "TLS Handshake" in output
    assert "Server Processing" in output
    assert "Content Transfer" in output
    assert "total:1264ms" in output or "Total=1264" in output


def test_format_httpstat_http():
    """测试 HTTP（非 HTTPS）请求的格式化"""
    httpstat_data = {
        "namelookup": 20.0,
        "connect": 150.0,
        "pretransfer": 150.0,  # HTTP 时等于 connect
        "starttransfer": 500.0,
        "total": 520.0,
        "dns_lookup": 20.0,
        "tcp_connection": 130.0,
        "tls_handshake": 0.0,
        "server_processing": 350.0,
        "content_transfer": 20.0,
    }
    
    output = format_httpstat(httpstat_data)
    
    # HTTP 请求不应该显示 TLS Handshake（或为 0）
    assert "DNS Lookup" in output
    assert "TCP Connection" in output
    # TLS 可能不出现或为 0
    
    # 验证没有 TLS 握手时间
    stat = HttpStat.from_dict(httpstat_data)
    assert not stat.is_https()


def test_format_httpstat_connection_reused():
    """测试连接复用的格式化"""
    httpstat_data = {
        "namelookup": 0.0,
        "connect": 0.0,
        "pretransfer": 0.0,
        "starttransfer": 200.0,
        "total": 250.0,
        "dns_lookup": 0.0,
        "tcp_connection": 0.0,
        "tls_handshake": 0.0,
        "server_processing": 200.0,
        "content_transfer": 50.0,
    }
    
    output = format_httpstat(httpstat_data)
    
    # 应该提示连接复用
    assert "Connection reused" in output or "Keep-Alive" in output


def test_build_timeline():
    """测试时间轴构建"""
    stat = HttpStat(
        namelookup=40.0,
        connect=325.0,
        pretransfer=905.0,
        starttransfer=1264.0,
        total=1264.0
    )
    
    timeline = _build_timeline(stat, is_https=True)
    
    # 验证时间轴包含关键元素
    assert "DNS Lookup" in timeline
    assert "TCP Connection" in timeline
    assert "TLS Handshake" in timeline
    assert "namelookup:40ms" in timeline
    assert "connect:325ms" in timeline
    assert "total:1264ms" in timeline


def test_build_stats_summary():
    """测试统计摘要构建"""
    stat = HttpStat(
        namelookup=40.0,
        connect=325.0,
        pretransfer=905.0,
        starttransfer=1264.0,
        total=1264.0
    )
    
    summary = _build_stats_summary(stat)
    
    # 验证摘要包含所有关键指标
    assert "DNS=40" in summary
    assert "TCP=285" in summary
    assert "TLS=580" in summary
    assert "Server=359" in summary
    assert "Total=1264" in summary


def test_format_httpstat_rich_fallback():
    """测试 Rich 格式化（如果可用）"""
    httpstat_data = {
        "namelookup": 100.0,
        "connect": 300.0,
        "pretransfer": 600.0,
        "starttransfer": 800.0,
        "total": 850.0,
        "dns_lookup": 100.0,
        "tcp_connection": 200.0,
        "tls_handshake": 300.0,
        "server_processing": 200.0,
        "content_transfer": 50.0,
    }
    
    # 尝试使用 rich 格式化
    output = format_httpstat_rich(httpstat_data, url="example.com")
    
    # 无论是否有 rich，都应该有输出
    assert len(output) > 0
    assert "DNS" in output or "Lookup" in output
    

def test_print_httpstat_doesnt_crash():
    """测试打印函数不会崩溃"""
    httpstat_data = {
        "namelookup": 50.0,
        "connect": 200.0,
        "pretransfer": 500.0,
        "starttransfer": 700.0,
        "total": 750.0,
        "dns_lookup": 50.0,
        "tcp_connection": 150.0,
        "tls_handshake": 300.0,
        "server_processing": 200.0,
        "content_transfer": 50.0,
    }
    
    # 测试不会抛出异常
    try:
        print_httpstat(httpstat_data, url="test.com", use_rich=True)
        print_httpstat(httpstat_data, url="test.com", use_rich=False)
    except Exception as e:
        pytest.fail(f"print_httpstat raised exception: {e}")


def test_format_httpstat_large_numbers():
    """测试大数值的格式化"""
    httpstat_data = {
        "namelookup": 500.0,
        "connect": 1500.0,
        "pretransfer": 3000.0,
        "starttransfer": 8000.0,
        "total": 10000.0,
        "dns_lookup": 500.0,
        "tcp_connection": 1000.0,
        "tls_handshake": 1500.0,
        "server_processing": 5000.0,
        "content_transfer": 2000.0,
    }
    
    output = format_httpstat(httpstat_data)
    
    # 验证大数值能正确显示
    assert "10000" in output or "10.0" in output.replace(" ", "")
    assert "5000" in output or "5.0" in output.replace(" ", "")


def test_format_httpstat_zero_values():
    """测试全零值的格式化"""
    httpstat_data = HttpStat().to_dict()
    
    output = format_httpstat(httpstat_data)
    
    # 应该能正常格式化，不抛出异常
    assert len(output) > 0
