from __future__ import annotations

from collections import deque
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Any

from .commands import CommandRegistry, ParsedAction
from .connections import TwitchConnection, YouTubeConnection
from .input import GameInput


class MessageQueue:
    def __init__(self, message_rate: float, max_length: int) -> None:
        self.message_rate = max(0.0, float(message_rate))
        self.max_length = max(1, int(max_length))
        self.items: deque[dict[str, str]] = deque(maxlen=self.max_length)
        self.last_time = time.monotonic()

    def extend(self, messages: list[dict[str, str]]) -> None:
        self.items.extend(messages)

    def pop_ready(self, now: float | None = None) -> list[dict[str, str]]:
        now = time.monotonic() if now is None else now
        if not self.items:
            self.last_time = now
            return []

        if self.message_rate == 0:
            count = len(self.items)
        else:
            ratio = (now - self.last_time) / self.message_rate
            count = int(ratio * len(self.items))

        if count <= 0:
            return []

        count = min(count, len(self.items))
        out = [self.items.popleft() for _ in range(count)]
        self.last_time = now
        return out


class ChatPlaysApp:
    def __init__(self, config: dict[str, Any], *, input_backend: GameInput | None = None) -> None:
        self.config = config
        input_cfg = config["input"]
        self.registry = CommandRegistry(config["commands"], input_cfg["default_press_seconds"])
        self.input = input_backend or GameInput()
        queue_cfg = config["queue"]
        self.queue = MessageQueue(queue_cfg["message_rate"], queue_cfg["max_length"])
        self.executor = ThreadPoolExecutor(max_workers=max(1, int(queue_cfg["workers"])))
        self.connections: list[Any] = []
        self._build_connections()

    def _build_connections(self) -> None:
        stream = self.config.get("stream", {})
        twitch = str(stream.get("twitch_channel", "")).strip()
        youtube_id = str(stream.get("youtube_channel_id", "")).strip()
        youtube_url = str(stream.get("youtube_stream_url", "")).strip()
        if twitch:
            self.connections.append(TwitchConnection(twitch))
        if youtube_id or youtube_url:
            self.connections.append(YouTubeConnection(youtube_id, youtube_url))

    def run(self) -> None:
        countdown = max(0, int(self.config.get("countdown_seconds", 5)))
        if countdown:
            print(f"ChatPlays starts in {countdown}s. Focus the game window.")
            for remaining in range(countdown, 0, -1):
                print(remaining)
                time.sleep(1)

        try:
            for connection in self.connections:
                try:
                    connection.connect()
                except Exception as exc:
                    print(f"[{connection.__class__.__name__}] initial connection failed: {exc}")

            print("ChatPlays running. Ctrl+C stops and releases every held input.")
            while True:
                received = 0
                for connection in self.connections:
                    messages = connection.poll()
                    received += len(messages)
                    self.queue.extend(messages)

                ready = self.queue.pop_ready()
                for message in ready:
                    self.executor.submit(self._handle_message, message)

                if not ready and received == 0:
                    time.sleep(0.01)
        except KeyboardInterrupt:
            print("\nStopping ChatPlays...")
        finally:
            self.input.release_all()
            for connection in self.connections:
                try:
                    connection.close()
                except Exception:
                    pass
            self.executor.shutdown(wait=False, cancel_futures=True)

    def _handle_message(self, message: dict[str, str]) -> None:
        action = self.registry.resolve(message.get("message", ""))
        if not action:
            return

        username = message.get("username", "unknown")
        platform = message.get("platform", "chat")
        print(f"[{platform}] {username}: {message.get('message', '')} -> {action.name}")
        try:
            self._execute(action)
        except Exception as exc:
            print(f"[input] {action.name}: {exc}")

    def _execute(self, action: ParsedAction) -> None:
        if action.release_all:
            self.input.release_all()
            return

        spec = action.spec
        default_seconds = self.registry.default_press_seconds

        if "key" in spec:
            key = str(spec["key"])
            if action.hold and action.duration is None:
                self.input.key_down(key)
                return
            duration = action.duration if action.duration is not None else float(spec.get("duration", default_seconds))
            self.input.press_key(key, duration)
            return

        if "mouse_button" in spec:
            button = str(spec["mouse_button"])
            if action.hold and action.duration is None:
                self.input.mouse_down(button)
                return
            duration = action.duration if action.duration is not None else float(spec.get("duration", default_seconds))
            self.input.click(button, duration)
            return

        if "mouse_move" in spec:
            move = spec["mouse_move"]
            if not isinstance(move, list) or len(move) != 2:
                raise ValueError("mouse_move must be [dx, dy]")
            self.input.move_relative(int(move[0]), int(move[1]))
            return

        raise ValueError(f"command {action.name!r} has no supported action")
