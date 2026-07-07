import tkinter as tk

import cv2
import customtkinter as ctk
from PIL import Image, ImageTk

MAX_CANVAS_W = 760
MAX_CANVAS_H = 640
HANDLE_PX = 10          # corner grab radius (canvas pixels)
MIN_BOX_ORIG = 12       # minimum box size (original-image pixels)

BOX_COLOR = "#00e676"
BOX_SELECTED = "#ff5252"
BOX_WIDTH = 2


class _PageCanvas(tk.Canvas):
    """Canvas showing a manga page scaled to fit, with box overlays in original coords."""

    def __init__(self, master, img_bgr, **kwargs):
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(img_rgb)

        self.scale = min(1.0, MAX_CANVAS_W / pil.width, MAX_CANVAS_H / pil.height)
        disp_w = max(1, int(pil.width * self.scale))
        disp_h = max(1, int(pil.height * self.scale))

        super().__init__(master, width=disp_w, height=disp_h,
                         highlightthickness=0, bg="gray14", **kwargs)

        self._photo = ImageTk.PhotoImage(pil.resize((disp_w, disp_h), Image.Resampling.LANCZOS))
        self.create_image(0, 0, anchor="nw", image=self._photo)

    def to_canvas(self, box):
        x1, y1, x2, y2 = box
        s = self.scale
        return x1 * s, y1 * s, x2 * s, y2 * s

    def to_orig(self, x, y):
        s = self.scale
        return x / s, y / s


class DetectionReviewDialog(ctk.CTkToplevel):
    """Review YOLO detections: delete false positives, draw missed bubbles, adjust boxes.

    show() returns the edited box list, or None if the user cancels the page.
    """

    def __init__(self, master, img_bgr, boxes):
        super().__init__(master)
        self.title("Review detected bubbles")
        self.resizable(False, False)
        self.transient(master)

        self.result = list(boxes)  # default: closing the window keeps current boxes
        self.boxes = [list(b) for b in boxes]
        self.selected = None
        self._drag = None  # ("move", idx, dx, dy) | ("resize", idx, anchor) | ("new", x0, y0)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(padx=12, pady=12)

        self.canvas = _PageCanvas(body, img_bgr)
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Delete>", lambda e: self._delete_selected())

        hint = ("Click a box to select it (Delete key removes it). "
                "Drag a corner to resize, drag inside to move, drag empty space to draw a new box.")
        ctk.CTkLabel(body, text=hint, wraplength=MAX_CANVAS_W, justify="left",
                     text_color="gray70").pack(anchor="w", pady=(8, 0))

        buttons = ctk.CTkFrame(body, fg_color="transparent")
        buttons.pack(fill="x", pady=(10, 0))
        self.count_label = ctk.CTkLabel(buttons, text="")
        self.count_label.pack(side="left")
        ctk.CTkButton(buttons, text="Cancel page", fg_color="#8b3a3a", hover_color="#a04545",
                      command=self._cancel).pack(side="right", padx=(6, 0))
        ctk.CTkButton(buttons, text="Delete selected",
                      fg_color="gray30", command=self._delete_selected).pack(side="right", padx=(6, 0))
        ctk.CTkButton(buttons, text="Continue  ➜", command=self._continue).pack(side="right")

        self._redraw()
        self.protocol("WM_DELETE_WINDOW", self._continue)

    # -- drawing ------------------------------------------------------
    def _redraw(self):
        self.canvas.delete("box")
        for i, box in enumerate(self.boxes):
            x1, y1, x2, y2 = self.canvas.to_canvas(box)
            color = BOX_SELECTED if i == self.selected else BOX_COLOR
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color,
                                         width=BOX_WIDTH, tags="box")
            if i == self.selected:
                for cx, cy in ((x1, y1), (x2, y1), (x1, y2), (x2, y2)):
                    self.canvas.create_rectangle(cx - 4, cy - 4, cx + 4, cy + 4,
                                                 fill=color, outline="", tags="box")
        self.count_label.configure(text=f"{len(self.boxes)} bubbles")

    # -- hit testing ---------------------------------------------------
    def _corner_at(self, idx, x, y):
        x1, y1, x2, y2 = self.canvas.to_canvas(self.boxes[idx])
        corners = {"nw": (x1, y1), "ne": (x2, y1), "sw": (x1, y2), "se": (x2, y2)}
        for name, (cx, cy) in corners.items():
            if abs(x - cx) <= HANDLE_PX and abs(y - cy) <= HANDLE_PX:
                return name
        return None

    def _box_at(self, x, y):
        for i in reversed(range(len(self.boxes))):
            x1, y1, x2, y2 = self.canvas.to_canvas(self.boxes[i])
            if x1 <= x <= x2 and y1 <= y <= y2:
                return i
        return None

    # -- mouse events ---------------------------------------------------
    def _on_press(self, event):
        x, y = event.x, event.y

        if self.selected is not None:
            corner = self._corner_at(self.selected, x, y)
            if corner:
                # anchor = the corner opposite the one being dragged
                x1, y1, x2, y2 = self.boxes[self.selected]
                anchor = {"nw": (x2, y2), "ne": (x1, y2), "sw": (x2, y1), "se": (x1, y1)}[corner]
                self._drag = ("resize", self.selected, anchor)
                return

        idx = self._box_at(x, y)
        if idx is not None:
            self.selected = idx
            ox, oy = self.canvas.to_orig(x, y)
            x1, y1, _, _ = self.boxes[idx]
            self._drag = ("move", idx, ox - x1, oy - y1)
        else:
            self.selected = None
            ox, oy = self.canvas.to_orig(x, y)
            self._drag = ("new", ox, oy)
        self._redraw()

    def _on_drag(self, event):
        if not self._drag:
            return
        ox, oy = self.canvas.to_orig(event.x, event.y)
        kind = self._drag[0]

        if kind == "move":
            _, idx, dx, dy = self._drag
            x1, y1, x2, y2 = self.boxes[idx]
            w, h = x2 - x1, y2 - y1
            nx1, ny1 = ox - dx, oy - dy
            self.boxes[idx] = [int(nx1), int(ny1), int(nx1 + w), int(ny1 + h)]
        elif kind == "resize":
            _, idx, (ax, ay) = self._drag
            self.boxes[idx] = [int(min(ox, ax)), int(min(oy, ay)),
                               int(max(ox, ax)), int(max(oy, ay))]
        elif kind == "new":
            _, x0, y0 = self._drag
            self.canvas.delete("rubber")
            cx1, cy1, cx2, cy2 = self.canvas.to_canvas(
                [min(x0, ox), min(y0, oy), max(x0, ox), max(y0, oy)])
            self.canvas.create_rectangle(cx1, cy1, cx2, cy2, outline="#40c4ff",
                                         width=BOX_WIDTH, dash=(4, 3), tags="rubber")
            return
        self._redraw()

    def _on_release(self, event):
        if not self._drag:
            return
        kind = self._drag[0]
        if kind == "new":
            self.canvas.delete("rubber")
            _, x0, y0 = self._drag
            ox, oy = self.canvas.to_orig(event.x, event.y)
            box = [int(min(x0, ox)), int(min(y0, oy)), int(max(x0, ox)), int(max(y0, oy))]
            if box[2] - box[0] >= MIN_BOX_ORIG and box[3] - box[1] >= MIN_BOX_ORIG:
                self.boxes.append(box)
                self.selected = len(self.boxes) - 1
        else:
            idx = self._drag[1]
            x1, y1, x2, y2 = self.boxes[idx]
            if x2 - x1 < MIN_BOX_ORIG or y2 - y1 < MIN_BOX_ORIG:
                self.boxes[idx] = [x1, y1, max(x2, x1 + MIN_BOX_ORIG), max(y2, y1 + MIN_BOX_ORIG)]
        self._drag = None
        self._redraw()

    # -- actions ---------------------------------------------------------
    def _delete_selected(self):
        if self.selected is not None and self.selected < len(self.boxes):
            del self.boxes[self.selected]
            self.selected = None
            self._redraw()

    def _continue(self):
        self.result = [list(b) for b in self.boxes]
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def show(self):
        self.grab_set()
        self.wait_window()
        return self.result


class TranslationEditDialog(ctk.CTkToplevel):
    """Edit translated texts per bubble before rendering. No extra API call.

    show() returns the edited {id: text} dict, or None if the user cancels the page.
    """

    def __init__(self, master, img_bgr, koordinat_jejak, texts):
        super().__init__(master)
        self.title("Edit translations")
        self.resizable(False, False)
        self.transient(master)

        self.koordinat_jejak = koordinat_jejak
        self.result = dict(texts)  # closing the window keeps texts as-is
        self._entries = {}

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(padx=12, pady=12, fill="both", expand=True)

        self.canvas = _PageCanvas(body, img_bgr)
        self.canvas.pack(side="left")
        self._draw_numbered_boxes()

        right = ctk.CTkFrame(body, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True, padx=(12, 0))

        ctk.CTkLabel(right, text="Bubble translations — type SKIP to leave a bubble untouched",
                     wraplength=320, justify="left").pack(anchor="w")

        scroll = ctk.CTkScrollableFrame(right, width=340, height=MAX_CANVAS_H - 90)
        scroll.pack(fill="both", expand=True, pady=(6, 0))

        ordered_ids = sorted(koordinat_jejak.keys(), key=lambda k: int(k))
        for bubble_id in ordered_ids:
            row = ctk.CTkFrame(scroll, fg_color="gray17")
            row.pack(fill="x", pady=(0, 6))
            ctk.CTkLabel(row, text=f"#{bubble_id}", width=34,
                         font=ctk.CTkFont(weight="bold")).pack(side="left", anchor="n", padx=(4, 2), pady=4)
            box = ctk.CTkTextbox(row, height=64, wrap="word")
            box.pack(side="left", fill="x", expand=True, padx=(0, 4), pady=4)
            box.insert("1.0", texts.get(bubble_id, "SKIP"))
            box.bind("<FocusIn>", lambda e, b=bubble_id: self._highlight(b))
            self._entries[bubble_id] = box

        buttons = ctk.CTkFrame(right, fg_color="transparent")
        buttons.pack(fill="x", pady=(8, 0))
        ctk.CTkButton(buttons, text="Cancel page", fg_color="#8b3a3a", hover_color="#a04545",
                      command=self._cancel).pack(side="right", padx=(6, 0))
        ctk.CTkButton(buttons, text="Render  ➜", command=self._render).pack(side="right")

        self.protocol("WM_DELETE_WINDOW", self._render)

    def _draw_numbered_boxes(self, highlight_id=None):
        self.canvas.delete("box")
        for bubble_id, box in self.koordinat_jejak.items():
            x1, y1, x2, y2 = self.canvas.to_canvas(box)
            color = BOX_SELECTED if bubble_id == highlight_id else BOX_COLOR
            self.canvas.create_rectangle(x1, y1, x2, y2, outline=color,
                                         width=3 if bubble_id == highlight_id else BOX_WIDTH,
                                         tags="box")
            self.canvas.create_text(x1 + 4, y1 + 4, anchor="nw", text=bubble_id,
                                    fill=color, font=("Arial", 13, "bold"), tags="box")

    def _highlight(self, bubble_id):
        self._draw_numbered_boxes(highlight_id=bubble_id)

    def _render(self):
        edited = dict(self.result)
        for bubble_id, box in self._entries.items():
            text = box.get("1.0", "end").strip()
            edited[bubble_id] = text if text else "SKIP"
        self.result = edited
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()

    def show(self):
        self.grab_set()
        self.wait_window()
        return self.result
