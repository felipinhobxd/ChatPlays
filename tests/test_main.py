import unittest
from pathlib import Path

from main import _run_ui


class FakeEvent:
    def __init__(self):
        self.set_called = False

    def set(self):
        self.set_called = True


class FakeWorker:
    def __init__(self):
        self.join_called = False

    def is_alive(self):
        return True

    def join(self):
        self.join_called = True


class FakeUI:
    def __init__(self):
        self.stop_event = FakeEvent()
        self.worker = FakeWorker()
        self.run_called = False

    def run(self):
        self.run_called = True


class MainShutdownTests(unittest.TestCase):
    def test_ui_shutdown_waits_for_runtime_cleanup(self):
        ui = FakeUI()

        _run_ui(Path("config.json"), ui_factory=lambda _path: ui)

        self.assertTrue(ui.run_called)
        self.assertTrue(ui.stop_event.set_called)
        self.assertTrue(ui.worker.join_called)


if __name__ == "__main__":
    unittest.main()
