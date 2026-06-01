from __future__ import annotations

from pathlib import Path
import os
import tempfile
import unittest

from drun.loader.collector import AmbiguousTestTargetError, InvalidTestPathError, discover


class CollectorLayoutTests(unittest.TestCase):
    def test_discovers_new_case_and_suite_layout_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tcases = root / "tcases"
            tsuites = root / "tsuites"
            tcases.mkdir()
            tsuites.mkdir()
            case_file = tcases / "tc_login.yaml"
            suite_file = tsuites / "ts_smoke.yaml"
            case_file.write_text("config:\n  name: Login\nsteps: []\n", encoding="utf-8")
            suite_file.write_text("config:\n  name: Smoke\ncaseflow: []\n", encoding="utf-8")

            found = discover([tcases, tsuites])

            self.assertEqual([p.resolve() for p in found], [case_file.resolve(), suite_file.resolve()])

    def test_rejects_legacy_testcases_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy_dir = root / "testcases"
            legacy_dir.mkdir()
            legacy_file = legacy_dir / "test_login.yaml"
            legacy_file.write_text("config:\n  name: Login\nsteps: []\n", encoding="utf-8")

            with self.assertRaisesRegex(InvalidTestPathError, "Legacy directories are not supported"):
                discover([legacy_file])
    def test_rejects_file_without_required_tc_prefix_under_tcases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tcases = root / "tcases"
            tcases.mkdir()
            invalid_file = tcases / "login.yaml"
            invalid_file.write_text("config:\n  name: Login\nsteps: []\n", encoding="utf-8")

            with self.assertRaisesRegex(InvalidTestPathError, "Files under tcases/ must be named tc_"):
                discover([invalid_file])
    def test_rejects_tc_file_under_tsuites(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tsuites = root / "tsuites"
            tsuites.mkdir()
            invalid_file = tsuites / "tc_login.yaml"
            invalid_file.write_text("config:\n  name: Login\nsteps: []\n", encoding="utf-8")

            with self.assertRaisesRegex(InvalidTestPathError, "Files under tsuites/ must be named ts_"):
                discover([invalid_file])
    def test_rejects_invalid_module_directory_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            module_dir = root / "tcases" / "auth-v2"
            module_dir.mkdir(parents=True)
            case_file = module_dir / "tc_login.yaml"
            case_file.write_text("config:\n  name: Login\nsteps: []\n", encoding="utf-8")

            with self.assertRaisesRegex(InvalidTestPathError, "Invalid test module directory"):
                discover([case_file])
    def test_skips_hidden_and_dunder_module_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hidden_dir = root / "tcases" / ".hidden"
            dunder_dir = root / "tcases" / "__pycache__"
            hidden_dir.mkdir(parents=True)
            dunder_dir.mkdir()
            hidden_file = hidden_dir / "tc_hidden.yaml"
            dunder_file = dunder_dir / "tc_cache.yaml"
            hidden_file.write_text("config:\n  name: Hidden\nsteps: []\n", encoding="utf-8")
            dunder_file.write_text("config:\n  name: Cache\nsteps: []\n", encoding="utf-8")

            self.assertEqual(discover([root / "tcases"]), [])
    def test_no_extension_case_target_searches_tcases(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tcases = root / "tcases"
            tcases.mkdir()
            case_file = tcases / "tc_login.yaml"
            case_file.write_text("config:\n  name: Login\nsteps: []\n", encoding="utf-8")
            os.chdir(root)
            try:
                found = discover(["tc_login"])
            finally:
                os.chdir(old_cwd)

        self.assertEqual([p.resolve() for p in found], [case_file.resolve()])
    def test_no_extension_target_without_tc_or_ts_prefix_fails(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tcases").mkdir()
            os.chdir(root)
            try:
                with self.assertRaisesRegex(InvalidTestPathError, "must start with tc_ or ts_"):
                    discover(["login"])
            finally:
                os.chdir(old_cwd)
    def test_no_extension_target_with_duplicate_matches_is_ambiguous(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            auth = root / "tcases" / "auth"
            admin = root / "tcases" / "admin"
            auth.mkdir(parents=True)
            admin.mkdir()
            (auth / "tc_login.yaml").write_text("config:\n  name: Auth\nsteps: []\n", encoding="utf-8")
            (admin / "tc_login.yaml").write_text("config:\n  name: Admin\nsteps: []\n", encoding="utf-8")
            os.chdir(root)
            try:
                with self.assertRaisesRegex(AmbiguousTestTargetError, "Ambiguous test target: tc_login"):
                    discover(["tc_login"])
            finally:
                os.chdir(old_cwd)
    def test_no_extension_suite_target_searches_tsuites_only(self) -> None:
        old_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tcases = root / "tcases"
            tsuites = root / "tsuites"
            tcases.mkdir()
            tsuites.mkdir()
            (tcases / "ts_smoke.yaml").write_text("config:\n  name: Wrong\nsteps: []\n", encoding="utf-8")
            suite_file = tsuites / "ts_smoke.yaml"
            suite_file.write_text("config:\n  name: Smoke\ncaseflow: []\n", encoding="utf-8")
            os.chdir(root)
            try:
                found = discover(["ts_smoke"])
            finally:
                os.chdir(old_cwd)

        self.assertEqual([p.resolve() for p in found], [suite_file.resolve()])
    def test_directory_scan_fails_on_invalid_yaml_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tcases = root / "tcases"
            tcases.mkdir()
            (tcases / "tc_login.yaml").write_text("config:\n  name: Login\nsteps: []\n", encoding="utf-8")
            (tcases / "login.yaml").write_text("config:\n  name: Bad\nsteps: []\n", encoding="utf-8")

            with self.assertRaisesRegex(InvalidTestPathError, "Files under tcases/ must be named tc_"):
                discover([tcases])
    def test_directory_scan_returns_yaml_files_sorted_by_full_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            auth = root / "tcases" / "auth"
            admin = root / "tcases" / "admin"
            auth.mkdir(parents=True)
            admin.mkdir()
            admin_file = admin / "tc_login.yaml"
            auth_file = auth / "tc_login.yaml"
            auth_file.write_text("config:\n  name: Auth\nsteps: []\n", encoding="utf-8")
            admin_file.write_text("config:\n  name: Admin\nsteps: []\n", encoding="utf-8")

            found = discover([root / "tcases"])

            self.assertEqual([p.resolve() for p in found], [admin_file.resolve(), auth_file.resolve()])
    def test_running_project_root_with_cases_and_suites_is_ambiguous(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "tcases").mkdir()
            (root / "tsuites").mkdir()
            (root / "tcases" / "tc_login.yaml").write_text("config:\n  name: Login\nsteps: []\n", encoding="utf-8")
            (root / "tsuites" / "ts_smoke.yaml").write_text("config:\n  name: Smoke\ncaseflow: []\n", encoding="utf-8")

            with self.assertRaisesRegex(AmbiguousTestTargetError, "contains both tcases/ and tsuites/"):
                discover([root])


if __name__ == "__main__":
    unittest.main()
