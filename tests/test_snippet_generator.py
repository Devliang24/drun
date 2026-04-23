from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from drun.commands.run import _save_code_snippets
from drun.exporters.snippet import SnippetGenerator
from drun.models.case import Case


def _build_case() -> Case:
    return Case.model_validate(
        {
            "config": {
                "name": "渠道调试",
                "base_url": "https://example.com",
                "variables": {"channel_name": "default-name"},
            },
            "steps": [
                {
                    "name": "创建渠道",
                    "request": {
                        "method": "POST",
                        "path": "/api/channel",
                        "headers": {
                            "Authorization": "Bearer ${jwt_token}",
                            "Content-Type": "application/json",
                        },
                        "json": {
                            "name": "${channel_name}",
                            "key": "${ENV(MINIMAX_API_KEY)}",
                            "token": "${jwt_token}",
                        },
                    },
                }
            ],
        }
    )


def _build_case_with_sleep() -> Case:
    return Case.model_validate(
        {
            "config": {
                "name": "带等待的调试",
                "base_url": "https://example.com",
            },
            "steps": [
                {
                    "name": "创建渠道",
                    "request": {
                        "method": "POST",
                        "path": "/api/channel",
                        "json": {"name": "demo"},
                    },
                },
                {
                    "name": "等待处理",
                    "sleep": 2000,
                },
            ],
        }
    )


class _FakeLogger:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def info(self, message: str, *args) -> None:
        if args:
            message = message % args
        self.messages.append(message)


class SnippetGeneratorTests(unittest.TestCase):
    def test_generate_shell_script_includes_runtime_token(self) -> None:
        case = _build_case()
        generator = SnippetGenerator()

        script = generator.generate_shell_script_for_step(
            case,
            step_idx=0,
            total_steps=1,
            envmap={
                "jwt_token": "jwt-token-123",
                "channel_name": "runtime-channel",
                "MINIMAX_API_KEY": "minimax-key-xyz",
            },
        )

        self.assertIn("Authorization: Bearer jwt-token-123", script)
        self.assertIn('"token":"jwt-token-123"', script)
        self.assertIn('"name":"runtime-channel"', script)
        self.assertIn('"key":"minimax-key-xyz"', script)

    def test_generate_python_script_includes_runtime_token(self) -> None:
        case = _build_case()
        generator = SnippetGenerator()

        script = generator.generate_python_script_for_step(
            case,
            step_idx=0,
            total_steps=1,
            envmap={
                "jwt_token": "jwt-token-123",
                "channel_name": "runtime-channel",
                "MINIMAX_API_KEY": "minimax-key-xyz",
            },
        )

        self.assertIn('"Authorization": "Bearer jwt-token-123"', script)
        self.assertIn('"token": "jwt-token-123"', script)
        self.assertIn('"name": "runtime-channel"', script)
        self.assertIn('"key": "minimax-key-xyz"', script)

    def test_save_code_snippets_skips_sleep_steps(self) -> None:
        case = _build_case_with_sleep()
        logger = _FakeLogger()

        with TemporaryDirectory() as tmpdir:
            _save_code_snippets(
                items=[(case, {"file": "demo.yaml"})],
                output_dir=tmpdir,
                languages="all",
                env_store={},
                log=logger,
            )

            files = sorted(path.name for path in Path(tmpdir).iterdir())

        self.assertEqual(
            files,
            [
                "step1_创建渠道_curl.sh",
                "step1_创建渠道_python.py",
            ],
        )
        self.assertTrue(
            any("Skip sleep step: 等待处理" in message for message in logger.messages)
        )


if __name__ == "__main__":
    unittest.main()
