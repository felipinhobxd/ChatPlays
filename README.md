# ChatPlays

**Twitch/YouTube chat → controls sent only to the game you choose.**

ChatPlays v4 keeps the project intentionally small: native Python desktop UI, Twitch + YouTube chat, customizable commands and direct Windows window targeting.

## Download — Windows

Download **`ChatPlays.exe`** from the latest GitHub Release and run it. No Python, Node.js, browser, API key or installer is required.

The app saves its portable settings in `config.json` beside the executable.

## 1. Choose the game

Open the **Jogo / Alvo** tab first. ChatPlays has two modes:

### Program/game already open

Click **Atualizar lista** and choose the exact game window. The list shows:

- window title;
- process name;
- PID;
- executable path.

For Minecraft, choose the actual Minecraft window (commonly `javaw.exe`), not the launcher.

### Emulator + ROM

Choose both files:

```text
Emulator: C:\...\visualboyadvance\visualboyadvance-m.exe
ROM:      C:\...\Pokemon emerald pt br\PK EMR (PT-BR).gba
```

When you press **Iniciar**, ChatPlays launches the emulator with the ROM and attaches to that emulator window.

## Isolated input

Keyboard commands are delivered directly to the selected window with Windows `PostMessage`. Mouse clicks and window-relative pointer messages are also routed to that target, so the physical mouse cursor is not moved by ChatPlays.

The target is remembered using **PID + executable path + process name + window title**. This helps distinguish multiple instances such as different `javaw.exe` windows.

Most importantly, there is **no global-input fallback**. If the selected game closes or cannot be found, ChatPlays logs the error and sends nothing to the rest of Windows. OBS, browser, chat and other applications are not used as fallback targets.

> Some 3D/raw-input games can ignore background mouse messages. ChatPlays deliberately does not switch to global mouse/keyboard injection automatically, because doing that could affect the rest of the PC.

## Chat connections

The **Conexões** tab configures:

- public Twitch chat through IRC/TLS;
- YouTube Live chat without an API key;
- Twitch and YouTube simultaneously.

## Commands

The **Comandos** tab lets you add, edit, remove or restore controls. A command is stored as simple data:

```json
"jump": {"key": "space", "aliases": ["jump", "pular", "pulo"]}
```

Supported actions:

- `"key": "x"` or combos such as `"shift+f5"`;
- `"mouse_button": "left"` (`left`, `right`, `middle`);
- `"mouse_move": [80, 0]` for window-relative movement;
- optional `"duration": 0.2` in seconds.

Examples from chat:

```text
cima
pular
clique
hold cima 2s
segurar clique 500ms
hold w
soltar
```

`hold` / `segurar` can be timed or indefinite. `release` / `soltar` releases every key or mouse button held by ChatPlays.

## Advanced settings and log

The **Avançado** tab controls countdown, queue rate, queue length, workers and default press duration. The **Log** tab shows connections, received commands, target information and input errors live.

## Run from source

Requires Python 3.10+ on Windows:

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

Or double-click `run.bat`.

Console mode remains available:

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
chatplays/target.py      Windows window/process discovery + target resolver
chatplays/input.py       isolated PostMessage keyboard/mouse backend
chatplays/config.py      defaults + portable config
chatplays/ui.py          native Tkinter desktop UI
tests/                   targeted regression tests
```

## Credits

ChatPlays is MIT licensed. Parts of the Twitch/YouTube connection approach and keyboard mapping are adapted from DougDoug's MIT-licensed TwitchPlays project and prior ChatPlays versions. See [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
