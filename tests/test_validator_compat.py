from __future__ import annotations

import unittest

from drun.runner.assertions import compare
from drun.runner.runner import Runner


class ValidatorCompatTests(unittest.TestCase):
    def test_jsonpath_length_suffix_is_supported(self) -> None:
        runner = Runner(log=None)
        resp = {"body": {"data": [{"id": 1}, {"id": 2}, {"id": 3}]}}

        actual = runner._resolve_check("$.data.length", resp)
        self.assertEqual(actual, 3)

        passed, err = compare("gt", actual, 0)
        self.assertTrue(passed)
        self.assertIsNone(err)

    def test_neq_alias_and_none_literal_compat(self) -> None:
        runner = Runner(log=None)
        resp = {"body": {"data": {"items": [{"id": "abc"}, {"id": None}]}}}

        actual_non_null = runner._resolve_check("$.data.items[0].id", resp)
        passed_non_null, err_non_null = compare("neq", actual_non_null, "None")
        self.assertTrue(passed_non_null)
        self.assertIsNone(err_non_null)

        actual_null = runner._resolve_check("$.data.items[1].id", resp)
        passed_null, err_null = compare("neq", actual_null, "None")
        self.assertFalse(passed_null)
        self.assertIsNone(err_null)


if __name__ == "__main__":
    unittest.main()
