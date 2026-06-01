from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "drun-usage"


def _extract_fenced_yaml_blocks(text: str) -> list[str]:
    return re.findall(r"```ya?ml\n(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)


def _iter_skill_markdown_files() -> list[Path]:
    return sorted(SKILL_DIR.rglob("*.md"))


class DrunUsageSkillTests(unittest.TestCase):
    def test_anti_patterns_cover_common_invalid_dsl(self) -> None:
        anti_patterns = (SKILL_DIR / "references" / "anti-patterns.md").read_text(
            encoding="utf-8"
        )

        for expected in (
            "request.url",
            "request.path",
            "request.json",
            "request.body",
            "validate",
            "check",
            "cases",
            "caseflow",
            "loop",
            "foreach",
            "repeat",
            "request.files",
            "request.data",
            "顶层 `parameters`",
            "config.parameters",
            "sleep",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, anti_patterns)

    def test_agent_usage_covers_supported_agent_contexts(self) -> None:
        agent_usage = (SKILL_DIR / "references" / "agent-usage.md").read_text(
            encoding="utf-8"
        )

        for expected in (
            "pi",
            "Claude Code",
            "Codex",
            "通用",
            "~/.agents/skills",
            "~/.claude/skills",
            "drun-usage/SKILL.md",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, agent_usage)

    def test_cli_cheatsheet_mentions_core_commands(self) -> None:
        cheatsheet = (SKILL_DIR / "references" / "cli-cheatsheet.md").read_text(
            encoding="utf-8"
        )

        for expected in (
            "drun c",
            "drun r",
            "drun q",
            "drun o",
            "drun w",
            "drun e curl",
            "drun s",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, cheatsheet)

    def test_yaml_fields_reference_mentions_core_fields(self) -> None:
        fields = (SKILL_DIR / "references" / "yaml-fields.md").read_text(
            encoding="utf-8"
        )

        for expected in (
            "config",
            "steps",
            "request",
            "request.path",
            "request.body",
            "request.data",
            "request.files",
            "extract",
            "check",
            "response.save_body_to",
            "export.csv",
            "caseflow",
            "invoke",
            "sleep",
            "repeat",
            "config.parameters",
            "与 `request` 同级",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, fields)

    def test_maintenance_reference_mentions_update_triggers(self) -> None:
        maintenance = (SKILL_DIR / "references" / "maintenance.md").read_text(
            encoding="utf-8"
        )

        for expected in ("CLI", "YAML DSL", "报告", "错误码", "convert", "export curl"):
            with self.subTest(expected=expected):
                self.assertIn(expected, maintenance)

    def test_recipes_include_safe_executable_commands(self) -> None:
        recipes = (SKILL_DIR / "references" / "recipes.md").read_text(encoding="utf-8")

        for expected in ("drun c", "drun r", "-secrets mask", "${ENV("):
            with self.subTest(expected=expected):
                self.assertIn(expected, recipes)

    def test_skill_does_not_recommend_unsupported_yaml_aliases(self) -> None:
        unsupported_fields = ("capture", "ext", "checked", "checkpoints")
        for markdown_file in _iter_skill_markdown_files():
            text = markdown_file.read_text(encoding="utf-8")
            for block_index, yaml_block in enumerate(
                _extract_fenced_yaml_blocks(text), start=1
            ):
                for field in unsupported_fields:
                    with self.subTest(
                        file=markdown_file.name, block=block_index, field=field
                    ):
                        self.assertNotRegex(
                            yaml_block,
                            rf"(?m)^\s*{re.escape(field)}\s*:",
                            f"Unsupported YAML field '{field}' appears in {markdown_file}",
                        )

    def test_skill_points_to_cross_agent_usage_reference(self) -> None:
        skill_text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")

        self.assertIn("references/agent-usage.md", skill_text)

        referenced_paths = set(re.findall(r"references/[A-Za-z0-9_.-]+\.md", skill_text))
        for referenced_path in referenced_paths:
            with self.subTest(reference=referenced_path):
                self.assertTrue(
                    (SKILL_DIR / referenced_path).exists(),
                    f"Missing drun-usage reference: {referenced_path}",
                )


if __name__ == "__main__":
    unittest.main()
