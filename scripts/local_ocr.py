"""OCR our own high-resolution page scans (from the book PDF) to get every printed line and its position.

The archive.org OCR (2008, low-resolution images) drops and garbles too many lines to place records reliably.
This runs RapidOCR (pip install rapidocr-onnxruntime) locally on each column.

  python scripts/local_ocr.py 37 50
Writes source/ocr/pNNNN.json: [{"column", "x0", "y0", "x1", "y1", "text", "conf"}] with coordinates as page fractions.
"""
import json, os, sys
import numpy as np
import pymupdf
from rapidocr_onnxruntime import RapidOCR

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZOOM = 5          # ~3000 px per page width: small citation type comes out clean
BANDS = 4         # columns are OCR'd in overlapping vertical bands
OVERLAP = 0.02

engine = RapidOCR()
pages = json.load(open(os.path.join(ROOT, "data", "pages.json"), encoding="utf-8"))
doc = pymupdf.open(os.path.join(ROOT, "book", "adictionaryengl00goog.pdf"))
os.makedirs(os.path.join(ROOT, "source", "ocr"), exist_ok=True)


def ocr_region(page, fx0, fy0, fx1, fy1):
    W, H = page.rect.width, page.rect.height
    clip = pymupdf.Rect(W * fx0, H * fy0, W * fx1, H * fy1)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip, colorspace=pymupdf.csRGB)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
    result, _ = engine(img, use_cls=False)  # no text in the book is rotated; the classifier misfires
    out = []
    for box, text, conf in result or []:
        xs, ys = [p[0] for p in box], [p[1] for p in box]
        out.append({
            "x0": fx0 + min(xs) / pix.width * (fx1 - fx0), "x1": fx0 + max(xs) / pix.width * (fx1 - fx0),
            "y0": fy0 + min(ys) / pix.height * (fy1 - fy0), "y1": fy0 + max(ys) / pix.height * (fy1 - fy0),
            "text": text, "conf": round(float(conf), 3),
        })
    return out


def merge_rows(found):
    """Join pieces of one printed line (the detector sometimes splits a line at wide word gaps).
    Pieces that overlap vertically by more than half their height are the same line; where two
    pieces also overlap horizontally, keep the more confident one (drops misreads of the same ink)."""
    rows = []
    for l in sorted(found, key=lambda l: l["y0"]):
        h = l["y1"] - l["y0"]
        row = next((r for r in rows if min(r[0]["y1"], l["y1"]) - max(r[0]["y0"], l["y0"]) > 0.5 * min(h, r[0]["y1"] - r[0]["y0"])), None)
        if row is None:
            rows.append([l])
            continue
        clash = next((p for p in row if min(p["x1"], l["x1"]) - max(p["x0"], l["x0"]) > 0.3 * min(p["x1"] - p["x0"], l["x1"] - l["x0"])), None)
        if clash:
            if l["conf"] > clash["conf"]:
                row[row.index(clash)] = l
        else:
            row.append(l)
    merged = []
    for row in rows:
        row.sort(key=lambda p: p["x0"])
        merged.append({"x0": min(p["x0"] for p in row), "x1": max(p["x1"] for p in row),
                       "y0": min(p["y0"] for p in row), "y1": max(p["y1"] for p in row),
                       "text": " ".join(p["text"] for p in row), "conf": min(p["conf"] for p in row)})
    return merged


def main(first, last):
    for p in range(first, last + 1):
        meta = pages[str(p)]
        page = doc[meta["leaf"] - 1]
        lines = []
        for c, (x0, x1) in enumerate(meta["columns"], 1):
            found = []
            for b in range(BANDS):
                y0 = max(0.0, 0.08 + b * (0.86 / BANDS) - OVERLAP)
                y1 = min(1.0, 0.08 + (b + 1) * (0.86 / BANDS) + OVERLAP)
                found += ocr_region(page, max(0, x0 - 0.01), y0, min(1, x1 + 0.005), y1)
            # Drop duplicates from band overlaps: same line found twice has nearly the same top.
            found.sort(key=lambda l: (l["y0"], l["x0"]))
            kept = []
            for l in found:
                if kept and abs(l["y0"] - kept[-1]["y0"]) < 0.004 and abs(l["x0"] - kept[-1]["x0"]) < 0.02:
                    if len(l["text"]) > len(kept[-1]["text"]):
                        kept[-1] = l
                    continue
                kept.append(l)
            lines += [{"column": c, **{k: (round(v, 5) if isinstance(v, float) else v) for k, v in l.items()}}
                      for l in merge_rows(kept)]
        with open(os.path.join(ROOT, "source", "ocr", f"p{p:04d}.json"), "w", encoding="utf-8") as f:
            json.dump(lines, f, ensure_ascii=False, indent=0)
        print(p, len(lines), "lines")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
