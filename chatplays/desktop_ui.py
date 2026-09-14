from .target import list_open_windows
from .ui import ChatPlaysUI as BaseChatPlaysUI
from .ui_targeting import choose_target_window


class ChatPlaysUI(BaseChatPlaysUI):
    """Desktop UI with fail-closed target selection."""

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
