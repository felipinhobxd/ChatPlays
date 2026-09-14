import unittest

from chatplays.target import WindowInfo


class UITargetDataTests(unittest.TestCase):
    def test_window_info_label_identifies_instance(self):
        window = WindowInfo(
            hwnd=123,
            pid=456,
            title="Minecraft 1.21",
            process="javaw.exe",
            exe=r"C:\Java\javaw.exe",
        )
        self.assertIn("Minecraft 1.21", window.label)
        self.assertIn("javaw.exe", window.label)
        self.assertIn("456", window.label)


if __name__ == "__main__":
    unittest.main()
