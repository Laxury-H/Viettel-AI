"""Build the offline ICD-10 VN lookup used by the pipeline.

Two independent renderings of the same legal appendix are merged:

  A. icd10_vn_tt06_2026.json - extracted here, directly from the official PDF
     https://datafiles.chinhphu.vn/cpp/files/vbpq/2026/4/06-byt-kem.pdf
     (Phu luc ban hanh kem theo Thong tu 06/2026/TT-BYT). Primary source, but the
     PDF lets cells overflow their column, so a minority of long names lose a word
     to the neighbouring column.

  B. tt06_thirdparty_rows.json - a third-party rendering of the same appendix
     (https://checkxml.gpp.vn/icd/tt06_data.js). Cleaner names, but not an
     authoritative source on its own.

They agree exactly on the six statutory flag columns (Dieu 4 of the circular) for
every code checked, and A's code set is a strict subset of B's, so B is used for
the text and A is used to mark which rows were confirmed against the primary PDF.
Codes only B knows about are kept but flagged unverified, so a caller can choose
to trust only the primary-source subset.
"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
THIRD_PARTY = os.path.join(BASE, "tt06_thirdparty_rows.json")
PRIMARY = os.path.join(BASE, "icd10_vn_tt06_2026.json")
OUT = os.path.join(BASE, "icd10_vn_tt06_lookup.json")

# Bit positions match columns 24..29 of the appendix, in order.
FLAG_NAMES = [
    "khong_duoc_la_benh_chinh",          # cot 24
    "khong_khuyen_khich_benh_chinh",     # cot 25
    "co_ma_4_hoac_5_ky_tu_cu_the_hon",   # cot 26
    "chi_ma_hoa_nguyen_nhan_tu_vong",    # cot 27
    "chi_o_nu_gioi",                     # cot 28
    "chi_o_nam_gioi",                    # cot 29
]

STRIP_MARK = re.compile(r"[*†+]")


def main():
    with open(THIRD_PARTY, encoding="utf-8") as f:
        rows = json.load(f)
    verified = set()
    if os.path.exists(PRIMARY):
        with open(PRIMARY, encoding="utf-8") as f:
            verified = {r["code"] for r in json.load(f)}

    out = {}
    for code_raw, nodot, name_vi, name_en, note_vi, note_en, _a, flagbits in rows:
        code = STRIP_MARK.sub("", code_raw)
        flags = [FLAG_NAMES[i] for i in range(6) if flagbits >> i & 1]
        out[code] = {
            "code": code,
            "code_raw": code_raw,
            "code_nodot": nodot,
            "name_vi": " ".join(name_vi.split()),
            "name_en": " ".join(name_en.split()),
            "note_vi": " ".join(note_vi.split()),
            "note_en": " ".join(note_en.split()),
            "flags": flags,
            # Codes the circular forbids outright as a primary diagnosis, or
            # supersedes with a more specific child. Never emit these.
            "usable_as_primary": not (
                "khong_duoc_la_benh_chinh" in flags
                or "co_ma_4_hoac_5_ky_tu_cu_the_hon" in flags
                or "chi_ma_hoa_nguyen_nhan_tu_vong" in flags
            ),
            "confirmed_in_official_pdf": code in verified,
        }

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    n = len(out)
    conf = sum(1 for v in out.values() if v["confirmed_in_official_pdf"])
    prim = sum(1 for v in out.values() if v["usable_as_primary"])
    print(f"{OUT}")
    print(f"  tong ma            : {n}")
    print(f"  xac nhan tu PDF goc: {conf}")
    print(f"  dung duoc lam benh chinh: {prim}")


if __name__ == "__main__":
    main()
