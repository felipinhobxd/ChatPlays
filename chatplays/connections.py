from __future__ import annotations

import concurrent.futures
import json
import random
import re
import socket
import ssl
import time
from typing import Any

import requests


class TwitchConnection:
    """Anonymous, read-only Twitch IRC connection."""

    def __init__(self, channel: str) -> None:
        self.channel = channel.strip().lower().lstrip("#")
        self.sock: ssl.SSLSocket | None = None
        self.buffer = ""
        self._privmsg = re.compile(r"^:([^!]+)!.* PRIVMSG #[^ ]+ :(.*)$")

    def connect(self) -> None:
        self.close()
        print(f"[Twitch] connecting to #{self.channel}...")
        raw = socket.create_connection(("irc.chat.twitch.tv", 6697), timeout=10)
        context = ssl.create_default_context()
        self.sock = context.wrap_socket(raw, server_hostname="irc.chat.twitch.tv")
        self.sock.settimeout(0.02)
        nick = f"justinfan{random.randint(10000, 99999)}"
        self._send("PASS SCHMOOPIIE")
        self._send(f"NICK {nick}")
        self._send(f"JOIN #{self.channel}")
        print("[Twitch] connected")

    def _send(self, line: str) -> None:
        if not self.sock:
            return
        self.sock.sendall((line + "\r\n").encode("utf-8"))

    def poll(self) -> list[dict[str, str]]:
        if not self.sock:
            self.connect()

        try:
            while True:
                try:
                    chunk = self.sock.recv(4096)
                except socket.timeout:
                    break
                if not chunk:
                    raise ConnectionError("Twitch closed the connection")
                self.buffer += chunk.decode("utf-8", errors="replace")
        except Exception as exc:
            print(f"[Twitch] {exc}; reconnecting...")
            time.sleep(1)
            self.connect()
            return []

        messages: list[dict[str, str]] = []
        while "\r\n" in self.buffer:
            line, self.buffer = self.buffer.split("\r\n", 1)
            if line.startswith("PING"):
                self._send("PONG :tmi.twitch.tv")
                continue
            match = self._privmsg.match(line)
            if match:
                messages.append({"username": match.group(1), "message": match.group(2), "platform": "twitch"})
        return messages

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
    _initial_data_re = re.compile(r"(?:window\s*\[\s*[\"']ytInitialData[\"']\s*\]|ytInitialData)\s*=\s*({.+?})\s*;", re.DOTALL)
    _config_re = re.compile(r"(?:ytcfg\s*\.set)\s*\(({.+?})\)\s*;", re.DOTALL)

    def __init__(self, channel_id: str = "", stream_url: str = "") -> None:
        self.channel_id = channel_id.strip()
        self.stream_url = stream_url.strip()
        self.session: requests.Session | None = None
        self.config: dict[str, Any] = {}
        self.payload: dict[str, Any] = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.fetch_job: concurrent.futures.Future[list[dict[str, str]]] | None = None
        self.next_fetch_time = 0.0

    @staticmethod
    def _continuation(data: dict[str, Any]) -> str:
        cont = data["continuationContents"]["liveChatContinuation"]["continuations"][0]
        if "timedContinuationData" in cont:
            return cont["timedContinuationData"]["continuation"]
        return cont["invalidationContinuationData"]["continuation"]

    def connect(self) -> None:
        self.close_session()
        print("[YouTube] connecting...")
        self.session = requests.Session()
        self.session.headers["User-Agent"] = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36"
        )
        requests.utils.add_dict_to_cookiejar(self.session.cookies, {"CONSENT": "YES+"})

        if self.stream_url:
            live_url = self.stream_url
        elif self.channel_id:
            live_url = f"https://youtube.com/channel/{self.channel_id}/live"
        else:
            raise RuntimeError("YouTube requires channel_id or stream_url")

        page = self.session.get(live_url, timeout=15)
        if page.status_code == 404 and self.channel_id:
            page = self.session.get(f"https://youtube.com/c/{self.channel_id}/live", timeout=15)
        page.raise_for_status()

        initial_match = self._initial_data_re.search(page.text)
        if not initial_match:
            raise RuntimeError("YouTube: ytInitialData not found; is the channel live?")
        initial_data = json.loads(initial_match.group(1))

        try:
            iframe_continuation = initial_data["contents"]["twoColumnWatchNextResults"]["conversationBar"]["liveChatRenderer"]["header"]["liveChatHeaderRenderer"]["viewSelector"]["sortFilterSubMenuRenderer"]["subMenuItems"][1]["continuation"]["reloadContinuationData"]["continuation"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("YouTube live chat was not found; is the stream live and chat enabled?") from exc

        chat_page = self.session.get(
            f"https://youtube.com/live_chat?continuation={iframe_continuation}", timeout=15
        )
        chat_page.raise_for_status()

        initial_match = self._initial_data_re.search(chat_page.text)
        config_match = self._config_re.search(chat_page.text)
        if not initial_match or not config_match:
            raise RuntimeError("YouTube live-chat bootstrap data was not found")

        initial_data = json.loads(initial_match.group(1))
        self.config = json.loads(config_match.group(1))
        self.payload = {
            "context": self.config["INNERTUBE_CONTEXT"],
            "continuation": self._continuation(initial_data),
            "webClientInfo": {"isDocumentHidden": False},
        }
        self.next_fetch_time = 0.0
        print("[YouTube] connected")

    def _fetch(self) -> list[dict[str, str]]:
        assert self.session is not None
        endpoint = (
            "https://www.youtube.com/youtubei/v1/live_chat/get_live_chat"
            f"?key={self.config['INNERTUBE_API_KEY']}&prettyPrint=false"
        )
        response = self.session.post(endpoint, json=self.payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        self.payload["continuation"] = self._continuation(data)

        out: list[dict[str, str]] = []
        continuation = data.get("continuationContents", {}).get("liveChatContinuation", {})
        for action in continuation.get("actions", []):
            item = action.get("addChatItemAction", {}).get("item", {}).get("liveChatTextMessageRenderer")
            if not item:
                continue
            username = item.get("authorName", {}).get("simpleText", "unknown")
            parts: list[str] = []
            for part in item.get("message", {}).get("runs", []):
                if "text" in part:
                    parts.append(part["text"])
                elif "emoji" in part:
                    parts.append(part["emoji"].get("emojiId", ""))
            out.append({"username": username, "message": "".join(parts), "platform": "youtube"})
        return out

    def poll(self) -> list[dict[str, str]]:
        if self.session is None:
            try:
                self.connect()
            except Exception as exc:
                print(f"[YouTube] {exc}; retrying in 5s")
                time.sleep(5)
                return []

        now = time.time()
        if self.fetch_job is None and now >= self.next_fetch_time:
            self.fetch_job = self.executor.submit(self._fetch)
            return []

        if self.fetch_job is None or not self.fetch_job.done():
            return []

        job = self.fetch_job
        self.fetch_job = None
        self.next_fetch_time = now + self.FETCH_INTERVAL
        try:
            return job.result()
        except Exception as exc:
            print(f"[YouTube] {exc}; reconnecting")
            self.close_session()
            return []

    def close_session(self) -> None:
        if self.session:
            self.session.close()
        self.session = None
        self.config = {}
        self.payload = {}
        self.fetch_job = None

    def close(self) -> None:
        self.close_session()
        self.executor.shutdown(wait=False, cancel_futures=True)
