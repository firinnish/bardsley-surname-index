"""Apply readings confirmed by a person looking at the scan, and mark those rows human_checked.

Each fix replaces text in record_text/first_name/last_name/notes on every row of the matched citation
line, sets confidence to high and human_checked to true. Rows marked human_checked must never be
changed by transcription passes. Add new confirmations to CHECKS and re-run (it is idempotent).
  python scripts/apply_human_checks.py
"""
import glob, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (page, text that identifies the citation line, {printed/wrong: confirmed}, notes for named rows)
CHECKS = [
    (39, "James Galliere", {"Varcilles?": "Vareilles", "Varcilles": "Vareilles"}, {
        "Faith": "Marriage allegation (licence) with James Galliere Vareilles",
        "James Galliere": "Marriage allegation (licence) with Faith Aikeroyd"}),
    (43, "Eton and Margaret Aleblaster", {"Kobeit": "Robert"}, {
        "Margaret": "Licence to marry Robert Eton",
        "Robert": "Licence to marry Margaret Aleblaster"}),
    (45, "Aldred, vicar of Rushall", {"Henrv": "Henry"}, {"Henry": "Vicar of Rushall"}),
    (46, "Thomas Alfra", {"Alfrav": "Alfray"}, {"Thomas": ""}),
    (49, "Johu le Aleman", {}, {"Johu": "First name printed 'Johu' (confirmed by eye)"}),
]

marked = 0
for page, key, fixes, notes in CHECKS:
    path = os.path.join(ROOT, "data", "raw", f"p{page:04d}.json")
    rows = json.load(open(path, encoding="utf-8"))
    for r in rows:
        fixed = r["record_text"]
        for old, new in fixes.items():
            fixed = fixed.replace(old, new)
        if key not in fixed:
            continue
        for old, new in fixes.items():
            for f in ("record_text", "first_name", "last_name"):
                r[f] = r[f].replace(old, new)
        if r["first_name"] in notes:
            r["notes"] = notes[r["first_name"]]
        r["confidence"] = "high"
        r["human_checked"] = True
        marked += 1
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
print("rows marked human_checked:", marked)
