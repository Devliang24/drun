"""
E2E 测试：验证 httpstat 数据在整个系统中的流动
"""

import tempfile
import json
from pathlib import Path
from drun.models.case import Case
from drun.models.config import Config
from drun.models.step import Step
from drun.models.request import StepRequest
from drun.runner.runner import Runner
from drun.reporter.json_reporter import write_json
from drun.utils.logging import get_logger


def test_httpstat_end_to_end_with_runner():
    """测试从 Runner 到 Report 的完整 httpstat 数据流"""
    # 创建一个简单的测试用例
    case = Case(
        config=Config(
            name="Test HTTP Stat E2E",
            base_url="https://httpbin.org"
        ),
        steps=[
            Step(
                name="Get Request",
                request=StepRequest(
                    method="GET",
                    path="/get",
                    params={"test": "httpstat"}
                )
            )
        ]
    )
    
    logger = get_logger("test")
    
    # 创建启用了 http_stat 的 Runner
    runner = Runner(
        log=logger,
        enable_http_stat=True
    )
    
    # 运行测试用例
    result = runner.run_case(case, global_vars={}, params={})
    
    # 验证结果
    assert result.status == "passed"
    assert len(result.steps) == 1
    
    step_result = result.steps[0]
    assert step_result.name == "Get Request"
    assert step_result.status == "passed"
    
    # 验证 httpstat 存在且有效
    assert step_result.httpstat is not None
    assert "total" in step_result.httpstat
    assert step_result.httpstat["total"] > 0
    assert "dns_lookup" in step_result.httpstat
    assert "tcp_connection" in step_result.httpstat
    assert "tls_handshake" in step_result.httpstat
    assert "server_processing" in step_result.httpstat
    assert "content_transfer" in step_result.httpstat


def test_httpstat_disabled_by_default():
    """测试默认情况下不包含 httpstat"""
    case = Case(
        config=Config(
            name="Test No HTTP Stat",
            base_url="https://httpbin.org"
        ),
        steps=[
            Step(
                name="Get Request",
                request=StepRequest(
                    method="GET",
                    path="/get"
                )
            )
        ]
    )
    
    logger = get_logger("test")
    
    # 创建默认的 Runner（未启用 http_stat）
    runner = Runner(log=logger)
    
    # 运行测试用例
    result = runner.run_case(case, global_vars={}, params={})
    
    # 验证结果
    assert result.status == "passed"
    step_result = result.steps[0]
    
    # httpstat 应该是 None
    assert step_result.httpstat is None


def test_httpstat_in_json_report():
    """测试 httpstat 数据能正确写入 JSON 报告"""
    case = Case(
        config=Config(
            name="Test JSON Report",
            base_url="https://httpbin.org"
        ),
        steps=[
            Step(
                name="POST Request",
                request=StepRequest(
                    method="POST",
                    path="/post",
                    body={"test": "data"}
                )
            )
        ]
    )
    
    logger = get_logger("test")
    runner = Runner(log=logger, enable_http_stat=True)
    
    # 运行测试
    case_result = runner.run_case(case, global_vars={}, params={})
    
    # 创建报告
    from drun.models.report import RunReport
    report = RunReport(
        summary={
            "total_cases": 1,
            "passed_cases": 1,
            "failed_cases": 0,
        },
        cases=[case_result]
    )
    
    # 写入临时文件
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = Path(tmpdir) / "summary.json"
        write_json(report, json_path)
        
        # 读取并验证
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        assert "cases" in data
        assert len(data["cases"]) == 1
        assert "steps" in data["cases"][0]
        assert len(data["cases"][0]["steps"]) == 1
        
        step_data = data["cases"][0]["steps"][0]
        assert "httpstat" in step_data
        assert step_data["httpstat"] is not None
        assert "total" in step_data["httpstat"]
        assert step_data["httpstat"]["total"] > 0


def test_httpstat_multiple_steps():
    """测试多个步骤都包含 httpstat"""
    case = Case(
        config=Config(
            name="Test Multiple Steps",
            base_url="https://httpbin.org"
        ),
        steps=[
            Step(
                name="Step 1 - GET",
                request=StepRequest(method="GET", path="/get")
            ),
            Step(
                name="Step 2 - POST",
                request=StepRequest(
                    method="POST",
                    path="/post",
                    body={"step": 2}
                )
            ),
            Step(
                name="Step 3 - PUT",
                request=StepRequest(
                    method="PUT",
                    path="/put",
                    body={"step": 3}
                )
            ),
        ]
    )
    
    logger = get_logger("test")
    runner = Runner(log=logger, enable_http_stat=True)
    
    result = runner.run_case(case, global_vars={}, params={})
    
    assert result.status == "passed"
    assert len(result.steps) == 3
    
    # 验证每个步骤都有 httpstat
    for i, step in enumerate(result.steps, 1):
        assert step.httpstat is not None
        assert step.httpstat["total"] > 0
        print(f"Step {i} total time: {step.httpstat['total']}ms")
