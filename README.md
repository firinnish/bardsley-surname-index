# Bardsley Surname Index

A searchable database of the people cited in C. W. Bardsley, *A Dictionary of English and Welsh
Surnames, with Special American Instances* (1901), from the Internet Archive scan
[adictionaryengl00goog](https://archive.org/details/adictionaryengl00goog).

Transcribed so far: printed pages 37–50 (1,039 names, 949 of them dated, under 149 surname entries).
Each row is one name as printed; people named together in one record each get a row. Surnames not printed
(wives, parents named in patronymics) are "(unknown)".

The site is plain static files, published with GitHub Pages from the `main` branch root.
Not in the repository (see `.gitignore`): the 55 MB book PDF, transcription crops and OCR caches.
Recreate them with `scripts/render_pages.py` and `scripts/locate_lines.py`, and download the PDF from the
Internet Archive into `book/`.

## Files

| Path | What it is |
|---|---|
| `index.html` | The search page. Serve the folder (`python -m http.server`) and open it; it reads `data/entries.json` and `pages/`. |
| `data/entries.csv` | Every row, flat, for spreadsheets. |
| `data/entries.json` | Same data for the page (surname-entry fields stored once per headword). |
| `data/raw/pNNNN.json` | Hand-checked transcription of each printed page. **Edit these to fix mistakes**, then rebuild. |
| `scripts/apply_human_checks.py` | Readings a person has confirmed against the scan. Add to its list and re-run; those rows get `human_checked: true` and are never changed again. |
| `data/sources.json` | Bardsley's key to abbreviations (pp. xiii–xvi): `A` = Hundred Rolls 1273, `K` = Testa de Nevill, etc. |
| `data/pages.json` | Scan size and column boundaries per page. |
| `data/line_positions.json` | Where each record sits on its scan, for the line box in the viewer. |
| `pages/pNNNN.png` | Page scans for the viewer (~200 KB each). |
| `book/adictionaryengl00goog.pdf` | The full book PDF from the Internet Archive. |
| `source/TRANSCRIPTION_SPEC.md` | The rules each page is transcribed by. |

## Adding pages

```
python scripts/render_pages.py 41 50      # scans + column crops (needs: pip install pymupdf)
# transcribe each page into data/raw/p0041.json ... following source/TRANSCRIPTION_SPEC.md
python scripts/locate_lines.py 41 50      # find each record's line on the scan
python scripts/build_data.py              # rebuild entries.json / entries.csv
```

Page numbers are the printed numbers (p. 37 = scan leaf 56); `source/page_numbers.json` maps them.
