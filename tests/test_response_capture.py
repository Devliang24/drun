from __future__ import annotations

import base64
import unittest

from drun.runner.response_capture import capture_step_response
from drun.runner.runner import Runner


class ResponseCaptureTests(unittest.TestCase):
    def test_capture_keeps_report_response_safe_for_binary_payloads(self) -> None:
        runner = Runner(log=None, reveal_secrets=True)
        payload = b"abc"
        resp_obj = {
            "status_code": 200,
            "body": None,
            "raw_bytes": payload,
            "content_type": "audio/mpeg",
            "body_size": len(payload),
            "body_bytes_b64": base64.b64encode(payload).decode("ascii"),
            "saved_body_to": "/tmp/out.mp3",
            "save_error": "Save response body failed: nope",
        }

        capture = capture_step_response(runner=runner, resp_obj=resp_obj)

        self.assertEqual(capture.raw_response["raw_bytes"], payload)
        self.assertNotIn("raw_bytes", capture.report_response)
        self.assertEqual(capture.report_response["status_code"], 200)
        self.assertEqual(capture.report_response["content_type"], "audio/mpeg")
        self.assertEqual(capture.report_response["body_size"], 3)
        self.assertEqual(capture.report_response["body_bytes_b64"], "YWJj")
        self.assertEqual(capture.report_response["saved_body_to"], "/tmp/out.mp3")
        self.assertEqual(
            capture.report_response["save_error"],
            "Save response body failed: nope",
        )


if __name__ == "__main__":
    unittest.main()
