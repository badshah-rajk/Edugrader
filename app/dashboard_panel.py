"""
EduGrader — Dashboard Panel
Class-wide statistics, marks overview, and export controls.
"""
import customtkinter as ctk
from app.theme import *


class DashboardPanel(ctk.CTkFrame):
    """
    Statistics dashboard shown when no specific student is selected,
    or as a slide-in overlay.
    """

    def __init__(self, master, pdf_manager, on_export_csv,
                 on_export_all_pdfs, **kwargs):
        super().__init__(master, fg_color=NAVY, **kwargs)
        self.pm             = pdf_manager
        self.on_export_csv  = on_export_csv
        self.on_export_pdfs = on_export_all_pdfs
        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # ── Header ────────────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color=NAVY_MID, corner_radius=0, height=60)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_propagate(False)

        ctk.CTkLabel(hdr, text="📊  Class Dashboard",
                     font=FONT_HEADING, text_color=AMBER).pack(
            side="left", padx=20, pady=14)

        ctk.CTkButton(hdr, text="🔄 Refresh",
                      fg_color=STEEL, width=100, height=32,
                      command=self.refresh).pack(side="right", padx=16, pady=14)

        # ── Scrollable body ───────────────────────────────────────────────────
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        scroll.columnconfigure((0, 1, 2, 3), weight=1)
        self._body = scroll

        self._stat_labels = {}
        self._table_frame = None
        self.refresh()

    # ── Public ────────────────────────────────────────────────────────────────
    def refresh(self):
        for w in self._body.winfo_children():
            w.destroy()
        self._render_summary()
        self._render_table()
        self._render_export_buttons()

    # ── Summary cards ─────────────────────────────────────────────────────────
    def _render_summary(self):
        s = self.pm.summary()

        cards = [
            ("👥", "Total Students", str(s["total"]),       CYAN),
            ("✅", "Completed",       str(s["done"]),        GREEN),
            ("🔄", "In Progress",     str(s["in_progress"]), AMBER),
            ("⏳", "Pending",         str(s["pending"]),     MUTED),
        ]

        # Marks stats
        all_marks  = [st.total_marks for st in self.pm.students if st.total_marks > 0]
        if all_marks:
            avg = sum(all_marks) / len(all_marks)
            hi  = max(all_marks)
            lo  = min(all_marks)
            cards += [
                ("📈", "Average Marks", f"{avg:.1f}", AMBER),
                ("🏆", "Highest",        f"{hi}",      GREEN),
                ("📉", "Lowest",         f"{lo}",      RED),
            ]

        row = ctk.CTkFrame(self._body, fg_color="transparent")
        row.pack(fill="x", pady=(0, 16))
        for i, (icon, label, val, color) in enumerate(cards):
            card = ctk.CTkFrame(row, fg_color=NAVY_MID, corner_radius=12)
            card.pack(side="left", expand=True, fill="both", padx=6)
            ctk.CTkLabel(card, text=icon, font=("Helvetica", 26)).pack(pady=(12, 2))
            ctk.CTkLabel(card, text=val, font=("Helvetica", 22, "bold"),
                         text_color=color).pack()
            ctk.CTkLabel(card, text=label, font=FONT_SMALL,
                         text_color=MUTED).pack(pady=(0, 12))

        # Progress bar
        if s["total"] > 0:
            pct = s["done"] / s["total"]
            ctk.CTkLabel(self._body, text=f"Grading Progress — {int(pct*100)}%",
                         font=FONT_SUB, text_color=SILVER, anchor="w").pack(
                fill="x", padx=6)
            prog = ctk.CTkProgressBar(self._body, progress_color=GREEN,
                                       fg_color=NAVY_MID, height=16,
                                       corner_radius=8)
            prog.set(pct)
            prog.pack(fill="x", padx=6, pady=(4, 16))

    # ── Student table ─────────────────────────────────────────────────────────
    def _render_table(self):
        ctk.CTkLabel(self._body, text="📋  Student Records",
                     font=FONT_SUB, text_color=AMBER, anchor="w").pack(
            fill="x", padx=6, pady=(0, 6))

        headers = ["Name", "Roll No.", "Subject", "Pages", "Status", "Marks"]
        hrow = ctk.CTkFrame(self._body, fg_color=NAVY_MID, corner_radius=8)
        hrow.pack(fill="x", padx=6, pady=2)
        for h in headers:
            ctk.CTkLabel(hrow, text=h, font=FONT_SUB,
                         text_color=AMBER, width=110, anchor="w").pack(
                side="left", padx=8, pady=6)

        STATUS_COLORS = {"Pending": MUTED, "In Progress": AMBER, "Done": GREEN}
        for student in self.pm.students:
            row = ctk.CTkFrame(self._body, fg_color=NAVY_LIGHT,
                                corner_radius=6)
            row.pack(fill="x", padx=6, pady=1)
            vals = [
                (student.student_name[:18], WHITE),
                (student.roll_no or "—",   SILVER),
                (student.subject or "—",   SILVER),
                (str(student.page_count),  SILVER),
                (student.status,           STATUS_COLORS.get(student.status, MUTED)),
                (str(student.total_marks) if student.total_marks else "—", CYAN),
            ]
            for txt, col in vals:
                ctk.CTkLabel(row, text=txt, font=FONT_BODY,
                             text_color=col, width=110, anchor="w").pack(
                    side="left", padx=8, pady=5)

        if not self.pm.students:
            ctk.CTkLabel(self._body,
                         text="No students loaded. Use File → Load Folder.",
                         font=FONT_BODY, text_color=MUTED).pack(pady=20)

    # ── Export buttons ────────────────────────────────────────────────────────
    def _render_export_buttons(self):
        exp = ctk.CTkFrame(self._body, fg_color="transparent")
        exp.pack(fill="x", padx=6, pady=16)

        ctk.CTkLabel(exp, text="🔽  Export",
                     font=FONT_SUB, text_color=AMBER).pack(side="left", padx=8)

        ctk.CTkButton(
            exp, text="📊  Export CSV Grades",
            fg_color=GREEN, text_color=WHITE,
            width=180, height=36, corner_radius=8,
            command=self.on_export_csv
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            exp, text="📄  Export All Annotated PDFs",
            fg_color=STEEL, text_color=WHITE,
            width=220, height=36, corner_radius=8,
            command=self.on_export_pdfs
        ).pack(side="left", padx=8)
