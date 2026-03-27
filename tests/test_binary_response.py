from __future__ import annotations

import base64
import logging
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import httpx

from drun.engine.http import HTTPClient
from drun.loader.yaml_loader import load_yaml_file
from drun.reporter.json_reporter import write_json
from drun.runner.runner import Runner


class BinaryResponseTests(unittest.TestCase):
    def test_http_client_exposes_binary_metadata(self) -> None:
        payload = b"\x00\x01\x02audio"

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                content=payload,
                headers={"content-type": "audio/mpeg"},
                request=request,
            )

        client = HTTPClient(base_url="https://example.test")
        client.client = httpx.Client(
            base_url="https://example.test",
            transport=httpx.MockTransport(handler),
        )

        result = client.request({"method": "GET", "path": "/tts"})

        self.assertIsNone(result["body"])
        self.assertEqual(result["content_type"], "audio/mpeg")
        self.assertEqual(result["body_size"], len(payload))
        self.assertEqual(result["raw_bytes"], payload)
        self.assertEqual(result["body_bytes_b64"], base64.b64encode(payload).decode("ascii"))
        client.close()

    def test_runner_save_body_to_writes_binary_response_and_supports_hooks(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            case_file = tmpdir / "test_tts.yaml"
            case_file.write_text(
                """
config:
  name: TTS Download
  base_url: https://example.test
steps:
  - name: save tts
    request:
      method: GET
      path: /tts
    response:
      save_body_to: artifacts/tts_out.mp3
    teardown_hooks:
      - "${remember_raw_bytes(response)}"
    validate:
      - eq: [status_code, 200]
      - eq: [$content_type, audio/mpeg]
      - eq: [$body_size, 3]
""".strip(),
                encoding="utf-8",
            )

            cases, _ = load_yaml_file(case_file)
            runner = Runner(log=logging.getLogger("binary-test"), persist_env_file=str(tmpdir / ".env"))

            class FakeHTTPClient:
                def request(self, req):
                    return {
                        "status_code": 200,
                        "headers": {"content-type": "audio/mpeg"},
                        "body": None,
                        "content_type": "audio/mpeg",
                        "body_size": 3,
                        "raw_bytes": b"abc",
                        "body_bytes_b64": base64.b64encode(b"abc").decode("ascii"),
                        "elapsed_ms": 1.0,
                        "url": "https://example.test/tts",
                        "method": req.get("method", "GET"),
                    }

                def close(self):
                    pass

            def remember_raw_bytes(response):
                if response.get("raw_bytes") != b"abc":
                    raise AssertionError("raw_bytes missing from hook context")
                return {}

            runner._build_client = lambda case: FakeHTTPClient()

            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                result = runner.run_case(
                    cases[0],
                    global_vars={},
                    params={},
                    funcs={"remember_raw_bytes": remember_raw_bytes},
                    envmap={},
                    source=str(case_file),
                )
            finally:
                os.chdir(old_cwd)

            self.assertEqual(result.status, "passed")
            step = result.steps[0]
            saved_path = Path(step.response["saved_body_to"])
            self.assertTrue(saved_path.exists())
            self.assertEqual(saved_path.read_bytes(), b"abc")
            self.assertEqual(step.response["content_type"], "audio/mpeg")
            self.assertEqual(step.response["body_size"], 3)
            self.assertEqual(step.response["body_bytes_b64"], base64.b64encode(b"abc").decode("ascii"))

            report_file = tmpdir / "report.json"
            write_json(runner.build_report([result]), report_file)
            self.assertTrue(report_file.exists())


if __name__ == "__main__":
    unittest.main()
