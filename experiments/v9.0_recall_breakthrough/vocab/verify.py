# -*- coding: utf-8 -*-
"""
Bo kiem ma OFFLINE - dung luc phat trien VA luc suy luan (khong goi mang).

Nguon (tat ca da tai ve san, khong can dang ky):
  who_icd10_2019_titles.json : tieu de CHINH THUC WHO ICD-10 2019 (ban VN dua vao)
  icd10_index.json           : ICD-10-CM FY2026 (CDC, public domain) - phu tro
  rxcui_index.json           : RxNorm Current Prescribable Content (NLM, no license)
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
_L = lambda n: json.load(open(os.path.join(HERE, n), encoding="utf-8"))

WHO = _L("who_icd10_2019_titles.json")
CM = _L("icd10_index.json")
RX = _L("rxcui_index.json")


def check_icd(code):
    """Tra ve (hop_le_theo_WHO, tieu_de, nguon)."""
    code = code.strip()
    w = WHO.get(code)
    if w and w.get("found"):
        return True, w["title"], "WHO ICD-10 2019"
    c = CM.get(code)
    if c:
        # Ton tai trong ICD-10-CM nhung CHUA xac nhan trong WHO ICD-10
        return None, c["desc"], "ICD-10-CM FY2026 (CHUA xac nhan WHO)"
    return False, None, None


def check_rxcui(rxcui):
    """Tra ve (co_trong_ban_ke_don_My, ten, tty).
    Luu y: False KHONG co nghia la sai - thuoc khong luu hanh o My
    (vd trimetazidine, alverine) van la RXCUI hop le."""
    e = RX.get(str(rxcui).strip())
    return (True, e["name"], e["tty"]) if e else (False, None, None)


if __name__ == "__main__":
    ROOT = os.path.dirname(HERE)
    pairs = json.load(open(os.path.join(ROOT, "v63_code_pairs.json"), encoding="utf-8"))
    rows, warn = [], []
    for p in pairs:
        for c in p["codes"]:
            c = c.strip()
            if c.isdigit():
                ok, name, tty = check_rxcui(c)
                r = {"text": p["text"], "code": c, "system": "RxNorm",
                     "official": name, "tty": tty, "who_valid": None,
                     "in_us_prescribable": ok, "mentions": p.get("mentions")}
            else:
                ok, title, src = check_icd(c)
                r = {"text": p["text"], "code": c, "system": "ICD-10",
                     "official": title, "source": src, "who_valid": ok,
                     "mentions": p.get("mentions")}
                if ok is not True:
                    warn.append(r)
            rows.append(r)
    json.dump(rows, open(os.path.join(HERE, "verification_table.json"), "w",
                         encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(rows)} dong -> verification_table.json")
    print(f"CANH BAO (ma khong co trong WHO ICD-10 2019): {len(warn)}")
    for w in warn:
        print("  ", w["code"], "|", w["text"], "|", w["official"], "|", w.get("source"))
