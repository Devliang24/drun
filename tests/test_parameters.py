from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from drun.loader.parameters import expand_parameters


class ParameterExpansionTests(unittest.TestCase):
    def test_expands_csv_and_zipped_parameters_as_product(self) -> None:
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            csv_file = tmpdir / "users.csv"
            csv_file.write_text("user_id,active\n1,true\n2,false\n", encoding="utf-8")
            (tmpdir / "Dhook.py").write_text("", encoding="utf-8")
            case_file = tmpdir / "case.yaml"
            case_file.write_text("", encoding="utf-8")

            expanded = expand_parameters(
                [
                    {"csv": {"path": "users.csv"}},
                    {"region-tier": [["us", "gold"], ["eu", "silver"]]},
                ],
                source_path=case_file,
            )

        self.assertEqual(
            expanded,
            [
                {"user_id": 1, "active": True, "region": "us", "tier": "gold"},
                {"user_id": 1, "active": True, "region": "eu", "tier": "silver"},
                {"user_id": 2, "active": False, "region": "us", "tier": "gold"},
                {"user_id": 2, "active": False, "region": "eu", "tier": "silver"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
