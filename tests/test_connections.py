import unittest

from chatplays.connections import TwitchConnection, YouTubeConnection


class FakeSocket:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.sent = []
        self.closed = False

    def recv(self, _size):
        if not self.chunks:
            raise TimeoutError
        item = self.chunks.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def sendall(self, payload):
        self.sent.append(payload)

    def close(self):
        self.closed = True


class ConnectionTests(unittest.TestCase):
    def test_twitch_privmsg_is_parsed(self):
        connection = TwitchConnection("Example")
        connection.sock = FakeSocket(
            [b":viewer!viewer@viewer.tmi.twitch.tv PRIVMSG #example :cima\r\n"]
        )
        messages = connection.poll()
        self.assertEqual(
            messages,
            [{"username": "viewer", "message": "cima", "platform": "twitch"}],
        )
        connection.close()

    def test_twitch_split_utf8_sequence_is_preserved(self):
        connection = TwitchConnection("example")
        prefix = b":viewer!viewer@viewer.tmi.twitch.tv PRIVMSG #example :olhar "
        suffix = "cima 😀\r\n".encode()
        split_at = suffix.index(b"\xf0") + 2
        connection.sock = FakeSocket([prefix + suffix[:split_at], suffix[split_at:]])

        messages = connection.poll()

        self.assertEqual(messages[0]["message"], "olhar cima 😀")
        self.assertNotIn("�", messages[0]["message"])
        connection.close()

    def test_twitch_ping_is_answered(self):
        connection = TwitchConnection("example")
        sock = FakeSocket([b"PING :tmi.twitch.tv\r\n"])
        connection.sock = sock
        self.assertEqual(connection.poll(), [])
        self.assertIn(b"PONG :tmi.twitch.tv\r\n", sock.sent)
        connection.close()

    def test_youtube_timed_continuation(self):
        data = {
            "continuationContents": {
                "liveChatContinuation": {
                    "continuations": [
                        {"timedContinuationData": {"continuation": "next-token"}}
                    ]
                }
            }
        }
        self.assertEqual(YouTubeConnection._continuation(data), "next-token")

    def test_youtube_invalidation_continuation(self):
        data = {
            "continuationContents": {
                "liveChatContinuation": {
                    "continuations": [
                        {"invalidationContinuationData": {"continuation": "next-token"}}
                    ]
                }
            }
        }
        self.assertEqual(YouTubeConnection._continuation(data), "next-token")


if __name__ == "__main__":
    unittest.main()
