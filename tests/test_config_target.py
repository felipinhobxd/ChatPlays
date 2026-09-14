import json
import tempfile
import unittest
from pathlib import Path

from chatplays.config import load_config


class TargetConfigTests(unittest.TestCase):
    def test_existing_program_target_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "stream": {"twitch_channel": "example"},
                        "target": {
                            "mode": "program",
                            "pid": 321,
                            "title": "Minecraft",
                            "process": "javaw.exe",
                            "exe": r"C:\Java\javaw.exe",
                        },
                        "commands": {"up": {"key": "up", "aliases": ["up"]}},
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config["target"]["pid"], 321)
            self.assertEqual(config["target"]["process"], "javaw.exe")
            self.assertEqual(config["target"]["emulator_exe"], "")


if __name__ == "__main__":
    unittest.main()
