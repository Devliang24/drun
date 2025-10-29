from __future__ import annotations

import unittest

from drun.templating.engine import TemplateEngine


class TemplateEngineHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self.templater = TemplateEngine()

    def test_nested_hook_calls_preserve_native_types(self) -> None:
        funcs = {
            "double": lambda x: x * 2,
            "increment": lambda val: int(val) + 1,
        }

        base_vars = self.templater.render_value({"start": "${double(2)}"}, {}, funcs)
        self.assertEqual(base_vars["start"], 4)
        self.assertIsInstance(base_vars["start"], int)

        step_vars = self.templater.render_value(
            {"payload": "${double($start)}"},
            {**base_vars},
            funcs,
        )
        self.assertEqual(step_vars["payload"], 8)
        self.assertIsInstance(step_vars["payload"], int)

        expect_value = self.templater.render_value(
            "${increment($payload)}",
            {**base_vars, **step_vars},
            funcs,
        )
        self.assertEqual(expect_value, 9)
        self.assertIsInstance(expect_value, int)


if __name__ == "__main__":
    unittest.main()
