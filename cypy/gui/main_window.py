import os
import queue
import threading
import time
import traceback

import customtkinter as ctk
from tkinter import filedialog, messagebox

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    HAS_DND = True
except ImportError:
    HAS_DND = False

import cypy.core.config as config
from cypy.core.version import APP_VER

PROVIDERS = ["gemini", "openai", "zen", "openrouter", "custom"]
LANG_PRESETS = ["English", "Indonesian", "Japanese", "Mandarin",
                "Spanish", "Portuguese", "Javanese", "Custom..."]

SUPPORTED_FILETYPES = [
    ("All supported", "*.png *.jpg *.jpeg *.webp *.pdf *.cbz *.zip *.cbr *.rar"),
    ("Images", "*.png *.jpg *.jpeg *.webp"),
    ("PDF", "*.pdf"),
    ("Archives", "*.cbz *.zip *.cbr *.rar"),
]

ARCHIVE_EXTENSIONS = (".zip", ".cbz", ".rar", ".cbr")


if HAS_DND:
    class _Root(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    class _Root(ctk.CTk):
        pass


class CypyApp(_Root):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")

        self.title(f"cypy {APP_VER} — Manga Translator")
        self.geometry("980x640")
        self.minsize(860, 560)

        self._set_icon()

        # Worker state
        self.worker = None
        self.stop_flag = threading.Event()
        self.log_queue = queue.Queue()
        self.yolo_model = None

        # Windows opened lazily
        self._tweaks_window = None
        self._glossary_window = None

        if config.load_local_profile():
            self.log_queue.put("[+] Loaded local profile (cypy_profile.json)")

        self._build_sidebar()
        self._build_main_area()
        self._load_settings_into_sidebar()

        self._poll_logs()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _set_icon(self):
        try:
            from PIL import Image, ImageTk
            icon_path = os.path.join(config.ASSETS_DIR, "favicon.png")
            if os.path.exists(icon_path):
                self._icon_image = ImageTk.PhotoImage(Image.open(icon_path))
                self.iconphoto(True, self._icon_image)
        except Exception:
            pass

    def _build_sidebar(self):
        sidebar = ctk.CTkScrollableFrame(self, width=270)
        sidebar.pack(side="left", fill="y", padx=(10, 5), pady=10)
        self.sidebar = sidebar

        ctk.CTkLabel(sidebar, text="Settings", font=ctk.CTkFont(size=17, weight="bold")).pack(
            anchor="w", padx=10, pady=(8, 12))

        # --- Provider ---
        ctk.CTkLabel(sidebar, text="API Provider").pack(anchor="w", padx=10)
        self.provider_var = ctk.StringVar(value=config.LLM_PROVIDER or "gemini")
        self.provider_menu = ctk.CTkOptionMenu(
            sidebar, values=PROVIDERS, variable=self.provider_var,
            command=self._on_provider_change)
        self.provider_menu.pack(fill="x", padx=10, pady=(2, 8))

        ctk.CTkLabel(sidebar, text="API Key").pack(anchor="w", padx=10)
        self.api_key_entry = ctk.CTkEntry(sidebar, show="•", placeholder_text="paste API key")
        self.api_key_entry.pack(fill="x", padx=10, pady=(2, 8))

        self.base_url_label = ctk.CTkLabel(sidebar, text="Base URL (OpenAI-compatible)")
        self.base_url_entry = ctk.CTkEntry(sidebar, placeholder_text="https://api.example.com/v1")

        ctk.CTkLabel(sidebar, text="Model").pack(anchor="w", padx=10)
        self.model_entry = ctk.CTkEntry(sidebar)
        self.model_entry.pack(fill="x", padx=10, pady=(2, 8))

        # --- Language ---
        ctk.CTkLabel(sidebar, text="Target Language").pack(anchor="w", padx=10)
        self.lang_var = ctk.StringVar(value="Indonesian")
        self.lang_menu = ctk.CTkOptionMenu(
            sidebar, values=LANG_PRESETS, variable=self.lang_var,
            command=self._on_lang_change)
        self.lang_menu.pack(fill="x", padx=10, pady=(2, 4))
        self.custom_lang_entry = ctk.CTkEntry(sidebar, placeholder_text="e.g. Korean, Thai, Arabic")

        self.save_button = ctk.CTkButton(sidebar, text="Save Settings", command=self._save_sidebar_settings)
        self.save_button.pack(fill="x", padx=10, pady=(10, 14))

        # --- Review options ---
        ctk.CTkLabel(sidebar, text="Interactive Review", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10)
        self.review_boxes_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(sidebar, text="Review detected bubbles",
                        variable=self.review_boxes_var).pack(anchor="w", padx=10, pady=(6, 2))
        self.review_texts_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(sidebar, text="Edit translations before render",
                        variable=self.review_texts_var).pack(anchor="w", padx=10, pady=(2, 12))

        # --- Extra panels ---
        ctk.CTkButton(sidebar, text="Layout Tweaks…", fg_color="gray30",
                      command=self._open_tweaks).pack(fill="x", padx=10, pady=(2, 4))
        ctk.CTkButton(sidebar, text="Glossary…", fg_color="gray30",
                      command=self._open_glossary).pack(fill="x", padx=10, pady=(2, 8))

    def _build_main_area(self):
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(side="left", fill="both", expand=True, padx=(5, 10), pady=10)

        # Drop zone
        drop_text = "Drop image / PDF / CBZ / folder here" if HAS_DND else "Select a file or folder to translate"
        self.drop_frame = ctk.CTkFrame(main, height=110, border_width=2, border_color="gray40")
        self.drop_frame.pack(fill="x")
        self.drop_frame.pack_propagate(False)
        self.drop_label = ctk.CTkLabel(self.drop_frame, text=drop_text,
                                       font=ctk.CTkFont(size=15))
        self.drop_label.pack(expand=True)

        if HAS_DND:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)

        button_row = ctk.CTkFrame(main, fg_color="transparent")
        button_row.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(button_row, text="Open File…", command=self._pick_file).pack(
            side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(button_row, text="Open Folder…", command=self._pick_folder).pack(
            side="left", expand=True, fill="x", padx=(4, 4))
        self.cancel_button = ctk.CTkButton(button_row, text="Cancel", state="disabled",
                                           fg_color="#8b3a3a", hover_color="#a04545",
                                           command=self._cancel_job)
        self.cancel_button.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(main, mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(10, 0))
        self.progress_bar.set(0)

        # Log panel
        self.log_box = ctk.CTkTextbox(main, wrap="word", font=ctk.CTkFont(family="Consolas", size=12))
        self.log_box.pack(fill="both", expand=True, pady=(10, 0))
        self.log_box.configure(state="disabled")

        self._append_log(f"cypy {APP_VER} GUI ready~ ♪")
        self._append_log("Configure a provider on the left, then drop a file to translate.")
        if not HAS_DND:
            self._append_log("[i] tkinterdnd2 not installed — drag-and-drop disabled, use the buttons.")

    # ------------------------------------------------------------------
    # Sidebar state <-> config
    # ------------------------------------------------------------------
    def _load_settings_into_sidebar(self):
        provider = (config.LLM_PROVIDER or "gemini").lower()
        if provider not in PROVIDERS:
            provider = "gemini"
        self.provider_var.set(provider)
        self._on_provider_change(provider)

        lang = config.TARGET_LANGUAGE or "Indonesian"
        if lang in LANG_PRESETS:
            self.lang_var.set(lang)
        else:
            self.lang_var.set("Custom...")
            self._on_lang_change("Custom...")
            self.custom_lang_entry.insert(0, lang)

    def _on_provider_change(self, provider):
        api_key, model = config.get_provider_config(provider)

        self.api_key_entry.delete(0, "end")
        if api_key:
            self.api_key_entry.insert(0, api_key)

        self.model_entry.delete(0, "end")
        if model:
            self.model_entry.insert(0, model)

        if provider == "custom":
            self.base_url_label.pack(anchor="w", padx=10, after=self.api_key_entry)
            self.base_url_entry.pack(fill="x", padx=10, pady=(2, 8), after=self.base_url_label)
            self.base_url_entry.delete(0, "end")
            if config.CUSTOM_BASE_URL:
                self.base_url_entry.insert(0, config.CUSTOM_BASE_URL)
        else:
            self.base_url_label.pack_forget()
            self.base_url_entry.pack_forget()

    def _on_lang_change(self, value):
        if value == "Custom...":
            self.custom_lang_entry.pack(fill="x", padx=10, pady=(2, 4), after=self.lang_menu)
        else:
            self.custom_lang_entry.pack_forget()

    def _current_language(self):
        lang = self.lang_var.get()
        if lang == "Custom...":
            custom = self.custom_lang_entry.get().strip()
            return custom.title() if custom else "Indonesian"
        return lang

    def _save_sidebar_settings(self, quiet=False):
        from cypy.app import PROVIDER_INFO, _save_to_env, _save_to_env_simple

        provider = self.provider_var.get()
        api_key = self.api_key_entry.get().strip()
        model = self.model_entry.get().strip()
        language = self._current_language()

        config.LLM_PROVIDER = provider
        config.TARGET_LANGUAGE = language

        if provider == "gemini":
            config.GEMINI_API_KEY = api_key
            if model: config.MODEL_GEMINI = model
        elif provider == "openai":
            config.OPENAI_API_KEY = api_key
            if model: config.MODEL_OPENAI = model
        elif provider == "openrouter":
            config.OPENROUTER_API_KEY = api_key
            if model: config.MODEL_OPENROUTER = model
        elif provider == "zen":
            config.ZEN_API_KEY = api_key
            if model: config.MODEL_ZEN = model
        elif provider == "custom":
            config.CUSTOM_API_KEY = api_key
            config.CUSTOM_BASE_URL = self.base_url_entry.get().strip()
            if model: config.MODEL_CUSTOM = model

        config.save_settings()

        # Mirror into .env like the CLI does
        try:
            env_path = os.path.join(config.ROOT_DIR, ".env")
            info = PROVIDER_INFO.get(provider)
            _save_to_env_simple(env_path, "LLM_PROVIDER", provider)
            if info and api_key:
                _save_to_env(env_path, info["env_key"], api_key, provider)
            if provider == "custom" and config.CUSTOM_BASE_URL:
                _save_to_env_simple(env_path, "CUSTOM_BASE_URL", config.CUSTOM_BASE_URL)
            if info:
                os.environ[info["env_key"]] = api_key
        except Exception as e:
            self._append_log(f"[!] Warning: failed to update .env: {e}")

        if not quiet:
            self._append_log(f"[+] Settings saved (provider: {provider}, language: {language}).")

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------
    def _pick_file(self):
        path = filedialog.askopenfilename(filetypes=SUPPORTED_FILETYPES)
        if path:
            self._start_job(path)

    def _pick_folder(self):
        path = filedialog.askdirectory()
        if path:
            self._start_job(path)

    def _on_drop(self, event):
        paths = self.tk.splitlist(event.data)
        if paths:
            self._start_job(paths[0].strip("{}"))

    # ------------------------------------------------------------------
    # Job lifecycle
    # ------------------------------------------------------------------
    def _start_job(self, path):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("cypy", "A translation is already running.\nCancel it or wait for it to finish.")
            return

        path = os.path.normpath(path)
        if not os.path.exists(path):
            messagebox.showerror("cypy", f"Path not found:\n{path}")
            return

        self._save_sidebar_settings(quiet=True)

        provider_name = self.provider_var.get()
        api_key, _ = config.get_provider_config(provider_name)
        if provider_name in ("gemini", "openai", "openrouter") and not api_key:
            messagebox.showwarning(
                "cypy", f"An API key is required for {provider_name}.\nPaste it in the sidebar and try again.")
            self.api_key_entry.focus_set()
            return

        self.stop_flag.clear()
        self.cancel_button.configure(state="normal")
        self.progress_bar.start()

        self.worker = threading.Thread(target=self._run_job, args=(path,), daemon=True)
        self.worker.start()

    def _cancel_job(self):
        if self.worker and self.worker.is_alive():
            self.stop_flag.set()
            self._append_log("\n[!] Cancelling… current page will finish first.")
            self.cancel_button.configure(state="disabled")

    def _job_done(self):
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.cancel_button.configure(state="disabled")

    def _run_job(self, path):
        log = self.log_queue.put
        try:
            from cypy.core.translator import (
                proses_satu_gambar, proses_folder, mulai_ritual_pdf, mulai_ritual_archive)
            from cypy.core.providers import create_provider

            provider_name = self.provider_var.get()
            api_key, model_name = config.get_provider_config(provider_name)
            extra = {}
            if provider_name == "custom":
                extra["base_url"] = config.CUSTOM_BASE_URL
            provider = create_provider(provider_name, api_key=api_key, model_name=model_name, **extra)

            if self.yolo_model is None:
                if not os.path.exists(config.MODEL_YOLO):
                    log("[!] YOLO model file not found. Check your assets folder.")
                    return
                log("Loading YOLO model (first run only)…")
                from cypy.core.yolo_onnx import YOLOONNX as YOLO
                self.yolo_model = YOLO(config.MODEL_YOLO)

            target_language = self._current_language()
            review_mode = self.review_boxes_var.get() or self.review_texts_var.get()

            hooks = {
                "progress": log,
                "on_boxes": self._hook_boxes if self.review_boxes_var.get() else None,
                "on_translations": self._hook_translations if self.review_texts_var.get() else None,
            }
            batch_kwargs = dict(
                hooks,
                should_stop=self.stop_flag.is_set,
                max_workers=1 if review_mode else 3,
            )

            start_time = time.time()

            if os.path.isdir(path):
                proses_folder(path, self.yolo_model, provider=provider,
                              target_language=target_language, **batch_kwargs)
            elif path.lower().endswith(".pdf"):
                mulai_ritual_pdf(path, self.yolo_model, provider=provider,
                                 target_language=target_language, **batch_kwargs)
            elif path.lower().endswith(ARCHIVE_EXTENSIONS):
                mulai_ritual_archive(path, self.yolo_model, provider=provider,
                                     target_language=target_language, **batch_kwargs)
            elif path.lower().endswith(config.SUPPORTED_IMAGE_EXTENSIONS):
                hasil = proses_satu_gambar(path, self.yolo_model, provider=provider,
                                           target_language=target_language, **hooks)
                if hasil:
                    log(f"Done! Saved at: {hasil}")
            else:
                log("[!] Unsupported format. Give me PNG, JPG, JPEG, WEBP, PDF, CBZ, ZIP, CBR, RAR, or a folder~ ♪")
                return

            log(f"\n[Timer] Completed in {time.time() - start_time:.1f}s")

        except Exception as e:
            log(f"\n[!] An error occurred: {e}")
            log(traceback.format_exc())
        finally:
            self.after(0, self._job_done)

    # ------------------------------------------------------------------
    # Review hooks (called on worker thread; dialogs run on UI thread)
    # ------------------------------------------------------------------
    def _ui_request(self, fn):
        """Run fn() on the UI thread and block the worker until it returns."""
        result = {}
        done = threading.Event()

        def wrapper():
            try:
                result["value"] = fn()
            finally:
                done.set()

        self.after(0, wrapper)
        done.wait()
        return result.get("value")

    def _hook_boxes(self, img, boxes):
        if self.stop_flag.is_set():
            return None
        from cypy.gui.review import DetectionReviewDialog
        return self._ui_request(lambda: DetectionReviewDialog(self, img, boxes).show())

    def _hook_translations(self, img, koordinat_jejak, texts):
        if self.stop_flag.is_set():
            return None
        from cypy.gui.review import TranslationEditDialog
        return self._ui_request(lambda: TranslationEditDialog(self, img, koordinat_jejak, texts).show())

    # ------------------------------------------------------------------
    # Extra panels
    # ------------------------------------------------------------------
    def _open_tweaks(self):
        from cypy.gui.panels import TweaksWindow
        if self._tweaks_window is None or not self._tweaks_window.winfo_exists():
            self._tweaks_window = TweaksWindow(self)
        self._tweaks_window.focus()

    def _open_glossary(self):
        from cypy.gui.panels import GlossaryWindow
        if self._glossary_window is None or not self._glossary_window.winfo_exists():
            self._glossary_window = GlossaryWindow(self)
        self._glossary_window.focus()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    def _append_log(self, msg):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", str(msg).rstrip() + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _poll_logs(self):
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(msg)
        self.after(100, self._poll_logs)
