"""Extract the official ICD-10 VN table from the appendix of Circular 06/2026/TT-BYT.

Source PDF: https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/06-byt-kem.pdf
(Phu luc ban hanh kem theo Thong tu 06/2026/TT-BYT ngay 02/4/2026 cua Bo Y te)

Two quirks make the naive extract_table() lossy:
  1. Cells overflow their drawn rectangles, so extract_table() truncates the text.
  2. Rows are multi-line and the ruling grid does not always align with them, so
     bucketing words by the grid's cell tops merges two logical rows into one.

Strategy: the 29 column boundaries are identical on every page, so take them as
fixed. Then use the "MA BENH" column itself as the row anchor - each code-shaped
word there opens a new row band that runs to the next anchor. Every other word is
assigned to the band its top falls into.
"""
import json
import re
import sys

import pdfplumber

PDF = "TT06_2026_BYT_phuluc_ICD10.pdf"

# Column indices within the fixed 29-column layout, verified against the header
# page and against Dieu 4 of the circular (cot 24..29 = the six flag columns).
COL = {
    "chapter": 1,
    "block_range": 2,
    "chapter_en": 3,
    "chapter_vi": 4,
    "block_code": 5,
    "block_en": 6,
    "block_vi": 7,
    "cat3": 14,
    "cat3_en": 15,
    "cat3_vi": 16,
    "code": 17,
    "code_nodot": 18,
    "name_en": 19,
    "note_en": 20,
    "name_vi": 21,
    "note_vi": 22,
    "no_primary": 23,
    "discouraged_primary": 24,
    "unused_has_more_specific": 25,
    "mortality_only": 26,
    "female_only": 27,
    "male_only": 28,
}
CODE_COL = COL["code"]

# Codes may carry the WHO dagger/asterisk markers, e.g. "M01.03*", "A18.0+".
# On some pages the "MA BENH" and "MA BENH KHONG DAU" cells are rendered with no
# gap, so extract_words() returns them glued: "M01.03*M0103". Accept that only
# when the tail is exactly the dotless spelling of the head, never as a prefix
# match, so that free text starting with a code shape is not mistaken for one.
CODE_RE = re.compile(r"^([A-Z]\d{2}(?:\.\d{1,2})?)([*†+]?)(.*)$")


def parse_code(text):
    m = CODE_RE.match(text)
    if not m:
        return None
    code, _mark, rest = m.groups()
    if rest and rest != code.replace(".", ""):
        return None
    return code


NODOT_RE = re.compile(r"^([A-Z]\d{2})(\d{0,2})[*†+]?$")


def parse_nodot(text):
    """Recover a dotted code from the "MA BENH KHONG DAU" column: C111 -> C11.1."""
    m = NODOT_RE.match(text)
    if not m:
        return None
    head, tail = m.groups()
    return f"{head}.{tail}" if tail else head


def column_edges(pdf):
    """The 29 column left edges, taken from a page whose grid is fully drawn."""
    for page in pdf.pages[:20]:
        tables = page.find_tables()
        if not tables:
            continue
        xs = sorted({round(c[0], 1) for c in tables[0].cells})
        if len(xs) == 29:
            return xs
    raise RuntimeError("could not establish 29 column edges")


def col_of(x0, xs):
    ci = -1
    for i, x in enumerate(xs):
        if x0 >= x - 1.5:
            ci = i
        else:
            break
    return ci


def page_rows(page, xs):
    words = page.extract_words(keep_blank_chars=False, use_text_flow=False)
    if not words:
        return []

    buckets = [[] for _ in xs]
    for w in words:
        ci = col_of(w["x0"], xs)
        if ci >= 0:
            buckets[ci].append(w)

    # Row anchors: code-shaped words in the MA BENH column. On pages where the
    # neighbouring cell overflows into it the code gets glued to that text and is
    # unrecoverable, so fall back to the dotless twin in the next column and keep
    # whichever anchor sits alone on each baseline.
    cands = [(w["top"], 0, parse_code(w["text"]), w["text"]) for w in buckets[CODE_COL]]
    cands += [
        (w["top"], 1, parse_nodot(w["text"]), w["text"])
        for w in buckets[CODE_COL + 1]
    ]
    best = {}
    for top, pref, code, raw in cands:
        if not code:
            continue
        key = round(top / 3.0)
        if key not in best or pref < best[key][1]:
            best[key] = (top, pref, code, raw)
    anchors = sorted(best.values())
    if not anchors:
        return []
    anchors = [{"top": t, "code": c, "raw": r} for t, _p, c, r in anchors]

    bounds = [a["top"] - 2.0 for a in anchors] + [float("inf")]

    rows = [{} for _ in anchors]
    for ci, ws in enumerate(buckets):
        for w in ws:
            top = w["top"]
            ri = -1
            for i in range(len(anchors)):
                if bounds[i] <= top < bounds[i + 1]:
                    ri = i
                    break
            if ri < 0:
                continue
            rows[ri].setdefault(ci, []).append(w)

    out = []
    for ri, cells in enumerate(rows):
        rec = {}
        for key, ci in COL.items():
            ws = sorted(cells.get(ci, []), key=lambda w: (round(w["top"], 0), w["x0"]))
            rec[key] = " ".join(w["text"] for w in ws).strip()
        rec["code"] = anchors[ri]["code"]
        rec["code_raw"] = anchors[ri]["raw"]
        out.append(rec)
    return out


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    with pdfplumber.open(PDF) as pdf:
        xs = column_edges(pdf)
        print(f"column edges: {len(xs)}", file=sys.stderr)
        pages = pdf.pages[:limit] if limit else pdf.pages
        out, seen = [], set()
        for pno, page in enumerate(pages):
            for rec in page_rows(page, xs):
                key = (rec["code"], rec["name_vi"])
                if key in seen:
                    continue
                seen.add(key)
                rec["page"] = pno + 1
                out.append(rec)
            if not limit and (pno + 1) % 100 == 0:
                print(f"  page {pno+1}: {len(out)} rows", file=sys.stderr, flush=True)

    with open("icd10_vn_tt06_2026.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"rows: {len(out)}  unique codes: {len({r['code'] for r in out})}")


if __name__ == "__main__":
    main()
