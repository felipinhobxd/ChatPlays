import json
import tempfile
import unittest
from pathlib import Path

from chatplays.config import ConfigError, create_default_config, load_config


class ConfigTests(unittest.TestCase):
    def test_create_default_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = create_default_config(Path(tmp) / "config.json")
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("commands", data)
            self.assertIn("twitch_channel", data["stream"])
            self.assertEqual(data["target"]["mode"], "program")

    def test_defaults_are_added(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "stream": {"twitch_channel": "example"},
                        "commands": {"up": {"key": "up", "aliases": ["up"]}},
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config["queue"]["max_length"], 20)
            self.assertEqual(config["input"]["default_press_seconds"], 0.08)
            self.assertEqual(config["target"]["mode"], "program")

    def test_requires_stream(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.json"
            path.write_text(
                json.dumps({"stream": {}, "commands": {"up": {"key": "up"}}}),
                encoding="utf-8",
            )
            with self.assertRaises(ConfigError):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
