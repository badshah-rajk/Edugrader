"""
EduGrader — OCR Engine
Uses Google Cloud Vision FREE tier (1000 pages/month) as primary.
Falls back to Tesseract + OpenCV blur-recovery pipeline.
"""
import os
import base64
import json
import re
import tempfile
import threading
from pathlib import Path
import requests
import cv2
import numpy as np

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

# ─────────────────────────────────────────────────────────────────────────────
GOOGLE_VISION_URL = (
    "https://vision.googleapis.com/v1/images:annotate?key={api_key}"
)
# ─────────────────────────────────────────────────────────────────────────────


def enhance_image_for_ocr(img_array: np.ndarray) -> np.ndarray:
    """
    Multi-step preprocessing for blurred / low-quality answer-copy scans.
    Returns an enhanced grayscale uint8 image ready for OCR.
    """
    # Convert to grayscale if colour
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
    else:
        gray = img_array.copy()

    # ── 1. Deblur via unsharp-mask ───────────────────────────────────────────
    blur   = cv2.GaussianBlur(gray, (0, 0), 3)
    sharp  = cv2.addWeighted(gray, 1.5, blur, -0.5, 0)

    # ── 2. Estimate noise level ──────────────────────────────────────────────
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()

    # ── 3. Adaptive denoising based on blur score ────────────────────────────
    if lap_var < 100:          # very blurry
        denoised = cv2.fastNlMeansDenoising(sharp, h=15, templateWindowSize=7,
                                            searchWindowSize=21)
    elif lap_var < 500:        # moderately blurry
        denoised = cv2.fastNlMeansDenoising(sharp, h=7)
    else:                      # reasonably sharp
        denoised = sharp

    # ── 4. Contrast-Limited Adaptive Histogram Equalisation (CLAHE) ──────────
    clahe   = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    equaled = clahe.apply(denoised)

    # ── 5. Adaptive binarisation (handles uneven lighting) ───────────────────
    binary = cv2.adaptiveThreshold(
        equaled, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 10
    )

    # ── 6. Morphological cleanup (remove salt-and-pepper) ────────────────────
    kernel  = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=1)

    # ── 7. Deskew ────────────────────────────────────────────────────────────
    cleaned = _deskew(cleaned)

    return cleaned


def _deskew(img: np.ndarray) -> np.ndarray:
    """Correct small rotational skew in scanned pages."""
    coords  = np.column_stack(np.where(img < 128))   # dark pixels
    if len(coords) < 10:
        return img
    angle   = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    if abs(angle) < 0.5:          # negligible skew
        return img
    h, w    = img.shape
    centre  = (w // 2, h // 2)
    M       = cv2.getRotationMatrix2D(centre, angle, 1.0)
    rotated = cv2.warpAffine(img, M, (w, h),
                             flags=cv2.INTER_CUBIC,
                             borderMode=cv2.BORDER_REPLICATE)
    return rotated


# ─────────────────────────────────────────────────────────────────────────────
class OCREngine:
    """
    Wrapper that chooses the best available OCR backend.

    Priority:
      1. Google Cloud Vision API (free tier, 1 000 req/month) — best accuracy
      2. Tesseract + OpenCV preprocessing                     — always free
    """

    def __init__(self, google_api_key: str = ""):
        self.google_api_key   = google_api_key.strip()
        self._lock            = threading.Lock()
        self._google_call_cnt = 0   # rough counter this session

    # ── public ────────────────────────────────────────────────────────────────
    def process_image(self, img_array: np.ndarray,
                      use_google: bool = True) -> dict:
        """
        OCR a single image (NumPy BGR or gray array).

        Returns:
            {
              "text":       str,          # full extracted text
              "blocks":     list[dict],   # [{text, bbox, confidence}]
              "backend":    str,          # "google" | "tesseract"
              "blur_score": float,        # Laplacian variance (quality metric)
              "enhanced":   bool,
            }
        """
        blur_score = float(cv2.Laplacian(
            cv2.cvtColor(img_array, cv2.COLOR_BGR2GRAY)
            if len(img_array.shape) == 3 else img_array,
            cv2.CV_64F
        ).var())

        enhanced_img = enhance_image_for_ocr(img_array)
        enhanced     = True

        if use_google and self.google_api_key:
            try:
                result = self._google_vision(enhanced_img)
                result["blur_score"] = blur_score
                result["enhanced"]   = enhanced
                return result
            except Exception as exc:
                print(f"[OCR] Google Vision failed ({exc}), falling back to Tesseract")

        # Tesseract fallback
        return self._tesseract(enhanced_img, blur_score, enhanced)

    def process_image_path(self, path: str, use_google: bool = True) -> dict:
        img = cv2.imread(path)
        if img is None:
            return {"text": "", "blocks": [], "backend": "error",
                    "blur_score": 0, "enhanced": False}
        return self.process_image(img, use_google=use_google)

    # ── Google Vision ─────────────────────────────────────────────────────────
    def _google_vision(self, gray_img: np.ndarray) -> dict:
        _, buf  = cv2.imencode(".png", gray_img)
        b64     = base64.b64encode(buf.tobytes()).decode()

        payload = {
            "requests": [{
                "image":   {"content": b64},
                "features": [
                    {"type": "DOCUMENT_TEXT_DETECTION", "maxResults": 1}
                ]
            }]
        }
        url  = GOOGLE_VISION_URL.format(api_key=self.google_api_key)
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        ann  = data["responses"][0]
        if "error" in ann:
            raise RuntimeError(ann["error"].get("message", "Vision API error"))

        full_text = ann.get("fullTextAnnotation", {}).get("text", "")
        blocks    = []
        for page in ann.get("fullTextAnnotation", {}).get("pages", []):
            for block in page.get("blocks", []):
                for para in block.get("paragraphs", []):
                    words  = []
                    conf   = []
                    verts  = para.get("boundingBox", {}).get("vertices", [])
                    for word in para.get("words", []):
                        wtext = "".join(
                            s.get("text", "") for s in word.get("symbols", [])
                        )
                        words.append(wtext)
                        conf.append(word.get("confidence", 0.9))
                    if words:
                        bbox = _verts_to_bbox(verts)
                        blocks.append({
                            "text":       " ".join(words),
                            "bbox":       bbox,
                            "confidence": round(sum(conf)/len(conf)*100, 1)
                        })

        with self._lock:
            self._google_call_cnt += 1

        return {
            "text":    full_text,
            "blocks":  blocks,
            "backend": "google"
        }

    # ── Tesseract ─────────────────────────────────────────────────────────────
    def _tesseract(self, gray_img: np.ndarray,
                   blur_score: float, enhanced: bool) -> dict:
        if not TESSERACT_AVAILABLE:
            return {
                "text":       "⚠ Tesseract not installed. Install pytesseract + Tesseract-OCR.",
                "blocks":     [],
                "backend":    "none",
                "blur_score": blur_score,
                "enhanced":   enhanced,
            }

        # Choose PSM based on blur quality
        psm = "6" if blur_score > 200 else "4"
        cfg = f"--oem 3 --psm {psm} -l eng"

        full_text = pytesseract.image_to_string(gray_img, config=cfg)

        raw_data  = pytesseract.image_to_data(
            gray_img, config=cfg,
            output_type=pytesseract.Output.DICT
        )
        blocks = []
        n = len(raw_data["text"])
        for i in range(n):
            txt  = raw_data["text"][i].strip()
            conf = int(raw_data["conf"][i])
            if txt and conf > 10:
                x = raw_data["left"][i]
                y = raw_data["top"][i]
                w = raw_data["width"][i]
                h = raw_data["height"][i]
                blocks.append({
                    "text":       txt,
                    "bbox":       (x, y, x + w, y + h),
                    "confidence": conf,
                })

        return {
            "text":       full_text,
            "blocks":     blocks,
            "backend":    "tesseract",
            "blur_score": blur_score,
            "enhanced":   enhanced,
        }


# ── helpers ───────────────────────────────────────────────────────────────────
def _verts_to_bbox(verts):
    if not verts:
        return (0, 0, 0, 0)
    xs = [v.get("x", 0) for v in verts]
    ys = [v.get("y", 0) for v in verts]
    return (min(xs), min(ys), max(xs), max(ys))
