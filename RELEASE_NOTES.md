# ChatPlays v4.1.0

This update restores the safest part of the older ChatPlays workflow without bringing back the old heavy architecture.

- New **Game / Target** tab in the desktop UI.
- **Open program** mode lists visible Windows apps/games with window title, process, PID and executable path.
- Pick Minecraft, an emulator or another running game from that list and ChatPlays remembers the exact target.
- **Emulator + ROM** mode asks for the emulator `.exe` and ROM/game file, launches them together, then attaches to that emulator window.
- Keyboard commands are delivered directly to the selected window with Windows `PostMessage` instead of global `SendInput`.
- Mouse clicks and window-relative pointer messages are also sent to the selected window without moving the streamer's physical cursor.
- Target matching uses PID + executable path + process name + window title, reducing mistakes with multiple `javaw.exe` or emulator instances.
- If the selected window closes or cannot be found, ChatPlays fails closed: it logs the problem and **never falls back to the global Windows keyboard/mouse**.
- Existing Twitch/YouTube configuration, custom commands, aliases, HOLD, queue settings and live log remain available.

Compatibility note: isolated background input is strongest with emulators and games that accept normal Windows keyboard/mouse messages. Some 3D/raw-input games can ignore background mouse messages; ChatPlays intentionally does not switch to global input automatically because that would affect the rest of the PC.
