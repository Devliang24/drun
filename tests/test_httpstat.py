"""
单元测试：HttpStat 数据模型
"""

import pytest
from drun.models.httpstat import HttpStat


def test_httpstat_basic_calculation():
    """测试基本的时间计算"""
    stat = HttpStat(
        namelookup=40.0,
        connect=325.0,
        pretransfer=905.0,
        starttransfer=1264.0,
        total=1264.0
    )
    
    assert stat.dns_lookup == 40.0
    assert stat.tcp_connection == 285.0  # 325 - 40
    assert stat.tls_handshake == 580.0   # 905 - 325
    assert stat.server_processing == 359.0  # 1264 - 905
    assert stat.content_transfer == 0.0  # 1264 - 1264


def test_httpstat_http_no_tls():
    """测试 HTTP 请求（无 TLS 握手）"""
    stat = HttpStat(
        namelookup=20.0,
        connect=150.0,
        pretransfer=150.0,  # HTTP 时 pretransfer = connect
        starttransfer=500.0,
        total=520.0
    )
    
    assert stat.dns_lookup == 20.0
    assert stat.tcp_connection == 130.0
    assert stat.tls_handshake == 0.0  # 无 TLS
    assert stat.server_processing == 350.0
    assert stat.content_transfer == 20.0
    assert not stat.is_https()


def test_httpstat_connection_reuse():
    """测试连接复用场景（Keep-Alive）"""
    stat = HttpStat(
        namelookup=0.0,
        connect=0.0,
        pretransfer=0.0,
        starttransfer=200.0,
        total=250.0
    )
    
    assert stat.dns_lookup == 0.0
    assert stat.tcp_connection == 0.0
    assert stat.tls_handshake == 0.0
    assert stat.server_processing == 200.0
    assert stat.content_transfer == 50.0
    assert stat.is_connection_reused()


def test_httpstat_to_dict():
    """测试序列化为字典"""
    stat = HttpStat(
        namelookup=40.5,
        connect=325.7,
        pretransfer=905.3,
        starttransfer=1264.9,
        total=1264.9
    )
    
    data = stat.to_dict()
    assert data["dns_lookup"] == 40.5
    assert data["tcp_connection"] == 285.2  # 325.7 - 40.5
    assert data["total"] == 1264.9
    assert "namelookup" in data  # 包含原始时间点


def test_httpstat_from_dict():
    """测试从字典反序列化"""
    data = {
        "namelookup": 40.0,
        "connect": 325.0,
        "pretransfer": 905.0,
        "starttransfer": 1264.0,
        "total": 1264.0
    }
    
    stat = HttpStat.from_dict(data)
    assert stat.namelookup == 40.0
    assert stat.dns_lookup == 40.0
    assert stat.tcp_connection == 285.0


def test_httpstat_zero_values():
    """测试全零值场景"""
    stat = HttpStat()
    
    assert stat.total == 0.0
    assert stat.dns_lookup == 0.0
    assert stat.is_connection_reused()


def test_httpstat_negative_prevention():
    """测试防止负值（异常数据）"""
    # 故意设置不合理的时间点顺序
    stat = HttpStat(
        namelookup=100.0,
        connect=50.0,  # 比 namelookup 小（不合理）
        pretransfer=150.0,
        starttransfer=200.0,
        total=250.0
    )
    
    # 应该用 max(0, ...) 避免负值
    assert stat.tcp_connection >= 0.0


def test_httpstat_large_file_transfer():
    """测试大文件传输场景（content_transfer 时间长）"""
    stat = HttpStat(
        namelookup=30.0,
        connect=200.0,
        pretransfer=800.0,
        starttransfer=1000.0,
        total=5000.0  # 大部分时间在传输
    )
    
    assert stat.content_transfer == 4000.0
    assert stat.content_transfer > stat.server_processing


def test_httpstat_is_https():
    """测试 HTTPS 判断"""
    https_stat = HttpStat(
        namelookup=10.0,
        connect=100.0,
        pretransfer=500.0,  # 有 TLS 握手时间
        starttransfer=600.0,
        total=650.0
    )
    assert https_stat.is_https()
    
    http_stat = HttpStat(
        namelookup=10.0,
        connect=100.0,
        pretransfer=100.0,  # 无 TLS 握手
        starttransfer=200.0,
        total=250.0
    )
    assert not http_stat.is_https()
