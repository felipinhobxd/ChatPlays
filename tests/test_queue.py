import unittest

from chatplays.app import MessageQueue


class QueueTests(unittest.TestCase):
    def test_max_length_keeps_newest(self):
        queue = MessageQueue(0, 2)
        queue.extend([
            {"message": "one"},
            {"message": "two"},
            {"message": "three"},
        ])
        self.assertEqual([m["message"] for m in queue.items], ["two", "three"])

    def test_zero_rate_flushes_immediately(self):
        queue = MessageQueue(0, 10)
        queue.extend([{"message": "one"}, {"message": "two"}])
        out = queue.pop_ready(queue.last_time)
        self.assertEqual(len(out), 2)

    def test_rate_spreads_batch(self):
        queue = MessageQueue(1.0, 10)
        start = queue.last_time
        queue.extend([{"message": str(i)} for i in range(4)])
        self.assertEqual(queue.pop_ready(start + 0.24), [])
        self.assertEqual(len(queue.pop_ready(start + 0.25)), 1)


if __name__ == "__main__":
    unittest.main()
