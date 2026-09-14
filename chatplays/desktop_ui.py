import copy
import math
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from .config import ConfigError, load_runtime_config
from .profiles import (
    BUILTIN_PROFILES,
    ProfileError,
    apply_profile,
    load_profiles,
    load_user_profiles,
    profile_from_config,
    profile_path,
    save_profiles,
)
from .target import list_open_windows
from .ui import ChatPlaysUI as BaseChatPlaysUI
from .ui_targeting import choose_target_window


class ChatPlaysUI(BaseChatPlaysUI):
    """Desktop UI with fail-closed target selection, profiles and shared validation."""

    def _build_ui(self) -> None:
        super()._build_ui()
        self.profiles_tab = ttk.Frame(self.notebook, padding=16)
        self.notebook.insert(1, self.profiles_tab, text="Perfis")
        self._build_profiles_tab()

    def _build_profiles_tab(self) -> None:
        tab = self.profiles_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        ttk.Label(tab, text="Perfis de jogo", font=("Segoe UI", 13, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            tab,
            text=(
                "Salve alvo, comandos e ajustes de gameplay por jogo. Twitch e YouTube não fazem "
                "parte do perfil, então suas conexões continuam iguais ao trocar de jogo."
            ),
            wraplength=880,
        ).grid(row=1, column=0, sticky="w", pady=(4, 12))

        body = ttk.Frame(tab)
        body.grid(row=2, column=0, sticky="nsew")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)

        self.profile_tree = ttk.Treeview(
            body,
            columns=("name", "kind"),
            show="headings",
            selectmode="browse",
            height=12,
        )
        self.profile_tree.heading("name", text="Perfil")
        self.profile_tree.heading("kind", text="Tipo")
        self.profile_tree.column("name", width=420, anchor="w")
        self.profile_tree.column("kind", width=180, anchor="w")
        self.profile_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(body, orient="vertical", command=self.profile_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.profile_tree.configure(yscrollcommand=scrollbar.set)
        self.profile_tree.bind("<<TreeviewSelect>>", self._on_profile_selected)

        editor = ttk.LabelFrame(tab, text="Perfil selecionado", padding=10)
        editor.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        editor.columnconfigure(1, weight=1)
        self.profile_name_var = tk.StringVar()
        ttk.Label(editor, text="Nome").grid(row=0, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.profile_name_var).grid(
            row=0, column=1, sticky="ew", padx=(8, 0)
        )

        buttons = ttk.Frame(editor)
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Aplicar perfil", command=self._apply_selected_profile).pack(
            side="left"
        )
        ttk.Button(buttons, text="Salvar configuração atual", command=self._save_current_profile).pack(
            side="left", padx=6
        )
        ttk.Button(buttons, text="Excluir personalizado", command=self._delete_selected_profile).pack(
            side="left"
        )

        self.profile_file_var = tk.StringVar(value=f"Arquivo: {profile_path(self.config_path)}")
        ttk.Label(editor, textvariable=self.profile_file_var, wraplength=820).grid(
            row=2, column=0, columnspan=2, sticky="w", pady=(10, 0)
        )
        ttk.Label(
            editor,
            text=(
                "Os modelos Minecraft e Pokémon / Emulador não possuem caminho de executável/ROM. "
                "Aplique o modelo, escolha o jogo real em Jogo / Alvo e salve por cima ou com outro nome."
            ),
            wraplength=820,
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        self._load_profiles_for_ui()
        self._refresh_profile_table()

    def _load_profiles_for_ui(self) -> None:
        path = profile_path(self.config_path)
        try:
            self.user_profiles = load_user_profiles(path)
            self.profiles = load_profiles(path)
        except (OSError, ProfileError) as exc:
            self.user_profiles = {}
            self.profiles = copy.deepcopy(BUILTIN_PROFILES)
            messagebox.showwarning(
                "Perfis não puderam ser carregados",
                f"{exc}\n\nOs modelos internos continuarão disponíveis.",
            )

    def _refresh_profile_table(self, selected: str | None = None) -> None:
        for item in self.profile_tree.get_children():
            self.profile_tree.delete(item)
        for name in sorted(self.profiles, key=str.casefold):
            if name in self.user_profiles:
                kind = "Personalizado"
            else:
                kind = "Modelo interno"
            self.profile_tree.insert("", "end", iid=name, values=(name, kind))
        if selected and selected in self.profiles:
            self.profile_tree.selection_set(selected)
            self.profile_tree.see(selected)
            self.profile_name_var.set(selected)

    def _on_profile_selected(self, _event: tk.Event) -> None:
        selected = self.profile_tree.selection()
        if selected:
            self.profile_name_var.set(selected[0])

    def _profile_change_allowed(self) -> bool:
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("ChatPlays em execução", "Pare o ChatPlays antes de trocar perfis.")
            return False
        return True

    def _apply_selected_profile(self) -> None:
        if not self._profile_change_allowed():
            return
        selected = self.profile_tree.selection()
        name = selected[0] if selected else self.profile_name_var.get().strip()
        profile = self.profiles.get(name)
        if not profile:
            messagebox.showerror("Perfil não encontrado", "Selecione um perfil válido.")
            return

        current = copy.deepcopy(self.config)
        current["stream"] = {
            "twitch_channel": self.twitch_var.get().strip(),
            "youtube_channel_id": self.youtube_id_var.get().strip(),
            "youtube_stream_url": self.youtube_url_var.get().strip(),
        }
        self.config = apply_profile(current, profile)
        target = self.config.get("target", {})
        self.target_mode_var.set(str(target.get("mode", "program")))
        self.emulator_var.set(str(target.get("emulator_exe", "")))
        self.rom_var.set(str(target.get("rom", "")))
        self.selected_window = None

        self.commands = copy.deepcopy(self.config.get("commands", {}))
        self._new_command()
        self._refresh_command_table()
        self.countdown_var.set(str(self.config.get("countdown_seconds", 5)))
        queue_cfg = self.config.get("queue", {})
        input_cfg = self.config.get("input", {})
        self.message_rate_var.set(str(queue_cfg.get("message_rate", 0.35)))
        self.max_length_var.set(str(queue_cfg.get("max_length", 20)))
        self.default_press_var.set(str(input_cfg.get("default_press_seconds", 0.08)))
        self._refresh_targets()
        self._append_log(f"Perfil '{name}' aplicado. Conexões da live foram preservadas.")

    def _save_current_profile(self) -> None:
        if not self._profile_change_allowed():
            return
        name = self.profile_name_var.get().strip()
        if not name:
            messagebox.showerror("Nome obrigatório", "Informe um nome para o perfil.")
            return
        if name in self.profiles and not messagebox.askyesno(
            "Sobrescrever perfil", f"Sobrescrever o perfil '{name}' com a configuração atual?"
        ):
            return
        try:
            config = self._build_config()
            self.user_profiles[name] = profile_from_config(config)
            save_profiles(profile_path(self.config_path), self.user_profiles)
            self.profiles = load_profiles(profile_path(self.config_path))
        except (OSError, TypeError, ValueError, ProfileError) as exc:
            messagebox.showerror("Não foi possível salvar o perfil", str(exc))
            return
        self._refresh_profile_table(selected=name)
        self._append_log(f"Perfil '{name}' salvo em profiles.json.")

    def _delete_selected_profile(self) -> None:
        if not self._profile_change_allowed():
            return
        selected = self.profile_tree.selection()
        name = selected[0] if selected else self.profile_name_var.get().strip()
        if name not in self.user_profiles:
            messagebox.showinfo(
                "Modelo interno",
                "Esse é um modelo interno. Ele não é apagado; salve uma versão personalizada se quiser alterá-lo.",
            )
            return
        if not messagebox.askyesno("Excluir perfil", f"Excluir o perfil personalizado '{name}'?"):
            return
        try:
            self.user_profiles.pop(name, None)
            save_profiles(profile_path(self.config_path), self.user_profiles)
            self.profiles = load_profiles(profile_path(self.config_path))
        except (OSError, ProfileError) as exc:
            messagebox.showerror("Não foi possível excluir o perfil", str(exc))
            return
        self.profile_name_var.set("")
        self._refresh_profile_table()
        self._append_log(f"Perfil personalizado '{name}' excluído.")

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
