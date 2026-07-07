import customtkinter as ctk

import cypy.core.config as config


class TweaksWindow(ctk.CTkToplevel):
    """Layout tweaks auto-generated from config.TWEAKABLE_PARAMS."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Layout Tweaks")
        self.geometry("520x600")
        self.transient(master)

        self._controls = {}

        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        for key, meta in config.TWEAKABLE_PARAMS.items():
            frame = ctk.CTkFrame(scroll, fg_color="gray17")
            frame.pack(fill="x", pady=(0, 8))

            header = ctk.CTkFrame(frame, fg_color="transparent")
            header.pack(fill="x", padx=8, pady=(6, 0))
            ctk.CTkLabel(header, text=key, font=ctk.CTkFont(weight="bold")).pack(side="left")

            current = getattr(config, meta["var_name"], meta["default"])

            if "options" in meta:
                var = ctk.StringVar(value=str(current))
                ctk.CTkSegmentedButton(frame, values=meta["options"], variable=var).pack(
                    fill="x", padx=8, pady=(6, 0))
                self._controls[key] = ("str", var, None)
            elif meta["type"] == "bool":
                var = ctk.BooleanVar(value=bool(current))
                ctk.CTkSwitch(frame, text="enabled", variable=var).pack(
                    anchor="w", padx=8, pady=(6, 0))
                self._controls[key] = ("bool", var, None)
            else:
                var = ctk.DoubleVar(value=float(current))
                value_label = ctk.CTkLabel(header, text=self._fmt(meta, current), text_color="gray70")
                value_label.pack(side="right")
                steps = int((meta["max"] - meta["min"]) * (1 if meta["type"] == "int" else 20)) or 1
                slider = ctk.CTkSlider(
                    frame, from_=meta["min"], to=meta["max"], number_of_steps=steps, variable=var,
                    command=lambda v, m=meta, lbl=value_label: lbl.configure(text=self._fmt(m, v)))
                slider.pack(fill="x", padx=8, pady=(6, 0))
                self._controls[key] = (meta["type"], var, value_label)

            desc = meta["desc"]
            if "effect" in meta:
                desc += "\n" + meta["effect"]
            ctk.CTkLabel(frame, text=desc, wraplength=440, justify="left",
                         text_color="gray60", font=ctk.CTkFont(size=11)).pack(
                anchor="w", padx=8, pady=(4, 8))

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=10, pady=10)
        self.status_label = ctk.CTkLabel(buttons, text="", text_color="gray70")
        self.status_label.pack(side="left")
        ctk.CTkButton(buttons, text="Reset defaults", fg_color="gray30",
                      command=self._reset).pack(side="right", padx=(6, 0))
        ctk.CTkButton(buttons, text="Apply && Save", command=self._apply).pack(side="right")

    @staticmethod
    def _fmt(meta, value):
        return str(int(value)) if meta["type"] == "int" else f"{float(value):.2f}"

    def _apply(self):
        for key, (kind, var, _) in self._controls.items():
            meta = config.TWEAKABLE_PARAMS[key]
            value = var.get()
            if kind == "int":
                value = int(round(value))
            elif kind == "float":
                value = round(float(value), 3)
            setattr(config, meta["var_name"], value)

        if config.save_local_profile():
            self.status_label.configure(text="Saved to cypy_profile.json ✓")
        else:
            self.status_label.configure(text="[!] Failed to save profile")

    def _reset(self):
        for key, (kind, var, label) in self._controls.items():
            meta = config.TWEAKABLE_PARAMS[key]
            var.set(meta["default"])
            if label is not None:
                label.configure(text=self._fmt(meta, meta["default"]))


class GlossaryWindow(ctk.CTkToplevel):
    """Editor for config.GLOSSARY — consistent name/term translations across pages."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Glossary")
        self.geometry("480x520")
        self.transient(master)

        self._rows = []

        ctk.CTkLabel(
            self, wraplength=440, justify="left", text_color="gray70",
            text=("Terms here are always translated the same way (character names, honorifics, "
                  "attack names…). Left: original term. Right: the translation to use."),
        ).pack(anchor="w", padx=12, pady=(12, 4))

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12)
        ctk.CTkLabel(header, text="Original", width=180, anchor="w").pack(side="left", padx=(0, 6))
        ctk.CTkLabel(header, text="Translate as", anchor="w").pack(side="left")

        self.scroll = ctk.CTkScrollableFrame(self)
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(2, 0))

        for src, dst in config.GLOSSARY.items():
            self._add_row(src, dst)
        if not self._rows:
            self._add_row()

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=10, pady=10)
        self.status_label = ctk.CTkLabel(buttons, text="", text_color="gray70")
        self.status_label.pack(side="left")
        ctk.CTkButton(buttons, text="+ Add term", fg_color="gray30",
                      command=self._add_row).pack(side="right", padx=(6, 0))
        ctk.CTkButton(buttons, text="Save", command=self._save).pack(side="right")

    def _add_row(self, src="", dst=""):
        row = ctk.CTkFrame(self.scroll, fg_color="transparent")
        row.pack(fill="x", pady=(0, 4))

        src_entry = ctk.CTkEntry(row, width=180)
        src_entry.pack(side="left", padx=(0, 6))
        src_entry.insert(0, src)

        dst_entry = ctk.CTkEntry(row)
        dst_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        dst_entry.insert(0, dst)

        entry_pair = (row, src_entry, dst_entry)
        ctk.CTkButton(row, text="✕", width=28, fg_color="gray30",
                      command=lambda: self._remove_row(entry_pair)).pack(side="left")
        self._rows.append(entry_pair)

    def _remove_row(self, entry_pair):
        row, _, _ = entry_pair
        row.destroy()
        self._rows.remove(entry_pair)

    def _save(self):
        glossary = {}
        for _, src_entry, dst_entry in self._rows:
            src = src_entry.get().strip()
            dst = dst_entry.get().strip()
            if src and dst:
                glossary[src] = dst

        config.GLOSSARY = glossary
        if config.save_settings():
            self.status_label.configure(text=f"Saved {len(glossary)} terms ✓")
        else:
            self.status_label.configure(text="[!] Failed to save settings")
