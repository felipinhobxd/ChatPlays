# ChatPlays

A small Python app that lets **Twitch and/or YouTube live chat control the game currently focused on your Windows PC**.

This rewrite intentionally follows the spirit of [DougDoug's TwitchPlays](https://github.com/DougDougGithub/TwitchPlays): very little setup, very little code, and game input that behaves like real keyboard/mouse input. ChatPlays adds a cleaner config file, Twitch + YouTube at the same time, PT-BR aliases, safe HOLD/release, thread-safe overlapping inputs, tests, and automatic reconnects.

## Why this version is simpler

- Python instead of Node.js.
- One runtime dependency: `requests`.
- No web wizard, local server, installer framework, dashboard, profiles database, or bundled drivers.
- No Twitch OAuth required for reading public chat.
- No YouTube API key required.
- Commands live in one `config.json` file.
- Windows `SendInput` is used directly, so there is no `pyautogui`/`pynput`/`keyboard` stack.
- `Ctrl+C` always releases keys and mouse buttons before exiting.

## Start on Windows

1. Install Python 3.10+.
2. Double-click `run.bat`.
3. On first run, ChatPlays creates `config.json` from `config.example.json`.
4. Put your Twitch channel and/or YouTube channel/live URL in `config.json`.
5. Run `run.bat` again, focus the game during the countdown, and let chat play.

You can also run it manually:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
copy config.example.json config.json
.venv\Scripts\python main.py
```

Validate the config without connecting:

```powershell
.venv\Scripts\python main.py --check
```

## Commands

Commands are data, not code. Example:

```json
"jump": { "key": "space", "aliases": ["jump", "pular", "pulo"] }
```

Supported action fields:

- `"key": "x"` — keyboard key or combo such as `shift+f5`.
- `"mouse_button": "left"` — left/right/middle click.
- `"mouse_move": [80, 0]` — relative mouse movement, useful for camera control.
- `"duration": 0.2` — optional press duration in seconds.

Built-in chat syntax:

- `up`, `cima`, `a`, `jump`, `click`, etc. run configured actions.
- `hold up 2s` / `segurar cima 500ms` holds an input for a specific time.
- `hold up` keeps it held until `release` / `soltar`.
- `release` / `soltar` immediately releases everything ChatPlays is holding.

The example config already includes classic emulator controls plus Minecraft-friendly WASD, jump, click and camera commands. Delete or change anything you do not want.

## Queue

The queue keeps the useful behavior from DougDoug's template: chat messages can be spread over a short time instead of firing an entire Twitch batch at once.

```json
"queue": {
  "message_rate": 0.35,
  "max_length": 20,
  "workers": 20
}
```

Set `message_rate` to `0` for immediate processing.

## Notes

- The game must be the foreground window. This is intentional: it is much simpler and more compatible with games than the old background-window system.
- ChatPlays is Windows-first because its game input backend uses Windows `SendInput` scan codes.
- YouTube's public live-chat page can change over time; the reader reconnects automatically, but a future YouTube markup change may require a small update.

## Credits

ChatPlays is MIT licensed. Parts of the connection approach and DirectInput key-code mapping are adapted from DougDoug's MIT-licensed TwitchPlays project. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
