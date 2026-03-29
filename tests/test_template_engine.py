from __future__ import annotations

import unittest

from drun.models.case import Case
from drun.models.config import Config
from drun.models.request import StepRequest
from drun.models.step import Step
from drun.runner.runner import Runner
from drun.templating.engine import TemplateEngine, UnresolvedVarError


class TemplateEngineStrictModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = TemplateEngine()

    def test_strict_mode_raises_unresolved_var_for_missing_simple_name(self) -> None:
        with self.assertRaises(UnresolvedVarError) as ctx:
            self.engine.render_value("${missing_var}", {}, strict=True)

        self.assertIn("missing_var", str(ctx.exception))

    def test_strict_mode_reports_missing_root_name_for_attribute_expression(self) -> None:
        with self.assertRaises(UnresolvedVarError) as ctx:
            self.engine.render_value("${user.name}", {}, strict=True)

        self.assertIn("user", str(ctx.exception))
        self.assertNotIn("user.name", str(ctx.exception))

    def test_strict_mode_preserves_runtime_error_for_full_expression(self) -> None:
        with self.assertRaises(ZeroDivisionError):
            self.engine.render_value("${1/0}", {}, strict=True)

    def test_strict_mode_rejects_missing_var_inside_string(self) -> None:
        with self.assertRaises(UnresolvedVarError) as ctx:
            self.engine.render_value("https://x/${missing_var}", {}, strict=True)

        self.assertIn("missing_var", str(ctx.exception))

    def test_strict_mode_rejects_missing_root_name_inside_string_expression(self) -> None:
        with self.assertRaises(UnresolvedVarError) as ctx:
            self.engine.render_value("https://x/${items[0]}", {}, strict=True)

        self.assertIn("items", str(ctx.exception))

    def test_strict_mode_preserves_runtime_error_inside_string_expression(self) -> None:
        with self.assertRaises(ZeroDivisionError):
            self.engine.render_value("https://x/${1/0}", {}, strict=True)

    def test_non_strict_mode_keeps_unresolved_token(self) -> None:
        rendered = self.engine.render_value("https://x/${missing_var}", {}, strict=False)
        self.assertEqual(rendered, "https://x/${missing_var}")


class _FakeHTTPClient:
    def __init__(self) -> None:
        self.request_called = False
        self.closed = False

    def request(self, req):
        self.request_called = True
        raise AssertionError("HTTP request should not be sent when strict rendering fails")

    def close(self) -> None:
        self.closed = True


class RunnerStrictRenderingTests(unittest.TestCase):
    def test_run_case_fails_before_http_for_unresolved_request_expression(self) -> None:
        runner = Runner(log=None)
        fake_client = _FakeHTTPClient()
        runner._build_client = lambda case: fake_client
        case = Case(
            config=Config(name="Strict Unresolved", base_url="https://example.test"),
            steps=[
                Step(
                    name="Step 1: Missing",
                    request=StepRequest(method="GET", path="https://x/${missing_var}"),
                )
            ],
        )

        with self.assertRaises(UnresolvedVarError) as ctx:
            runner.run_case(case, global_vars={}, params={}, funcs={}, envmap={})

        self.assertIn("missing_var", str(ctx.exception))
        self.assertFalse(fake_client.request_called)
        self.assertTrue(fake_client.closed)

    def test_run_case_preserves_runtime_error_before_http(self) -> None:
        runner = Runner(log=None)
        fake_client = _FakeHTTPClient()
        runner._build_client = lambda case: fake_client
        case = Case(
            config=Config(name="Strict Runtime Error", base_url="https://example.test"),
            steps=[
                Step(
                    name="Step 1: Runtime",
                    request=StepRequest(method="GET", path="https://x/${1/0}"),
                )
            ],
        )

        with self.assertRaises(ZeroDivisionError):
            runner.run_case(case, global_vars={}, params={}, funcs={}, envmap={})

        self.assertFalse(fake_client.request_called)
        self.assertTrue(fake_client.closed)


if __name__ == "__main__":
    unittest.main()
