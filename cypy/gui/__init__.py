# ==========================================
# ✦ CYPY GUI - Desktop interface for the manga translator~ ♪ ✦
# ==========================================


def main():
    """Entry point for `cypy-gui` / `python -m cypy.gui`."""
    from cypy.gui.main_window import CypyApp

    app = CypyApp()
    app.mainloop()
