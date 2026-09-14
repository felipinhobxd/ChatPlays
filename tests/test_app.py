import unittest
from threading import Event

from chatplays.app import ChatPlaysApp
from chatplays.commands import ParsedAction


class FakeInput:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def record(*args, **kwargs):
            self.calls.append((name, args, kwargs))

        return record


class FakeConnection:
    def __init__(self):
        self.closed = False

    def poll(self):
        return []

    def close(self):
        self.closed = True


class AppTests(unittest.TestCase):
    def setUp(self):
        self.input = FakeInput()
        self.app = ChatPlaysApp(
            {
                "stream": {},
                "queue": {"message_rate": 0, "max_length": 10, "workers": 1},
                "input": {"default_press_seconds": 0.08},
                "commands": {"up": {"key": "up", "aliases": ["up"]}},
            },
            input_backend=self.input,
        )
        self.addCleanup(lambda: self.app.executor.shutdown(wait=False, cancel_futures=True))

    def test_key_press(self):
        self.app._execute(ParsedAction("up", {"key": "up"}))
        self.assertEqual(
            self.input.calls[-1],
            ("press_key", ("up", 0.08), {"stop_event": None}),
        )

    def test_indefinite_hold(self):
        self.app._execute(ParsedAction("up", {"key": "up"}, hold=True))
        self.assertEqual(self.input.calls[-1], ("key_down", ("up",), {}))

    def test_mouse_move(self):
        self.app._execute(ParsedAction("look", {"mouse_move": [10, -5]}))
        self.assertEqual(self.input.calls[-1], ("move_relative", (10, -5), {}))

    def test_release_all(self):
        self.app._execute(ParsedAction("release", {}, release_all=True))
        self.assertEqual(self.input.calls[-1], ("release_all", (), {}))

    def test_stopped_action_does_not_send_input(self):
        stop_event = Event()
        stop_event.set()
        self.app._execute(ParsedAction("up", {"key": "up"}), stop_event)
        self.assertEqual(self.input.calls, [])

    def test_early_stop_still_closes_connections_and_releases_input(self):
        connection = FakeConnection()
        self.app.connections = [connection]
        stop_event = Event()
        stop_event.set()

        self.app.run(stop_event)

        self.assertTrue(connection.closed)
        self.assertIn(("prepare", (), {}), self.input.calls)
        self.assertIn(("release_all", (), {}), self.input.calls)


if __name__ == "__main__":
    unittest.main()
