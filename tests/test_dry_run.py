"""Tests for `drun r -dry-run`."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from drun.commands.dry_run import build_dry_run_plan_text
from drun.loader.yaml_loader import expand_parameters, load_yaml_file
from drun.models.case import Case
from drun.models.config import Config
from drun.models.request import StepRequest
from drun.models.step import Step
from drun.models.checks import normalize_checks


class BuildDryRunPlanTests(unittest.TestCase):
    """Unit tests for build_dry_run_plan_text output structure."""

    def _build_items(self, case: Case) -> list[tuple[Case, dict, list[dict]]]:
        param_sets = expand_parameters(case.parameters, source_path="test.yaml")
        return [(case, {"file": "test.yaml"}, param_sets)]

    def test_empty_plan_shows_zero_requests(self) -> None:
        case = Case(
            config=Config(name="Empty"),
            steps=[],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("DRY RUN", text)
        self.assertIn("HTTP requests sent: 0", text)
        self.assertIn("Cases: 1", text)

    def test_simple_request_step_preview(self) -> None:
        case = Case(
            config=Config(name="Ping", base_url="https://api.example.com"),
            steps=[
                Step(
                    name="Ping",
                    request=StepRequest(method="GET", path="/ping"),
                    checks=normalize_checks([{"eq": ["status_code", 200]}]),
                )
            ],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url="https://api.example.com",
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("request  GET /ping", text)
        self.assertIn("checks: eq(status_code, 200)", text)

    def test_request_step_with_extract_and_check(self) -> None:
        case = Case(
            config=Config(name="Login"),
            steps=[
                Step(
                    name="Login",
                    request=StepRequest(method="POST", path="/login"),
                    checks=normalize_checks(
                        [{"eq": ["status_code", 200]}, {"exists": ["$.data.token", True]}]
                    ),
                    extract={"token": "$.data.token", "user_id": "$.data.user_id"},
                )
            ],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("request  POST /login", text)
        self.assertIn("checks: eq(status_code, 200), exists($.data.token, True)", text)
        self.assertIn("extracts: token <= $.data.token, user_id <= $.data.user_id", text)

    def test_invoke_step_preview(self) -> None:
        case = Case(
            config=Config(name="Flow"),
            steps=[Step(name="Call Login", invoke="tc_login")],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("invoke   tc_login", text)

    def test_invoke_step_with_repeat(self) -> None:
        case = Case(
            config=Config(name="Flow"),
            steps=[
                Step(name="Poll", invoke="tc_status", repeat=3)
            ],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("invoke   tc_status repeat=3", text)

    def test_invoke_step_with_case_name_selector(self) -> None:
        case = Case(
            config=Config(name="Flow"),
            steps=[
                Step(
                    name="Select",
                    invoke="tc_multi",
                    invoke_case_name="获取 token",
                )
            ],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("invoke   tc_multi", text)
        self.assertIn("case=获取 token", text)

    def test_invoke_step_with_case_names_selector(self) -> None:
        case = Case(
            config=Config(name="Flow"),
            steps=[
                Step(
                    name="Select",
                    invoke="tc_multi",
                    invoke_case_names=["获取 token", "刷新 token"],
                )
            ],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("invoke   tc_multi", text)
        self.assertIn("cases=获取 token,刷新 token", text)

    def test_sleep_step_preview(self) -> None:
        case = Case(
            config=Config(name="Pause"),
            steps=[Step(name="Wait", sleep=500)],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("sleep    500ms", text)

    def test_parameter_expansion_shows_all_instances(self) -> None:
        """Array parameters produce correct instance count and display."""
        case = Case(
            config=Config(name="Multi"),
            parameters=[{"user_id": [1, 2, 3]}],
            steps=[
                Step(
                    name="Get user",
                    request=StepRequest(method="GET", path="/users/${user_id}"),
                )
            ],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("Instances: 3", text)
        self.assertIn("user_id=1", text)
        self.assertIn("user_id=2", text)
        self.assertIn("user_id=3", text)
        self.assertIn("Case instances: 3", text)

    def test_parameter_truncation_respects_limit(self) -> None:
        """When instances exceed dry_run_limit, only N are shown."""
        case = Case(
            config=Config(name="Many"),
            parameters=[{"n": list(range(100))}],
            steps=[
                Step(
                    name="Ping",
                    request=StepRequest(method="GET", path="/ping"),
                )
            ],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=5,
            reveal_secrets=True,
        )

        self.assertIn("Instances: 100", text)
        self.assertIn("and 95 more instance(s)", text)
        self.assertIn("-dry-run-limit 100", text)

    def test_request_renders_static_variables(self) -> None:
        """Path variables from config.variables and params render correctly."""
        case = Case(
            config=Config(name="Render", variables={"prefix": "v2"}),
            steps=[
                Step(
                    name="Fetch",
                    request=StepRequest(
                        method="GET", path="/${prefix}/users/${user_id}"
                    ),
                )
            ],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={"user_id": "42"},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("GET /v2/users/42", text)

    def test_tags_and_selector_in_output(self) -> None:
        case = Case(
            config=Config(name="Tagged", tags=["smoke", "critical"]),
            steps=[
                Step(
                    name="Ping",
                    request=StepRequest(method="GET", path="/ping"),
                )
            ],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="dev",
            env_file_label=".env.dev",
            base_url="https://api.example.com",
            files_count=2,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter="smoke and not slow",
            case_selector=["Tagged"],
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("Tags: smoke, critical", text)
        self.assertIn("Tag filter: smoke and not slow", text)
        self.assertIn("Case selector: Tagged", text)
        self.assertIn("Environment: dev", text)
        self.assertIn("Env file: .env.dev", text)

    def test_no_parameter_case_shows_one_instance(self) -> None:
        case = Case(
            config=Config(name="Simple"),
            steps=[
                Step(
                    name="Ping",
                    request=StepRequest(method="GET", path="/ping"),
                )
            ],
        )
        items = self._build_items(case)

        text = build_dry_run_plan_text(
            target="test.yaml",
            env_label="none",
            env_file_label="(none)",
            base_url=None,
            files_count=1,
            items=[(case, {"file": "test.yaml"})],
            parameterized_items=items,
            tag_filter=None,
            case_selector=None,
            global_vars={},
            env_store={},
            dry_run_limit=20,
            reveal_secrets=True,
        )

        self.assertIn("Instances: 1", text)
        self.assertIn("Params: (none)", text)


class YAMLLoadDryRunTests(unittest.TestCase):
    """Verify YAML loading still produces useful preview data."""

    def test_load_and_expand_from_file(self) -> None:
        with TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "tc_demo.yaml"
            case_file.write_text(
                """
config:
  name: Demo
  base_url: https://api.example.com
  parameters:
    - role: [admin, user]
steps:
  - name: Check role ${role}
    request:
      method: GET
      path: /roles/${role}
    check:
      - eq: [status_code, 200]
""".strip(),
                encoding="utf-8",
            )

            cases, meta = load_yaml_file(case_file)
            self.assertEqual(len(cases), 1)

            param_sets = expand_parameters(
                cases[0].parameters, source_path=meta.get("file")
            )
            self.assertEqual(len(param_sets), 2)

            items = [(cases[0], meta, param_sets)]

            text = build_dry_run_plan_text(
                target="tc_demo.yaml",
                env_label="none",
                env_file_label="(none)",
                base_url="https://api.example.com",
                files_count=1,
                items=[(cases[0], meta)],
                parameterized_items=items,
                tag_filter=None,
                case_selector=None,
                global_vars={},
                env_store={},
                dry_run_limit=20,
                reveal_secrets=True,
            )

            self.assertIn("Instances: 2", text)
            self.assertIn("role='admin'", text)
            self.assertIn("role='user'", text)
            self.assertIn("GET /roles/admin", text)
            self.assertIn("GET /roles/user", text)


if __name__ == "__main__":
    unittest.main()
