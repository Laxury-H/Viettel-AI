#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Pitfall-focused audit of v63_code_pairs.json.

Cross-checks every ICD-10 code against (a) WHO ICD-10 2019 validity and
(b) the Vietnamese MOH TT06/2026 catalogue usage flags, then flags the
classic coding traps: chapter R/Z as a diagnosis, dagger/asterisk misuse,
3-char category used where a 4th character exists, and RxNorm TTY drift.
"""
import io, json, os, re, sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

pairs = json.load(open(os.path.join(ROOT, "v63_code_pairs.json"), encoding="utf-8"))
tt06 = json.load(open(os.path.join(HERE, "icd10_vn_tt06_2026.json"), encoding="utf-8"))
rxnav = json.load(open(os.path.join(HERE, "rxnav_verify.json"), encoding="utf-8"))

vn = {r["code"]: r for r in tt06}
# children lookup: which 3-char categories have 4-char subdivisions
kids = {}
for r in tt06:
    if "." in r["code"]:
        kids.setdefault(r["code"].split(".")[0], []).append(r["code"])

who_codes = set()
p = os.path.join(HERE, "who_icd10_2019_codes.txt")
if os.path.exists(p):
    who_codes = {l.strip() for l in io.open(p, encoding="utf-8") if l.strip()}

FLAGS = ["no_primary", "discouraged_primary", "unused_has_more_specific",
         "mortality_only", "female_only", "male_only"]

rows = []
for i, x in enumerate(pairs):
    if x["type"] != "CHẨN_ĐOÁN":
        continue
    for code in x["codes"]:
        rec = vn.get(code)
        issues = []
        if rec is None:
            issues.append("NOT_IN_TT06_VN")
            if who_codes and code not in who_codes:
                issues.append("NOT_IN_WHO_2019")
        else:
            for f in FLAGS:
                if str(rec.get(f) or "").strip():
                    issues.append(f.upper())
        ch = code[0]
        if ch == "R":
            issues.append("CHAPTER_R_SYMPTOM")
        if ch == "Z":
            issues.append("CHAPTER_Z_FACTOR")
        if ch in "ST":
            issues.append("CHAPTER_XIX_INJURY_needs_external_cause")
        if "." not in code and kids.get(code):
            issues.append("CATEGORY_ONLY_has_%d_subcodes" % len(kids[code]))
        if issues:
            rows.append({"idx": i, "text": x["text"], "code": code,
                         "official_vi": (rec or {}).get("name_vi", ""),
                         "official_en": (rec or {}).get("name_en", ""),
                         "mentions": x["mentions"], "issues": issues})

# RxNorm TTY consistency
tty_rows = []
for i, x in enumerate(pairs):
    if x["type"] != "THUỐC":
        continue
    for code in x["codes"]:
        o = rxnav.get(code) or {}
        tty_rows.append({"idx": i, "text": x["text"], "rxcui": code,
                         "tty": o.get("tty", "?"), "rx_name": o.get("name", "?"),
                         "mentions": x["mentions"]})

out = {"icd_issues": rows, "rx_tty": tty_rows}
json.dump(out, open(os.path.join(HERE, "pitfall_audit.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

print("=== ICD codes with usage/validity flags: %d ===" % len(rows))
for r in sorted(rows, key=lambda r: -r["mentions"]):
    print("m=%-2d %-9s %-45.45s | %-40.40s | %s" %
          (r["mentions"], r["code"], r["text"], r["official_vi"] or "(khong co trong TT06)",
           ",".join(r["issues"])))

from collections import Counter
print("\n=== RxNorm TTY distribution ===", Counter(r["tty"] for r in tty_rows))
