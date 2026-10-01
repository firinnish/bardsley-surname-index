"""Compare each transcribed name and year with what our local OCR independently reads on that line.

Two independent readings agreeing is strong evidence; disagreements are where a person should look.
Run after local_ocr.py and locate_lines.py:
  python scripts/crosscheck.py           -> prints a summary, writes data/review.csv
Rows marked human_checked are skipped.
"""
import csv, glob, json, os, re
from difflib import SequenceMatcher

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"sir", "fil", "son", "of", "de", "le", "la", "del", "the", "bart", "atte", "in", "et", "uxor", "ejus", "relicta"}
pos = json.load(open(os.path.join(ROOT, "data", "line_positions.json"), encoding="utf-8"))


def name_words(name):
    name = re.sub(r"\[[^\]]*\]|\(unknown\)|\?", "", name)
    return [w for w in re.findall(r"[^\W\d_]+", name) if w.lower() not in SKIP and len(w) > 1]


def years(text):
    # OCR often reads old-style figures as letters: 18o2, 161o, 157!
    t = text.translate(str.maketrans({"o": "0", "O": "0", "l": "1", "I": "1", "!": "1", "z": "2", "S": "5"}))
    return set(re.findall(r"\b1[0-9]{3}\b", t))


CONFUSIONS = [("rn", "m"), ("vv", "w"), ("li", "h"), ("c", "e"), ("h", "b"), ("i", "l"), ("I", "l"), ("1", "l"),
              ("f", "l"), ("u", "n"), ("o", "a"), ("y", "v"), ("é", "e"), ("j", "i"), ("J", "I"), ("K", "R")]


def blur(s):
    """Collapse letters OCR commonly confuses, so only real differences remain."""
    s = s.lower()
    for a, b in CONFUSIONS:
        s = s.replace(a.lower(), b.lower())
    return s


def closest(word, text):
    cands = re.findall(r"[^\W\d_]+", text)
    best = max(cands, key=lambda c: SequenceMatcher(None, word.lower(), c.lower()).ratio(), default="")
    return best, SequenceMatcher(None, word.lower(), best.lower()).ratio() if best else 0


issues, checked, unplaced = [], 0, 0
for path in sorted(glob.glob(os.path.join(ROOT, "data", "raw", "p*.json"))):
    page = int(os.path.basename(path)[1:5])
    ocr_path = os.path.join(ROOT, "source", "ocr", f"p{page:04d}.json")
    if not os.path.exists(ocr_path):
        continue
    ocr = json.load(open(ocr_path, encoding="utf-8"))
    for r in json.load(open(path, encoding="utf-8")):
        if not r["record_text"] or r.get("human_checked"):
            continue
        k = "|".join([str(r["page"]), r["headword"], r["first_name"], r["last_name"], r["record_text"]])
        if k not in pos or not pos[k][2]:
            unplaced += 1  # only compare against lines we matched confidently
            continue
        top, bottom, _ = pos[k]
        # Only the record's own lines: their tops fall inside its span.
        text = " ".join(l["text"] for l in ocr if l["column"] == r["column"] and top - 0.003 <= l["y0"] < bottom - 0.003)
        checked += 1
        name = f"{r['first_name']} {r['last_name']}".strip()
        for w in name_words(r["first_name"]) + name_words(r["last_name"]):
            if w not in r["record_text"]:
                continue  # name implied or expanded, not printed on this line
            if blur(w) in blur(text):
                continue
            best, score = closest(w, text)
            # The OCR read a similar but genuinely different word (not just a letter it often confuses).
            if score >= 0.6 and len(best) >= len(w) - 1 and blur(best) != blur(w):
                issues.append((page, r["column"], name, "name", w, best, r["record_text"]))
        printed = years(r["record_text"])  # skip "ibid." lines whose year is inherited, not printed
        for y in printed - years(text):
            if years(text):
                issues.append((page, r["column"], name, "year", y, " ".join(sorted(years(text))), r["record_text"]))

with open(os.path.join(ROOT, "data", "review.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f)
    w.writerow(["page", "column", "name", "field", "transcribed", "local OCR reads", "record_text"])
    w.writerows(issues)
print(f"compared {checked} rows against local OCR ({unplaced} not placed confidently, skipped); "
      f"{len(issues)} disagreements -> data/review.csv")
