from concurrent.futures import Future, ThreadPoolExecutor
import json
import random
import re
import socket
import ssl
import time
from typing import Any

import requests


class TwitchConnection:
    """Anonymous, read-only Twitch IRC over TLS."""

    _privmsg = re.compile(r"^:([^!]+)!.* PRIVMSG #[^ ]+ :(.*)$")

    def __init__(self, channel: str) -> None:
        self.channel = channel.strip().lower().lstrip("#")
        self.sock: ssl.SSLSocket | None = None
        self.buffer = ""
        self.retry_at = 0.0

    def connect(self) -> None:
        self.close()
        raw = socket.create_connection(("irc.chat.twitch.tv", 6697), timeout=10)
        self.sock = ssl.create_default_context().wrap_socket(
            raw, server_hostname="irc.chat.twitch.tv"
        )
        self.sock.settimeout(0.02)
        self.buffer = ""
        nick = f"justinfan{random.randint(10000, 99999)}"
        for line in ("PASS SCHMOOPIIE", f"NICK {nick}", f"JOIN #{self.channel}"):
            self._send(line)
        print(f"[Twitch] connected to #{self.channel}")

    def _send(self, line: str) -> None:
        if self.sock:
            self.sock.sendall(f"{line}\r\n".encode())

    def poll(self) -> list[dict[str, str]]:
        now = time.monotonic()
        if not self.sock:
            if now < self.retry_at:
                return []
            try:
                self.connect()
            except Exception as exc:
                return self._retry(exc, now)

        try:
            while True:
                try:
                    chunk = self.sock.recv(4096)  # type: ignore[union-attr]
                except socket.timeout:
                    break
                if not chunk:
                    raise ConnectionError("connection closed")
                self.buffer += chunk.decode(errors="replace")
        except Exception as exc:
            return self._retry(exc, now)

        messages = []
        while "\r\n" in self.buffer:
            line, self.buffer = self.buffer.split("\r\n", 1)
            if line.startswith("PING"):
                self._send("PONG :tmi.twitch.tv")
                continue
            match = self._privmsg.match(line)
            if match:
                messages.append({
                    "username": match.group(1),
                    "message": match.group(2),
                    "platform": "twitch",
                })
        return messages

    def _retry(self, error: Exception, now: float) -> list[dict[str, str]]:
        print(f"[Twitch] {error}; retrying in 2s")
        self.close()
        self.retry_at = now + 2
        return []

    def close(self) -> None:
        if self.sock:
            try:
                self.sock.close()
            except OSError:
                pass
        self.sock = None


class YouTubeConnection:
    """No-API-key YouTube live-chat reader adapted from DougDoug TwitchPlays."""

    FETCH_INTERVAL = 1.0
    _initial_re = re.compile(
        r"(?:window\s*\[\s*[\"']ytInitialData[\"']\s*\]|ytInitialData)\s*=\s*({.+?})\s*;",
        re.DOTALL,
    )
    _config_re = re.compile(r"(?:ytcfg\s*\.set)\s*\(({.+?})\)\s*;", re.DOTALL)

    def __init__(self, channel_id: str = "", stream_url: str = "") -> None:
        self.channel_id = channel_id.strip()
        self.stream_url = stream_url.strip()
        self.session: requests.Session | None = None
        self.config: dict[str, Any] = {}
        self.payload: dict[str, Any] = {}
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.fetch_job: Future[list[dict[str, str]]] | None = None
        self.next_fetch = 0.0
        self.retry_at = 0.0

    @staticmethod
    def _continuation(data: dict[str, Any]) -> str:
        continuation = data["continuationContents"]["liveChatContinuation"]["continuations"][0]
        for key in ("timedContinuationData", "invalidationContinuationData"):
            if key in continuation:
                return continuation[key]["continuation"]
        raise KeyError("YouTube continuation token not found")

    @staticmethod
    def _extract(pattern: re.Pattern[str], text: str, label: str) -> dict[str, Any]:
        match = pattern.search(text)
        if not match:
            raise RuntimeError(f"YouTube {label} not found")
        return json.loads(match.group(1))

    def connect(self) -> None:
        self._close_session()
        session = requests.Session()
        session.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/153 Safari/537.36"
        )
        requests.utils.add_dict_to_cookiejar(session.cookies, {"CONSENT": "YES+"})
        self.session = session

        live_url = self.stream_url or f"https://youtube.com/channel/{self.channel_id}/live"
        page = session.get(live_url, timeout=15)
        if page.status_code == 404 and self.channel_id and not self.stream_url:
            page = session.get(f"https://youtube.com/c/{self.channel_id}/live", timeout=15)
        page.raise_for_status()

        initial = self._extract(self._initial_re, page.text, "ytInitialData")
        try:
            items = initial["contents"]["twoColumnWatchNextResults"]["conversationBar"]
            items = items["liveChatRenderer"]["header"]["liveChatHeaderRenderer"]
            items = items["viewSelector"]["sortFilterSubMenuRenderer"]["subMenuItems"]
            iframe_token = items[1]["continuation"]["reloadContinuationData"]["continuation"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("YouTube live chat not found; is the stream live?") from exc

        chat = session.get(
            f"https://youtube.com/live_chat?continuation={iframe_token}", timeout=15
        )
        chat.raise_for_status()
        initial = self._extract(self._initial_re, chat.text, "live-chat data")
        self.config = self._extract(self._config_re, chat.text, "client config")
        self.payload = {
            "context": self.config["INNERTUBE_CONTEXT"],
            "continuation": self._continuation(initial),
            "webClientInfo": {"isDocumentHidden": False},
        }
        self.next_fetch = 0.0
        print("[YouTube] connected")

    def _fetch(self) -> list[dict[str, str]]:
        if not self.session:
            return []
        endpoint = (
            "https://www.youtube.com/youtubei/v1/live_chat/get_live_chat"
            f"?key={self.config['INNERTUBE_API_KEY']}&prettyPrint=false"
        )
        response = self.session.post(endpoint, json=self.payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        self.payload["continuation"] = self._continuation(data)

        messages = []
        live_chat = data.get("continuationContents", {}).get("liveChatContinuation", {})
        for action in live_chat.get("actions", []):
            item = action.get("addChatItemAction", {}).get("item", {})
            item = item.get("liveChatTextMessageRenderer")
            if not item:
                continue
            parts = []
            for part in item.get("message", {}).get("runs", []):
                parts.append(part.get("text") or part.get("emoji", {}).get("emojiId", ""))
            messages.append({
                "username": item.get("authorName", {}).get("simpleText", "unknown"),
                "message": "".join(parts),
                "platform": "youtube",
            })
        return messages

    def poll(self) -> list[dict[str, str]]:
        now = time.monotonic()
        if self.session is None:
            if now < self.retry_at:
                return []
            try:
                self.connect()
            except Exception as exc:
                return self._retry(exc, now)

        if self.fetch_job is None and now >= self.next_fetch:
            self.fetch_job = self.executor.submit(self._fetch)
            return []
        if self.fetch_job is None or not self.fetch_job.done():
            return []

        job, self.fetch_job = self.fetch_job, None
        self.next_fetch = now + self.FETCH_INTERVAL
        try:
            return job.result()
        except Exception as exc:
            return self._retry(exc, now)

    def _retry(self, error: Exception, now: float) -> list[dict[str, str]]:
        print(f"[YouTube] {error}; retrying in 5s")
        self._close_session()
        self.retry_at = now + 5
        return []

    def _close_session(self) -> None:
        if self.fetch_job and not self.fetch_job.done():
            self.fetch_job.cancel()
        self.fetch_job = None
        if self.session:
            self.session.close()
        self.session = None
        self.config.clear()
        self.payload.clear()

    def close(self) -> None:
        self._close_session()
        self.executor.shutdown(wait=False, cancel_futures=True)
