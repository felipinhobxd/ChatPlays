# ChatPlays v4.0.1

This update fixes the v4.0.0 first-run experience and makes ChatPlays a real desktop app.

- `ChatPlays.exe` now opens a native Windows configuration UI instead of creating a JSON file and closing.
- Configure Twitch channel, YouTube channel/live URL, commands, keys, mouse actions, aliases, durations and queue settings without editing files.
- Add, edit, remove and restore commands from the Commands tab.
- Start and stop ChatPlays directly from the UI.
- Live log shows connection status, chat commands and input errors.
- Stop/exit safely releases held keys and mouse buttons.
- `config.json` is still saved beside the executable for portability.
- `--headless` remains available when running from a console.
- Windows builds now use PyInstaller windowed mode, so the release behaves like a desktop application.
