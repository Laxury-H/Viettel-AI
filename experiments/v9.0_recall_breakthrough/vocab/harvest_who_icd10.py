# -*- coding: utf-8 -*-
"""
Thu thap tieu de CHINH THUC WHO ICD-10 (ban 2019 - dung ban ma Bo Y te VN dua vao)
cho DUNG cac ma dang su dung trong v63_code_pairs.json.

Chi chay LUC PHAT TRIEN. Ket qua la file JSON tinh -> suy luan chay 100% offline.
Endpoint: icd.who.int/browse10/2019/en/JsonGetChildrenConcepts (cong khai, khong can khoa API).
"""
import json, os, re, time, urllib.request, urllib.parse, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BASE = "https://icd.who.int/browse10/2019/en/JsonGetChildrenConcepts"
ROOTS = "https://icd.who.int/browse10/2019/en/JsonGetRootConcepts?useHtml=false"
UA = {"User-Agent": "Mozilla/5.0 (research; ICD-10 title verification)"}
_cache = {}


def children(concept_id):
    if concept_id in _cache:
        return _cache[concept_id]
    url = BASE + "?" + urllib.parse.urlencode(
        {"ConceptId": concept_id, "useHtml": "false", "showAdvancedInfo": "false"})
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
    except Exception as e:
        print("  ! loi", concept_id, e)
        data = []
    out = {}
    for x in data:
        cid = x["ID"]
        lab = x["label"]
        # bo tien to ma trong label: "I64 Stroke, ..." -> "Stroke, ..."
        if lab.startswith(cid):
            lab = lab[len(cid):].strip()
        out[cid] = lab
    _cache[concept_id] = out
    time.sleep(0.25)
    return out


def main():
    pairs = json.load(open(os.path.join(ROOT, "v63_code_pairs.json"), encoding="utf-8"))
    codes = sorted({c.strip() for p in pairs for c in p["codes"] if not c.strip().isdigit()})
    print("can tra:", len(codes), "ma ICD")

    # 1. Lay danh sach chuong -> block
    print("buoc 1: lay cay chuong/block ...")
    with urllib.request.urlopen(urllib.request.Request(ROOTS, headers=UA), timeout=30) as r:
        chapters = {x["ID"] for x in json.loads(r.read().decode("utf-8"))}
    blocks = {}                        # "I60-I69" -> label
    for ch in chapters:
        for b, lab in children(ch).items():
            blocks[b] = lab
    print("  so block:", len(blocks))

    block_range = []
    for b in blocks:
        m = re.match(r"^([A-Z])(\d+)-([A-Z])(\d+)$", b)
        if m:
            block_range.append((m.group(1) + m.group(2), m.group(3) + m.group(4), b))

    def descend(block, cat, depth=0):
        """Chuong II long block nhieu tang (C00-C97 > C00-C75 > C15-C26 > C20)."""
        if depth > 4:
            return None
        kids = children(block)
        if cat in kids:
            return block
        for k in kids:
            m = re.match(r"^([A-Z]\d+)-([A-Z]\d+)$", k)
            if m and m.group(1) <= cat <= m.group(2):
                found = descend(k, cat, depth + 1)
                if found:
                    return found
        return None

    def find_block(cat):                # cat = ma 3 ky tu, vd "I64"
        cands = [b for lo, hi, b in block_range if lo[0] == cat[0] and lo <= cat <= hi]
        for b in cands:
            found = descend(b, cat)
            if found:
                return found
        return cands[0] if cands else None

    # 2. Tra tung ma
    print("buoc 2: tra tieu de ...")
    result = {}
    for c in codes:
        cat = c.split(".")[0]
        parent = cat if "." in c else find_block(cat)
        if parent is None:
            result[c] = {"found": False, "title": None, "note": "khong tim thay block cha"}
            continue
        sib = children(parent)
        if c in sib:
            result[c] = {"found": True, "title": sib[c], "parent": parent}
        else:
            result[c] = {"found": False, "title": None, "parent": parent,
                         "siblings": sorted(sib)[:12]}

    out = os.path.join(HERE, "who_icd10_2019_titles.json")
    json.dump(result, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    bad = [c for c, v in result.items() if not v["found"]]
    print(f"\nXAC NHAN CO TRONG WHO ICD-10 2019: {len(codes)-len(bad)}/{len(codes)}")
    if bad:
        print("KHONG TIM THAY:")
        for c in bad:
            print("  ", c, result[c].get("siblings"))
    print("->", out)


if __name__ == "__main__":
    main()
