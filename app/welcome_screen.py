"""
EduGrader — Welcome Screen
Animated splash with logo, tagline, and action buttons.
"""
import customtkinter as ctk
from app.theme import *


class WelcomeScreen(ctk.CTkFrame):
    """
    Full-window welcome page shown on first launch.
    Calls on_start(action) where action is 'new' | 'open' | 'demo'.
    """

    def __init__(self, master, on_start, **kwargs):
        super().__init__(master, fg_color=NAVY, **kwargs)
        self.on_start = on_start
        self._build()
        self._animate_logo(0)

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)

        # ── Top spacer + Logo block ──────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="s", pady=(40, 0))

        # Decorative accent bar
        ctk.CTkFrame(top, width=80, height=4,
                     fg_color=AMBER, corner_radius=2).pack(pady=(0, 18))

        self._logo_lbl = ctk.CTkLabel(
            top, text="EduGrader",
            font=("Georgia", 52, "bold"),
            text_color=WHITE
        )
        self._logo_lbl.pack()

        ctk.CTkLabel(
            top,
            text="Student Answer Copy  ·  OCR & Annotation System",
            font=("Helvetica", 15),
            text_color=SILVER
        ).pack(pady=(6, 0))

        # ── Centre card ───────────────────────────────────────────────────────
        card = ctk.CTkFrame(self, fg_color=NAVY_LIGHT,
                            corner_radius=20, border_width=1,
                            border_color=STEEL)
        card.grid(row=1, column=0, padx=80, pady=40, sticky="ew")
        card.columnconfigure((0, 1, 2), weight=1)

        feats = [
            ("📄", "Bulk PDF Loading",    "Drop a folder of answer\ncopies and process all"),
            ("🔍", "Free OCR Engine",     "Google Vision + Tesseract\nwith blur recovery"),
            ("✏️",  "Full Annotations",   "Stamps · highlights ·\ncomments · marks"),
            ("📊", "Marks Dashboard",     "Per-student & class-wide\nstatistics"),
            ("💾", "Export Reports",      "Annotated PDFs + CSV\ngrade sheets"),
        ]
        for i, (icon, title, desc) in enumerate(feats):
            col = i % 3
            row = i // 3
            f = ctk.CTkFrame(card, fg_color=NAVY_MID, corner_radius=12)
            f.grid(row=row, column=col, padx=14, pady=14, sticky="nsew")
            ctk.CTkLabel(f, text=icon, font=("Helvetica", 30)).pack(pady=(14, 4))
            ctk.CTkLabel(f, text=title, font=FONT_SUB,
                         text_color=AMBER).pack()
            ctk.CTkLabel(f, text=desc, font=FONT_SMALL,
                         text_color=SILVER, justify="center").pack(pady=(2, 14))

        # ── Buttons ───────────────────────────────────────────────────────────
        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=2, column=0, pady=(0, 60))

        btns = [
            ("🚀  Start New Project", "new",  AMBER,      DARK_TEXT),
            ("📂  Open Session",      "open", STEEL_LIGHT, WHITE),
            ("🎓  Load Demo",         "demo", NAVY_MID,    SILVER),
        ]
        for label, action, bg, fg in btns:
            ctk.CTkButton(
                btn_row, text=label,
                width=210, height=50,
                font=FONT_SUB,
                fg_color=bg, text_color=fg,
                hover_color=_hover(bg),
                corner_radius=CORNER_R,
                command=lambda a=action: self.on_start(a)
            ).pack(side="left", padx=12)

        # ── Footer ────────────────────────────────────────────────────────────
        ctk.CTkLabel(self, text="© EduGrader  —  100% Free  |  No Cloud Required",
                     font=FONT_SMALL, text_color=MUTED).place(relx=0.5, rely=0.97,
                                                               anchor="s")

    # ── Logo pulse animation ──────────────────────────────────────────────────
    _SIZES = [52, 54, 56, 54]

    def _animate_logo(self, step):
        size = self._SIZES[step % len(self._SIZES)]
        self._logo_lbl.configure(font=("Georgia", size, "bold"))
        self.after(600, self._animate_logo, step + 1)


# ── helper ────────────────────────────────────────────────────────────────────
def _hover(hex_color: str) -> str:
    """Darken a hex colour slightly for hover state."""
    h = hex_color.lstrip("#")
    rgb = tuple(max(0, int(h[i:i+2], 16) - 20) for i in (0, 2, 4))
    return "#{:02X}{:02X}{:02X}".format(*rgb)
