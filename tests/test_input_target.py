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

    def test_partial_combo_failure_rolls_back_state(self):
        backend = GameInput({"mode": "program", "pid": 123})
        with mock.patch.object(
            backend,
            "_send_key",
            side_effect=[None, RuntimeError("lost target"), None],
        ) as send:
            with self.assertRaises(RuntimeError):
                backend.key_down("shift+f5")
        self.assertEqual(backend._held_keys, {})
        self.assertEqual(
            send.call_args_list,
            [
                mock.call("shift", False),
                mock.call("f5", False),
                mock.call("shift", True),
            ],
        )


if __name__ == "__main__":
    unittest.main()
