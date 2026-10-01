# Transcription spec: Bardsley, *A Dictionary of English and Welsh Surnames* (1901)

Goal: turn each printed page into JSON rows for a searchable names database.
Work ONLY from the page images. The archive.org OCR text is badly garbled; do not trust it.

## Inputs

- Column crops at native scan resolution: `source/crops/pNNNN_cC_bB.png`
  (page NNNN, column C = 1..3 left to right, band B = 1..3 top to bottom).
  Bands overlap vertically by a few lines, so a line can appear in two crops: transcribe it once.
  Column crops also show a sliver of the neighbouring column at the edges: ignore it.
- Whole page (lower resolution, for orientation): `pages/pNNNN.png`.
- Abbreviation key: `data/sources.json` (`letters` = letter codes, `named` = named works).
- If column 1 of your page starts in the middle of an entry, open the previous page's
  `_c3_b3` crop to learn which headword it is, its origin and its meaning.

## Layout of an entry

```
Abbey, Abbee, Abbe.—(1) Local, 'at the Abbey,' from residence thereby. (2) Offic., from the
ecclesiastical title. All the evidence is in favour of this view except in one instance.   <- headword + etymology + author's commentary
    Henry le Abbé, co. Salop, 1273. A.                                                       <- citation lines (one person each)
    Ralph le Abbe, co. Devon, Hen. III-Edw. I. K.
    William le Abbe, co. Devon, ibid.
    1648. Married—George Abbey and Mary Feild: St. Jas. Clerkenwell, iii. 82.
    London, 4, 1, 0; Philadelphia, 11, 0, 6.                                                <- modern directory counts (NOT people)
```

Headword origin labels: Bapt. = Baptismal, Local, Occup. = Occupational, Offic. = Official,
Nick. = Nickname, Pat. = Patronymic. Some entries have (1)/(2) alternatives.

## Output

Write a JSON array to `data/raw/pNNNN.json`, rows in reading order (column 1 top to bottom, then 2, then 3).
One row per citation line (per named person record). Fields:

| field | content |
|---|---|
| `page` | printed page number (integer), e.g. 38 |
| `column` | 1, 2 or 3 |
| `headword` | full headword line as printed, e.g. `"Abbey, Abbee, Abbe"` |
| `origin` | `"Baptismal"`, `"Local"`, `"Occupational"`, `"Official"`, `"Nickname"`, or several joined with `"; "` in the book's order |
| `meaning` | the etymology, concise and close to the book's words, e.g. `"the son of Aaron"`, `"(1) at the Abbey, from residence thereby; (2) from the ecclesiastical title"`. For a cross-reference entry like `"Bapt.; v. Abbs, of which it is a variant"` write `"variant of Abbs"` |
| `author_comment` | the author's commentary on the surname, near-verbatim (light trimming OK), e.g. `"A Jewish surname settled in England. I have not met with a single English Aaron in mediaeval times."`. Same value on every row of that headword. `""` if none |
| `modern_distribution` | the directory-count line verbatim, e.g. `"London, 8, 4, 4; Philadelphia, 12, 17, 7"`; MDB lines too, joined with `"; "`. Same on every row of the headword. `""` if none |
| `first_name` | as printed. Expand only obvious contractions in square brackets: `"Eliz[abeth]"`, `"Will[iam]"`, `"Dan[iel]"`, `"Robt." -> "Rob[er]t"`. Latin forms stay Latin (`"Johannes"`, `"Willelmus"`) |
| `last_name` | as printed, including particles: `"le Abbé"`, `"del Abbay"`, `"de Mikelfeld"`, `"fil. Abi"` |
| `date` | as printed: `"1273"`, `"1696"`, `"Hen. III-Edw. I"`, `"1 Edw. III"`, `"20 Edw. I"`, `"12-13 Edw. I"`, `"1748-9"`, `"temp. Eliz."`. For `ibid.` lines copy the date of the line it refers to. `""` if none |
| `event` | `"Baptism"`, `"Marriage"`, `"Marriage licence"`, `"Burial"`, `"Will"`, `"Emigration"`, or `""`. Use the printed word (Bapt./Married/Buried) to decide |
| `place` | the place as printed but with abbreviations expanded, e.g. `"co. Salop"` -> `"Shropshire"`, `"Thetford, co. Norf."` -> `"Thetford, Norfolk"`, `"St. Geo. Han. Sq."` -> `"St. George, Hanover Square, London"`, `"St. Jas. Clerkenwell"` -> `"St. James, Clerkenwell, London"`, `"Magd. Coll."` -> `"Magdalen College, Oxford"` |
| `county` | normalized region for a dropdown: historic county name (`"Shropshire"`, `"Yorkshire"`, `"Lancashire"`, `"Norfolk"`...), or `"London"` for any London/Westminster parish or London marriage licence, `"Oxford"`/`"York"` only if the city itself is meant (Freemen of York -> `"York"`), or a country/colony (`"Virginia"`, `"Philadelphia"`). `""` if no place at all |
| `notes` | record-level context, in plain English: relationships (`"daughter of Henrye Abbes"`, `"wife of Johannes del Abdy"`), the spouse in a marriage (`"Married Mary Feild"`), offices and occupations (`"Now mayor of the Towne of Bedford"`, `"taylour (tailor)"`), events (`"Embarked in the George for Virginia"`), `dictus` aliases. `""` if none |
| `source_abbrev` | the source exactly as printed: the letter code (`"A"`, `"K"`, `"R"`, `"W. 2"`, `"FF. vi. 445"`) or the named citation (`"Reg. St. Mary Aldermary, London, p. 112"`). For `ibid.` lines write `"ibid."` plus any page, e.g. `"ibid. p. 446"` |
| `source` | expanded, ibid. resolved, volume/page kept: `"Hundred Rolls, 1273"`, `"Testa de Nevill, sive Liber Feodorum, temp. Hen. III-Edw. I"`, `"History of Norfolk (Blomefield and Parkin), vol. vi, p. 445"`, `"Register of St. Mary Aldermary, London (Harleian Society), p. 112"`. Use `data/sources.json`; if a work is not in the key, expand it sensibly and keep the printed form |
| `record_text` | the citation line verbatim as printed (keep `1273. A.`, `ibid.`, italics as plain text). Use straight ASCII apostrophes/quotes and a plain hyphen-minus for dashes inside it (an em-dash after Married/Bapt. may be written as `—`) |
| `confidence` | `"high"`, or `"low"` when the print is damaged/unclear (say why in notes, starting `"[Unclear: ...]"`) |

### Special cases

- **Headword with no citation lines** (only commentary and/or directory counts): emit ONE row with
  `first_name: ""`, `last_name` = the first form of the headword, all record fields empty,
  and the headword fields filled. Use `record_text: ""`.
- **Marriages**: `"1648. Married—George Abbey and Mary Feild"` -> the row is for the person bearing a form of the
  headword surname (George Abbey), notes `"Married Mary Feild"`. If the headword-surname bearer is the bride
  (`"Married—Richard Powney and Eleanor Abadam"`), the row is Eleanor Abadam with notes `"Married Richard Powney"`.
- **Baptisms**: `"1631. Bapt.—Eliz., d. Henrye Abbes"` -> first `"Eliz[abeth]"`, last `"Abbes"`, notes `"daughter of Henrye Abbes"`.
  `s.` = son, `d.` = daughter.
- **Burials from a house**: `"1628. Buried—George Woodlve, from Dan. Abiss"` -> row for `"Dan[iel]" "Abiss"`,
  notes `"George Woodlve was buried from his house"`.
- **Continuation dashes** `"— —"` at the start of a line repeat the previous date/event.
- **Several people of the headword surname in one line**: one row per such person.
- **Latin**: `"uxor ejus"` = his wife; `"fil."` = son/daughter of; `"relicta"` = widow of; `"dictus"` = called. Explain in notes.
- **Quoted literary passages** (e.g. a line of Chaucer) are not people: put them in `author_comment` only if short, else skip.
- Do NOT emit rows for the directory-count lines (`London, 8, 4, 4; ...`) or `MDB.` lines; they go in `modern_distribution`.

### Never modernise or correct spellings

Names, `record_text` and every other transcribed field keep the book's exact letters, even when they look like
misprints: medieval spellings are often strange. "Kobeit" stays "Kobeit" (or "Robeit?" if the first letter is
genuinely unclear), never "Robert"; "Johu" stays "Johu"; "Henrv" stays "Henrv". Where a letter is damaged and
you are not sure of the reading, put your best reading of the PRINTED letters followed by "?" (e.g. "Alfrav?"),
and describe the damage in notes. Do not offer a modern equivalent in the name fields; a note may say
"possibly a misprint for ..." if helpful. Editorial expansions of abbreviations in [square brackets] are allowed.

### Gender

Do not infer gender from a first name. A parent is "Parent of ..." unless the print says father/mother
(pater/mater). "fil." may be filius or filia, so its child is "child of ...". Use son/daughter, wife/husband,
widow only when the print states it ("s.", "d.", "uxor", "relicta", "Married").

### One row per NAME (overrides the special cases above where they differ)

The database is for searching names, so **every personal name printed in a citation gets its own row**, not
just the person bearing the headword surname. All rows from one citation line share its `date`, `event`, `place`,
`county`, `source_abbrev`, `source`, `record_text` and `confidence`; they differ in `first_name`, `last_name`
and `notes`. Put the extra rows directly after the headword-bearer's row, in the order the names are printed.

- **Marriages / licences**: `"1648. Married—George Abbey and Mary Feild"` -> row George Abbey (notes `"Married Mary Feild"`)
  AND row Mary Feild (notes `"Married George Abbey"`).
- **Baptisms**: `"1631. Bapt.—Eliz., d. Henrye Abbes"` -> row Eliz[abeth] Abbes (notes `"Daughter of Henrye Abbes"`)
  AND row Henrye Abbes (notes `"Parent of Eliz[abeth] Abbes, baptised"`). When the child's surname is implied, copy it:
  `"1641. Bapt.—Willm., s. Willm. Abbison"` gives Will[iam] Abbison (child) and Will[iam] Abbison (father).
  `"John, son of John and Susanah Adee"` gives three rows.
- **Burials from a house**: `"Buried—George Woodlve, from Dan. Abiss"` -> Dan[iel] Abiss (notes `"George Woodlve was buried from his house"`)
  AND George Woodlve (notes `"Buried from the house of Dan[iel] Abiss"`).
- **Wives / households**: `"Johannes del Abdy, et Agnes, uxor ejus"` -> Johannes del Abdy AND Agnes with
  `last_name: "(unknown)"` (never assume a wife shared her husband's surname), notes `"Wife (uxor ejus) of Johannes del Abdy"`.
  Use `"(unknown)"` for any surname that is not printed. An unnamed wife (`"et uxor"`) gets no row.
- **Patronymics** (`fil.`, `son of`, `relicta`): `"John fil. Adam"` -> John with `last_name: "fil. Adam"` AND a row for the
  parent: first `"Adam"`, last `"(unknown)"`, notes `"Parent of John fil. Adam. Recorded as a patronymic - may not necessarily
  be nominative form"` (for `relicta X`: `"Husband of ..."`).
- **dictus / alias / or**: `"William de Mikelfeld, dictus del Abbay"` -> TWO rows: William `"de Mikelfeld"` (notes
  `"Also called William del Abbay"`) and William `"del Abbay"` (notes `"Also called William de Mikelfeld"`).
  Same for `"alias"` and `"Warin Arnold, or Ernold"`.
- **Other named people in the line** (the conveyor in a deed, a master of a servant, a witness): their own row,
  with their role in notes, e.g. Robert Rodes, notes `"Conveyed a house in Gateshead to William Abletson"`.
- **People named with a date and source inside the author's commentary** (e.g. `"Cf. Roger a'Hulle (co. Oxf., 1273. A.)"`,
  `"Adekin le Fullere (1273, Hundred Rolls)"`): their own row, `record_text` = the phrase as printed, notes
  `"Cited in the author's commentary"`.
- People named WITHOUT any date (e.g. "Lower says:", authors, saints, Chaucer's characters) get no row.

## Worked example (page 37, column 1)

```json
[
  {"page":37,"column":1,"headword":"Aaron, Aarons, Aaronson","origin":"Baptismal","meaning":"the son of Aaron",
   "author_comment":"A Jewish surname settled in England. I have not met with a single English Aaron in mediaeval times.",
   "modern_distribution":"London, 8, 4, 4; Philadelphia, 12, 17, 7",
   "first_name":"Jacob","last_name":"Aarron","date":"1696","event":"","place":"St. Mary Aldermary, London","county":"London",
   "notes":"","source_abbrev":"Reg. St. Mary Aldermary, London, p. 112",
   "source":"Register of St. Mary Aldermary, London (Harleian Society), p. 112",
   "record_text":"Jacob Aarron, 1696: Reg. St. Mary Aldermary, London, p. 112.","confidence":"high"},
  {"page":37,"column":1,"headword":"Abadam","origin":"Baptismal","meaning":"the son of Adam (Welsh ap- or ab-Adam)",
   "author_comment":"Cf. Bethell, Bloyd, Breeze, &c.","modern_distribution":"",
   "first_name":"Thomas","last_name":"Appadam","date":"1 Edw. III","event":"","place":"Somerset","county":"Somerset",
   "notes":"","source_abbrev":"Kirby's Quest, p. 219",
   "source":"Kirby's Quest for Somerset (Exchequer Lay Subsidy, 1 Edw. III), Somerset Record Society, 1889, p. 219",
   "record_text":"Thomas Appadam, co. Soms., 1 Edw. III: Kirby's Quest, p. 219.","confidence":"high"},
  {"page":37,"column":1,"headword":"Abadam","origin":"Baptismal","meaning":"the son of Adam (Welsh ap- or ab-Adam)",
   "author_comment":"Cf. Bethell, Bloyd, Breeze, &c.","modern_distribution":"",
   "first_name":"Eleanor","last_name":"Abadam","date":"1754","event":"Marriage","place":"St. George's Chapel, Mayfair, London","county":"London",
   "notes":"Married Richard Powney","source_abbrev":"St. Geo. Chap. Mayfair, p. 280",
   "source":"Register of St. George's Chapel, Mayfair, 1740-54 (Harleian Society), p. 280",
   "record_text":"1754. Married—Richard Powney and Eleanor Abadam: St. Geo. Chap. Mayfair, p. 280.","confidence":"high"}
]
```

## Quality bar

Accuracy over speed. Read every crop; double-check numbers (dates, volume and page numbers) and the spelling of
names letter by letter, since genealogists will rely on them. The old-style numerals look like `1273`, `1696` with
descending 3/5/7/9: read carefully. If uncertain, mark `confidence: "low"` rather than guessing silently.
Output must be valid JSON (UTF-8). Verify by parsing it with `python -c "import json;print(len(json.load(open(r'data/raw/pNNNN.json',encoding='utf-8'))))"`.
