import copy
import math
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

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

    def _build_advanced_tab(self) -> None:
        tab = self.advanced_tab
        tab.columnconfigure(1, weight=1)
        queue_cfg = self.config["queue"]
        input_cfg = self.config["input"]

        self.countdown_var = tk.StringVar(value=str(self.config.get("countdown_seconds", 5)))
        self.message_rate_var = tk.StringVar(value=str(queue_cfg.get("message_rate", 0.35)))
        self.max_length_var = tk.StringVar(value=str(queue_cfg.get("max_length", 20)))
        self.default_press_var = tk.StringVar(
            value=str(input_cfg.get("default_press_seconds", 0.08))
        )

        fields = (
            ("Contagem antes de iniciar (s)", self.countdown_var),
            ("Velocidade da fila / message rate (s)", self.message_rate_var),
            ("Máximo de mensagens na fila", self.max_length_var),
            ("Duração padrão de tecla (s)", self.default_press_var),
        )
        for row, (label, variable) in enumerate(fields):
            ttk.Label(tab, text=label).grid(
                row=row,
                column=0,
                sticky="w",
                pady=6,
                padx=(0, 12),
            )
            ttk.Entry(tab, textvariable=variable, width=16).grid(
                row=row, column=1, sticky="w", pady=6
            )

        ttk.Label(
            tab,
            text=(
                "Os comandos de chat continuam chegando normalmente, mas teclas e mouse são "
                "executados em uma fila única para evitar inputs simultâneos conflitantes. "
                "Use 'soltar' / 'release' para interromper um comando temporizado e limpar "
                "inputs antigos ainda pendentes."
            ),
            wraplength=760,
        ).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(16, 0))

    def _build_config(self) -> dict[str, Any]:
        if self.command_name_var.get().strip() and not self._save_command(silent=True):
            raise ValueError("Existe um comando inválido no editor.")

        countdown = int(self.countdown_var.get())
        message_rate = float(self.message_rate_var.get().replace(",", "."))
        max_length = int(self.max_length_var.get())
        default_press = float(self.default_press_var.get().replace(",", "."))

        if countdown < 0:
            raise ValueError("A contagem antes de iniciar não pode ser negativa.")
        if not math.isfinite(message_rate) or message_rate < 0:
            raise ValueError("A velocidade da fila precisa ser um número finito e não negativo.")
        if max_length < 1:
            raise ValueError("O máximo da fila precisa ser pelo menos 1.")
        if not math.isfinite(default_press) or default_press <= 0:
            raise ValueError("A duração padrão da tecla precisa ser um número finito maior que zero.")

        return {
            "stream": {
                "twitch_channel": self.twitch_var.get().strip(),
                "youtube_channel_id": self.youtube_id_var.get().strip(),
                "youtube_stream_url": self.youtube_url_var.get().strip(),
            },
            "target": self._target_config(),
            "countdown_seconds": countdown,
            "queue": {
                "message_rate": message_rate,
                "max_length": max_length,
            },
            "input": {"default_press_seconds": default_press},
            "commands": copy.deepcopy(self.commands),
        }

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
