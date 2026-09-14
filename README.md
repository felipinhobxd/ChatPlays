# ChatPlays

**Twitch/YouTube chat → real keyboard and mouse input.**

ChatPlays v4 is intentionally small. It keeps the useful idea behind [DougDoug's TwitchPlays](https://github.com/DougDougGithub/TwitchPlays) and removes the old project's heavy Node/web/installer architecture.

## Download — Windows

Download **`ChatPlays.exe`** from the latest GitHub Release and run it.

Double-click it. The app opens a native Windows UI where you configure Twitch/YouTube, commands, keys, mouse actions and timing, then press **Iniciar**. Settings are saved to `config.json` beside the executable automatically.

No Python, Node.js, browser, API key, or installer is required for the release build.

## What it does

- Reads public **Twitch** chat anonymously over IRC/TLS.
- Reads **YouTube Live** chat without an API key.
- Twitch and YouTube can run **at the same time**.
- Sends keyboard scan codes through Windows `SendInput`.
- Sends relative mouse movement/clicks for games such as Minecraft.
- Supports PT-BR and English aliases.
- Supports `hold` / `segurar` from 1 ms to 10 s or indefinitely.
- `release` / `soltar` releases every input ChatPlays is holding.
- Bounded DougDoug-style message queue prevents a whole chat batch firing at once.
- Reconnects one platform without freezing the other.
- The desktop UI starts/stops the runtime and shows a live log.
- Closing or stopping the app releases held inputs safely.

## Configuration

The **Conexões** tab configures Twitch and YouTube. The **Comandos** tab lets you add, edit or remove chat commands and map each one to a keyboard key, mouse button or relative mouse movement. The **Avançado** tab controls queue and timing values.

ChatPlays still stores everything in a portable `config.json` beside the executable. A command is just data:

```json
"jump": {"key": "space", "aliases": ["jump", "pular", "pulo"]}
```

Supported actions:

- `"key": "x"` or combos such as `"shift+f5"`
- `"mouse_button": "left"` (`left`, `right`, `middle`)
- `"mouse_move": [80, 0]` for relative camera movement
- optional `"duration": 0.2` in seconds

Chat examples:

```text
cima
pular
clique
hold cima 2s
segurar clique 500ms
hold w
soltar
```

The default file includes emulator arrows/A/B plus WASD, jump, mouse clicks and camera movement. Delete or change commands you do not use.

## Run from source

Requires Python 3.10+ on Windows:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

Or double-click `run.bat`.

Useful commands:

```powershell
.venv\Scripts\python main.py --headless
.venv\Scripts\python main.py --check
.venv\Scripts\python main.py --version
python -m unittest discover -s tests -v
```

## Project layout

```text
main.py                  entry point
chatplays/app.py         runtime + queue
chatplays/commands.py    parser + aliases + HOLD
chatplays/connections.py Twitch + YouTube readers
chatplays/input.py       Windows SendInput backend
chatplays/config.py      defaults + config validation
chatplays/ui.py          native Tkinter desktop UI
tests/                   targeted regression tests
```

## Scope

v4 deliberately targets the **foreground game on Windows**. That removes a large amount of fragile window targeting, launcher automation, local web UI, bundled drivers, virtual gamepad code and installer maintenance.

If a feature makes the core harder to understand than the feature is worth, it should stay out of the core.

## Credits

ChatPlays is MIT licensed. Parts of the Twitch/YouTube connection approach and DirectInput scan-code mapping are adapted from DougDoug's MIT-licensed TwitchPlays project and prior contributors. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
