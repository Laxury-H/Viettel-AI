# -*- coding: utf-8 -*-
"""
Xay dung chi muc tra cuu OFFLINE tu hai nguon KHONG CAN GIAY PHEP:
  1. ICD-10-CM FY2026 (CDC/NCHS, US public domain)  -> icd10_index.json
  2. RxNorm Current Prescribable Content (NLM, "no license required") -> rxcui_index.json

Ket qua la file JSON tinh, dung duoc luc suy luan ma khong goi mang.
"""
import json, os, re, collections

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------- ICD-10-CM ----------
# Dinh dang cot co dinh cua icd10cm-order-YYYY.txt (xem icd10OrderFiles.pdf):
#   [0:5]   order number
#   [6:13]  code (KHONG co dau cham)
#   [14]    valid/billable flag (0 = header/khong thanh toan duoc, 1 = billable)
#   [16:76] short description
#   [77:]   long description
def build_icd10():
    src = os.path.join(HERE, "icd10cm_2026", "icd10cm-order-2026.txt")
    idx = {}
    with open(src, encoding="utf-8") as f:
        for line in f:
            if len(line) < 78:
                continue
            code = line[6:13].strip()
            billable = line[14] == "1"
            long_desc = line[77:].rstrip("\n").strip()
            # chuan hoa ve dang co dau cham: A000 -> A00.0
            dotted = code if len(code) <= 3 else code[:3] + "." + code[3:]
            idx[dotted] = {"raw": code, "billable": billable, "desc": long_desc}
    return idx

# ---------- RxNorm ----------
# RXNCONSO.RRF: RXCUI|LAT|TS|LUI|STT|SUI|ISPREF|AUI|SAUI|SCUI|SDUI|SAB|TTY|CODE|STR|SRL|SUPPRESS|CVF|
def build_rxnorm():
    src = os.path.join(HERE, "rxnorm_prescribe", "RXNCONSO.RRF")
    names = collections.defaultdict(dict)
    with open(src, encoding="utf-8") as f:
        for line in f:
            p = line.split("|")
            if len(p) < 15 or p[11] != "RXNORM":
                continue
            rxcui, tty, s = p[0], p[12], p[14]
            names[rxcui][tty] = s
    out = {}
    for rxcui, tt in names.items():
        # uu tien ten chuan hoa: IN (ingredient) > PIN > MIN > SCD > SBD > bat ky
        for tty in ("IN", "PIN", "MIN", "SCDC", "SCD", "SBD", "BN"):
            if tty in tt:
                out[rxcui] = {"tty": tty, "name": tt[tty]}
                break
        else:
            tty, s = next(iter(tt.items()))
            out[rxcui] = {"tty": tty, "name": s}
    return out

if __name__ == "__main__":
    icd = build_icd10()
    rx = build_rxnorm()
    json.dump(icd, open(os.path.join(HERE, "icd10_index.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    json.dump(rx, open(os.path.join(HERE, "rxcui_index.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print("ICD-10-CM entries :", len(icd))
    print("RxNorm RXCUI      :", len(rx))
