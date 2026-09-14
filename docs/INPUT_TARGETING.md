# Isolated window targeting

ChatPlays v4.1 sends controls only to an explicitly selected Windows window.

## Open program mode

The desktop UI enumerates visible top-level windows and stores the selected target using PID, executable path, process name and window title. PID is preferred while that exact process is alive; path/process/title are used to reacquire the intended window after a restart.

## Emulator + ROM mode

The UI stores the emulator executable and ROM path. On Start, ChatPlays launches:

```text
<emulator.exe> <rom-file>
```

and waits for the emulator window before connecting chat control.

## Input isolation

Keyboard events use `PostMessage(WM_KEYDOWN/WM_KEYUP)` against the resolved target HWND. Mouse buttons and window-relative mouse movement also use window messages. ChatPlays does not call a global input fallback if the target is missing.

If a target disappears, commands fail closed and the live log reports the problem. This protects OBS, browsers, editors and other applications from receiving chat controls.

Some raw-input games can ignore background mouse messages. That is treated as a compatibility limitation rather than a reason to silently enable global input.
