"""
EduGrader — Annotation Toolbar
Floating tool palette for all annotation types.
"""
import customtkinter as ctk
from app.theme import *


TOOLS = [
    # (id,             label,      icon,  color,    group)
    ("stamp_correct",  "Correct",  "✓",   GREEN,    "stamps"),
    ("stamp_wrong",    "Wrong",    "✗",   RED,      "stamps"),
    ("stamp_partial",  "Partial",  "≈",   AMBER,    "stamps"),
    ("highlight",      "Highlight","▬",   PURPLE,   "draw"),
    ("underline",      "Underline","╌",   CYAN,     "draw"),
    ("comment",        "Comment",  "💬",  CYAN,     "comment"),
    ("text_box",       "Text",     "T",   WHITE,    "comment"),
    ("arrow",          "Arrow",    "↗",   AMBER,    "draw"),
    ("free_draw",      "Draw",     "✏",   ORANGE,   "draw"),
    ("marks_box",      "Marks",    "📊",  GREEN,    "marks"),
]

GROUPS = ["stamps", "draw", "comment", "marks"]
GROUP_LABELS = {
    "stamps":  "📌 Stamps",
    "draw":    "✏ Draw",
    "comment": "💬 Comment",
    "marks":   "📊 Marks",
}


class AnnotationToolbar(ctk.CTkFrame):
    """
    Vertical toolbar on the right side.
    on_tool_select(tool_id, color) → callback
    """

    def __init__(self, master, on_tool_select, **kwargs):
        super().__init__(master, fg_color=NAVY_MID, width=90,
                         corner_radius=0, **kwargs)
        self.on_tool_select = on_tool_select
        self._active        = None
        self._color         = AMBER
        self._btns          = {}
        self._build()

    def _build(self):
        self.pack_propagate(False)

        # Title
        hdr = ctk.CTkFrame(self, fg_color=NAVY, corner_radius=0, height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="Tools", font=FONT_SMALL,
                     text_color=AMBER).pack(expand=True)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                         scrollbar_button_color=STEEL,
                                         width=80)
        scroll.pack(fill="both", expand=True)

        for group in GROUPS:
            # Group label
            ctk.CTkLabel(scroll, text=GROUP_LABELS[group],
                         font=("Helvetica", 9, "bold"),
                         text_color=MUTED).pack(pady=(8, 2))

            for tid, label, icon, color, grp in TOOLS:
                if grp != group:
                    continue
                btn = ctk.CTkButton(
                    scroll,
                    text=f"{icon}\n{label}",
                    width=72, height=54,
                    fg_color=NAVY,
                    text_color=color,
                    hover_color=STEEL,
                    corner_radius=8,
                    font=("Helvetica", 10),
                    command=lambda t=tid, c=color: self._select(t, c)
                )
                btn.pack(pady=3)
                self._btns[tid] = (btn, color)

        # Separator
        ctk.CTkFrame(self, fg_color=STEEL, height=1).pack(fill="x", pady=4)

        # Color picker strip
        ctk.CTkLabel(self, text="Color", font=FONT_SMALL,
                     text_color=MUTED).pack(pady=2)
        colors = [GREEN, RED, AMBER, CYAN, PURPLE, ORANGE, WHITE]
        color_row = ctk.CTkFrame(self, fg_color="transparent")
        color_row.pack(pady=4)
        for i, c in enumerate(colors):
            dot = ctk.CTkButton(
                color_row, text="", width=16, height=16,
                fg_color=c, hover_color=c, corner_radius=8,
                command=lambda col=c: self._set_color(col)
            )
            if i % 2 == 0:
                dot.grid(row=i//2, column=0, padx=2, pady=2)
            else:
                dot.grid(row=i//2, column=1, padx=2, pady=2)

        # Deselect / pointer button
        ctk.CTkButton(
            self, text="↖\nPointer", width=72, height=44,
            fg_color=NAVY, text_color=SILVER,
            hover_color=STEEL, font=("Helvetica", 9),
            command=self._deselect
        ).pack(pady=6)

        # Undo hint
        ctk.CTkLabel(self, text="Right-click\n= delete",
                     font=("Helvetica", 8), text_color=MUTED).pack(pady=4)

    def _select(self, tool_id: str, color: str):
        self._active = tool_id
        self._color  = color
        self._update_buttons()
        self.on_tool_select(tool_id, color)

    def _set_color(self, color: str):
        self._color = color
        if self._active:
            self.on_tool_select(self._active, color)

    def _deselect(self):
        self._active = None
        self._update_buttons()
        self.on_tool_select(None, self._color)

    def _update_buttons(self):
        for tid, (btn, orig_color) in self._btns.items():
            if tid == self._active:
                btn.configure(fg_color=STEEL, border_width=2,
                               border_color=AMBER)
            else:
                btn.configure(fg_color=NAVY, border_width=0)
