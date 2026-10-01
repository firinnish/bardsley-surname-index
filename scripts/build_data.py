"""Merge per-page transcriptions (data/raw/pNNNN.json) into data/entries.json and data/entries.csv.

Adds: id, year_from/year_to (regnal years converted), normalized location, archive.org link.
Run from the project root:  python scripts/build_data.py
"""
import csv, glob, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
ARCHIVE = "https://archive.org/details/adictionaryengl00goog/page/{page}/mode/1up"

FIELDS = ["page", "column", "headword", "origin", "meaning", "author_comment", "modern_distribution",
          "first_name", "last_name", "date", "event", "place", "county", "notes",
          "source_abbrev", "source", "record_text", "confidence"]

# Reign: (accession year, accession month, last year of reign)
REIGNS = {
    "Will. I": (1066, 12, 1087), "Will. II": (1087, 9, 1100), "Hen. I": (1100, 8, 1135),
    "Steph.": (1135, 12, 1154), "Hen. II": (1154, 12, 1189), "Ric. I": (1189, 9, 1199),
    "John": (1199, 5, 1216), "Hen. III": (1216, 10, 1272), "Edw. I": (1272, 11, 1307),
    "Edw. II": (1307, 7, 1327), "Edw. III": (1327, 1, 1377), "Ric. II": (1377, 6, 1399),
    "Hen. IV": (1399, 9, 1413), "Hen. V": (1413, 3, 1422), "Hen. VI": (1422, 9, 1461),
    "Edw. IV": (1461, 3, 1483), "Ric. III": (1483, 6, 1485), "Hen. VII": (1485, 8, 1509),
    "Hen. VIII": (1509, 4, 1547), "Edw. VI": (1547, 1, 1553), "Mary": (1553, 7, 1558),
    "Eliz.": (1558, 11, 1603), "Jas. I": (1603, 3, 1625), "Chas. I": (1625, 3, 1649),
    "Chas. II": (1649, 1, 1685), "Jas. II": (1685, 2, 1688), "Will. III": (1689, 2, 1702),
    "Anne": (1702, 3, 1714), "Geo. I": (1714, 8, 1727), "Geo. II": (1727, 6, 1760),
    "Geo. III": (1760, 10, 1820),
}
REIGN_RE = re.compile(
    r"(?:(\d{1,2})(?:\s*-\s*(\d{1,2}))?\s+)?"
    r"(William|Will|Wm|Henry|Hen|Edward|Edw|Richard|Ric|Stephen|Steph|John|Eliz|Elizabeth|James|Jas|Charles|Chas|Mary|Anne|George|Geo)\b\.?"
    r"(?:\s+(VIII|VII|VI|IV|V|III|II|I)\b)?")
FULL_NAMES = {"William": "Will", "Wm": "Will", "Henry": "Hen", "Edward": "Edw", "Richard": "Ric", "Stephen": "Steph",
              "Elizabeth": "Eliz", "James": "Jas", "Charles": "Chas", "George": "Geo"}
ROMAN = {"xi": 11, "xii": 12, "xiii": 13, "xiv": 14, "xv": 15, "xvi": 16, "xvii": 17, "xviii": 18}

def reign_key(name, numeral):
    name = FULL_NAMES.get(name, name)
    if name in ("John", "Mary", "Anne"):
        return name
    if name in ("Steph", "Eliz"):
        return name + "."
    return f"{name}. {numeral or 'I'}"

def regnal_span(key, n):
    """Calendar years covered by regnal year n of a reign."""
    acc, month, _ = REIGNS[key]
    start = acc + n - 1
    return start, (start if month == 1 else start + 1)

def year_range(date):
    """'1273' -> (1273, 1273); '1748-9' -> (1748, 1749); '20 Edw. I' -> (1291, 1292);
    'Hen. III-Edw. I' -> (1216, 1307). Returns (None, None) when undatable."""
    if not date:
        return None, None
    # Edward the Confessor (Domesday's "T.R.E.", "King Edward's reign", "the Confessor's survey").
    if re.search(r"Confessor|King Edward's reign|T\. ?R\. ?E\.", date):
        return 1042, 1066
    m = re.search(r"\b(x[ivx]+|\d{2})(?:th|st|nd|rd)\.? cent", date, re.I)
    if m:
        g = m.group(1)
        c = int(g) if g.isdigit() else ROMAN.get(g.lower())
        if c:
            return (c - 1) * 100, (c - 1) * 100 + 99
    years = []
    for m in REIGN_RE.finditer(date):
        if not (m.group(3) and (m.group(4) or m.group(3) in ("John", "Mary", "Anne", "Steph", "Stephen", "Eliz", "Elizabeth"))):
            continue
        key = reign_key(m.group(3), m.group(4))
        if key not in REIGNS:
            continue
        if m.group(1):
            a, b = int(m.group(1)), int(m.group(2) or m.group(1))
            years += [regnal_span(key, a)[0], regnal_span(key, b)[1]]
        else:
            years += [REIGNS[key][0], REIGNS[key][2]]
    for m in re.finditer(r"\b(1[0-9]{3})(?:\s*-\s*(\d{1,4}))?\b", date):
        y = int(m.group(1))
        years.append(y)
        if m.group(2):
            tail = m.group(2)
            y2 = int(str(y)[: 4 - len(tail)] + tail)
            if y2 >= y:
                years.append(y2)
    if not years:
        return None, None
    return min(years), max(years)

# Dropdown locations: counties, plus London and places abroad.
LOCATION_ALIASES = {
    "York": "Yorkshire", "City of York": "Yorkshire", "Oxford": "Oxfordshire", "Cambridge": "Cambridgeshire",
    "Chester": "Cheshire", "Westminster": "London", "Middlesex (London)": "London",
    "Salop": "Shropshire", "Norwich": "Norfolk", "Lincoln": "Lincolnshire", "Bedford": "Bedfordshire",
    "Huntingdon": "Huntingdonshire", "Northampton": "Northamptonshire", "Nottingham": "Nottinghamshire",
    "Derby": "Derbyshire", "Leicester": "Leicestershire", "Warwick": "Warwickshire", "Gloucester": "Gloucestershire",
    "Hereford": "Herefordshire", "Worcester": "Worcestershire", "Stafford": "Staffordshire", "Hertford": "Hertfordshire",
    "Buckingham": "Buckinghamshire", "Berks": "Berkshire", "Wilts": "Wiltshire", "Hants": "Hampshire",
    "Newcastle upon Tyne": "Northumberland", "Liverpool": "Lancashire", "Manchester": "Lancashire",
}

def norm_location(county):
    county = (county or "").strip()
    return LOCATION_ALIASES.get(county, county)

SOURCE_TAILS = [
    r",\s*vol\.\s*[ivxl]+(,\s*pt\.\s*[ivxl]+)?(,\s*p\.\s*\d+)?[\d\-.]*$",  # ", vol. ii, pt. ii, p. 76"
    r",\s*[ivxl]+\.\s*\d+(\s*-\s*\d+)?\.?$",                              # ", iii. 82"
    r",\s*p\.\s*\d+(\s*-\s*\d+)?\.?$",                                    # ", p. 112"
]

SOURCE_WORK_ALIASES = [
    (r"^Register of St\. Mary Aldermary", "Register of St. Mary Aldermary, London, 1558-1754 (Harleian Society)"),
    (r"^Close Rolls?\b", "Close Rolls"),
]

def source_work(source):
    """'Register of St. James, Clerkenwell, 1551-1754 (Harleian Society), iii. 82' -> the work without volume/page."""
    s = (source or "").strip()
    for _ in range(3):
        for pat in SOURCE_TAILS:
            s = re.sub(pat, "", s).strip()
    for pat, canonical in SOURCE_WORK_ALIASES:
        if re.match(pat, s):
            return canonical
    return s

# When the book prints no place but the source itself is local, the location follows from the source.
SOURCE_LOCATION = [
    (r"Poll Tax, (West Riding of Yorkshire|Howdenshire)", "Yorkshire"),
    (r"Kirby's Quest for Somerset", "Somerset"),
    (r"Lay Exchequer Subsidy Rolls, co\. Lanc", "Lancashire"),
    (r"Freemen of the City of York", "Yorkshire"),
    (r"History of Norfolk", "Norfolk"),
    (r"Register of St\. (George|James|Mary Aldermary|Antholin|Dionis|Michael, Cornhill|Peter, Cornhill|Thomas the Apostle)", "London"),
    (r"Bishop of London|Dean and Chapter of Westminster", "London"),
    (r"Visitation of Bedfordshire", "Bedfordshire"),
    (r"Ravenstonedale", "Westmorland"),
]

def location_from_source(source):
    for pat, loc in SOURCE_LOCATION:
        if re.search(pat, source or ""):
            return loc
    return ""

def main():
    rows, problems = [], []
    for path in sorted(glob.glob(os.path.join(RAW, "p*.json"))):
        with open(path, encoding="utf-8") as f:
            page_rows = json.load(f)
        for i, r in enumerate(page_rows):
            missing = [k for k in FIELDS if k not in r]
            if missing:
                problems.append(f"{os.path.basename(path)} row {i}: missing {missing}")
            rows.append({k: r.get(k, "") for k in FIELDS})

    # A headword can run across a page break; give every row the fullest version of its headword fields.
    head = {}
    for r in rows:
        h = head.setdefault(r["headword"], {})
        for k in ("origin", "meaning", "author_comment", "modern_distribution"):
            if len(str(r[k] or "")) > len(str(h.get(k, ""))):
                h[k] = r[k]
    for r in rows:
        r.update(head[r["headword"]])

    # Where each record sits on its scan (from scripts/locate_lines.py): [top, bottom, exact] as page fractions.
    lp_path = os.path.join(ROOT, "data", "line_positions.json")
    line_pos = json.load(open(lp_path, encoding="utf-8")) if os.path.exists(lp_path) else {}

    out = []
    for n, r in enumerate(rows, 1):
        line = line_pos.get("|".join([str(r["page"]), r["headword"], r["first_name"], r["last_name"], r["record_text"]]))
        y0, y1 = year_range(r["date"])
        if r["date"] and y0 is None:
            problems.append(f"p{r['page']} {r['first_name']} {r['last_name']}: undatable date {r['date']!r}")
        location = norm_location(r["county"])
        inferred = not location and bool(location_from_source(r["source"]))
        out.append({
            "id": n,
            **{k: (r[k].strip() if isinstance(r[k], str) else r[k]) for k in FIELDS if k != "county"},
            "location": location or location_from_source(r["source"]),
            "location_from_source": inferred,
            "year_from": y0, "year_to": y1,
            "source_work": source_work(r["source"]),
            "archive_url": ARCHIVE.format(page=r["page"]),
            "line": line,
        })

    # For the website: surname-level fields stored once per headword, records point at them.
    HEAD_KEYS = ("headword", "origin", "meaning", "author_comment", "modern_distribution")
    REC_KEYS = ("id", "first_name", "last_name", "date", "year_from", "year_to", "event", "place", "location",
                "location_from_source", "notes", "source_abbrev", "source", "source_work", "record_text", "page", "column", "line", "confidence")
    headwords, h_index, records = [], {}, []
    for r in out:
        if r["headword"] not in h_index:
            h_index[r["headword"]] = len(headwords)
            headwords.append({k: r[k] for k in HEAD_KEYS} | {"page": r["page"]})
        records.append({k: r[k] for k in REC_KEYS} | {"h": h_index[r["headword"]]})
    with open(os.path.join(ROOT, "data", "pages.json"), encoding="utf-8") as f:
        pages = json.load(f)
    site = {
        "book": {"title": "A Dictionary of English and Welsh Surnames, with Special American Instances",
                 "author": "Charles Wareing Bardsley", "year": 1901, "publisher": "London: Henry Frowde",
                 "archive_id": "adictionaryengl00goog"},
        "pages": {p: v for p, v in pages.items() if int(p) in {r["page"] for r in out}},
        "headwords": headwords, "records": records,
    }
    with open(os.path.join(ROOT, "data", "entries.json"), "w", encoding="utf-8") as f:
        json.dump(site, f, ensure_ascii=False, separators=(",", ":"))
    cols = ["id", "first_name", "last_name", "meaning", "origin", "date", "year_from", "year_to", "event",
            "location", "location_from_source", "place", "notes", "author_comment", "source", "source_work", "source_abbrev", "record_text",
            "page", "column", "headword", "modern_distribution", "confidence", "archive_url"]
    with open(os.path.join(ROOT, "data", "entries.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)

    pages = sorted({r["page"] for r in out})
    print(f"{len(out)} rows, {len({r['headword'] for r in out})} headwords, pages {pages}")
    for p in problems:
        print("WARN", p)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test-dates":
        for d in ["1273", "1748-9", "20 Edw. I", "Hen. III-Edw. I", "1 Edw. III", "12-13 Edw. I",
                  "temp. Hen. IV", "19 Eliz.", "10 Edw. III", "6 Edw. I", "Jan. 16, 1437", "c. 1400", "temp. 1300"]:
            print(f"{d!r:22} -> {year_range(d)}")
    else:
        main()
