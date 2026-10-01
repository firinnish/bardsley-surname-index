"""Find where each transcribed record sits on its page scan, so the website can point at the exact line.

The archive.org OCR text is too garbled to use as data, but its line boxes are accurate and its text is
close enough to fuzzy-match against our transcriptions. Records are matched in column order.

  python scripts/locate_lines.py 37 40
Downloads the hOCR for those pages (by byte range) and writes data/line_positions.json.
"""
import gzip, html, json, os, re, sys, urllib.request
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ITEM = "https://archive.org/download/adictionaryengl00goog/"
BBOX = re.compile(r"bbox (\d+) (\d+) (\d+) (\d+)")


def fetch_hocr(leaves):
    idx_path = os.path.join(ROOT, "source", "hocr_pageindex.json.gz")
    if not os.path.exists(idx_path):
        urllib.request.urlretrieve(ITEM + "adictionaryengl00goog_hocr_pageindex.json.gz", idx_path)
    idx = json.loads(gzip.open(idx_path).read())
    out = {}
    for leaf in leaves:
        cache = os.path.join(ROOT, "source", "hocr", f"leaf{leaf:04d}.html")
        if not os.path.exists(cache):
            os.makedirs(os.path.dirname(cache), exist_ok=True)
            start, end = idx[leaf - 1][2], idx[leaf - 1][3]
            req = urllib.request.Request(ITEM + "adictionaryengl00goog_hocr.html",
                                         headers={"Range": f"bytes={start}-{end - 1}", "User-Agent": "Mozilla/5.0"})
            with open(cache, "wb") as f:
                f.write(urllib.request.urlopen(req).read())
        out[leaf] = open(cache, encoding="utf-8", errors="replace").read()
    return out


def ocr_lines(hocr):
    """[(x0, y0, x1, y1, text)] as fractions of the page, in reading order."""
    page = BBOX.search(hocr)
    W, H = int(page.group(3)), int(page.group(4))
    lines = []
    for m in re.finditer(r'<span class="ocr_line"[^>]*title="([^"]*)"[^>]*>(.*?)</span>\s*</span>', hocr, re.S):
        x0, y0, x1, y1 = map(int, BBOX.search(m.group(1)).groups())
        words = re.findall(r'<span class="ocrx_word"[^>]*>(.*?)</span>', m.group(2), re.S)
        text = html.unescape(" ".join(re.sub(r"<[^>]+>", "", w) for w in words))
        lines.append((x0 / W, y0 / H, x1 / W, y1 / H, text))
    return lines


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()


def score(target, text):
    a, b = norm(target), norm(text)
    if not a or not b:
        return 0
    return SequenceMatcher(None, a[: len(b) + 8], b).ratio()


def key(r):
    return "|".join([str(r["page"]), r["headword"], r["first_name"], r["last_name"], r["record_text"]])


def main(first, last):
    pages = json.load(open(os.path.join(ROOT, "data", "pages.json"), encoding="utf-8"))
    hocr = fetch_hocr([pages[str(p)]["leaf"] for p in range(first, last + 1)])
    positions, found, approx, total = {}, 0, 0, 0
    for p in range(first, last + 1):
        meta = pages[str(p)]
        rows = json.load(open(os.path.join(ROOT, "data", "raw", f"p{p:04d}.json"), encoding="utf-8"))
        lines = ocr_lines(hocr[meta["leaf"]])
        for c, (cx0, cx1) in enumerate(meta["columns"], 1):
            in_col = sorted((l for l in lines if cx0 - 0.01 <= (l[0] + l[2]) / 2 <= cx1 + 0.01), key=lambda l: l[1])
            col = [l for l in in_col if l[4].strip()]
            col_rows = [r for r in rows if r["column"] == c]
            spans = [None] * len(col_rows)  # (top, bottom) where the OCR text matched
            pos = 0
            for k, r in enumerate(col_rows):
                total += 1
                # Several names come from one citation line: they share its position.
                if k and r["record_text"] and r["record_text"] == col_rows[k - 1]["record_text"]:
                    spans[k] = spans[k - 1]
                    found += bool(spans[k])
                    continue
                target = r["record_text"] or r["headword"]
                best, best_i = 0, None
                for i in range(pos, min(len(col), pos + 30)):
                    s = score(target, col[i][4])
                    # Try joining with the next line too, but only if it is physically the next line.
                    if i + 1 < len(col) and col[i + 1][1] - col[i][3] < 0.006:
                        s = max(s, score(target, col[i][4] + " " + col[i + 1][4]) - 0.05)
                    if s > best:
                        best, best_i = s, i
                if best_i is not None and best >= 0.55:
                    found += 1
                    # A column line holds about 46 characters; cover as many line boxes as the record needs.
                    first = in_col.index(col[best_i])
                    n_lines = max(1, -(-len(target) // 46)) if r["record_text"] else 1
                    run = [in_col[first]]
                    for l in in_col[first + 1:first + n_lines]:
                        if l[1] - run[-1][3] > 0.006:
                            break
                        run.append(l)
                    spans[k] = (run[0][1], run[-1][3])
                    pos = best_i + 1
            # The OCR lost the text of many small-print lines (their boxes survive, empty). Place an
            # unmatched row between its matched neighbours, snapped to one of those line boxes, but only
            # across short gaps: a long gap usually hides a headword paragraph and the guess would be poor.
            anchors = [k for k, s in enumerate(spans) if s]
            for k, r in enumerate(col_rows):
                if spans[k]:
                    positions[key(r)] = [round(spans[k][0], 4), round(spans[k][1], 4), 1]
                    continue
                before = [a for a in anchors if a < k]
                after = [a for a in anchors if a > k]
                if not before or not after:
                    continue
                a, b = before[-1], after[0]
                y0, y1 = spans[a][1], spans[b][0]
                step = (y1 - y0) / (b - a)
                if b - a > 6 or not 0.006 <= step <= 0.04:
                    continue
                guess = y0 + step * (k - a - 1)
                boxes = [l for l in in_col if y0 - 0.004 <= l[1] < y1]
                if boxes:
                    near = min(boxes, key=lambda l: abs(l[1] - guess))
                    guess, bottom = near[1], near[3]
                else:
                    bottom = guess + 0.012
                positions[key(r)] = [round(guess, 4), round(bottom, 4), 0]
                approx += 1
    with open(os.path.join(ROOT, "data", "line_positions.json"), "w", encoding="utf-8") as f:
        json.dump(positions, f, ensure_ascii=False, indent=0)
    print(f"{total} rows: {found} matched to an OCR line, {approx} placed between neighbours, "
          f"{total - found - approx} column only")


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
