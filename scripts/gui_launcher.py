#!/usr/bin/env python3
"""Small desktop launcher for the YouTube transcriber agent."""

from __future__ import annotations

import queue
import subprocess
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


ROOT = Path(__file__).resolve().parent.parent
RUN_PS1 = ROOT / "run.ps1"
OUT_DIR = ROOT / "out"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("YouTube Transcriber")
        self.root.geometry("760x560")

        self.url_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="auto")
        self.lang_var = tk.StringVar(value="zh")
        self.status_var = tk.StringVar(value="Ready")
        self.output_dir: Path | None = None
        self.worker: threading.Thread | None = None
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.preview_path: Path | None = None

        self._build()
        self.root.after(150, self._poll_logs)

    def _build(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="YouTube URL").pack(anchor="w")
        url_row = ttk.Frame(container)
        url_row.pack(fill="x", pady=(6, 12))
        ttk.Entry(url_row, textvariable=self.url_var).pack(side="left", fill="x", expand=True)
        ttk.Button(url_row, text="Paste", command=self._paste).pack(side="left", padx=(8, 0))

        options = ttk.Frame(container)
        options.pack(fill="x", pady=(0, 12))

        ttk.Label(options, text="Mode").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            options,
            textvariable=self.mode_var,
            values=("auto", "subtitles", "asr"),
            state="readonly",
            width=16,
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        ttk.Label(options, text="Language").grid(row=0, column=1, sticky="w", padx=(20, 0))
        ttk.Entry(options, textvariable=self.lang_var, width=16).grid(
            row=1, column=1, sticky="w", padx=(20, 0), pady=(6, 0)
        )

        actions = ttk.Frame(container)
        actions.pack(fill="x", pady=(0, 12))
        self.run_button = ttk.Button(actions, text="Start", command=self._start)
        self.run_button.pack(side="left")
        ttk.Button(actions, text="Open Output Folder", command=self._open_output).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(actions, text="Choose Existing Folder", command=self._pick_folder).pack(
            side="left", padx=(8, 0)
        )

        ttk.Label(container, text="Log").pack(anchor="w")
        self.log = tk.Text(container, wrap="word", height=22)
        self.log.pack(fill="both", expand=True, pady=(6, 8))

        ttk.Label(container, text="Preview").pack(anchor="w")
        self.preview = tk.Text(container, wrap="word", height=14)
        self.preview.pack(fill="both", expand=True, pady=(6, 8))

        status = ttk.Label(container, textvariable=self.status_var)
        status.pack(anchor="w")

    def _paste(self) -> None:
        try:
            self.url_var.set(self.root.clipboard_get().strip())
        except tk.TclError:
            messagebox.showerror("Clipboard", "Clipboard does not contain text.")

    def _append_log(self, text: str) -> None:
        self.log.insert("end", text)
        self.log.see("end")

    def _poll_logs(self) -> None:
        while True:
            try:
                event, payload = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if event == "log":
                self._append_log(payload)
            elif event == "done":
                self.run_button.config(state="normal")
                self.status_var.set(payload)
                self._load_preview()
            elif event == "error":
                self.run_button.config(state="normal")
                self.status_var.set("Failed")
                messagebox.showerror("Transcription failed", payload)

        self.root.after(150, self._poll_logs)

    def _start(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Missing URL", "Paste a YouTube URL first.")
            return

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.output_dir = OUT_DIR / f"run-{stamp}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.preview_path = self.output_dir / "transcript.txt"
        self.log.delete("1.0", "end")
        self.preview.delete("1.0", "end")
        self.run_button.config(state="disabled")
        self.status_var.set("Running")

        cmd = [
            "powershell",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RUN_PS1),
            url,
            "-Output",
            str(self.output_dir / "transcript.txt"),
            "-SrtOutput",
            str(self.output_dir / "transcript.srt"),
            "-JsonOutput",
            str(self.output_dir / "transcript.json"),
            "-Mode",
            self.mode_var.get(),
        ]

        language = self.lang_var.get().strip()
        if language:
            cmd.extend(["-Language", language])

        self.worker = threading.Thread(target=self._run_process, args=(cmd,), daemon=True)
        self.worker.start()

    def _run_process(self, cmd: list[str]) -> None:
        self.log_queue.put(("log", f"Running command:\n{' '.join(cmd)}\n\n"))
        try:
            process = subprocess.Popen(
                cmd,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            self.log_queue.put(("error", str(exc)))
            return

        assert process.stdout is not None
        for line in process.stdout:
            self.log_queue.put(("log", line))

        return_code = process.wait()
        if return_code != 0:
            self.log_queue.put(("error", f"Process exited with code {return_code}."))
            return

        done_msg = "Completed"
        if self.output_dir:
            done_msg = f"Completed: {self.output_dir}"
        self.log_queue.put(("done", done_msg))

    def _open_output(self) -> None:
        target = self.output_dir or OUT_DIR
        target.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(["explorer", str(target)])

    def _load_preview(self) -> None:
        if not self.preview_path or not self.preview_path.exists():
            return
        try:
            content = self.preview_path.read_text(encoding="utf-8-sig")
        except OSError as exc:
            self.preview.delete("1.0", "end")
            self.preview.insert("end", f"Failed to load preview: {exc}")
            return

        self.preview.delete("1.0", "end")
        self.preview.insert("end", content[:20000])

    def _pick_folder(self) -> None:
        selected = filedialog.askdirectory(initialdir=OUT_DIR if OUT_DIR.exists() else ROOT)
        if selected:
            self.output_dir = Path(selected)
            self.preview_path = self.output_dir / "transcript.txt"
            self.status_var.set(f"Selected: {self.output_dir}")
            self._load_preview()


def main() -> int:
    root = tk.Tk()
    ttk.Style().theme_use("vista")
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
