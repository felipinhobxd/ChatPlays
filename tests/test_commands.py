import unittest

from chatplays.commands import CommandRegistry, normalize, parse_duration

COMMANDS = {
    "up": {"key": "up", "aliases": ["up", "cima"]},
    "click": {"mouse_button": "left", "aliases": ["click", "clique"]},
    "look": {"mouse_move": [10, 0], "aliases": ["look"]},
}


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.registry = CommandRegistry(COMMANDS, 0.08)

    def test_normalize_accents_and_spaces(self):
        self.assertEqual(normalize("  CÍMA   "), "cima")

    def test_exact_alias(self):
        action = self.registry.resolve("CÍMA")
        self.assertIsNotNone(action)
        self.assertEqual(action.name, "up")
        self.assertEqual(action.spec["key"], "up")

    def test_timed_hold(self):
        action = self.registry.resolve("hold cima 250ms")
        self.assertTrue(action.hold)
        self.assertAlmostEqual(action.duration, 0.25)

    def test_indefinite_hold(self):
        action = self.registry.resolve("segurar clique")
        self.assertTrue(action.hold)
        self.assertIsNone(action.duration)

    def test_release(self):
        self.assertTrue(self.registry.resolve("soltar tudo").release_all)

    def test_cannot_hold_mouse_move(self):
        self.assertIsNone(self.registry.resolve("hold look 1s"))

    def test_duration_parser(self):
        self.assertAlmostEqual(parse_duration("2.5s"), 2.5)
        self.assertAlmostEqual(parse_duration("37ms"), 0.037)
        with self.assertRaises(ValueError):
            parse_duration("20s")

    def test_duplicate_alias_rejected(self):
        with self.assertRaises(ValueError):
            CommandRegistry({
                "one": {"key": "a", "aliases": ["same"]},
                "two": {"key": "b", "aliases": ["same"]},
            })


if __name__ == "__main__":
    unittest.main()
