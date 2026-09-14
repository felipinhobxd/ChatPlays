import tempfile
import unittest
from pathlib import Path

from chatplays.profiles import (
    BUILTIN_PROFILES,
    apply_profile,
    load_profiles,
    load_user_profiles,
    profile_from_config,
    profile_path,
    save_profiles,
)


class ProfileTests(unittest.TestCase):
    def test_builtin_profiles_cover_minecraft_and_emulator(self):
        self.assertIn("Minecraft", BUILTIN_PROFILES)
        self.assertIn("Pokémon / Emulador", BUILTIN_PROFILES)
        self.assertEqual(BUILTIN_PROFILES["Minecraft"]["target"]["mode"], "program")
        self.assertEqual(
            BUILTIN_PROFILES["Pokémon / Emulador"]["target"]["mode"], "emulator"
        )
        self.assertIn("jump", BUILTIN_PROFILES["Minecraft"]["commands"])
        self.assertIn("a", BUILTIN_PROFILES["Pokémon / Emulador"]["commands"])

    def test_profile_excludes_stream_connections(self):
        config = {
            "stream": {"twitch_channel": "private-channel"},
            "target": {"mode": "program", "pid": 42},
            "countdown_seconds": 3,
            "queue": {"message_rate": 0.2, "max_length": 10},
            "input": {"default_press_seconds": 0.1},
            "commands": {"jump": {"key": "space", "aliases": ["jump"]}},
        }
        profile = profile_from_config(config)
        self.assertNotIn("stream", profile)
        self.assertEqual(profile["target"]["pid"], 42)

    def test_apply_profile_preserves_stream_and_does_not_alias_data(self):
        config = {
            "stream": {"twitch_channel": "sindromegames"},
            "target": {"mode": "program", "pid": 1},
            "commands": {},
        }
        profile = {
            "target": {"mode": "program", "pid": 99},
            "commands": {"up": {"key": "up", "aliases": ["up"]}},
        }
        merged = apply_profile(config, profile)
        self.assertEqual(merged["stream"]["twitch_channel"], "sindromegames")
        self.assertEqual(merged["target"]["pid"], 99)
        merged["commands"]["up"]["aliases"].append("cima")
        self.assertEqual(profile["commands"]["up"]["aliases"], ["up"])

    def test_custom_profiles_round_trip_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profiles.json"
            custom = {
                "Meu jogo": {
                    "target": {"mode": "program", "pid": 7},
                    "commands": {"a": {"key": "x", "aliases": ["a"]}},
                }
            }
            save_profiles(path, custom)
            self.assertEqual(load_user_profiles(path), custom)
            self.assertIn("Meu jogo", load_profiles(path))
            self.assertFalse((Path(directory) / ".profiles.json.tmp").exists())

    def test_user_profile_can_override_builtin_without_mutating_template(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profiles.json"
            save_profiles(path, {"Minecraft": {"target": {"mode": "program", "pid": 123}}})
            profiles = load_profiles(path)
            self.assertEqual(profiles["Minecraft"]["target"]["pid"], 123)
            self.assertEqual(BUILTIN_PROFILES["Minecraft"]["target"]["pid"], 0)

    def test_profile_path_lives_beside_config(self):
        self.assertEqual(
            profile_path(Path("C:/ChatPlays/config.json")),
            Path("C:/ChatPlays/profiles.json"),
        )


if __name__ == "__main__":
    unittest.main()
