import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from typing import Any, Callable, Protocol

from .commands import CommandRegistry, ParsedAction
from .connections import TwitchConnection, YouTubeConnection
from .input import GameInput

Log = Callable[[str], None]


class Connection(Protocol):
    def poll(self) -> list[dict[str, str]]: ...
    def close(self) -> None: ...


class MessageQueue:
    def __init__(self, message_rate: float, max_length: int) -> None:
        self.message_rate = max(0.0, float(message_rate))
        self.items: deque[dict[str, str]] = deque(maxlen=max(1, int(max_length)))
        self.last_time = time.monotonic()

    def extend(self, messages: list[dict[str, str]]) -> None:
        self.items.extend(messages)

    def pop_ready(self, now: float | None = None) -> list[dict[str, str]]:
        now = time.monotonic() if now is None else now
        if not self.items:
            self.last_time = now
            return []

        count = len(self.items) if self.message_rate == 0 else int(
            ((now - self.last_time) / self.message_rate) * len(self.items)
        )
        if count <= 0:
            return []

        ready = [self.items.popleft() for _ in range(min(count, len(self.items)))]
        self.last_time = now
        return ready


class ChatPlaysApp:
    def __init__(
        self,
        config: dict[str, Any],
        input_backend: GameInput | None = None,
        logger: Log = print,
    ) -> None:
        self.config = config
        self.log = logger
        self.input = input_backend or GameInput()
        self.registry = CommandRegistry(
            config["commands"], config["input"]["default_press_seconds"]
        )
        queue = config["queue"]
        self.queue = MessageQueue(queue["message_rate"], queue["max_length"])
        self.executor = ThreadPoolExecutor(max_workers=max(1, int(queue["workers"])))
        self.connections = self._connections(config["stream"])

    def _connections(self, stream: dict[str, Any]) -> list[Connection]:
        connections: list[Connection] = []
        twitch = str(stream.get("twitch_channel", "")).strip()
        youtube_id = str(stream.get("youtube_channel_id", "")).strip()
        youtube_url = str(stream.get("youtube_stream_url", "")).strip()
        if twitch:
            connections.append(TwitchConnection(twitch, logger=self.log))
        if youtube_id or youtube_url:
            connections.append(YouTubeConnection(youtube_id, youtube_url, logger=self.log))
        return connections

    def run(self, stop_event: Event | None = None) -> None:
        stop_event = stop_event or Event()
        countdown = max(0, int(self.config.get("countdown_seconds", 5)))
        if countdown:
            self.log(f"Iniciando em {countdown}s. Coloque o jogo em foco.")
            for remaining in range(countdown, 0, -1):
                self.log(str(remaining))
                if stop_event.wait(1):
                    return

        self.log("ChatPlays iniciado.")
        try:
            while not stop_event.is_set():
                received = 0
                for connection in self.connections:
                    messages = connection.poll()
                    received += len(messages)
                    self.queue.extend(messages)

                ready = self.queue.pop_ready()
                for message in ready:
                    self.executor.submit(self._handle_message, message)
                if not ready and not received:
                    stop_event.wait(0.01)
        except KeyboardInterrupt:
            self.log("Parando ChatPlays...")
        finally:
            self.input.release_all()
            for connection in self.connections:
                connection.close()
            self.executor.shutdown(wait=False, cancel_futures=True)
            self.log("ChatPlays parado; teclas e botões foram soltos.")

    def _handle_message(self, message: dict[str, str]) -> None:
        action = self.registry.resolve(message.get("message", ""))
        if not action:
            return
        self.log(
            f"[{message.get('platform', 'chat')}] {message.get('username', 'unknown')}: "
            f"{message.get('message', '')} -> {action.name}"
        )
        try:
            self._execute(action)
        except (OSError, RuntimeError, ValueError) as exc:
            self.log(f"[input] {action.name}: {exc}")

    def _execute(self, action: ParsedAction) -> None:
        if action.release_all:
            self.input.release_all()
            return

        spec = action.spec
        duration = action.duration
        if duration is None:
            duration = float(spec.get("duration", self.registry.default_press_seconds))

        if "key" in spec:
            key = str(spec["key"])
            if action.hold and action.duration is None:
                self.input.key_down(key)
            else:
                self.input.press_key(key, duration)
            return

        if "mouse_button" in spec:
            button = str(spec["mouse_button"])
            if action.hold and action.duration is None:
                self.input.mouse_down(button)
            else:
                self.input.click(button, duration)
            return

        move = spec.get("mouse_move")
        if isinstance(move, list) and len(move) == 2:
            self.input.move_relative(int(move[0]), int(move[1]))
            return
        raise ValueError(f"command {action.name!r} has no supported action")
