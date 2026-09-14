import unittest

from chatplays.target import WindowInfo
from chatplays.ui_targeting import choose_target_window


def window(hwnd, pid, title="Minecraft", exe=r"C:\Java\javaw.exe"):
    return WindowInfo(
        hwnd=hwnd,
        pid=pid,
        title=title,
        process="javaw.exe",
        exe=exe,
    )


class UITargetDataTests(unittest.TestCase):
    def test_window_info_label_identifies_instance(self):
        target = window(123, 456, "Minecraft 1.21")
        self.assertIn("Minecraft 1.21", target.label)
        self.assertIn("javaw.exe", target.label)
        self.assertIn("456", target.label)

    def test_saved_pid_selects_exact_instance(self):
        first = window(100, 10)
        second = window(200, 20)
        selected = choose_target_window(
            [first, second],
            {
                "pid": 20,
                "title": "Minecraft",
                "process": "javaw.exe",
                "exe": r"C:\Java\javaw.exe",
            },
        )
        self.assertEqual(selected, second)

    def test_current_selection_is_kept_when_still_open(self):
        first = window(100, 10)
        second = window(200, 20)
        selected = choose_target_window([first, second], {}, second)
        self.assertEqual(selected, second)

    def test_ambiguous_same_executable_does_not_auto_select(self):
        first = window(100, 10)
        second = window(200, 20)
        selected = choose_target_window(
            [first, second],
            {
                "pid": 999,
                "title": "Minecraft",
                "process": "javaw.exe",
                "exe": r"C:\Java\javaw.exe",
            },
        )
        self.assertIsNone(selected)


if __name__ == "__main__":
    unittest.main()
