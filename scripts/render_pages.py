"""Render printed pages of the book from the archive.org PDF.

  python scripts/render_pages.py 37 40

Writes, for each printed page N:
  pages/pNNNN.png              web image (~1600 px wide, 4 grey levels, ~200 KB)
  source/crops/pNNNN_cC_bB.png native-resolution column crops used for transcription
and updates data/pages.json with each page's column boundaries (fractions of width),
which the website uses to highlight the column an entry sits in.
"""
import json, os, sys
import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_ZOOM, CROP_ZOOM = 3.3, 6
QUANT = bytes(int(round(round(i / 85) * 85)) for i in range(256))  # 4 grey levels


def leaf_numbers():
    with open(os.path.join(ROOT, "source", "page_numbers.json"), encoding="utf-8") as f:
        pn = json.load(f)
    return {p["pageNumber"]: p["leafNum"] for p in pn["pages"] if p["pageNumber"]}


def column_bounds(pix):
    """Find the two vertical rules between the three columns, and the text block's outer edges."""
    w, h, s = pix.width, pix.height, pix.samples
    y0, y1 = int(h * 0.10), int(h * 0.92)
    longest, ink = [0] * w, [0] * w
    for x in range(w):
        run = best = count = gap = 0
        for y in range(y0, y1):
            if s[y * w + x] < 160:
                run += 1 + gap  # scanned rules are broken in places; bridge short gaps
                gap = 0
                count += 1
                if run > best:
                    best = run
            elif run and gap < 4:
                gap += 1
            else:
                run = gap = 0
        longest[x], ink[x] = best, count
    rules, x = [], 0
    while x < w:
        if longest[x] > (y1 - y0) * 0.25:
            start = x
            while x < w and longest[x] > (y1 - y0) * 0.25:
                x += 1
            rules.append((start + x) / 2)
        x += 1
    kept = []
    for r in rules:  # a smudge next to a rule can look like a second rule; rules are a column apart
        if 0.25 * w < r < 0.75 * w and (not kept or r - kept[-1] > 0.15 * w):
            kept.append(r)
    rules = kept[:2]
    if len(rules) == 2:
        # Columns are equal width, so the outer edges follow from the rules
        # (more robust than ink, which picks up specks in the scan margins).
        col = rules[1] - rules[0]
        left, right = max(0, rules[0] - col), min(w, rules[1] + col)
    else:
        inked = [x for x in range(int(w * 0.04), int(w * 0.96)) if ink[x] > (y1 - y0) * 0.05]
        left, right = (inked[0], inked[-1]) if inked else (0, w)
        third = (right - left) / 3
        rules = [left + third, left + 2 * third]
    edges = [left, rules[0], rules[1], right]
    return [[round(edges[i] / w, 4), round(edges[i + 1] / w, 4)] for i in range(3)]


def main(first, last):
    leaf_of = leaf_numbers()
    doc = pymupdf.open(os.path.join(ROOT, "book", "adictionaryengl00goog.pdf"))
    os.makedirs(os.path.join(ROOT, "pages"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "source", "crops"), exist_ok=True)
    meta_path = os.path.join(ROOT, "data", "pages.json")
    meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}

    for page_no in range(first, last + 1):
        leaf = leaf_of[str(page_no)]
        page = doc[leaf - 1]
        pix = page.get_pixmap(matrix=pymupdf.Matrix(WEB_ZOOM, WEB_ZOOM), colorspace=pymupdf.csGRAY)
        web = pymupdf.Pixmap(pymupdf.csGRAY, pix.width, pix.height, pix.samples.translate(QUANT), False)
        name = f"p{page_no:04d}.png"
        web.save(os.path.join(ROOT, "pages", name))
        meta[str(page_no)] = {"leaf": leaf, "image": f"pages/{name}", "width": pix.width,
                              "height": pix.height, "columns": column_bounds(pix)}

        W, H = page.rect.width, page.rect.height
        # Margins shift between recto and verso, so crop windows are wide and overlapping.
        for c, (fx0, fx1) in enumerate([(0.0, 0.43), (0.31, 0.71), (0.57, 1.0)]):
            for b in range(3):
                clip = pymupdf.Rect(W * fx0, H * (0.05 + b * 0.30), W * fx1, H * min(1.0, 0.39 + b * 0.30))
                sub = page.get_pixmap(matrix=pymupdf.Matrix(CROP_ZOOM, CROP_ZOOM), clip=clip, colorspace=pymupdf.csGRAY)
                sub.save(os.path.join(ROOT, "source", "crops", f"p{page_no:04d}_c{c + 1}_b{b + 1}.png"))
        print(page_no, "leaf", leaf, meta[str(page_no)]["columns"],
              os.path.getsize(os.path.join(ROOT, "pages", name)), "bytes")

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(dict(sorted(meta.items(), key=lambda kv: int(kv[0]))), f, indent=1)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
