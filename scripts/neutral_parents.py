"""Make parent/child relationships gender-neutral unless the print states the gender.

"Father of"/"Mother of" -> "Parent of" unless the citation says father/mother/pater/mater.
For patronymics ("fil." can be filius or filia) "son of"/"daughter of" -> "child of".
  python scripts/neutral_parents.py
"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATED = re.compile(r"\b(father|mother|pater|mater)\b", re.I)
changed = 0
for path in sorted(glob.glob(os.path.join(ROOT, "data", "raw", "p*.json"))):
    rows = json.load(open(path, encoding="utf-8"))
    for r in rows:
        before = r["notes"]
        if not STATED.search(r["record_text"]):
            r["notes"] = re.sub(r"\b(Father|Mother) of\b", "Parent of", r["notes"])
            r["notes"] = re.sub(r"\b(father|mother) of\b", "parent of", r["notes"])
        if r["last_name"].startswith("fil"):
            r["notes"] = re.sub(r"\b(son|daughter) of\b", "child of", r["notes"])
            r["notes"] = re.sub(r"\b(Son|Daughter) of\b", "Child of", r["notes"])
        changed += r["notes"] != before
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
print("notes changed:", changed)
