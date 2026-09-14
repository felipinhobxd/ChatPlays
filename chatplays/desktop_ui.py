import threading
from tkinter import messagebox

from .config import ConfigError, load_runtime_config
from .target import list_open_windows
from .ui import ChatPlaysUI as BaseChatPlaysUI
from .ui_targeting import choose_target_window


class ChatPlaysUI(BaseChatPlaysUI):
    """Desktop UI with fail-closed target selection and shared runtime validation."""

    def _refresh_targets(self) -> None:
        windows = list_open_windows()
        selected = choose_target_window(
            windows,
            self.config.get("target", {}),
            self.selected_window,
        )

        for item in self.target_tree.get_children():
            self.target_tree.delete(item)
        self.open_windows.clear()

        for window in windows:
            item_id = str(window.hwnd)
            self.open_windows[item_id] = window
            self.target_tree.insert(
                "",
                "end",
                iid=item_id,
                values=(window.title, window.process, window.pid, window.exe),
            )

        self.selected_window = selected
        if selected is not None:
            item_id = str(selected.hwnd)
            self.target_tree.selection_set(item_id)
            self.target_tree.see(item_id)
            self.selected_target_var.set(selected.label)
        elif windows:
            self.target_tree.selection_remove(self.target_tree.selection())
            self.selected_target_var.set("Selecione a janela exata do jogo.")
        else:
            self.selected_target_var.set("Nenhuma janela aberta encontrada.")

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self._save_config(notify=False):
            self.notebook.select(self.target_tab)
            return
        try:
            config = load_runtime_config(self.config_path)
        except (ConfigError, OSError, TypeError, ValueError) as exc:
            messagebox.showerror("Configuração incompleta", str(exc))
            return

        self.stop_event = threading.Event()
        self._set_status("Iniciando...", running=True)
        self._append_log("Iniciando ChatPlays...")
        self.notebook.select(self.log_tab)
        self.worker = threading.Thread(
            target=self._run_worker,
            args=(config, self.stop_event),
            daemon=True,
            name="ChatPlaysRuntime",
        )
        self.worker.start()
