import sys
import unittest
from unittest import mock

from chatplays.input import GameInput


@unittest.skipUnless(sys.platform == "win32", "Windows-only input backend")
class IsolatedInputTests(unittest.TestCase):
    def test_missing_target_raises_before_posting_key(self):
        with mock.patch("chatplays.input.TargetResolver.hwnd", side_effect=RuntimeError("missing")):
            backend = GameInput({"mode": "program", "pid": 123})
            with self.assertRaises(RuntimeError):
                backend.key_down("up")
            self.assertEqual(backend._held_keys, {})

    def test_combo_parser_keeps_supported_combos(self):
        self.assertEqual(GameInput._combo_keys("shift+f5"), ["shift", "f5"])


if __name__ == "__main__":
    unittest.main()
