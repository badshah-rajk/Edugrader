"""
EduGrader — PDF Manager
Loads student answer-copy PDFs, converts pages to PIL images,
caches results, and manages the student roster.
"""
import os
import json
import shutil
import tempfile
from pathlib import Path
from typing import Optional
import threading

import fitz                      # PyMuPDF — zero external deps for rendering
from PIL import Image
import numpy as np

CACHE_DIR  = Path(__file__).parent.parent / "ocr_cache"
CACHE_DIR.mkdir(exist_ok=True)

DPI = 200   # render resolution — good balance of quality vs speed


# ─────────────────────────────────────────────────────────────────────────────
class StudentRecord:
    """Represents one student's answer-copy PDF with metadata."""

    def __init__(self, pdf_path: str, student_name: str = "",
                 roll_no: str = "", subject: str = ""):
        self.pdf_path     = Path(pdf_path)
        self.student_name = student_name or self.pdf_path.stem
        self.roll_no      = roll_no
        self.subject      = subject
        self.page_count   = 0
        self.ocr_results  = {}    # {page_idx: ocr_dict}
        self.annotations  = {}    # {page_idx: [anno_dict, ...]}
        self.marks        = {}    # {question_id: marks_awarded}
        self.total_marks  = 0
        self.status       = "Pending"   # Pending | In Progress | Done
        self._doc: Optional[fitz.Document] = None
        self._lock        = threading.Lock()

        self._open()

    def _open(self):
        try:
            self._doc       = fitz.open(str(self.pdf_path))
            self.page_count = self._doc.page_count
        except Exception as e:
            self._doc       = None
            self.page_count = 0
            print(f"[PDF] Could not open {self.pdf_path}: {e}")

    def get_page_image(self, page_idx: int, dpi: int = DPI) -> Optional[Image.Image]:
        """Render a PDF page to a PIL Image."""
        with self._lock:
            if self._doc is None or page_idx >= self.page_count:
                return None
            page  = self._doc[page_idx]
            mat   = fitz.Matrix(dpi / 72, dpi / 72)
            pix   = page.get_pixmap(matrix=mat, alpha=False)
            img   = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            return img

    def get_page_array(self, page_idx: int) -> Optional[np.ndarray]:
        """Render page → BGR numpy array for OpenCV."""
        img = self.get_page_image(page_idx)
        if img is None:
            return None
        return np.array(img)[:, :, ::-1].copy()   # RGB → BGR

    def save_annotation(self, page_idx: int, anno: dict):
        self.annotations.setdefault(page_idx, []).append(anno)

    def remove_annotation(self, page_idx: int, anno_id: str):
        self.annotations[page_idx] = [
            a for a in self.annotations.get(page_idx, [])
            if a.get("id") != anno_id
        ]

    def to_dict(self) -> dict:
        return {
            "pdf_path":     str(self.pdf_path),
            "student_name": self.student_name,
            "roll_no":      self.roll_no,
            "subject":      self.subject,
            "page_count":   self.page_count,
            "ocr_results":  self.ocr_results,
            "annotations":  self.annotations,
            "marks":        self.marks,
            "total_marks":  self.total_marks,
            "status":       self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StudentRecord":
        rec = cls(
            d["pdf_path"],
            d.get("student_name", ""),
            d.get("roll_no", ""),
            d.get("subject", ""),
        )
        rec.ocr_results  = {int(k): v for k, v in d.get("ocr_results", {}).items()}
        rec.annotations  = {int(k): v for k, v in d.get("annotations", {}).items()}
        rec.marks        = d.get("marks", {})
        rec.total_marks  = d.get("total_marks", 0)
        rec.status       = d.get("status", "Pending")
        return rec

    def close(self):
        if self._doc:
            self._doc.close()
            self._doc = None


# ─────────────────────────────────────────────────────────────────────────────
class PDFManager:
    """Manages the roster of all loaded student PDFs."""

    PROJECT_FILE = "session.json"

    def __init__(self, project_dir: str = ""):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.students: list[StudentRecord] = []
        self._session_path = self.project_dir / self.PROJECT_FILE

    # ── loading ───────────────────────────────────────────────────────────────
    def load_folder(self, folder: str,
                    subject: str = "",
                    progress_cb=None) -> int:
        """
        Scan a folder for PDF files and create StudentRecord for each.
        Returns number of PDFs loaded.
        """
        folder = Path(folder)
        pdfs   = sorted(folder.glob("*.pdf"))
        loaded = 0
        for i, pdf in enumerate(pdfs):
            if any(s.pdf_path == pdf for s in self.students):
                continue                            # already loaded
            rec = StudentRecord(str(pdf), subject=subject)
            self.students.append(rec)
            loaded += 1
            if progress_cb:
                progress_cb(i + 1, len(pdfs), pdf.name)
        return loaded

    def add_pdf(self, pdf_path: str, student_name: str = "",
                roll_no: str = "", subject: str = "") -> StudentRecord:
        rec = StudentRecord(pdf_path, student_name, roll_no, subject)
        self.students.append(rec)
        return rec

    def remove_student(self, idx: int):
        if 0 <= idx < len(self.students):
            self.students[idx].close()
            self.students.pop(idx)

    # ── persistence ───────────────────────────────────────────────────────────
    def save_session(self, path: str = ""):
        path = path or str(self._session_path)
        data = [s.to_dict() for s in self.students]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_session(self, path: str = "") -> bool:
        path = path or str(self._session_path)
        if not os.path.exists(path):
            return False
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            self.students = []
            for d in data:
                if os.path.exists(d.get("pdf_path", "")):
                    self.students.append(StudentRecord.from_dict(d))
            return True
        except Exception as e:
            print(f"[Session] Load error: {e}")
            return False

    # ── stats ─────────────────────────────────────────────────────────────────
    def summary(self) -> dict:
        total   = len(self.students)
        done    = sum(1 for s in self.students if s.status == "Done")
        pending = sum(1 for s in self.students if s.status == "Pending")
        inprog  = total - done - pending
        return {
            "total": total, "done": done,
            "pending": pending, "in_progress": inprog
        }
