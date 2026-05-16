"""
EduGrader — Student List Sidebar
Shows all loaded students with status badges, search, and quick actions.
"""
import customtkinter as ctk
from app.theme import *


STATUS_COLORS = {
    "Pending":     MUTED,
    "In Progress": AMBER,
    "Done":        GREEN,
}

STATUS_ICONS = {
    "Pending":     "⏳",
    "In Progress": "🔄",
    "Done":        "✅",
}


class StudentListPanel(ctk.CTkFrame):
    """
    Left sidebar showing a scrollable list of StudentRecord entries.
    on_select(idx) → callback when user clicks a student.
    """

    def __init__(self, master, on_select, **kwargs):
        super().__init__(master, fg_color=NAVY_LIGHT,
                         width=SIDEBAR_W, corner_radius=0, **kwargs)
        self.on_select      = on_select
        self._students      = []
        self._selected_idx  = -1
        self._search_var    = ctk.StringVar()
        self._search_var.trace_add("write", self._on_search)
        self._card_frames   = []
        self._build()

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self):
        self.pack_propagate(False)

        # Header
        hdr = ctk.CTkFrame(self, fg_color=NAVY_MID, corner_radius=0, height=56)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="👥  Students",
                     font=FONT_SUB, text_color=AMBER).pack(
            side="left", padx=14, pady=14)

        self._count_lbl = ctk.CTkLabel(hdr, text="0",
                                        font=FONT_SMALL, text_color=SILVER)
        self._count_lbl.pack(side="right", padx=14)

        # Search
        srch = ctk.CTkFrame(self, fg_color=NAVY, corner_radius=0)
        srch.pack(fill="x", padx=8, pady=8)
        ctk.CTkEntry(srch, placeholder_text="🔍  Search student…",
                     textvariable=self._search_var,
                     fg_color=NAVY_MID, border_color=STEEL,
                     text_color=WHITE, height=34,
                     corner_radius=8).pack(fill="x", padx=6, pady=6)

        # Scroll area
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=STEEL,
            scrollbar_button_hover_color=AMBER
        )
        self._scroll.pack(fill="both", expand=True, padx=4, pady=4)

        # Bottom stats bar
        self._stats_bar = ctk.CTkFrame(self, fg_color=NAVY_MID,
                                        corner_radius=0, height=38)
        self._stats_bar.pack(fill="x", side="bottom")
        self._stats_bar.pack_propagate(False)
        self._stats_lbl = ctk.CTkLabel(self._stats_bar, text="",
                                        font=FONT_SMALL, text_color=SILVER)
        self._stats_lbl.pack(pady=8)

    # ── public API ────────────────────────────────────────────────────────────
    def load_students(self, students: list):
        self._students = students
        self._refresh()

    def refresh_student(self, idx: int):
        if 0 <= idx < len(self._students):
            self._refresh()

    def select(self, idx: int):
        self._selected_idx = idx
        self._highlight(idx)

    # ── internal ──────────────────────────────────────────────────────────────
    def _refresh(self):
        for w in self._card_frames:
            w.destroy()
        self._card_frames.clear()

        query = self._search_var.get().lower()
        visible = [
            (i, s) for i, s in enumerate(self._students)
            if query in s.student_name.lower() or
               query in s.roll_no.lower() or
               query in s.subject.lower()
        ]

        for orig_i, student in visible:
            card = self._make_card(self._scroll, orig_i, student)
            card.pack(fill="x", padx=6, pady=3)
            self._card_frames.append(card)

        self._count_lbl.configure(text=str(len(self._students)))
        self._update_stats()
        if self._selected_idx >= 0:
            self._highlight(self._selected_idx)

    def _make_card(self, parent, idx, student):
        card = ctk.CTkFrame(parent, fg_color=NAVY_MID,
                             corner_radius=10, cursor="hand2")
        card.bind("<Button-1>", lambda e, i=idx: self._click(i))

        # Status icon + name
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 2))

        status_icon = STATUS_ICONS.get(student.status, "⏳")
        status_col  = STATUS_COLORS.get(student.status, MUTED)

        ctk.CTkLabel(top, text=status_icon, font=("Helvetica", 14),
                     text_color=status_col).pack(side="left")
        name_lbl = ctk.CTkLabel(
            top,
            text=student.student_name[:22] + ("…" if len(student.student_name) > 22 else ""),
            font=FONT_SUB, text_color=WHITE, anchor="w"
        )
        name_lbl.pack(side="left", padx=6)

        # Make label clickable too
        name_lbl.bind("<Button-1>", lambda e, i=idx: self._click(i))

        # Sub-row: roll + pages + marks
        sub = ctk.CTkFrame(card, fg_color="transparent")
        sub.pack(fill="x", padx=10, pady=(0, 8))
        info = []
        if student.roll_no:
            info.append(f"#{student.roll_no}")
        info.append(f"{student.page_count}p")
        if student.total_marks:
            info.append(f"📊 {student.total_marks}")
        ctk.CTkLabel(sub, text="  ·  ".join(info),
                     font=FONT_SMALL, text_color=MUTED).pack(side="left")

        # Status badge
        badge = ctk.CTkLabel(
            sub, text=student.status,
            font=FONT_SMALL, text_color=status_col,
            width=80, anchor="e"
        )
        badge.pack(side="right")

        # bind children
        for child in card.winfo_children():
            child.bind("<Button-1>", lambda e, i=idx: self._click(i))

        card._idx = idx
        return card

    def _click(self, idx):
        self._selected_idx = idx
        self._highlight(idx)
        self.on_select(idx)

    def _highlight(self, idx):
        for card in self._card_frames:
            if hasattr(card, "_idx"):
                selected = card._idx == idx
                card.configure(
                    fg_color=STEEL if selected else NAVY_MID,
                    border_width=2 if selected else 0,
                    border_color=AMBER if selected else NAVY_MID
                )

    def _on_search(self, *_):
        self._refresh()

    def _update_stats(self):
        if not self._students:
            self._stats_lbl.configure(text="No students loaded")
            return
        done = sum(1 for s in self._students if s.status == "Done")
        pct  = int(done / len(self._students) * 100)
        self._stats_lbl.configure(
            text=f"✅ {done}/{len(self._students)} done  ({pct}%)"
        )
