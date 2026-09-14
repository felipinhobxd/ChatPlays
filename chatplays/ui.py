import copy
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from . import __version__
from .app import ChatPlaysApp
from .commands import CommandRegistry
from .config import DEFAULT_CONFIG, ConfigError, load_config, read_config, save_config

_ACTION_TYPES = ("key", "mouse_button", "mouse_move")


def _command_target(spec: dict[str, Any]) -> tuple[str, str]:
    if "key" in spec:
        return "key", str(spec["key"])
    if "mouse_button" in spec:
        return "mouse_button", str(spec["mouse_button"])
    move = spec.get("mouse_move")
    if isinstance(move, list) and len(move) == 2:
        return "mouse_move", f"{move[0]},{move[1]}"
    return "key", ""


def _parse_target(action_type: str, target: str) -> dict[str, Any]:
    target = target.strip()
    if action_type == "key":
        if not target:
            raise ValueError("Informe uma tecla, por exemplo: w, space, up ou shift+f5.")
        return {"key": target}
    if action_type == "mouse_button":
        button = target.lower()
        if button not in {"left", "right", "middle"}:
            raise ValueError("Botão do mouse deve ser left, right ou middle.")
        return {"mouse_button": button}
    if action_type == "mouse_move":
        parts = [part.strip() for part in target.split(",")]
        if len(parts) != 2:
            raise ValueError("Movimento do mouse deve ser dx,dy. Exemplo: 80,0.")
        return {"mouse_move": [int(parts[0]), int(parts[1])]}
    raise ValueError("Tipo de ação inválido.")


class ChatPlaysUI:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.root = tk.Tk()
        self.root.title(f"ChatPlays {__version__}")
        self.root.minsize(900, 650)
        self.root.geometry("1000x720")

        self.log_queue: queue.Queue[str] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.stop_event: threading.Event | None = None
        self.commands: dict[str, dict[str, Any]] = {}
        self.selected_command: str | None = None

        self._load_config()
        self._build_ui()
        self._refresh_command_table()
        self._set_status("Parado", running=False)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self._drain_log_queue)

    def _load_config(self) -> None:
        if not self.config_path.exists():
            save_config(self.config_path, copy.deepcopy(DEFAULT_CONFIG))
        try:
            self.config = read_config(self.config_path)
        except ConfigError as exc:
            messagebox.showwarning(
                "Configuração inválida",
                f"Não foi possível ler config.json:\n\n{exc}\n\nOs padrões serão usados.",
            )
            self.config = copy.deepcopy(DEFAULT_CONFIG)
        self.commands = copy.deepcopy(self.config.get("commands", DEFAULT_CONFIG["commands"]))

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(14, 12, 14, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="ChatPlays", font=("Segoe UI", 18, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Configure o chat e os controles, depois clique em Iniciar.",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(header, textvariable=self.status_var)
        self.status_label.grid(row=0, column=1, rowspan=2, sticky="e")

        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))

        self.connections_tab = ttk.Frame(self.notebook, padding=16)
        self.commands_tab = ttk.Frame(self.notebook, padding=12)
        self.advanced_tab = ttk.Frame(self.notebook, padding=16)
        self.log_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.connections_tab, text="Conexões")
        self.notebook.add(self.commands_tab, text="Comandos")
        self.notebook.add(self.advanced_tab, text="Avançado")
        self.notebook.add(self.log_tab, text="Log")

        self._build_connections_tab()
        self._build_commands_tab()
        self._build_advanced_tab()
        self._build_log_tab()
        self._build_footer()

    def _build_connections_tab(self) -> None:
        tab = self.connections_tab
        tab.columnconfigure(1, weight=1)
        stream = self.config["stream"]

        self.twitch_var = tk.StringVar(value=str(stream.get("twitch_channel", "")))
        self.youtube_id_var = tk.StringVar(value=str(stream.get("youtube_channel_id", "")))
        self.youtube_url_var = tk.StringVar(value=str(stream.get("youtube_stream_url", "")))

        ttk.Label(tab, text="Twitch", font=("Segoe UI", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        ttk.Label(tab, text="Canal").grid(row=1, column=0, sticky="w", padx=(0, 12))
        ttk.Entry(tab, textvariable=self.twitch_var).grid(row=1, column=1, sticky="ew")
        ttk.Label(
            tab,
            text="Exemplo: sindromegames. Não precisa de OAuth para ler o chat público.",
        ).grid(row=2, column=1, sticky="w", pady=(4, 18))

        ttk.Separator(tab).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        ttk.Label(tab, text="YouTube Live", font=("Segoe UI", 12, "bold")).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
        ttk.Label(tab, text="Channel ID").grid(row=5, column=0, sticky="w", padx=(0, 12))
        ttk.Entry(tab, textvariable=self.youtube_id_var).grid(row=5, column=1, sticky="ew")
        ttk.Label(tab, text="URL da live").grid(
            row=6, column=0, sticky="w", padx=(0, 12), pady=(10, 0)
        )
        ttk.Entry(tab, textvariable=self.youtube_url_var).grid(
            row=6, column=1, sticky="ew", pady=(10, 0)
        )
        ttk.Label(
            tab,
            text="Você pode preencher o Channel ID ou colar a URL da live. Twitch e YouTube podem funcionar juntos.",
            wraplength=720,
        ).grid(row=7, column=1, sticky="w", pady=(4, 0))

    def _build_commands_tab(self) -> None:
        tab = self.commands_tab
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)

        columns = ("name", "type", "target", "aliases", "duration")
        self.command_tree = ttk.Treeview(tab, columns=columns, show="headings", selectmode="browse")
        headings = {
            "name": "Nome",
            "type": "Tipo",
            "target": "Tecla / alvo",
            "aliases": "Comandos do chat",
            "duration": "Duração",
        }
        widths = {"name": 120, "type": 110, "target": 120, "aliases": 360, "duration": 80}
        for column in columns:
            self.command_tree.heading(column, text=headings[column])
            self.command_tree.column(column, width=widths[column], anchor="w")
        self.command_tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=self.command_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.command_tree.configure(yscrollcommand=scrollbar.set)
        self.command_tree.bind("<<TreeviewSelect>>", self._on_command_selected)

        editor = ttk.LabelFrame(tab, text="Editar comando", padding=10)
        editor.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        editor.columnconfigure(1, weight=1)
        editor.columnconfigure(3, weight=1)

        self.command_name_var = tk.StringVar()
        self.command_type_var = tk.StringVar(value="key")
        self.command_target_var = tk.StringVar()
        self.command_aliases_var = tk.StringVar()
        self.command_duration_var = tk.StringVar()

        ttk.Label(editor, text="Nome").grid(row=0, column=0, sticky="w")
        ttk.Entry(editor, textvariable=self.command_name_var).grid(
            row=0, column=1, sticky="ew", padx=(6, 14)
        )
        ttk.Label(editor, text="Tipo").grid(row=0, column=2, sticky="w")
        ttk.Combobox(
            editor,
            textvariable=self.command_type_var,
            values=_ACTION_TYPES,
            state="readonly",
        ).grid(row=0, column=3, sticky="ew", padx=(6, 0))

        ttk.Label(editor, text="Tecla / alvo").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(editor, textvariable=self.command_target_var).grid(
            row=1, column=1, sticky="ew", padx=(6, 14), pady=(8, 0)
        )
        ttk.Label(editor, text="Duração (s)").grid(row=1, column=2, sticky="w", pady=(8, 0))
        ttk.Entry(editor, textvariable=self.command_duration_var).grid(
            row=1, column=3, sticky="ew", padx=(6, 0), pady=(8, 0)
        )

        ttk.Label(editor, text="Aliases").grid(row=2, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(editor, textvariable=self.command_aliases_var).grid(
            row=2, column=1, columnspan=3, sticky="ew", padx=(6, 0), pady=(8, 0)
        )
        ttk.Label(
            editor,
            text="Separe aliases por vírgula. Mouse move usa dx,dy, por exemplo 80,0. Teclas aceitam combos como shift+f5.",
            wraplength=760,
        ).grid(row=3, column=0, columnspan=4, sticky="w", pady=(8, 0))

        buttons = ttk.Frame(editor)
        buttons.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(10, 0))
        ttk.Button(buttons, text="Novo", command=self._new_command).pack(side="left")
        ttk.Button(buttons, text="Salvar comando", command=self._save_command).pack(
            side="left", padx=6
        )
        ttk.Button(buttons, text="Remover", command=self._remove_command).pack(side="left")
        ttk.Button(buttons, text="Restaurar padrões", command=self._reset_commands).pack(
            side="right"
        )

    def _build_advanced_tab(self) -> None:
        tab = self.advanced_tab
        tab.columnconfigure(1, weight=1)
        queue_cfg = self.config["queue"]
        input_cfg = self.config["input"]

        self.countdown_var = tk.StringVar(value=str(self.config.get("countdown_seconds", 5)))
        self.message_rate_var = tk.StringVar(value=str(queue_cfg.get("message_rate", 0.35)))
        self.max_length_var = tk.StringVar(value=str(queue_cfg.get("max_length", 20)))
        self.workers_var = tk.StringVar(value=str(queue_cfg.get("workers", 20)))
        self.default_press_var = tk.StringVar(
            value=str(input_cfg.get("default_press_seconds", 0.08))
        )

        fields = (
            ("Contagem antes de iniciar (s)", self.countdown_var),
            ("Velocidade da fila / message rate (s)", self.message_rate_var),
            ("Máximo de mensagens na fila", self.max_length_var),
            ("Workers simultâneos", self.workers_var),
            ("Duração padrão de tecla (s)", self.default_press_var),
        )
        for row, (label, variable) in enumerate(fields):
            ttk.Label(tab, text=label).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 12))
            ttk.Entry(tab, textvariable=variable, width=16).grid(
                row=row, column=1, sticky="w", pady=6
            )

        ttk.Label(
            tab,
            text="Os valores padrão funcionam bem para a maioria dos jogos. Reduza message rate para responder mais rápido; aumente se o chat estiver muito caótico.",
            wraplength=720,
        ).grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(16, 0))

    def _build_log_tab(self) -> None:
        self.log_text = tk.Text(self.log_tab, wrap="word", state="disabled", height=20)
        self.log_text.pack(fill="both", expand=True)

    def _build_footer(self) -> None:
        footer = ttk.Frame(self.root, padding=(14, 0, 14, 14))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, text=f"Config: {self.config_path}").grid(row=0, column=0, sticky="w")
        ttk.Button(footer, text="Salvar", command=self._save_config).grid(
            row=0, column=1, padx=(8, 0)
        )
        self.stop_button = ttk.Button(footer, text="Parar", command=self._stop)
        self.stop_button.grid(row=0, column=2, padx=(8, 0))
        self.start_button = ttk.Button(footer, text="Iniciar", command=self._start)
        self.start_button.grid(row=0, column=3, padx=(8, 0))

    def _refresh_command_table(self) -> None:
        for item in self.command_tree.get_children():
            self.command_tree.delete(item)
        for name, spec in self.commands.items():
            action_type, target = _command_target(spec)
            aliases = ", ".join(str(alias) for alias in spec.get("aliases", []))
            duration = spec.get("duration", "")
            self.command_tree.insert(
                "",
                "end",
                iid=name,
                values=(name, action_type, target, aliases, duration),
            )

    def _on_command_selected(self, _event: tk.Event) -> None:
        selected = self.command_tree.selection()
        if not selected:
            return
        name = selected[0]
        spec = self.commands[name]
        action_type, target = _command_target(spec)
        self.selected_command = name
        self.command_name_var.set(name)
        self.command_type_var.set(action_type)
        self.command_target_var.set(target)
        self.command_aliases_var.set(", ".join(str(alias) for alias in spec.get("aliases", [])))
        self.command_duration_var.set(str(spec.get("duration", "")))

    def _new_command(self) -> None:
        self.command_tree.selection_remove(self.command_tree.selection())
        self.selected_command = None
        self.command_name_var.set("")
        self.command_type_var.set("key")
        self.command_target_var.set("")
        self.command_aliases_var.set("")
        self.command_duration_var.set("")

    def _save_command(self, *, silent: bool = False) -> bool:
        try:
            name = self.command_name_var.get().strip()
            if not name:
                raise ValueError("Informe um nome para o comando.")
            spec = _parse_target(self.command_type_var.get(), self.command_target_var.get())
            aliases = [item.strip() for item in self.command_aliases_var.get().split(",") if item.strip()]
            spec["aliases"] = aliases
            duration_text = self.command_duration_var.get().strip()
            if duration_text:
                duration = float(duration_text.replace(",", "."))
                if duration <= 0:
                    raise ValueError("Duração precisa ser maior que zero.")
                spec["duration"] = duration

            old_name = self.selected_command
            if old_name and old_name != name:
                self.commands.pop(old_name, None)
            candidate = copy.deepcopy(self.commands)
            candidate[name] = spec
            CommandRegistry(candidate, float(self.default_press_var.get() or 0.08))
            self.commands = candidate
            self.selected_command = name
            self._refresh_command_table()
            self.command_tree.selection_set(name)
            self.command_tree.see(name)
            if not silent:
                self._append_log(f"Comando '{name}' salvo.")
            return True
        except (TypeError, ValueError) as exc:
            if not silent:
                messagebox.showerror("Comando inválido", str(exc))
            return False

    def _remove_command(self) -> None:
        selected = self.command_tree.selection()
        if not selected:
            return
        name = selected[0]
        if messagebox.askyesno("Remover comando", f"Remover '{name}'?"):
            self.commands.pop(name, None)
            self._new_command()
            self._refresh_command_table()

    def _reset_commands(self) -> None:
        if not messagebox.askyesno("Restaurar padrões", "Restaurar todos os comandos padrão?"):
            return
        self.commands = copy.deepcopy(DEFAULT_CONFIG["commands"])
        self._new_command()
        self._refresh_command_table()

    def _build_config(self) -> dict[str, Any]:
        if self.command_name_var.get().strip() and not self._save_command(silent=True):
            raise ValueError("Existe um comando inválido no editor.")
        countdown = int(self.countdown_var.get())
        message_rate = float(self.message_rate_var.get().replace(",", "."))
        max_length = int(self.max_length_var.get())
        workers = int(self.workers_var.get())
        default_press = float(self.default_press_var.get().replace(",", "."))
        if min(countdown, max_length, workers) < 0 or message_rate < 0 or default_press <= 0:
            raise ValueError("Os valores avançados precisam ser positivos.")
        if max_length < 1 or workers < 1:
            raise ValueError("Fila e workers precisam ser pelo menos 1.")

        return {
            "stream": {
                "twitch_channel": self.twitch_var.get().strip(),
                "youtube_channel_id": self.youtube_id_var.get().strip(),
                "youtube_stream_url": self.youtube_url_var.get().strip(),
            },
            "countdown_seconds": countdown,
            "queue": {
                "message_rate": message_rate,
                "max_length": max_length,
                "workers": workers,
            },
            "input": {"default_press_seconds": default_press},
            "commands": copy.deepcopy(self.commands),
        }

    def _save_config(self, *, notify: bool = True) -> bool:
        try:
            config = self._build_config()
            CommandRegistry(config["commands"], config["input"]["default_press_seconds"])
            save_config(self.config_path, config)
            self.config = config
            if notify:
                self._append_log("Configuração salva.")
            return True
        except (OSError, TypeError, ValueError) as exc:
            messagebox.showerror("Não foi possível salvar", str(exc))
            return False

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            return
        if not self._save_config(notify=False):
            return
        try:
            config = load_config(self.config_path)
            CommandRegistry(config["commands"], config["input"]["default_press_seconds"])
        except (ConfigError, OSError, TypeError, ValueError) as exc:
            messagebox.showerror("Configuração incompleta", str(exc))
            self.notebook.select(self.connections_tab)
            return

        self.stop_event = threading.Event()
        self._set_status("Iniciando...", running=True)
        self._append_log("Iniciando ChatPlays...")
        self.worker = threading.Thread(
            target=self._run_worker,
            args=(config, self.stop_event),
            daemon=True,
            name="ChatPlaysRuntime",
        )
        self.worker.start()

    def _run_worker(self, config: dict[str, Any], stop_event: threading.Event) -> None:
        try:
            ChatPlaysApp(config, logger=self.log_queue.put).run(stop_event)
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            self.log_queue.put(f"ERRO: {exc}")
        finally:
            self.log_queue.put("__CHATPLAYS_STOPPED__")

    def _stop(self) -> None:
        if self.stop_event:
            self.stop_event.set()
            self._set_status("Parando...", running=True)

    def _set_status(self, text: str, *, running: bool) -> None:
        self.status_var.set(f"Status: {text}")
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(state="normal" if running else "disabled")

    def _drain_log_queue(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if line == "__CHATPLAYS_STOPPED__":
                self._set_status("Parado", running=False)
            else:
                self._append_log(line)
        self.root.after(100, self._drain_log_queue)

    def _append_log(self, line: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{line}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _on_close(self) -> None:
        if self.stop_event:
            self.stop_event.set()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def run_ui(config_path: Path) -> None:
    ChatPlaysUI(config_path).run()
