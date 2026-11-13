"""Give every patronymic parent its own row, consistently across all pages.

Covers Latin "fil."/"filius"/"filia", "son of", "le fiz", and Welsh "ap"/"ab" (incl. "ap-Evan"). For a row like
"Richard ap Edward" with no existing row for Edward from the same citation, adds
first_name "Edward", last_name "(unknown)", notes "Parent of Richard ap Edward. Recorded as a patronymic - ...".
Only simple single-parent forms are handled; pedigree chains ("ap Madoc ap Tudir") are left to the transcriber.
Idempotent:  python scripts/add_patronymic_parents.py
"""
import glob, json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAG = "Recorded as a patronymic - may not necessarily be nominative form"
PAT = re.compile(r"^(?:fil\.?|filius|filia|son of|le fiz|ap|ab)[\s-]+([A-Z][^\s,()?\[\]]*\??)$")

added = 0
for path in sorted(glob.glob(os.path.join(ROOT, "data", "raw", "p*.json"))):
    rows = json.load(open(path, encoding="utf-8"))
    out = []
    for i, r in enumerate(rows):
        out.append(r)
        m = PAT.match(r["last_name"].strip())
        if not m or not r["first_name"] or r.get("human_checked"):
            continue
        parent = m.group(1)
        same = [x for x in rows if x["record_text"] == r["record_text"]]
        if any(x["first_name"] == parent and x is not r for x in same):
            continue
        out.append(dict(r, first_name=parent, last_name="(unknown)",
                        notes=f"Parent of {r['first_name']} {r['last_name']}. {FLAG}", human_checked=False))
        added += 1
        print(os.path.basename(path), r["first_name"], r["last_name"], "->", parent)
    if len(out) != len(rows):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
print("parent rows added:", added)
