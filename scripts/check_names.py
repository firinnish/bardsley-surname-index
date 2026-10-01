"""List rows whose name is not spelled exactly as in the printed citation text.

Names must keep the book's spelling (no modernising). Editorial expansions in [square brackets],
"(unknown)", and a trailing "?" for an uncertain reading are allowed.
  python scripts/check_names.py
"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"sir", "fil", "son", "of", "de", "le", "la", "del", "the", "bart"}


def words(name):
    name = re.sub(r"\[[^\]]*\]", "", name).replace("(unknown)", "")
    return [w for w in re.findall(r"[^\W\d_]+(?:'[^\W\d_]+)?", name) if w.lower() not in SKIP]


for path in sorted(glob.glob(os.path.join(ROOT, "data", "raw", "p*.json"))):
    for i, r in enumerate(json.load(open(path, encoding="utf-8"))):
        text = r["record_text"]
        if not text or r.get("human_checked"):  # a person confirmed it: don't second-guess
            continue
        missing = [w for w in words(r["first_name"]) + words(r["last_name"]) if w not in text]
        if missing:
            print(f"{os.path.basename(path)[1:5]} {i:3} | {r['first_name']} | {r['last_name']} | missing {missing} | {text[:90]}")
