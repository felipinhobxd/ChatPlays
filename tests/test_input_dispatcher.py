import unittest
from threading import Event

from chatplays.commands import ParsedAction
from chatplays.input_dispatcher import InputDispatcher


class InputDispatcherTests(unittest.TestCase):
    def test_actions_run_one_at_a_time_in_submission_order(self):
        first_started = Event()
        allow_first_to_finish = Event()
        calls = []

        def execute(action, _cancel_event):
            calls.append(("start", action.name))
            if action.name == "first":
                first_started.set()
                allow_first_to_finish.wait(1)
            calls.append(("end", action.name))

        dispatcher = InputDispatcher(execute)
        self.addCleanup(dispatcher.shutdown)
        dispatcher.submit(ParsedAction("first", {"key": "a"}))
        dispatcher.submit(ParsedAction("second", {"key": "b"}))

        self.assertTrue(first_started.wait(1))
        self.assertNotIn(("start", "second"), calls)
        allow_first_to_finish.set()
        self.assertTrue(dispatcher.wait_idle())
        self.assertEqual(
            calls,
            [
                ("start", "first"),
                ("end", "first"),
                ("start", "second"),
                ("end", "second"),
            ],
        )

    def test_release_interrupts_current_action_and_drops_older_pending_input(self):
        first_started = Event()
        calls = []

        def execute(action, cancel_event):
            calls.append(("start", action.name))
            if action.name == "first":
                first_started.set()
                cancel_event.wait(1)
                calls.append(("cancelled", cancel_event.is_set()))
            calls.append(("end", action.name))

        dispatcher = InputDispatcher(execute)
        self.addCleanup(dispatcher.shutdown)
        dispatcher.submit(ParsedAction("first", {"key": "a"}))
        self.assertTrue(first_started.wait(1))
        dispatcher.submit(ParsedAction("stale", {"key": "b"}))
        dispatcher.submit(ParsedAction("release", {}, release_all=True))

        self.assertTrue(dispatcher.wait_idle())
        self.assertIn(("cancelled", True), calls)
        self.assertNotIn(("start", "stale"), calls)
        self.assertIn(("start", "release"), calls)

    def test_commands_submitted_after_release_still_run_after_release(self):
        calls = []
        dispatcher = InputDispatcher(lambda action, _event: calls.append(action.name))
        self.addCleanup(dispatcher.shutdown)

        dispatcher.submit(ParsedAction("release", {}, release_all=True))
        dispatcher.submit(ParsedAction("new", {"key": "a"}))

        self.assertTrue(dispatcher.wait_idle())
        self.assertEqual(calls, ["release", "new"])


if __name__ == "__main__":
    unittest.main()
