# -*- coding: utf-8 -*-
"""Doi chieu 409 cap ma dang dung voi chi muc ICD-10-CM / RxNorm offline."""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

icd = json.load(open(os.path.join(HERE, "icd10_index.json"), encoding="utf-8"))
rx = json.load(open(os.path.join(HERE, "rxcui_index.json"), encoding="utf-8"))
pairs = json.load(open(os.path.join(ROOT, "v63_code_pairs.json"), encoding="utf-8"))

icd_codes, rx_codes = collections.Counter(), collections.Counter()
for p in pairs:
    for c in p["codes"]:
        c = c.strip()
        (rx_codes if c.isdigit() else icd_codes)[c] += p.get("mentions", 1)

print("=== ICD-10 ===")
print("ma rieng biet:", len(icd_codes))
miss = []
for c in sorted(icd_codes):
    if c not in icd:
        miss.append(c)
print("KHONG co trong ICD-10-CM FY2026:", len(miss))
for c in miss:
    # thu tim ma cha (3 ky tu)
    parent = c.split(".")[0]
    hint = icd.get(parent, {}).get("desc", "-- ca ma cha cung khong ton tai --")
    print(f"   {c:10s} mentions={icd_codes[c]:3d}  | cha {parent}: {hint[:70]}")

print()
print("=== RxNorm ===")
print("RXCUI rieng biet:", len(rx_codes))
rmiss = [c for c in sorted(rx_codes, key=int) if c not in rx]
print("KHONG co trong Current Prescribable Content:", len(rmiss))
for c in rmiss:
    print(f"   {c:10s} mentions={rx_codes[c]:3d}")

# Xuat bang doi chieu day du de review thu cong
rows = []
for p in pairs:
    for c in p["codes"]:
        c = c.strip()
        if c.isdigit():
            e = rx.get(c)
            rows.append({"text": p["text"], "type": p["type"], "code": c,
                         "system": "RxNorm", "mentions": p.get("mentions"),
                         "official_name": e["name"] if e else None,
                         "tty": e["tty"] if e else None,
                         "found": bool(e)})
        else:
            e = icd.get(c)
            rows.append({"text": p["text"], "type": p["type"], "code": c,
                         "system": "ICD-10-CM", "mentions": p.get("mentions"),
                         "official_name": e["desc"] if e else None,
                         "tty": None, "found": bool(e)})
json.dump(rows, open(os.path.join(HERE, "audit_v63_report.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n-> bang doi chieu:", os.path.join(HERE, "audit_v63_report.json"), f"({len(rows)} dong)")
