import tempfile
import unittest
from pathlib import Path

from chatplays.target import TargetResolver, WindowInfo, best_window, normalize_path


class TargetTests(unittest.TestCase):
    def test_normalize_path_removes_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "game.exe"
            self.assertEqual(normalize_path(f'"{path}"'), str(path.resolve()))

    def test_exact_pid_and_path_wins(self):
        windows = [
            WindowInfo(10, 100, "Minecraft", "javaw.exe", r"C:\Java\javaw.exe"),
            WindowInfo(11, 200, "Minecraft", "javaw.exe", r"D:\Java\javaw.exe"),
        ]
        target = {
            "pid": 200,
            "title": "Minecraft",
            "process": "javaw.exe",
            "exe": r"D:\Java\javaw.exe",
        }
        self.assertEqual(best_window(windows, target), windows[1])

    def test_reused_pid_with_wrong_exe_is_not_trusted(self):
        wrong_pid = WindowInfo(10, 777, "Other", "game.exe", r"C:\Other\game.exe")
        correct = WindowInfo(11, 888, "Pokemon", "emu.exe", r"C:\Emu\emu.exe")
        target = {
            "pid": 777,
            "title": "Pokemon",
            "process": "emu.exe",
            "exe": r"C:\Emu\emu.exe",
        }
        self.assertEqual(best_window([wrong_pid, correct], target), correct)

    def test_title_fallback_selects_java_window(self):
        launcher = WindowInfo(10, 100, "Launcher", "javaw.exe", r"C:\Java\javaw.exe")
        minecraft = WindowInfo(
            11,
            101,
            "Minecraft 1.21",
            "javaw.exe",
            r"C:\Java\javaw.exe",
        )
        target = {
            "title": "Minecraft 1.21",
            "process": "javaw.exe",
            "exe": r"C:\Java\javaw.exe",
        }
        self.assertEqual(best_window([launcher, minecraft], target), minecraft)

    def test_program_mode_requires_target(self):
        with self.assertRaises(ValueError):
            TargetResolver({"mode": "program"}).validate()

    def test_emulator_mode_requires_real_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            emulator = Path(tmp) / "emulator.exe"
            rom = Path(tmp) / "game.gba"
            emulator.write_bytes(b"")
            rom.write_bytes(b"")
            TargetResolver(
                {
                    "mode": "emulator",
                    "emulator_exe": str(emulator),
                    "rom": str(rom),
                }
            ).validate()


if __name__ == "__main__":
    unittest.main()
