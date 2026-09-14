import unittest

from chatplays.ui import _command_target, _parse_target


class UIHelpersTests(unittest.TestCase):
    def test_parse_key(self):
        self.assertEqual(_parse_target("key", "shift+f5"), {"key": "shift+f5"})

    def test_parse_mouse_button(self):
        self.assertEqual(_parse_target("mouse_button", "LEFT"), {"mouse_button": "left"})

    def test_parse_mouse_move(self):
        self.assertEqual(_parse_target("mouse_move", "80,-20"), {"mouse_move": [80, -20]})

    def test_command_target(self):
        self.assertEqual(_command_target({"mouse_move": [10, 20]}), ("mouse_move", "10,20"))


if __name__ == "__main__":
    unittest.main()
