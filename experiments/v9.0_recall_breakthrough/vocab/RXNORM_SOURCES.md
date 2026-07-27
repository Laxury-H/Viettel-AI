# RxNorm - nguon du lieu offline (kiem chung 2026-07-27)

## File da tai ve thu muc nay
| File | Kich thuoc | Nguon | Giay phep |
|---|---|---|---|
| RxNorm_full_prescribe_current.zip | 74.2 MB | https://download.nlm.nih.gov/rxnorm/RxNorm_full_prescribe_07062026.zip | **KHONG can dang ky, khong han che** |
| rxnorm_prescribe_concepts.tsv | 3.5 MB | dan xuat tu RXNCONSO.RRF | nhu tren |
| rxnorm_name_index.json | 7.5 MB | ten (ke ca SY/PSN/TMSY) -> [rxcui] | nhu tren |
| rxnorm_rxcui_tty.json | 0.8 MB | rxcui -> TTY | nhu tren |
| rxcui_verified.json | - | 70 RXCUI dang dung, xac minh qua RxNav | - |
| rxnorm_fix_candidates.json | - | de xuat sua | - |

CANH BAO: file `rxnorm_prescribe_current.zip` (52 MB) co san trong thu muc nay **KHONG phai zip hop le**
(zipfile bao "File is not a zip file") - nhieu kha nang la trang loi HTML. Nen xoa, dung file moi.

## Ba kenh phan phoi RxNorm
1. **RxNav REST API** (https://rxnav.nlm.nih.gov/REST/...) - mien phi, khong can key, KHONG duoc dung luc
   suy luan vi phai goi mang. Chi dung luc phat trien de tra cuu.
2. **RxNorm Full Release** (RxNorm_full_MMDDYYYY.zip, ~1.5 GB) tai
   https://download.nlm.nih.gov/umls/kss/rxnorm/RxNorm_full_current.zip
   -> **BAT BUOC co tai khoan UTS/UMLS** (mien phi nhung phai dang ky + chap nhan license).
   Chua toan bo synonym INN/Anh (paracetamol, salbutamol, frusemide...) va thuoc khong ban o My.
3. **RxNorm Current Prescribable Content** (RxNorm_full_prescribe_MMDDYYYY.zip, 74 MB)
   -> **KHONG can login, khong han che giay phep**. Day la file da tai. Chi chua thuoc dang luu hanh o My.
   NLM ghi ro: "provides this subset without any licensing restrictions."

## Do phu cua subset mien phi voi bang ma hien tai
68/70 RXCUI dang dung co trong subset. Thieu 2: 10826 (trimetazidine), 17627 (alverine)
- deu la thuoc khong luu hanh o My, chi co trong full release.

## Han che quan trong
Name index tu subset **khong co** cac ten INN/Anh ma benh an Viet Nam hay dung:
paracetamol, salbutamol, frusemide, glyceryl trinitrate, adrenaline... RxNorm full co day du.
Neu khong lay duoc full release, phai hard-code bang synonym VN/INN -> RXCUI.

## Cau truc TTY (nguon: https://www.nlm.nih.gov/research/umls/rxnorm/docs/appendix5.html)
IN=Ingredient (fluoxetine) | PIN=Precise Ingredient (fluoxetine hydrochloride)
MIN=Multiple Ingredients (fluoxetine/olanzapine) | BN=Brand Name (Prozac)
SCDC=ingredient+strength | SCDF=ingredient+dose form | SCD=ingredient+strength+dose form
SBDC/SBDF/SBD = tuong ung co brand | BPCK/GPCK = pack

### Quy uoc gan ma de xuat
- Mention chi la ten hoat chat ("omeprazole", "paracetamol")  -> **IN** (7646, 161)
- Ten hoat chat da dang muoi cu the ("alverin citrate")        -> **PIN** neu co (71767), khong thi IN
- Phoi hop nhieu hoat chat ("cotrimoxazol")                    -> **MIN** (10831)
- Ten biet duoc tran ("Tylenol", "Crestor", "Zosyn")           -> **BN** (202433, 320864, 74170)
- Ten generic + lieu + dang bao che ("acetaminophen 500mg")    -> **SCD** (198440)
- Biet duoc + lieu + dang ("Coumadin 3mg vien")                -> **SBD** (neu khong co thi SCD)
- KHONG nen dung SCDC lam ma cuoi (la thanh phan, khong phai thuoc hoan chinh)
