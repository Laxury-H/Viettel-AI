"""Audit the ICD-10 codes in v63_code_pairs.json against the official Vietnamese
catalogue (Phu luc Thong tu 06/2026/TT-BYT), via icd10_vn_tt06_lookup.json.

Three outcomes per code:
  invalid  - not in the catalogue at all; must be replaced
  supersed - the circular forbids it because a more specific 4/5-char child exists
  info     - sex-restricted or discouraged-as-primary; usually fine, just noted
"""
import collections
import json
import os

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)

with open(os.path.join(BASE, "icd10_vn_tt06_lookup.json"), encoding="utf-8") as f:
    icd = json.load(f)
with open(os.path.join(ROOT, "v63_code_pairs.json"), encoding="utf-8") as f:
    pairs = json.load(f)

used = collections.Counter()
texts = collections.defaultdict(list)
for p in pairs:
    if p.get("type") != "CHẨN_ĐOÁN":
        continue
    for c in p.get("codes", []):
        used[c] += p.get("mentions", 0)
        texts[c].append(p["text"])


def children(code):
    return sorted(k for k in icd if k.startswith(code + ".") or
                  (len(k) == len(code) + 1 and k.startswith(code) and "." in code))


invalid, superseded, info = [], [], []
for code, n in used.most_common():
    rec = icd.get(code)
    if rec is None:
        invalid.append({"code": code, "mentions": n, "texts": texts[code][:3]})
        continue
    entry = {
        "code": code,
        "mentions": n,
        "name_vi": rec["name_vi"],
        "flags": rec["flags"],
        "texts": texts[code][:2],
        "children": [
            {"code": k, "name_vi": icd[k]["name_vi"]} for k in children(code)
        ],
    }
    if "co_ma_4_hoac_5_ky_tu_cu_the_hon" in rec["flags"] or \
       "khong_duoc_la_benh_chinh" in rec["flags"]:
        superseded.append(entry)
    elif rec["flags"]:
        info.append(entry)

print(f"Ma ICD-10 dang dung          : {len(used)}")
print(f"  KHONG co trong danh muc VN : {len(invalid)}")
print(f"  Bi thay the boi ma cu the hon: {len(superseded)}")
print(f"  Ghi chu (gioi tinh / khuyen cao): {len(info)}")

print("\n=== PHAI SUA: khong co trong Thong tu 06 ===")
for e in invalid:
    print(f"  {e['code']:9s} x{e['mentions']:<3d} {e['texts']}")

print("\n=== PHAI SUA: Thong tu cam dung vi co ma cu the hon ===")
for e in superseded:
    print(f"  {e['code']:9s} x{e['mentions']:<3d} {e['name_vi'][:58]}")
    print(f"      dung cho : {e['texts']}")
    print(f"      thay bang: " + ", ".join(c["code"] for c in e["children"][:11]))

print("\n=== GHI CHU (khong phai loi) ===")
for e in info:
    print(f"  {e['code']:9s} x{e['mentions']:<3d} {','.join(e['flags'])}  {e['name_vi'][:44]}")

with open(os.path.join(BASE, "icd_audit_vs_tt06.json"), "w", encoding="utf-8") as f:
    json.dump({"invalid": invalid, "superseded": superseded, "info": info},
              f, ensure_ascii=False, indent=1)
print("\n-> icd_audit_vs_tt06.json")
