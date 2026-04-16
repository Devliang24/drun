from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
