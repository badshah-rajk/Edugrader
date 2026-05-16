"""
EduGrader — Annotation Engine
All annotation types: marks, comments, highlights, underlines,
correct/wrong stamps, arrows, free-draw, and text boxes.
Renders onto PIL images and exports to annotated PDFs.
"""
import uuid
import math
from dataclasses import dataclass, field, asdict
from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import io


# ── Data types ────────────────────────────────────────────────────────────────
ANNO_TYPES = [
    "stamp_correct",    # ✓ green stamp
    "stamp_wrong",      # ✗ red stamp
    "stamp_partial",    # ≈ orange stamp
    "highlight",        # semi-transparent rect
    "underline",        # coloured line under text
    "comment",          # speech-bubble text box
    "text_box",         # plain text label
    "arrow",            # arrow from A→B
    "free_draw",        # freehand strokes
    "marks_box",        # marks awarded bubble
]


@dataclass
class Annotation:
    id:          str   = field(default_factory=lambda: uuid.uuid4().hex[:8])
    type:        str   = "comment"
    x:           int   = 0
    y:           int   = 0
    x2:          int   = 0    # for rect/arrow end
    y2:          int   = 0
    text:        str   = ""
    color:       str   = "#F5A623"
    font_size:   int   = 18
    line_width:  int   = 3
    points:      list  = field(default_factory=list)   # for free_draw
    marks:       float = 0.0
    max_marks:   float = 0.0
    question_no: str   = ""
    visible:     bool  = True

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Annotation":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── Renderer ──────────────────────────────────────────────────────────────────
class AnnotationRenderer:
    """Draws annotations onto a PIL Image (for both display and export)."""

    STAMP_RADIUS = 22
    COMMENT_PAD  = 8

    def render_all(self, img: Image.Image,
                   annotations: list[Annotation],
                   scale: float = 1.0) -> Image.Image:
        """Return a new PIL image with all annotations drawn."""
        out  = img.copy().convert("RGBA")
        over = Image.new("RGBA", out.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(over)

        for ann in annotations:
            if not ann.visible:
                continue
            try:
                self._draw(draw, over, ann, scale)
            except Exception as e:
                print(f"[Anno] render error {ann.type}: {e}")

        result = Image.alpha_composite(out, over).convert("RGB")
        return result

    def _draw(self, draw: ImageDraw.Draw, over: Image.Image,
              ann: Annotation, scale: float):
        s  = scale
        x, y, x2, y2 = int(ann.x*s), int(ann.y*s), int(ann.x2*s), int(ann.y2*s)
        c  = ann.color
        lw = max(1, int(ann.line_width * s))

        if ann.type == "stamp_correct":
            self._stamp(draw, x, y, "✓", "#27AE60", s)

        elif ann.type == "stamp_wrong":
            self._stamp(draw, x, y, "✗", "#E74C3C", s)

        elif ann.type == "stamp_partial":
            self._stamp(draw, x, y, "≈", "#F5A623", s)

        elif ann.type == "highlight":
            rect_over = Image.new("RGBA", over.size, (0, 0, 0, 0))
            rd = ImageDraw.Draw(rect_over)
            rgb = _hex_to_rgb(c)
            rd.rectangle([x, y, x2, y2], fill=(*rgb, 80))
            over.paste(rect_over, mask=rect_over)

        elif ann.type == "underline":
            draw.line([(x, y), (x2, y2)], fill=c, width=lw)

        elif ann.type == "comment":
            self._comment_box(draw, x, y, ann.text, c, s)

        elif ann.type == "text_box":
            fs = max(10, int(ann.font_size * s))
            draw.text((x, y), ann.text, fill=c)

        elif ann.type == "arrow":
            self._arrow(draw, x, y, x2, y2, c, lw)

        elif ann.type == "free_draw" and ann.points:
            pts = [(int(px*s), int(py*s)) for px, py in ann.points]
            if len(pts) >= 2:
                draw.line(pts, fill=c, width=lw, joint="curve")

        elif ann.type == "marks_box":
            self._marks_box(draw, x, y, ann.marks, ann.max_marks,
                            ann.question_no, s)

    # ── Stamp ─────────────────────────────────────────────────────────────────
    def _stamp(self, draw, x, y, symbol, color, scale):
        r   = int(self.STAMP_RADIUS * scale)
        rgb = _hex_to_rgb(color)
        draw.ellipse([x-r, y-r, x+r, y+r], fill=(*rgb, 200), outline=(*rgb, 255), width=2)
        draw.text((x - r//2, y - r//2), symbol, fill="white")

    # ── Comment bubble ────────────────────────────────────────────────────────
    def _comment_box(self, draw, x, y, text, color, scale):
        if not text:
            return
        pad   = int(self.COMMENT_PAD * scale)
        lines = text.split("\n")
        max_w = max(len(l) for l in lines) * 7 + pad * 2
        h     = len(lines) * 16 + pad * 2

        rgb = _hex_to_rgb(color)
        # Box
        draw.rounded_rectangle([x, y, x+max_w, y+h],
                                radius=6, fill=(*rgb, 220), outline=(*rgb, 255), width=2)
        # Tail
        draw.polygon([(x+10, y+h), (x+4, y+h+12), (x+20, y+h)],
                     fill=(*rgb, 220))
        # Text
        draw.text((x+pad, y+pad), text, fill="white")

    # ── Arrow ─────────────────────────────────────────────────────────────────
    def _arrow(self, draw, x1, y1, x2, y2, color, width):
        draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
        # Arrowhead
        angle  = math.atan2(y2-y1, x2-x1)
        size   = width * 4
        for sign in (1, -1):
            ax = x2 - size * math.cos(angle - sign * math.pi/6)
            ay = y2 - size * math.sin(angle - sign * math.pi/6)
            draw.line([(x2, y2), (int(ax), int(ay))], fill=color, width=width)

    # ── Marks box ─────────────────────────────────────────────────────────────
    def _marks_box(self, draw, x, y, marks, max_marks, qno, scale):
        pad  = 6
        text = f"Q{qno}: {marks}/{max_marks}" if qno else f"{marks}/{max_marks}"
        tw   = len(text) * 8 + pad * 2
        th   = 24
        color = "#27AE60" if marks >= max_marks * 0.7 else (
                "#F5A623"  if marks >= max_marks * 0.4 else "#E74C3C")
        rgb  = _hex_to_rgb(color)
        draw.rounded_rectangle([x, y, x+tw, y+th],
                                radius=4, fill=(*rgb, 230), outline=(*rgb, 255))
        draw.text((x+pad, y+4), text, fill="white")


# ── Export annotated PDF ──────────────────────────────────────────────────────
def export_annotated_pdf(page_images: list[Image.Image],
                         annotations_by_page: dict,
                         output_path: str,
                         renderer: AnnotationRenderer = None):
    """
    Render annotations on each page and save as a new PDF.
    page_images: list of PIL Images (one per page)
    annotations_by_page: {page_idx: [Annotation, ...]}
    """
    if renderer is None:
        renderer = AnnotationRenderer()

    rendered = []
    for i, img in enumerate(page_images):
        annos = [Annotation.from_dict(a) if isinstance(a, dict) else a
                 for a in annotations_by_page.get(i, [])]
        rendered_img = renderer.render_all(img, annos)
        rendered.append(rendered_img.convert("RGB"))

    if rendered:
        rendered[0].save(
            output_path,
            save_all=True,
            append_images=rendered[1:],
            format="PDF",
        )


# ── helpers ───────────────────────────────────────────────────────────────────
def _hex_to_rgb(hex_color: str) -> tuple:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c*2 for c in h)
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
