from __future__ import annotations

import builtins
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import httpx

from drun.engine.http import HTTPClient
from drun.engine.request_files import RequestFilesError
from drun.loader.yaml_loader import load_yaml_file
from drun.utils.errors import LoadError


class RequestFilesTests(unittest.TestCase):
    def test_loader_accepts_documented_files_shorthand(self) -> None:
        with TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "test_upload.yaml"
            case_file.write_text(
                """
config:
  name: Upload
  base_url: https://example.test
steps:
  - name: upload avatar
    request:
      method: POST
      path: /upload
      files:
        avatar: ["data/avatar.jpg", "image/jpeg"]
""".strip(),
                encoding="utf-8",
            )

            cases, _ = load_yaml_file(case_file)
            self.assertEqual(cases[0].steps[0].request.files["avatar"], ["data/avatar.jpg", "image/jpeg"])

    def test_loader_rejects_invalid_files_list_shape(self) -> None:
        with TemporaryDirectory() as tmp:
            case_file = Path(tmp) / "test_upload.yaml"
            case_file.write_text(
                """
config:
  name: Upload
  base_url: https://example.test
steps:
  - name: upload avatar
    request:
      method: POST
      path: /upload
      files:
        avatar: ["data/avatar.jpg", "image/jpeg", "extra"]
""".strip(),
                encoding="utf-8",
            )

            with self.assertRaises(LoadError):
                load_yaml_file(case_file)

    def test_http_client_normalizes_single_path_upload_and_closes_file(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            upload_file = tmpdir / "sample.txt"
            upload_file.write_text("hello multipart", encoding="utf-8")

            opened_handles = []
            captured = {}

            def tracking_open(*args, **kwargs):
                handle = builtins.open(*args, **kwargs)
                opened_handles.append(handle)
                return handle

            def handler(request: httpx.Request) -> httpx.Response:
                captured["content_type"] = request.headers.get("content-type")
                captured["body"] = request.read()
                return httpx.Response(200, json={"ok": True}, request=request)

            client = HTTPClient(base_url="https://example.test")
            client.client = httpx.Client(
                base_url="https://example.test",
                transport=httpx.MockTransport(handler),
            )

            with patch("drun.engine.request_files.open", side_effect=tracking_open):
                result = client.request(
                    {
                        "method": "POST",
                        "path": "/upload",
                        "data": {"kind": "avatar"},
                        "files": {"file": str(upload_file)},
                    }
                )

            self.assertEqual(result["status_code"], 200)
            self.assertIn("multipart/form-data", captured["content_type"])
            self.assertIn(b'filename="sample.txt"', captured["body"])
            self.assertTrue(opened_handles)
            self.assertTrue(all(handle.closed for handle in opened_handles))
            client.close()

    def test_http_client_closes_opened_files_on_transport_error(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            upload_file = tmpdir / "sample.txt"
            upload_file.write_text("hello multipart", encoding="utf-8")

            opened_handles = []

            def tracking_open(*args, **kwargs):
                handle = builtins.open(*args, **kwargs)
                opened_handles.append(handle)
                return handle

            def handler(_: httpx.Request) -> httpx.Response:
                raise RuntimeError("network boom")

            client = HTTPClient(base_url="https://example.test")
            client.client = httpx.Client(
                base_url="https://example.test",
                transport=httpx.MockTransport(handler),
            )

            with patch("drun.engine.request_files.open", side_effect=tracking_open):
                with self.assertRaises(RuntimeError):
                    client.request(
                        {
                            "method": "POST",
                            "path": "/upload",
                            "files": {"file": [str(upload_file), "text/plain"]},
                        }
                    )

            self.assertTrue(opened_handles)
            self.assertTrue(all(handle.closed for handle in opened_handles))
            client.close()

    def test_http_client_rejects_body_with_files(self) -> None:
        with TemporaryDirectory() as tmp:
            upload_file = Path(tmp) / "sample.txt"
            upload_file.write_text("hello multipart", encoding="utf-8")

            client = HTTPClient(base_url="https://example.test")
            with self.assertRaises(RequestFilesError):
                client.request(
                    {
                        "method": "POST",
                        "path": "/upload",
                        "body": {"kind": "avatar"},
                        "files": {"file": str(upload_file)},
                    }
                )
            client.close()

    def test_http_client_preserves_httpx_tuple_upload(self) -> None:
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["content_type"] = request.headers.get("content-type")
            captured["body"] = request.read()
            return httpx.Response(200, json={"ok": True}, request=request)

        client = HTTPClient(base_url="https://example.test")
        client.client = httpx.Client(
            base_url="https://example.test",
            transport=httpx.MockTransport(handler),
        )

        result = client.request(
            {
                "method": "POST",
                "path": "/upload",
                "files": {"file": ("hello.txt", b"hello world", "text/plain")},
            }
        )

        self.assertEqual(result["status_code"], 200)
        self.assertIn("multipart/form-data", captured["content_type"])
        self.assertIn(b'filename="hello.txt"', captured["body"])
        self.assertIn(b"hello world", captured["body"])
        client.close()

    def test_http_client_errors_before_send_when_path_missing(self) -> None:
        client = HTTPClient(base_url="https://example.test")
        with self.assertRaises(RequestFilesError):
            client.request(
                {
                    "method": "POST",
                    "path": "/upload",
                    "files": {"file": "missing-file.wav"},
                }
            )
        client.close()
