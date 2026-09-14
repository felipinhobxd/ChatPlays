import unittest

from chatplays.validation import validate_runtime_config


def valid_config():
    return {
        "stream": {"twitch_channel": "example"},
        "target": {"mode": "program", "pid": 123},
        "countdown_seconds": 5,
        "queue": {"message_rate": 0.35, "max_length": 20},
        "input": {"default_press_seconds": 0.08},
        "commands": {"up": {"key": "up", "aliases": ["up"]}},
    }


class RuntimeValidationTests(unittest.TestCase):
    def test_valid_config_is_returned_unchanged(self):
        config = valid_config()
        self.assertIs(validate_runtime_config(config), config)

    def test_legacy_workers_key_is_ignored(self):
        config = valid_config()
        config["queue"]["workers"] = 0
        self.assertIs(validate_runtime_config(config), config)

    def test_non_finite_message_rate_is_rejected(self):
        config = valid_config()
        config["queue"]["message_rate"] = float("nan")
        with self.assertRaisesRegex(ValueError, "finito"):
            validate_runtime_config(config)

    def test_default_press_must_be_positive(self):
        config = valid_config()
        config["input"]["default_press_seconds"] = 0
        with self.assertRaisesRegex(ValueError, "duração padrão"):
            validate_runtime_config(config)

    def test_non_finite_default_press_is_rejected(self):
        config = valid_config()
        config["input"]["default_press_seconds"] = float("inf")
        with self.assertRaisesRegex(ValueError, "finito"):
            validate_runtime_config(config)

    def test_target_is_required_at_runtime(self):
        config = valid_config()
        config["target"] = {"mode": "program"}
        with self.assertRaisesRegex(ValueError, "Selecione"):
            validate_runtime_config(config)


if __name__ == "__main__":
    unittest.main()
