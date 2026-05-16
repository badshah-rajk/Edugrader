"""
EduGrader — OCR Results Panel
Shows extracted text, blur quality indicator, word-confidence
highlighting, and backend status.
"""
import customtkinter as ctk
from app.theme import *


class OCRResultsPanel(ctk.CTkFrame):
    """
    Bottom/side panel showing OCR text output with metadata.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=NAVY_LIGHT, corner_radius=0, **kwargs)
        self._build()

    def _build(self):
        # Header row
        hdr = ctk.CTkFrame(self, fg_color=NAVY_MID, corner_radius=0, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="📝  OCR Extracted Text",
                     font=FONT_SUB, text_color=AMBER).pack(side="left", padx=12, pady=8)

        self._backend_lbl = ctk.CTkLabel(hdr, text="—", font=FONT_SMALL,
                                          text_color=MUTED)
        self._backend_lbl.pack(side="right", padx=12)

        self._blur_lbl = ctk.CTkLabel(hdr, text="", font=FONT_SMALL,
                                       text_color=MUTED)
        self._blur_lbl.pack(side="right", padx=6)

        # Text area with scroll
        txt_frame = ctk.CTkFrame(self, fg_color="transparent")
        txt_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self._text_box = ctk.CTkTextbox(
            txt_frame,
            fg_color=NAVY,
            text_color=WHITE,
            font=FONT_MONO,
            border_color=STEEL,
            border_width=1,
            corner_radius=8,
            wrap="word",
            state="disabled"
        )
        self._text_box.pack(fill="both", expand=True)

        # Stats row
        stats = ctk.CTkFrame(self, fg_color=NAVY, corner_radius=0, height=34)
        stats.pack(fill="x")
        stats.pack_propagate(False)

        self._word_count  = ctk.CTkLabel(stats, text="Words: —",
                                          font=FONT_SMALL, text_color=MUTED)
        self._word_count.pack(side="left", padx=12, pady=6)

        self._conf_lbl    = ctk.CTkLabel(stats, text="Confidence: —",
                                          font=FONT_SMALL, text_color=MUTED)
        self._conf_lbl.pack(side="left", padx=12)

        # Copy button
        ctk.CTkButton(stats, text="📋 Copy", width=80, height=24,
                      fg_color=STEEL, font=FONT_SMALL,
                      command=self._copy).pack(side="right", padx=8, pady=5)

    # ── Public API ────────────────────────────────────────────────────────────
    def show_ocr_result(self, ocr_dict: dict):
        if not ocr_dict:
            self._set_text("No OCR result yet. Click 'Run OCR' on the toolbar.")
            return

        text     = ocr_dict.get("text", "").strip()
        backend  = ocr_dict.get("backend", "unknown")
        blur     = ocr_dict.get("blur_score", 0)
        blocks   = ocr_dict.get("blocks", [])
        enhanced = ocr_dict.get("enhanced", False)

        self._set_text(text or "(No text detected)")

        # Backend label
        icon = "🌐" if backend == "google" else "🔧"
        self._backend_lbl.configure(
            text=f"{icon} {backend.title()}",
            text_color=CYAN if backend == "google" else AMBER
        )

        # Blur quality
        if blur < 50:
            quality, qcolor = "Very Blurry", RED
        elif blur < 200:
            quality, qcolor = "Blurry", ORANGE
        elif blur < 500:
            quality, qcolor = "Moderate", AMBER
        else:
            quality, qcolor = "Sharp", GREEN
        self._blur_lbl.configure(
            text=f"📷 {quality}  (score: {blur:.0f}){' ⚡' if enhanced else ''}",
            text_color=qcolor
        )

        # Word count
        words = len(text.split()) if text else 0
        self._word_count.configure(text=f"Words: {words}")

        # Avg confidence
        if blocks:
            avg_conf = sum(b.get("confidence", 0) for b in blocks) / len(blocks)
            conf_color = GREEN if avg_conf > 80 else (AMBER if avg_conf > 50 else RED)
            self._conf_lbl.configure(
                text=f"Confidence: {avg_conf:.1f}%",
                text_color=conf_color
            )
        else:
            self._conf_lbl.configure(text="Confidence: N/A", text_color=MUTED)

    def show_processing(self, msg: str = "Processing…"):
        self._set_text(f"⏳  {msg}")
        self._backend_lbl.configure(text="Running…", text_color=AMBER)

    def show_error(self, msg: str):
        self._set_text(f"❌  Error:\n{msg}")
        self._backend_lbl.configure(text="Error", text_color=RED)

    def clear(self):
        self._set_text("")
        self._backend_lbl.configure(text="—", text_color=MUTED)
        self._blur_lbl.configure(text="")
        self._word_count.configure(text="Words: —")
        self._conf_lbl.configure(text="Confidence: —", text_color=MUTED)

    # ── internal ──────────────────────────────────────────────────────────────
    def _set_text(self, text: str):
        self._text_box.configure(state="normal")
        self._text_box.delete("1.0", "end")
        self._text_box.insert("1.0", text)
        self._text_box.configure(state="disabled")

    def _copy(self):
        text = self._text_box.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)
