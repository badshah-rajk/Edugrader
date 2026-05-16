"""
EduGrader — Main Application Controller
Wires all screens and panels together.
"""
import os
import csv
import json
import threading
import tkinter as tk
import tkinter.filedialog as fd
import tkinter.messagebox as mb
import customtkinter as ctk
from pathlib import Path

from app.theme import *
from app.welcome_screen    import WelcomeScreen
from app.student_list_panel import StudentListPanel
from app.pdf_viewer        import PDFViewerCanvas
from app.annotation_toolbar import AnnotationToolbar
from app.ocr_panel         import OCRResultsPanel
from app.dashboard_panel   import DashboardPanel
from app.pdf_manager       import PDFManager, StudentRecord
from app.ocr_engine        import OCREngine
from app.annotation_engine import (
    Annotation, AnnotationRenderer, export_annotated_pdf
)

EXPORT_DIR = Path(__file__).parent.parent / "exports"
EXPORT_DIR.mkdir(exist_ok=True)


class EduGraderApp:
    """Top-level application class."""

    APP_TITLE   = "EduGrader  —  Answer Copy OCR & Annotation"
    WIN_SIZE    = "1400x860"
    MIN_SIZE    = (1100, 700)

    def __init__(self):
        ctk.set_appearance_mode(CTK_APPEARANCE)
        ctk.set_default_color_theme(CTK_THEME)

        self.root = ctk.CTk()
        self.root.title(self.APP_TITLE)
        self.root.geometry(self.WIN_SIZE)
        self.root.minsize(*self.MIN_SIZE)
        self.root.configure(fg_color=NAVY)

        self.pm           = PDFManager()
        self.ocr_engine   = OCREngine()
        self._current_idx = -1
        self._current_page = 0
        self._google_key   = ""

        # Build layout
        self._show_welcome()

        # Intercept window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── Launch ────────────────────────────────────────────────────────────────
    def run(self):
        self.root.mainloop()

    # ══════════════════════════════════════════════════════════════════════════
    # WELCOME
    # ══════════════════════════════════════════════════════════════════════════
    def _show_welcome(self):
        for w in self.root.winfo_children():
            w.destroy()
        self._welcome = WelcomeScreen(self.root, on_start=self._welcome_action)
        self._welcome.pack(fill="both", expand=True)

    def _welcome_action(self, action: str):
        if action == "new":
            self._show_main()
            self._cmd_load_folder()
        elif action == "open":
            self._show_main()
            self._cmd_open_session()
        elif action == "demo":
            self._show_main()
            self._load_demo()

    # ══════════════════════════════════════════════════════════════════════════
    # MAIN WORKSPACE
    # ══════════════════════════════════════════════════════════════════════════
    def _show_main(self):
        for w in self.root.winfo_children():
            w.destroy()
        self._build_main_ui()

    def _build_main_ui(self):
        self.root.columnconfigure(0, weight=0)   # sidebar
        self.root.columnconfigure(1, weight=1)   # viewer
        self.root.columnconfigure(2, weight=0)   # tool bar
        self.root.rowconfigure(0, weight=0)       # topbar
        self.root.rowconfigure(1, weight=1)       # content
        self.root.rowconfigure(2, weight=0)       # ocr panel
        self.root.rowconfigure(3, weight=0)       # status bar

        # ── Top bar ───────────────────────────────────────────────────────────
        self._build_topbar()

        # ── Student list ──────────────────────────────────────────────────────
        self.student_panel = StudentListPanel(
            self.root, on_select=self._on_student_select
        )
        self.student_panel.grid(row=1, column=0, rowspan=2, sticky="nsew")

        # ── PDF Viewer ────────────────────────────────────────────────────────
        self.viewer = PDFViewerCanvas(self.root)
        self.viewer.grid(row=1, column=1, sticky="nsew", padx=0, pady=0)
        self.viewer.set_callbacks(
            on_add=self._on_anno_add,
            on_delete=self._on_anno_del
        )

        # ── Annotation toolbar ────────────────────────────────────────────────
        self.anno_toolbar = AnnotationToolbar(
            self.root, on_tool_select=self._on_tool_select
        )
        self.anno_toolbar.grid(row=1, column=2, sticky="nsew")

        # ── OCR panel (collapsible bottom) ────────────────────────────────────
        self.ocr_panel = OCRResultsPanel(self.root, height=200)
        self.ocr_panel.grid(row=2, column=1, sticky="nsew", padx=0)

        # ── Page nav bar ──────────────────────────────────────────────────────
        self._build_page_nav()

        # ── Status bar ────────────────────────────────────────────────────────
        self._build_status_bar()

    # ── Top bar ───────────────────────────────────────────────────────────────
    def _build_topbar(self):
        tb = ctk.CTkFrame(self.root, fg_color=NAVY_MID,
                           corner_radius=0, height=TOPBAR_H)
        tb.grid(row=0, column=0, columnspan=3, sticky="ew")
        tb.grid_propagate(False)
        tb.columnconfigure(2, weight=1)

        # Logo
        ctk.CTkLabel(tb, text="EduGrader",
                     font=("Georgia", 20, "bold"),
                     text_color=AMBER).grid(row=0, column=0, padx=16, pady=10)

        ctk.CTkLabel(tb, text="OCR & Annotation",
                     font=FONT_SMALL, text_color=MUTED).grid(
            row=0, column=1, padx=0)

        # Action buttons
        actions = [
            ("📂 Load Folder",   self._cmd_load_folder,   STEEL),
            ("➕ Add PDF",        self._cmd_add_pdf,        STEEL),
            ("▶ Run OCR",        self._cmd_run_ocr,        AMBER),
            ("▶▶ Batch OCR",    self._cmd_batch_ocr,      AMBER_DARK),
            ("💾 Save Session",   self._cmd_save_session,   NAVY),
            ("📊 Dashboard",     self._cmd_dashboard,      CYAN_DARK),
            ("📄 Export PDF",    self._cmd_export_pdf,     GREEN),
            ("🔑 API Key",       self._cmd_set_api_key,    NAVY),
            ("🏠 Home",          self._show_welcome,        NAVY),
        ]
        btn_frame = ctk.CTkFrame(tb, fg_color="transparent")
        btn_frame.grid(row=0, column=3, padx=16)
        for label, cmd, bg in actions:
            ctk.CTkButton(
                btn_frame, text=label, width=110, height=32,
                fg_color=bg, font=FONT_SMALL,
                text_color=DARK_TEXT if bg == AMBER else WHITE,
                hover_color=_hover(bg),
                corner_radius=8, command=cmd
            ).pack(side="left", padx=3)

    # ── Page navigation ───────────────────────────────────────────────────────
    def _build_page_nav(self):
        nav = ctk.CTkFrame(self.root, fg_color=NAVY_MID,
                            corner_radius=0, height=38)
        nav.grid(row=2, column=0, sticky="ew")
        nav.grid_propagate(False)

        ctk.CTkButton(nav, text="◀", width=32, height=26, fg_color=STEEL,
                      command=self._prev_page).pack(side="left", padx=6, pady=6)
        self._page_lbl = ctk.CTkLabel(nav, text="Page — / —",
                                       font=FONT_SMALL, text_color=SILVER)
        self._page_lbl.pack(side="left")
        ctk.CTkButton(nav, text="▶", width=32, height=26, fg_color=STEEL,
                      command=self._next_page).pack(side="left", padx=6)

        ctk.CTkButton(nav, text="🔍 Fit",  width=56, height=26, fg_color=NAVY,
                      font=FONT_SMALL, command=lambda: self.viewer.zoom_fit()
                      ).pack(side="right", padx=4, pady=6)
        ctk.CTkButton(nav, text="1:1",    width=40, height=26, fg_color=NAVY,
                      font=FONT_SMALL, command=lambda: self.viewer.zoom_reset()
                      ).pack(side="right", padx=4)

    # ── Status bar ────────────────────────────────────────────────────────────
    def _build_status_bar(self):
        sb = ctk.CTkFrame(self.root, fg_color=NAVY_MID,
                           corner_radius=0, height=STATUS_H)
        sb.grid(row=3, column=0, columnspan=3, sticky="ew")
        sb.grid_propagate(False)
        sb.columnconfigure(1, weight=1)

        self._status_lbl = ctk.CTkLabel(sb, text="Ready  —  Load a folder to begin",
                                         font=FONT_SMALL, text_color=SILVER,
                                         anchor="w")
        self._status_lbl.grid(row=0, column=0, padx=12, pady=6, sticky="w")

        self._progress = ctk.CTkProgressBar(sb, width=200, height=8,
                                             progress_color=AMBER,
                                             fg_color=STEEL)
        self._progress.grid(row=0, column=2, padx=12)
        self._progress.set(0)

    # ══════════════════════════════════════════════════════════════════════════
    # STUDENT / PAGE SELECTION
    # ══════════════════════════════════════════════════════════════════════════
    def _on_student_select(self, idx: int):
        self._current_idx  = idx
        self._current_page = 0
        self._load_page()
        # Update status
        s = self.pm.students[idx]
        self._set_status(f"📖 {s.student_name}  |  {s.page_count} pages  |  {s.status}")

    def _load_page(self):
        if self._current_idx < 0:
            return
        s   = self.pm.students[self._current_idx]
        pg  = self._current_page
        if s.page_count == 0:
            return

        self._page_lbl.configure(
            text=f"Page {pg+1} / {s.page_count}"
        )

        def _load():
            img = s.get_page_image(pg)
            if img is None:
                return
            annos = s.annotations.get(pg, [])
            self.viewer.after(0, lambda: self.viewer.set_page(img, annos))
            # Show cached OCR if available
            if pg in s.ocr_results:
                self.ocr_panel.after(0,
                    lambda: self.ocr_panel.show_ocr_result(s.ocr_results[pg]))

        threading.Thread(target=_load, daemon=True).start()

    def _prev_page(self):
        if self._current_idx < 0:
            return
        s = self.pm.students[self._current_idx]
        if self._current_page > 0:
            self._current_page -= 1
            self._load_page()

    def _next_page(self):
        if self._current_idx < 0:
            return
        s = self.pm.students[self._current_idx]
        if self._current_page < s.page_count - 1:
            self._current_page += 1
            self._load_page()

    # ══════════════════════════════════════════════════════════════════════════
    # ANNOTATION CALLBACKS
    # ══════════════════════════════════════════════════════════════════════════
    def _on_tool_select(self, tool_id, color):
        if tool_id:
            self.viewer.set_tool(tool_id, color)
        else:
            self.viewer.set_tool(None)

    def _on_anno_add(self, ann: Annotation):
        if self._current_idx < 0:
            return
        s = self.pm.students[self._current_idx]
        pg = self._current_page
        s.annotations.setdefault(pg, []).append(ann.to_dict())
        self._set_status(f"✏ Annotation added: {ann.type}")

    def _on_anno_del(self, anno_id: str):
        if self._current_idx < 0:
            return
        s = self.pm.students[self._current_idx]
        pg = self._current_page
        s.annotations[pg] = [
            a for a in s.annotations.get(pg, [])
            if a.get("id") != anno_id
        ]

    # ══════════════════════════════════════════════════════════════════════════
    # COMMANDS
    # ══════════════════════════════════════════════════════════════════════════
    def _cmd_load_folder(self):
        folder = fd.askdirectory(title="Select folder with student PDFs")
        if not folder:
            return
        subject = _ask_string(self.root, "Subject", "Enter subject name (optional):")
        self._set_status("Loading PDFs…")
        self._progress.set(0)

        def _load():
            def _cb(done, total, name):
                self.root.after(0, lambda:
                    (self._progress.set(done/total),
                     self._set_status(f"Loading {name} ({done}/{total})…")))
            count = self.pm.load_folder(folder, subject=subject or "", progress_cb=_cb)
            self.root.after(0, lambda: self._after_load(count))

        threading.Thread(target=_load, daemon=True).start()

    def _after_load(self, count: int):
        self.student_panel.load_students(self.pm.students)
        self._progress.set(1)
        self._set_status(f"✅ Loaded {count} PDFs  |  {len(self.pm.students)} total students")

    def _cmd_add_pdf(self):
        path = fd.askopenfilename(
            title="Select student PDF",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return
        name = _ask_string(self.root, "Student Name", "Enter student name:")
        roll = _ask_string(self.root, "Roll Number", "Enter roll number (optional):")
        subj = _ask_string(self.root, "Subject", "Enter subject (optional):")
        rec  = self.pm.add_pdf(path, name or "", roll or "", subj or "")
        self.student_panel.load_students(self.pm.students)
        self._set_status(f"➕ Added: {rec.student_name}")

    def _cmd_run_ocr(self):
        if self._current_idx < 0:
            mb.showinfo("OCR", "Select a student first.")
            return
        s  = self.pm.students[self._current_idx]
        pg = self._current_page
        self.ocr_panel.show_processing("Running OCR on this page…")
        self._set_status("⏳ Running OCR…")

        def _run():
            arr = s.get_page_array(pg)
            if arr is None:
                self.ocr_panel.after(0, lambda: self.ocr_panel.show_error("Could not render page."))
                return
            use_google = bool(self._google_key)
            result = self.ocr_engine.process_image(arr, use_google=use_google)
            s.ocr_results[pg] = result
            if s.status == "Pending":
                s.status = "In Progress"
            self.root.after(0, lambda: (
                self.ocr_panel.show_ocr_result(result),
                self.student_panel.load_students(self.pm.students),
                self._set_status(f"✅ OCR done  ({result['backend']})  "
                                 f"blur={result['blur_score']:.0f}")
            ))
        threading.Thread(target=_run, daemon=True).start()

    def _cmd_batch_ocr(self):
        if not self.pm.students:
            mb.showinfo("Batch OCR", "No students loaded.")
            return
        if not mb.askyesno("Batch OCR",
                           f"Run OCR on all {len(self.pm.students)} students "
                           f"(all pages)? This may take a while."):
            return
        self._set_status("⏳ Batch OCR started…")
        self._progress.set(0)

        def _run():
            total = len(self.pm.students)
            for i, s in enumerate(self.pm.students):
                for pg in range(s.page_count):
                    if pg not in s.ocr_results:
                        arr = s.get_page_array(pg)
                        if arr is not None:
                            res = self.ocr_engine.process_image(
                                arr, use_google=bool(self._google_key))
                            s.ocr_results[pg] = res
                s.status = "In Progress"
                pct = (i+1) / total
                self.root.after(0, lambda p=pct, n=s.student_name:
                    (self._progress.set(p),
                     self._set_status(f"OCR: {n}  ({int(p*100)}%)")))

            self.root.after(0, lambda: (
                self.student_panel.load_students(self.pm.students),
                self._set_status("✅ Batch OCR complete!")
            ))

        threading.Thread(target=_run, daemon=True).start()

    def _cmd_save_session(self):
        path = fd.asksaveasfilename(
            title="Save Session",
            defaultextension=".json",
            filetypes=[("Session files", "*.json")]
        )
        if path:
            self.pm.save_session(path)
            self._set_status(f"💾 Session saved: {Path(path).name}")

    def _cmd_open_session(self):
        path = fd.askopenfilename(
            title="Open Session",
            filetypes=[("Session files", "*.json")]
        )
        if path and self.pm.load_session(path):
            self.student_panel.load_students(self.pm.students)
            self._set_status(f"📂 Session loaded: {len(self.pm.students)} students")

    def _cmd_export_pdf(self):
        if self._current_idx < 0:
            mb.showinfo("Export", "Select a student first.")
            return
        s    = self.pm.students[self._current_idx]
        path = fd.asksaveasfilename(
            title="Export Annotated PDF",
            initialfile=f"{s.student_name}_annotated.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")]
        )
        if not path:
            return
        self._set_status("📄 Exporting annotated PDF…")

        def _exp():
            pages = [s.get_page_image(i) for i in range(s.page_count)]
            pages = [p for p in pages if p is not None]
            export_annotated_pdf(pages, s.annotations, path)
            s.status = "Done"
            self.root.after(0, lambda: (
                self.student_panel.load_students(self.pm.students),
                self._set_status(f"✅ Exported: {Path(path).name}"),
                mb.showinfo("Export", f"Annotated PDF saved:\n{path}")
            ))
        threading.Thread(target=_exp, daemon=True).start()

    def _cmd_export_all_pdfs(self):
        folder = fd.askdirectory(title="Select output folder for all annotated PDFs")
        if not folder:
            return
        self._set_status("📄 Exporting all annotated PDFs…")

        def _run():
            for i, s in enumerate(self.pm.students):
                out = os.path.join(folder, f"{s.student_name}_annotated.pdf")
                pages = [s.get_page_image(p) for p in range(s.page_count)]
                pages = [p for p in pages if p is not None]
                if pages:
                    export_annotated_pdf(pages, s.annotations, out)
                s.status = "Done"
                pct = (i+1) / len(self.pm.students)
                self.root.after(0, lambda p=pct:
                    (self._progress.set(p),
                     self._set_status(f"Exporting… {int(p*100)}%")))
            self.root.after(0, lambda: (
                self.student_panel.load_students(self.pm.students),
                self._set_status("✅ All PDFs exported!"),
                mb.showinfo("Export", f"All annotated PDFs saved to:\n{folder}")
            ))
        threading.Thread(target=_run, daemon=True).start()

    def _cmd_export_csv(self):
        if not self.pm.students:
            mb.showinfo("Export", "No students loaded.")
            return
        path = fd.asksaveasfilename(
            title="Export CSV Grades",
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")]
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["Name", "Roll No.", "Subject", "Status", "Total Marks"])
            for s in self.pm.students:
                w.writerow([s.student_name, s.roll_no, s.subject,
                            s.status, s.total_marks])
        self._set_status(f"📊 CSV exported: {Path(path).name}")
        mb.showinfo("Export", f"CSV saved:\n{path}")

    def _cmd_dashboard(self):
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Class Dashboard")
        dlg.geometry("900x600")
        dlg.configure(fg_color=NAVY)
        DashboardPanel(
            dlg,
            pdf_manager=self.pm,
            on_export_csv=self._cmd_export_csv,
            on_export_all_pdfs=self._cmd_export_all_pdfs
        ).pack(fill="both", expand=True)

    def _cmd_set_api_key(self):
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Google Vision API Key")
        dlg.geometry("460x220")
        dlg.configure(fg_color=NAVY_LIGHT)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="🔑  Google Cloud Vision API Key",
                     font=FONT_SUB, text_color=AMBER).pack(pady=16)
        ctk.CTkLabel(
            dlg,
            text="Free tier: 1,000 pages/month. Leave blank to use Tesseract only.",
            font=FONT_SMALL, text_color=MUTED
        ).pack()
        entry = ctk.CTkEntry(dlg, width=380, placeholder_text="AIza…",
                             fg_color=NAVY_MID, text_color=WHITE,
                             show="*")
        entry.insert(0, self._google_key)
        entry.pack(pady=12)

        def _save():
            self._google_key = entry.get().strip()
            self.ocr_engine.google_api_key = self._google_key
            dlg.destroy()
            self._set_status("🔑 API key saved" if self._google_key else "🔧 Using Tesseract only")

        ctk.CTkButton(dlg, text="Save", fg_color=AMBER, text_color=DARK_TEXT,
                      command=_save).pack()

    # ── Demo ─────────────────────────────────────────────────────────────────
    def _load_demo(self):
        """Create a demo student with a synthetic PDF for demonstration."""
        import fitz
        from PIL import Image, ImageDraw, ImageFont
        demo_path = Path(__file__).parent.parent / "sample_pdfs" / "demo_student.pdf"
        demo_path.parent.mkdir(exist_ok=True)

        if not demo_path.exists():
            # Generate a sample answer-copy PDF
            doc = fitz.open()
            for page_no in range(3):
                page = doc.new_page(width=595, height=842)
                page.insert_text((50, 60),  f"STUDENT: Demo Student", fontsize=16)
                page.insert_text((50, 90),  f"SUBJECT: Mathematics  |  ROLL: 42",  fontsize=12)
                page.insert_text((50, 130), f"─"*60, fontsize=10)
                page.insert_text((50, 160),
                    f"Q{page_no+1}. Solve the following quadratic equation:", fontsize=13)
                page.insert_text((50, 190),
                    f"     x² + 5x + 6 = 0", fontsize=13)
                page.insert_text((50, 240), "Answer:", fontsize=12)
                page.insert_text((50, 270),
                    "Factorising: (x + 2)(x + 3) = 0", fontsize=12)
                page.insert_text((50, 300), "Therefore x = -2  or  x = -3", fontsize=12)
                page.insert_text((50, 340), f"[Page {page_no+1} of 3]", fontsize=10)
            doc.save(str(demo_path))
            doc.close()

        rec = self.pm.add_pdf(str(demo_path), "Demo Student", "42", "Mathematics")
        self.student_panel.load_students(self.pm.students)
        self._on_student_select(0)
        self._set_status("🎓 Demo loaded — try the OCR and annotation tools!")

    # ══════════════════════════════════════════════════════════════════════════
    # UTILS
    # ══════════════════════════════════════════════════════════════════════════
    def _set_status(self, msg: str):
        if hasattr(self, "_status_lbl"):
            self._status_lbl.configure(text=msg)

    def _on_close(self):
        """Confirm before exit."""
        dlg = _ExitDialog(self.root)
        if dlg.confirmed:
            self.root.destroy()


# ── Exit dialog ───────────────────────────────────────────────────────────────
class _ExitDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Confirm Exit")
        self.geometry("380x200")
        self.configure(fg_color=NAVY_LIGHT)
        self.resizable(False, False)
        self.confirmed = False
        self.grab_set()
        self.lift()

        ctk.CTkLabel(self, text="👋  Exit EduGrader?",
                     font=FONT_HEADING, text_color=AMBER).pack(pady=22)
        ctk.CTkLabel(self,
                     text="Unsaved annotations will be lost.\nSave your session first!",
                     font=FONT_BODY, text_color=SILVER).pack()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(pady=20)
        ctk.CTkButton(btn_row, text="✓  Yes, Exit", fg_color=RED,
                      width=130, command=self._yes).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="✗  Cancel", fg_color=STEEL,
                      width=130, command=self._no).pack(side="left", padx=8)
        self.wait_window()

    def _yes(self):
        self.confirmed = True
        self.destroy()

    def _no(self):
        self.confirmed = False
        self.destroy()


# ── String prompt helper ──────────────────────────────────────────────────────
def _ask_string(parent, title: str, prompt: str) -> str:
    dlg = ctk.CTkToplevel(parent)
    dlg.title(title)
    dlg.geometry("380x160")
    dlg.configure(fg_color=NAVY_LIGHT)
    dlg.grab_set()
    dlg.lift()
    result = {"value": ""}

    ctk.CTkLabel(dlg, text=prompt, font=FONT_BODY,
                 text_color=SILVER).pack(pady=14)
    entry = ctk.CTkEntry(dlg, width=300, fg_color=NAVY_MID, text_color=WHITE)
    entry.pack(pady=4)
    entry.focus()

    def _ok(event=None):
        result["value"] = entry.get().strip()
        dlg.destroy()

    entry.bind("<Return>", _ok)
    ctk.CTkButton(dlg, text="OK", fg_color=AMBER, text_color=DARK_TEXT,
                  width=100, command=_ok).pack(pady=10)
    dlg.wait_window()
    return result["value"]


def _hover(hex_color: str) -> str:
    h = hex_color.lstrip("#")
    rgb = tuple(max(0, int(h[i:i+2], 16) - 20) for i in (0, 2, 4))
    return "#{:02X}{:02X}{:02X}".format(*rgb)
