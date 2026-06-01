from __future__ import annotations

from pathlib import Path
import re
from tempfile import TemporaryDirectory
import unittest

from tests.cli_runner import CliRunner

import drun.cli as cli
from drun.loader.yaml_loader import collect_yaml_diagnostics, load_yaml_file
from drun.utils.errors import (
    DIAGNOSTIC_CODE_CATALOG,
    DIAGNOSTIC_CODES,
    LoadError,
    is_known_diagnostic_code,
)


class DiagnosticCodeRegistryTests(unittest.TestCase):
    def test_registry_metadata_is_complete_and_unique(self) -> None:
        codes = [item.code for item in DIAGNOSTIC_CODE_CATALOG]

        self.assertEqual(len(codes), len(set(codes)))
        self.assertEqual(set(codes), set(DIAGNOSTIC_CODES))
        for code, item in DIAGNOSTIC_CODES.items():
            self.assertEqual(code, item.code)
            self.assertRegex(code, r"^DRUN-YAML-\d{3}$")
            self.assertTrue(item.title.strip())
            self.assertTrue(item.description.strip())
            self.assertTrue(is_known_diagnostic_code(code))

    def test_yaml_codes_used_by_implementation_are_registered(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        pattern = re.compile(r"DRUN-YAML-\d{3}")
        used_codes: set[str] = set()
        for path in (repo_root / "drun").rglob("*.py"):
            used_codes.update(pattern.findall(path.read_text(encoding="utf-8")))

        unknown_codes = used_codes - set(DIAGNOSTIC_CODES)
        self.assertFalse(
            unknown_codes,
            f"Register YAML diagnostic codes before using them: {sorted(unknown_codes)}",
        )


class YamlDiagnosticModelTests(unittest.TestCase):
    def test_check_field_loads_as_step_checks(self) -> None:
        with TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "test_check.yaml"
            case_file.write_text(
                """
config:
  name: Check DSL
steps:
  - name: ping
    request:
      method: GET
      path: /ping
    check:
      - eq: [status_code, 200]
""".strip(),
                encoding="utf-8",
            )

            cases, _ = load_yaml_file(case_file)

        self.assertEqual(cases[0].steps[0].checks[0].check, "status_code")

    def test_request_url_diagnostic_has_code_location_hint_and_example(self) -> None:
        with TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "test_bad.yaml"
            case_file.write_text(
                """
config:
  name: Bad URL
steps:
  - name: wrong field
    request:
      method: GET
      url: /api/users
""".strip(),
                encoding="utf-8",
            )

            diagnostics = collect_yaml_diagnostics(case_file)

            self.assertEqual(len(diagnostics), 1)
            diag = diagnostics[0]
            self.assertEqual(diag.code, "DRUN-YAML-003")
            self.assertIn("request.url", diag.message)
            self.assertEqual(diag.file, str(case_file))
            self.assertEqual(diag.line, 7)
            self.assertEqual(diag.path, "steps[0].request.url")
            self.assertIn("request.path", diag.hint or "")
            self.assertIn("path: /api/users", diag.example or "")

            with self.assertRaises(LoadError) as ctx:
                load_yaml_file(case_file)
            self.assertEqual(ctx.exception.diagnostic.code, "DRUN-YAML-003")

    def test_top_level_parameters_diagnostic_preserves_fix_example(self) -> None:
        with TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "test_users.yaml"
            case_file.write_text(
                """
parameters:
  - user_id: [1, 2, 3]
config:
  name: Users
steps:
  - name: ping
    request:
      method: GET
      path: /users
""".strip(),
                encoding="utf-8",
            )

            diagnostics = collect_yaml_diagnostics(case_file)

            self.assertEqual(diagnostics[0].code, "DRUN-YAML-006")
            self.assertIn("config.parameters", diagnostics[0].hint or "")
            self.assertIn("parameters:", diagnostics[0].example or "")

    def test_validate_field_reports_check_migration_diagnostic(self) -> None:
        with TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "test_legacy_validate.yaml"
            case_file.write_text(
                """
config:
  name: Legacy Validate
steps:
  - name: ping
    request:
      method: GET
      path: /ping
    validate:
      - eq: [status_code, 200]
""".strip(),
                encoding="utf-8",
            )

            diagnostics = collect_yaml_diagnostics(case_file)

            self.assertEqual(diagnostics[0].code, "DRUN-YAML-012")
            self.assertIn("renamed to check", diagnostics[0].message)
            self.assertEqual(diagnostics[0].path, "steps[0].validate")
            self.assertIn("Use `check` instead of `validate`", diagnostics[0].hint or "")
            self.assertIn("check:", diagnostics[0].example or "")

    def test_request_nested_validate_reports_check_migration_diagnostic(self) -> None:
        with TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "test_nested_legacy_validate.yaml"
            case_file.write_text(
                """
config:
  name: Nested Legacy Validate
steps:
  - name: ping
    request:
      method: GET
      path: /ping
      validate:
        - eq: [status_code, 200]
""".strip(),
                encoding="utf-8",
            )

            diagnostics = collect_yaml_diagnostics(case_file)

            self.assertEqual(diagnostics[0].code, "DRUN-YAML-012")
            self.assertEqual(diagnostics[0].path, "steps[0].request.validate")
            self.assertIn("Use `check` at the step level", diagnostics[0].hint or "")


class CheckCommandDiagnosticTests(unittest.TestCase):
    def test_check_aggregates_diagnostics_across_files(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("tc_a.yaml").write_text(
                """
config:
  name: A
steps:
  - name: bad json and check
    request:
      method: POST
      path: /users
      json:
        name: Alice
    check:
      - eq: [body.id, 1]
""".strip(),
                encoding="utf-8",
            )
            Path("tc_b.yaml").write_text(
                """
config:
  name: B
steps:
  - name: mixed target
    sleep: 1
    request:
      method: GET
      path: /ping
""".strip(),
                encoding="utf-8",
            )
            Path("tc_ok.yaml").write_text(
                """
config:
  name: OK
steps:
  - name: ping
    request:
      method: GET
      path: https://example.test/ping
""".strip(),
                encoding="utf-8",
            )

            result = runner.invoke(cli.app, ["c", "."])

        self.assertEqual(result.exit_code, 2)
        out = result.output
        self.assertIn("FAIL tc_a.yaml", out)
        self.assertIn("DRUN-YAML-004 request.json is not supported", out)
        self.assertIn("DRUN-YAML-007 Invalid check syntax: body.id", out)
        self.assertIn("FAIL tc_b.yaml", out)
        self.assertIn("DRUN-YAML-011 Step cannot combine", out)
        self.assertIn("OK tc_ok.yaml", out)
        self.assertIn("Checked 3 file(s): 1 OK, 2 failed, 3 error(s).", out)

    def test_check_limits_diagnostics_per_file(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            steps = []
            for idx in range(6):
                steps.append(
                    f"""
  - name: bad {idx}
    request:
      method: POST
      path: /users
      json:
        id: {idx}
""".rstrip()
                )
            Path("tc_many.yaml").write_text(
                "config:\n  name: Many\nsteps:\n" + "\n\n".join(steps),
                encoding="utf-8",
            )

            result = runner.invoke(cli.app, ["c", "tc_many.yaml"])

        self.assertEqual(result.exit_code, 2)
        self.assertEqual(result.output.count("DRUN-YAML-004"), 5)
        self.assertIn("... 1 more diagnostic(s) hidden for this file", result.output)
        self.assertIn("Checked 1 file(s): 0 OK, 1 failed, 6 error(s).", result.output)


class RunCommandDiagnosticTests(unittest.TestCase):
    def test_run_stops_on_first_yaml_diagnostic(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path(".env").write_text("BASE_URL=https://example.test\n", encoding="utf-8")
            Path("tc_bad.yaml").write_text(
                """
config:
  name: Bad URL
steps:
  - name: wrong field
    request:
      method: GET
      url: /api/users
""".strip(),
                encoding="utf-8",
            )

            result = runner.invoke(cli.app, ["r", "tc_bad.yaml"])

        self.assertEqual(result.exit_code, 2)
        self.assertIn("DRUN-YAML-003 Invalid request field: request.url", result.output)
        self.assertIn("Use `request.path` instead of `request.url`.", result.output)


if __name__ == "__main__":
    unittest.main()
