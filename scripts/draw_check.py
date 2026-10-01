"""Draw each record's located line on its page scan, to check locate_lines.py by eye.

  python scripts/draw_check.py 45      -> source/check_p0045.png (green = matched, orange = estimated)
"""
import json, os, sys
import pymupdf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pos = json.load(open(os.path.join(ROOT, "data", "line_positions.json"), encoding="utf-8"))
pages = json.load(open(os.path.join(ROOT, "data", "pages.json"), encoding="utf-8"))
for p in sys.argv[1:]:
    m = pages[str(int(p))]
    W, H = m["width"], m["height"]
    doc = pymupdf.open()
    pg = doc.new_page(width=W, height=H)
    pg.insert_image(pg.rect, filename=os.path.join(ROOT, m["image"]))
    for r in json.load(open(os.path.join(ROOT, "data", "raw", f"p{int(p):04d}.json"), encoding="utf-8")):
        k = "|".join([str(r["page"]), r["headword"], r["first_name"], r["last_name"], r["record_text"]])
        if k not in pos:
            continue
        t, b, exact = pos[k]
        x0, x1 = m["columns"][r["column"] - 1]
        pg.draw_rect(pymupdf.Rect(x0 * W, t * H, x1 * W, b * H), color=(0, .6, 0) if exact else (.9, .4, 0), width=2)
        pg.insert_text((x1 * W - 80, t * H + 10), (r["last_name"] or r["headword"])[:14], fontsize=10, color=(.85, 0, 0))
    pg.get_pixmap(matrix=pymupdf.Matrix(.9, .9)).save(os.path.join(ROOT, "source", f"check_p{int(p):04d}.png"))
