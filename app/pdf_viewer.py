"""
EduGrader — PDF Viewer + Annotation Canvas
Zoomable/pannable page viewer with live annotation drawing.
"""
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import threading
from app.theme import *
from app.annotation_engine import Annotation, AnnotationRenderer


class PDFViewerCanvas(ctk.CTkFrame):
    """
    Interactive PDF page viewer. Supports:
    • Zoom in/out (mouse wheel)
    • Pan (middle-drag or Alt+drag)
    • Active annotation tool drawing
    • Live annotation overlay
    """

    MIN_ZOOM = 0.3
    MAX_ZOOM = 4.0

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=NAVY, **kwargs)
        self._zoom         = 1.0
        self._pan_x        = 0
        self._pan_y        = 0
        self._drag_start   = None
        self._page_img     = None      # PIL Image at base resolution
        self._page_tk      = None      # PhotoImage (holds reference)
        self._annotations  = []        # [Annotation]
        self._draw_ann     = None      # Annotation being drawn now
        self._active_tool  = None      # e.g. "stamp_correct"
        self._active_color = "#F5A623"
        self._active_text  = ""
        self._renderer     = AnnotationRenderer()
        self._on_anno_add  = None      # callback(Annotation)
        self._on_anno_del  = None      # callback(anno_id)
        self._free_pts     = []        # for free_draw
        self._build()

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)

        # Canvas
        self._canvas = tk.Canvas(
            self, bg=NAVY, highlightthickness=0,
            cursor="crosshair"
        )
        self._canvas.grid(row=0, column=0, sticky="nsew")

        # Scrollbars
        sb_v = tk.Scrollbar(self, orient="vertical",
                             command=self._canvas.yview, bg=NAVY_MID)
        sb_h = tk.Scrollbar(self, orient="horizontal",
                             command=self._canvas.xview, bg=NAVY_MID)
        self._canvas.configure(yscrollcommand=sb_v.set,
                                xscrollcommand=sb_h.set)
        sb_v.grid(row=0, column=1, sticky="ns")
        sb_h.grid(row=1, column=0, sticky="ew")

        # Zoom bar
        zoom_bar = ctk.CTkFrame(self, fg_color=NAVY_MID,
                                  corner_radius=0, height=36)
        zoom_bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        zoom_bar.grid_columnconfigure(3, weight=1)

        ctk.CTkButton(zoom_bar, text="−", width=32, height=26,
                      fg_color=STEEL, command=self.zoom_out,
                      font=("Helvetica", 16, "bold")).grid(row=0, column=0, padx=6, pady=5)
        self._zoom_lbl = ctk.CTkLabel(zoom_bar, text="100%",
                                       font=FONT_SMALL, text_color=SILVER, width=50)
        self._zoom_lbl.grid(row=0, column=1)
        ctk.CTkButton(zoom_bar, text="+", width=32, height=26,
                      fg_color=STEEL, command=self.zoom_in,
                      font=("Helvetica", 16, "bold")).grid(row=0, column=2, padx=6, pady=5)
        ctk.CTkButton(zoom_bar, text="Fit", width=44, height=26,
                      fg_color=NAVY, command=self.zoom_fit,
                      font=FONT_SMALL, text_color=SILVER).grid(row=0, column=4, padx=4)
        ctk.CTkButton(zoom_bar, text="1:1", width=44, height=26,
                      fg_color=NAVY, command=self.zoom_reset,
                      font=FONT_SMALL, text_color=SILVER).grid(row=0, column=5, padx=4)

        # Bind events
        self._canvas.bind("<MouseWheel>",      self._on_wheel)
        self._canvas.bind("<Button-4>",        self._on_wheel)
        self._canvas.bind("<Button-5>",        self._on_wheel)
        self._canvas.bind("<ButtonPress-2>",   self._pan_start)
        self._canvas.bind("<B2-Motion>",       self._pan_move)
        self._canvas.bind("<ButtonPress-1>",   self._draw_start)
        self._canvas.bind("<B1-Motion>",       self._draw_move)
        self._canvas.bind("<ButtonRelease-1>", self._draw_end)
        self._canvas.bind("<Button-3>",        self._right_click)

    # ── Public API ────────────────────────────────────────────────────────────
    def set_page(self, pil_img: Image.Image, annotations: list):
        self._page_img   = pil_img
        self._annotations = [
            Annotation.from_dict(a) if isinstance(a, dict) else a
            for a in annotations
        ]
        self._redraw()

    def set_tool(self, tool: str, color: str = "#F5A623", text: str = ""):
        self._active_tool  = tool
        self._active_color = color
        self._active_text  = text
        cursor = {
            "stamp_correct": "plus",
            "stamp_wrong":   "X_cursor",
            "comment":       "pencil",
            "highlight":     "sb_h_double_arrow",
            "free_draw":     "pencil",
            "arrow":         "arrow",
        }.get(tool, "crosshair")
        self._canvas.configure(cursor=cursor)

    def set_annotations(self, annotations: list):
        self._annotations = [
            Annotation.from_dict(a) if isinstance(a, dict) else a
            for a in annotations
        ]
        self._redraw()

    def set_callbacks(self, on_add=None, on_delete=None):
        self._on_anno_add = on_add
        self._on_anno_del = on_delete

    def zoom_in(self):
        self._zoom = min(self.MAX_ZOOM, self._zoom * 1.25)
        self._redraw()

    def zoom_out(self):
        self._zoom = max(self.MIN_ZOOM, self._zoom / 1.25)
        self._redraw()

    def zoom_fit(self):
        if self._page_img is None:
            return
        cw = self._canvas.winfo_width()
        ch = self._canvas.winfo_height()
        if cw < 10 or ch < 10:
            return
        pw, ph = self._page_img.size
        self._zoom = min(cw / pw, ch / ph) * 0.95
        self._pan_x = self._pan_y = 0
        self._redraw()

    def zoom_reset(self):
        self._zoom = 1.0
        self._pan_x = self._pan_y = 0
        self._redraw()

    # ── Drawing ───────────────────────────────────────────────────────────────
    def _canvas_to_page(self, cx, cy):
        """Convert canvas pixel → page pixel (accounting for zoom & pan)."""
        return (int((cx - self._pan_x) / self._zoom),
                int((cy - self._pan_y) / self._zoom))

    def _draw_start(self, event):
        if self._active_tool is None:
            return
        px, py = self._canvas_to_page(event.x, event.y)

        if self._active_tool in ("stamp_correct", "stamp_wrong", "stamp_partial"):
            ann = Annotation(type=self._active_tool, x=px, y=py,
                             color=self._active_color)
            self._commit_annotation(ann)
            return

        if self._active_tool == "free_draw":
            self._free_pts = [(px, py)]
            self._draw_ann = Annotation(
                type="free_draw", x=px, y=py,
                color=self._active_color, line_width=3, points=[(px, py)]
            )
            return

        self._draw_ann = Annotation(
            type=self._active_tool,
            x=px, y=py, x2=px, y2=py,
            color=self._active_color,
            text=self._active_text,
        )

    def _draw_move(self, event):
        if self._draw_ann is None:
            return
        px, py = self._canvas_to_page(event.x, event.y)
        if self._draw_ann.type == "free_draw":
            self._draw_ann.points.append((px, py))
        else:
            self._draw_ann.x2 = px
            self._draw_ann.y2 = py
        self._redraw(live_ann=self._draw_ann)

    def _draw_end(self, event):
        if self._draw_ann is None:
            return
        px, py = self._canvas_to_page(event.x, event.y)
        if self._draw_ann.type == "free_draw":
            self._draw_ann.points.append((px, py))
        else:
            self._draw_ann.x2 = px
            self._draw_ann.y2 = py

        # Prompt for comment text
        if self._draw_ann.type == "comment" and not self._draw_ann.text:
            self._prompt_comment(self._draw_ann)
        elif self._draw_ann.type == "marks_box":
            self._prompt_marks(self._draw_ann)
        else:
            self._commit_annotation(self._draw_ann)
        self._draw_ann = None

    def _commit_annotation(self, ann: Annotation):
        self._annotations.append(ann)
        self._redraw()
        if self._on_anno_add:
            self._on_anno_add(ann)

    def _prompt_comment(self, ann: Annotation):
        dlg = _TextDialog(self._canvas.winfo_toplevel(),
                          title="Add Comment", label="Comment text:")
        txt = dlg.result
        if txt:
            ann.text = txt
            self._commit_annotation(ann)

    def _prompt_marks(self, ann: Annotation):
        dlg = _MarksDialog(self._canvas.winfo_toplevel())
        if dlg.result:
            ann.marks, ann.max_marks, ann.question_no = dlg.result
            self._commit_annotation(ann)

    def _right_click(self, event):
        """Right-click to delete nearest annotation."""
        px, py = self._canvas_to_page(event.x, event.y)
        best, best_d = None, 9999
        for ann in self._annotations:
            d = abs(ann.x - px) + abs(ann.y - py)
            if d < best_d:
                best, best_d = ann, d
        if best and best_d < 40:
            self._annotations.remove(best)
            self._redraw()
            if self._on_anno_del:
                self._on_anno_del(best.id)

    # ── Pan ───────────────────────────────────────────────────────────────────
    def _pan_start(self, event):
        self._drag_start = (event.x - self._pan_x, event.y - self._pan_y)

    def _pan_move(self, event):
        if self._drag_start:
            self._pan_x = event.x - self._drag_start[0]
            self._pan_y = event.y - self._drag_start[1]
            self._redraw()

    # ── Zoom wheel ────────────────────────────────────────────────────────────
    def _on_wheel(self, event):
        delta = getattr(event, "delta", 0)
        if delta == 0:
            delta = -1 if event.num == 5 else 1
        factor = 1.1 if delta > 0 else 0.9
        self._zoom = max(self.MIN_ZOOM, min(self.MAX_ZOOM, self._zoom * factor))
        self._redraw()

    # ── Rendering ─────────────────────────────────────────────────────────────
    def _redraw(self, live_ann: Annotation = None):
        if self._page_img is None:
            return
        self._zoom_lbl.configure(text=f"{int(self._zoom*100)}%")

        # Render annotations onto page
        annos = list(self._annotations)
        if live_ann:
            annos.append(live_ann)

        def _do():
            rendered = self._renderer.render_all(self._page_img, annos, scale=1.0)
            # Scale to zoom
            w = int(rendered.width * self._zoom)
            h = int(rendered.height * self._zoom)
            if w < 1 or h < 1:
                return
            scaled  = rendered.resize((w, h), Image.LANCZOS)
            tk_img  = ImageTk.PhotoImage(scaled)

            def _put():
                self._page_tk = tk_img
                self._canvas.delete("all")
                self._canvas.configure(scrollregion=(0, 0, w, h))
                self._canvas.create_image(
                    self._pan_x, self._pan_y,
                    anchor="nw", image=tk_img
                )
            self._canvas.after(0, _put)

        threading.Thread(target=_do, daemon=True).start()


# ── Simple dialogs ────────────────────────────────────────────────────────────
class _TextDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Input", label=""):
        super().__init__(parent)
        self.title(title)
        self.geometry("380x200")
        self.configure(fg_color=NAVY_LIGHT)
        self.result = None
        self.grab_set()

        ctk.CTkLabel(self, text=label, font=FONT_SUB,
                     text_color=AMBER).pack(pady=16)
        self._entry = ctk.CTkTextbox(self, height=80, fg_color=NAVY_MID,
                                     text_color=WHITE, border_color=STEEL)
        self._entry.pack(fill="x", padx=20)
        ctk.CTkButton(self, text="✓  Add", fg_color=AMBER, text_color=DARK_TEXT,
                      command=self._ok).pack(pady=12)
        self.wait_window()

    def _ok(self):
        self.result = self._entry.get("1.0", "end").strip()
        self.destroy()


class _MarksDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Enter Marks")
        self.geometry("320x260")
        self.configure(fg_color=NAVY_LIGHT)
        self.result = None
        self.grab_set()

        ctk.CTkLabel(self, text="📊  Marks Awarded",
                     font=FONT_SUB, text_color=AMBER).pack(pady=14)

        self._marks    = ctk.CTkEntry(self, placeholder_text="Marks awarded",
                                       fg_color=NAVY_MID, text_color=WHITE)
        self._marks.pack(fill="x", padx=24, pady=4)
        self._max      = ctk.CTkEntry(self, placeholder_text="Max marks",
                                       fg_color=NAVY_MID, text_color=WHITE)
        self._max.pack(fill="x", padx=24, pady=4)
        self._qno      = ctk.CTkEntry(self, placeholder_text="Question No. (optional)",
                                       fg_color=NAVY_MID, text_color=WHITE)
        self._qno.pack(fill="x", padx=24, pady=4)

        ctk.CTkButton(self, text="✓  Save", fg_color=GREEN,
                      command=self._ok).pack(pady=14)
        self.wait_window()

    def _ok(self):
        try:
            m  = float(self._marks.get())
            mx = float(self._max.get())
            qn = self._qno.get().strip()
            self.result = (m, mx, qn)
        except ValueError:
            pass
        self.destroy()
