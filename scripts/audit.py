"""Consistency checks over the built data. Run after build_data.py:  python scripts/audit.py"""
import json, os, re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FLAG = "Recorded as a patronymic"
d = json.load(open(os.path.join(ROOT, "data", "entries.json"), encoding="utf-8"))
H, R = d["headwords"], d["records"]


def show(title, rows, fmt=lambda r: f"p{r['page']} c{r['column']} | {r['first_name']} | {r['last_name']} | {r['notes'][:80]}"):
    print(f"{title}: {len(rows)}")
    for r in rows[:60]:
        print("   ", fmt(r))


show("Rows on a later page than their headword starts", [r for r in R if r["page"] != H[r["h"]]["page"]],
     lambda r: f"p{r['page']} (headword p{H[r['h']]['page']}) {r['first_name']} {r['last_name']}")

parents = [r for r in R if FLAG in r["notes"]]
show("Patronymic parent rows", parents)
pkeys = {(r["page"], r["record_text"]) for r in parents}
children = [r for r in R if re.match(r"(fil\.?|filius|filia|son of|relicta)\s", r["last_name"])]
show("Patronymic children with no parent row", [r for r in children if (r["page"], r["record_text"]) not in pkeys])

show("Other (unknown) surnames", [r for r in R if r["last_name"] == "(unknown)" and FLAG not in r["notes"]])
show("Gendered parent wording", [r for r in R if re.search(r"\b(Father|Mother) of\b", r["notes"])])
show("Dated after 1650", [r for r in R if (r["year_from"] or 0) > 1650], lambda r: f"{r['date']}")
