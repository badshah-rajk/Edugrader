# EduGrader 📚
### Student Answer Copy OCR & Annotation System

A fully-featured desktop application for teachers and evaluators to:
- Load folders of student PDF answer copies
- OCR every page (free Google Vision API + Tesseract fallback with blur recovery)
- Annotate pages with stamps, highlights, comments, arrows, free-draw, and marks
- Export annotated PDFs and CSV grade sheets
- View class-wide dashboards and statistics

---

## ✨ Features

| Category | Features |
|---|---|
| **PDF Management** | Bulk folder import, individual PDF add, page-by-page navigation |
| **OCR** | Google Cloud Vision (free tier), Tesseract+OpenCV, blur recovery, deskew, CLAHE |
| **Annotation** | ✓/✗/≈ stamps, highlights, underlines, comment bubbles, arrows, free-draw, marks boxes |
| **UI/UX** | Dark academic theme, animated welcome screen, exit confirmation, collapsible panels |
| **Export** | Annotated PDFs, CSV grade sheets, session JSON |
| **Dashboard** | Class stats, progress bar, marks averages |

---

## 🚀 Quick Start

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Tesseract (free OCR engine — no API key needed)
```bash
# Ubuntu / Debian
sudo apt install tesseract-ocr tesseract-ocr-eng

# macOS
brew install tesseract

# Windows — download installer:
# https://github.com/UB-Mannheim/tesseract/wiki
```

### 3. Run the app
```bash
python main.py
```

---

## 🔍 OCR Backends

### Option A — Google Cloud Vision (Best Quality, Free Tier)
1. Go to https://console.cloud.google.com/
2. Enable **Cloud Vision API**
3. Create an API key (free tier = 1,000 pages/month)
4. In EduGrader, click **🔑 API Key** and paste your key

### Option B — Tesseract (100% Free, No Limit, Works Offline)
Just install Tesseract (see above). EduGrader auto-detects it.

### Blur Recovery Pipeline
Even blurry / poor scans are processed through:
1. Unsharp masking (deblur)
2. Adaptive denoising (NlMeans)
3. CLAHE (contrast enhancement)
4. Adaptive binarisation
5. Morphological cleanup
6. Deskew correction

---

## ✏️ Annotation Tools

| Tool | Action | Use Case |
|---|---|---|
| **✓ Correct** | Single click | Mark correct answer |
| **✗ Wrong** | Single click | Mark wrong answer |
| **≈ Partial** | Single click | Partial credit |
| **▬ Highlight** | Click & drag | Highlight a region |
| **╌ Underline** | Click & drag | Underline text |
| **💬 Comment** | Click & drag → type | Add comment bubble |
| **T Text** | Click | Add text label |
| **↗ Arrow** | Click & drag | Draw arrow |
| **✏ Draw** | Click & drag | Freehand drawing |
| **📊 Marks** | Click & drag | Add marks box |

**Right-click** any annotation to delete it.

---

## 📁 Project Structure
```
EduGrader/
├── main.py                 # Entry point
├── requirements.txt
├── README.md
├── app/
│   ├── app.py              # Main controller
│   ├── theme.py            # Colors, fonts, constants
│   ├── welcome_screen.py   # Animated splash screen
│   ├── pdf_manager.py      # PDF loading & student records
│   ├── ocr_engine.py       # OCR + image enhancement
│   ├── annotation_engine.py # Annotation data + renderer + PDF export
│   ├── pdf_viewer.py       # Zoomable canvas + drawing
│   ├── annotation_toolbar.py # Tool palette sidebar
│   ├── student_list_panel.py # Scrollable student list
│   ├── ocr_panel.py        # OCR text display
│   └── dashboard_panel.py  # Statistics dashboard
├── exports/                # Exported PDFs & CSVs go here
├── ocr_cache/              # Cached OCR results
└── sample_pdfs/            # Demo PDFs
```

---

## 🎓 Typical Workflow

1. **Launch** → Welcome screen
2. **Start New Project** → Select folder with student PDFs
3. **Click a student** → Pages load in viewer
4. **Run OCR** → Text extracted, shown in bottom panel
5. **Select annotation tool** → Draw on page
6. **Set marks** → Use 📊 Marks tool
7. **Export** → Annotated PDF per student, or CSV for whole class
8. **Save Session** → Resume later

---

## 🛠 Requirements
- Python 3.10+
- Tesseract OCR (for offline OCR)
- Internet connection (only for Google Vision API)
- 4GB RAM recommended for large PDF batches

---

*Built with CustomTkinter · PyMuPDF · OpenCV · Pillow · pytesseract*
