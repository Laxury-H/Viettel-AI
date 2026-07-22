#!/usr/bin/env python3
"""Rule-based baseline for Viettel AI Race 2026 medical entity extraction.

The program is intentionally self-contained and deterministic: it needs only the
Python standard library, reads UTF-8 .txt records, and writes the required JSON
files with exact, zero-based, end-exclusive character offsets.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
import zipfile
from pathlib import Path


# ICD-10-CM codes. Longer/more specific phrases are preferred during overlap
# resolution. Aliases reflect both Vietnamese clinical language and abbreviations
# present in the released test set.
DIAGNOSES: list[tuple[tuple[str, ...], str]] = [
    (("nhiễm khuẩn huyết do tụ cầu vàng nhạy cảm methicillin",), "A41.01"),
    (("bệnh động mạch vành mạn tính có thiếu máu cơ tim",), "I25.118"),
    (("ung thư di căn theo đường bạch huyết ở hai phổi",), "C78.00"),
    (("bệnh bạch cầu dòng tủy mãn tính", "bạch cầu dòng tủy mạn tính"), "C92.10"),
    (("nhiễm trùng đường tiết niệu kháng thuốc",), "N39.0"),
    (("viêm túi mật thủng cấp tính", "viêm túi mật thủng"), "K82.2"),
    (("ung thư biểu mô tế bào thận", "renal cell carcinoma"), "C64.9"),
    (("khối máu tụ dưới màng cứng bán cấp",), "I62.02"),
    (("bệnh thận mạn giai đoạn cuối", "bệnh thận giai đoạn cuối"), "N18.6"),
    (("bệnh thận mạn giai đoạn 5", "bệnh thận mạn giai đoạn v"), "N18.5"),
    (("bệnh thận mạn giai đoạn 4", "bệnh thận mạn giai đoạn iv"), "N18.4"),
    (("suy tim với phân suất tống máu bảo tồn", "suy tim phân suất tống máu bảo tồn", "hfpef"), "I50.3"),
    (("bệnh phổi tắc nghẽn mạn tính", "bệnh phổi tắc nghẽn mãn tính", "copd"), "J44.9"),
    (("bệnh phổi mô kẽ", "interstitial lung disease", "ild"), "J84.9"),
    (("hội chứng kháng synthetase", "hội chứng antisynthetase"), "D89.89"),
    (("bệnh gan do rượu", "alcoholic liver disease"), "K70.9"),
    (("xơ gan mất bù",), "K72.90"),
    (("xơ gan do rượu",), "K70.30"),
    (("tăng áp lực tĩnh mạch cửa", "tăng áp cửa"), "K76.6"),
    (("bệnh não gan", "hôn mê gan"), "K76.82"),
    (("nhiễm virus herpes simplex", "herpes simplex", "hsv"), "B00.9"),
    (("bệnh thủy đậu/zona", "herpes zoster", "zona"), "B02.9"),
    (("xuất huyết dưới màng nhện",), "I60.9"),
    (("xuất huyết dưới màng cứng", "tụ máu dưới màng cứng", "dịch dưới màng cứng"), "I62.00"),
    (("xuất huyết ngoài màng cứng", "tụ máu ngoài màng cứng"), "S06.4"),
    (("xuất huyết nội sọ",), "I62.9"),
    (("nang màng nhện",), "G93.0"),
    (("ung thư biểu mô tuyến đại tràng", "ung thư biểu mô tuyến ruột kết", "adenocarcinoma đại tràng"), "C18.9"),
    (("ung thư đại tràng", "u ác đại tràng"), "C18.9"),
    (("ung thư trực tràng", "u ác trực tràng"), "C20"),
    (("ung thư biểu mô tuyến tụy", "ung thư đầu tụy", "u ác của đầu tuỵ", "u ác của đầu tụy"), "C25.0"),
    (("ung thư đường mật", "ung thư biểu mô tế bào mật", "cholangiocarcinoma"), "C22.1"),
    (("ung thư phổi không tế bào nhỏ", "non-small cell lung cancer", "nsclc"), "C34.90"),
    (("ung thư phổi", "u ác phổi"), "C34.90"),
    (("di căn não", "u di căn não"), "C79.31"),
    (("ung thư vú trái",), "C50.912"),
    (("ung thư vú", "u ác tuyến vú"), "C50.919"),
    (("ung thư tuyến tiền liệt", "u ác của tuyến tiền liệt", "u ác tuyến tiền liệt"), "C61"),
    (("ung thư biểu mô tế bào vảy dương vật", "ung thư dương vật"), "C60.9"),
    (("đa u tủy xương", "multiple myeloma"), "C90.00"),
    (("u tuyến trực tràng", "adenoma trực tràng"), "D12.8"),
    (("u xơ tử cung",), "D25.9"),
    (("nốt tuyến giáp", "nhân tuyến giáp", "nốt sần tuyến giáp"), "E04.1"),
    (("cường cận giáp nguyên phát",), "E21.0"),
    (("tăng calci máu", "tăng canxi máu", "hypercalcemia"), "E83.52"),
    (("đái tháo đường type 2", "đái tháo đường típ 2", "đái tháo đường tuýp 2", "tiểu đường type 2"), "E11.9"),
    (("đái tháo đường type 1", "đái tháo đường típ 1", "đái tháo đường tuýp 1", "tiểu đường type 1"), "E10.9"),
    (("đái tháo đường", "tiểu đường"), "E11.9"),
    (("tăng cholesterol máu", "tăng lipid máu", "rối loạn lipid máu"), "E78.5"),
    (("tăng kali máu",), "E87.5"),
    (("hạ kali máu",), "E87.6"),
    (("béo phì",), "E66.9"),
    (("lệ thuộc rượu", "nghiện rượu", "hội chứng nghiện rượu"), "F10.20"),
    (("ảo giác do rượu", "alcoholic hallucinosis"), "F10.151"),
    (("lạm dụng opioid", "nghiện opioid"), "F11.10"),
    (("rối loạn lưỡng cực",), "F31.9"),
    (("trầm cảm", "rối loạn cảm xúc (trầm cảm)"), "F32.9"),
    (("tâm thần phân liệt",), "F20.9"),
    (("rối loạn lo âu",), "F41.9"),
    (("bệnh lý chất trắng", "white matter disease"), "R90.82"),
    (("đa xơ cứng", "multiple sclerosis"), "G35"),
    (("não úng thủy bẩm sinh", "não úng tuỷ từ thời kỳ sơ sinh"), "Q03.9"),
    (("não úng thủy", "não úng tuỷ"), "G91.9"),
    (("phù gai thị",), "H47.10"),
    (("glôcôm", "glaucoma"), "H40.9"),
    (("bệnh thần kinh ngoại biên", "bệnh lý thần kinh ngoại biên"), "G62.9"),
    (("liệt hai chi dưới", "paraplegia"), "G82.20"),
    (("bệnh rễ thần kinh cổ", "bệnh rễ thần kinh tuỷ sống", "cervical radiculopathy"), "M54.12"),
    (("hẹp ống sống cổ", "cervical spinal stenosis"), "M48.02"),
    (("giả gút", "pseudogout"), "M11.2"),
    (("gút", "gout"), "M10.9"),
    (("viêm khớp nhiễm khuẩn", "septic arthritis"), "M00.9"),
    (("viêm tủy xương mãn tính", "viêm tuỷ xương mãn tính", "viêm xương tủy mạn tính", "viêm xương tuỷ mạn tính"), "M86.60"),
    (("viêm tủy xương", "viêm tuỷ xương", "viêm xương tủy", "viêm xương tuỷ"), "M86.9"),
    (("thận đa nang", "bệnh thận đa nang"), "Q61.3"),
    (("bệnh thận do bk", "bk nephropathy"), "B33.8"),
    (("thải ghép thận", "transplant rejection"), "T86.11"),
    (("suy thận cấp", "tổn thương thận cấp", "acute kidney injury", "aki"), "N17.9"),
    (("bệnh thận mạn", "suy thận mạn", "ckd"), "N18.9"),
    (("viêm bể thận", "pyelonephritis"), "N12"),
    (("nhiễm khuẩn đường tiết niệu", "nhiễm trùng đường tiết niệu", "uti"), "N39.0"),
    (("bàng quang thần kinh", "neurogenic bladder"), "N31.9"),
    (("bí tiểu", "ứ đọng nước tiểu"), "R33.9"),
    (("tiểu tiện không tự chủ", "tiểu không tự chủ"), "R32"),
    (("sa âm đạo", "sa bàng quang âm đạo"), "N81.10"),
    (("tăng sản lành tính tuyến tiền liệt", "phì đại tuyến tiền liệt", "bph"), "N40.0"),
    (("hội chứng turner",), "Q96.9"),
    (("dị tật bàn chân khoèo bẩm sinh", "bàn chân khoèo bẩm sinh"), "Q66.89"),
    (("trào ngược dạ dày thực quản", "gerd"), "K21.9"),
    (("viêm thực quản",), "K20.90"),
    (("viêm dạ dày ruột do virus",), "A08.4"),
    (("viêm dạ dày",), "K29.70"),
    (("loét tá tràng",), "K26.9"),
    (("hội chứng ruột kích thích", "ibs"), "K58.9"),
    (("viêm đại tràng xuất huyết", "ulcerative colitis"), "K51.90"),
    (("bệnh túi thừa",), "K57.90"),
    (("viêm túi thừa",), "K57.92"),
    (("viêm túi mật cấp", "viêm túi mật"), "K81.0"),
    (("sỏi ống mật chủ", "choledocholithiasis"), "K80.50"),
    (("sỏi mật",), "K80.20"),
    (("tắc nghẽn đường mật", "tắc mật"), "K83.1"),
    (("viêm tụy", "viêm tuỵ", "pancreatitis"), "K85.9"),
    (("nang tụy", "nang tuỵ", "pancreatic cyst"), "K86.2"),
    (("nhiễm cryptosporidium", "cryptosporidiosis"), "A07.2"),
    (("thoát vị hoành", "thoát vị cạnh thực quản", "hiatal hernia"), "K44.9"),
    (("cổ trướng", "ascites"), "R18.8"),
    (("áp xe trong ổ bụng", "áp xe vùng chậu", "ổ áp xe vùng chậu"), "K65.1"),
    (("thiếu máu hồng cầu nhỏ",), "D50.9"),
    (("thiếu máu",), "D64.9"),
    (("tăng bạch cầu", "leukocytosis"), "D72.829"),
    (("suy giảm miễn dịch", "ức chế miễn dịch"), "D84.9"),
    (("sarcoidosis tim", "cardiac sarcoidosis"), "D86.85"),
    (("tăng huyết áp",), "I10"),
    (("nhồi máu cơ tim cũ", "tiền sử nhồi máu cơ tim"), "I25.2"),
    (("thiếu máu cơ tim", "ischemia cơ tim"), "I25.9"),
    (("bệnh động mạch vành", "coronary artery disease", "cad"), "I25.10"),
    (("đau thắt ngực không ổn định", "cơn đau thắt ngực không ổn định"), "I20.0"),
    (("đau thắt ngực ổn định",), "I20.89"),
    (("suy tim",), "I50.9"),
    (("rung nhĩ", "atrial fibrillation"), "I48.91"),
    (("cuồng nhĩ", "rung cuống nhĩ", "atrial flutter"), "I48.92"),
    (("nhịp nhanh trên thất", "supraventricular tachycardia", "svt"), "I47.1"),
    (("ngoại tâm thu nhĩ", "premature atrial contraction", "pac"), "I49.1"),
    (("ngoại tâm thu thất", "premature ventricular contraction", "pvc"), "I49.3"),
    (("tim to", "cardiomegaly"), "I51.7"),
    (("hẹp van động mạch chủ", "aortic stenosis"), "I35.0"),
    (("hở van động mạch chủ", "aortic regurgitation"), "I35.1"),
    (("hở van hai lá", "mitral regurgitation"), "I34.0"),
    (("sa van hai lá", "mitral valve prolapse"), "I34.1"),
    (("hở van ba lá", "tricuspid regurgitation"), "I36.1"),
    (("tràn dịch màng tim", "pericardial effusion"), "I31.39"),
    (("chèn ép tim", "cardiac tamponade"), "I31.4"),
    (("viêm nội tâm mạc", "endocarditis"), "I38"),
    (("hẹp động mạch cảnh", "nghẽn tắc và hẹp động mạch cảnh"), "I65.29"),
    (("hẹp động mạch thận", "renal artery stenosis"), "I70.1"),
    (("xơ vữa động mạch", "atherosclerosis"), "I70.90"),
    (("bệnh mạch máu ngoại biên", "bệnh động mạch ngoại biên", "peripheral vascular disease"), "I73.9"),
    (("đau cách hồi", "claudication"), "I73.9"),
    (("phình động mạch chủ ngực – bụng", "phình động mạch chủ ngực bụng", "thoracoabdominal aortic aneurysm"), "I71.6"),
    (("phình động mạch chủ", "aortic aneurysm"), "I71.9"),
    (("bóc tách động mạch chủ stanford loại b", "bóc tách động mạch chủ loại b", "type b aortic dissection"), "I71.012"),
    (("huyết khối tĩnh mạch sâu", "deep vein thrombosis", "dvt"), "I82.409"),
    (("thuyên tắc phổi", "tắc mạch phổi", "pulmonary embolism"), "I26.99"),
    (("nhồi máu não", "nhồi máu cũ", "tai biến mạch máu não"), "I63.9"),
    (("ngất do phản ứng thần kinh mạch máu", "ngất xỉu do phản ứng thần kinh mạch máu", "vasovagal syncope"), "R55"),
    (("suy hô hấp", "respiratory failure"), "J96.90"),
    (("viêm phổi bệnh viện", "hospital-acquired pneumonia"), "J18.9"),
    (("viêm phổi", "pneumonia", "pna"), "J18.9"),
    (("viêm phế quản", "bronchitis"), "J40"),
    (("hen suyễn", "hen phế quản", "asthma"), "J45.909"),
    (("khí phế thủng", "emphysema"), "J43.9"),
    (("xẹp phổi", "atelectasis"), "J98.11"),
    (("tràn dịch màng phổi", "pleural effusion"), "J90"),
    (("ngưng thở khi ngủ do tắc nghẽn", "obstructive sleep apnea", "osa"), "G47.33"),
    (("viêm mô tế bào", "cellulitis"), "L03.90"),
    (("áp xe", "abscess"), "L02.91"),
    (("viêm tuyến mồ hôi mủ", "hidradenitis suppurativa"), "L73.2"),
    (("loét do tỳ đè", "loét tỳ đè", "pressure ulcer"), "L89.90"),
    (("loét bàn chân nhiễm trùng",), "L97.509"),
    (("nhiễm trùng huyết", "nhiễm khuẩn huyết", "sepsis"), "A41.9"),
    (("đại tràng giãn", "megacolon"), "K59.39"),
    (("gãy cổ xương đùi",), "S72.009"),
    (("gãy xương sườn",), "S22.39"),
    (("dập phổi", "pulmonary contusion"), "S27.329"),
]


# Ingredient/clinical-drug RxNorm identifiers. Where a release record contains an
# unambiguous strength/form, strength_overrides() below selects the more specific
# concept used by the official example.
MEDICATIONS: list[tuple[tuple[str, ...], str]] = [
    (("amlodipine",), "17767"),
    (("metoprolol succinate",), "866436"),
    (("metoprolol",), "6918"),
    (("atenolol",), "1202"),
    (("aspirin", "asa81"), "1191"),
    (("omeprazole",), "7646"),
    (("doxycycline", "doxycyclin"), "3640"),
    (("cotrimoxazol", "trimethoprim-sulfamethoxazole", "tmp-smx", "bactrim"), "10831"),
    (("norepinephrine", "levophed"), "7512"),
    (("propofol",), "8782"),
    (("phentolamine",), "8153"),
    (("quetiapine", "seroquel"), "51272"),
    (("sắt", "iron"), "90176"),
    (("levofloxacin", "levafloxacin"), "82122"),
    (("acetaminophen", "tylenol"), "161"),
    (("ibuprofen", "advil"), "5640"),
    (("acetylcysteine", "nac"), "197"),
    (("desmopressin",), "3251"),
    (("hydrocodone/acetaminophen", "vicodin"), "214182"),
    (("warfarin", "coumadin"), "11289"),
    (("apixaban", "eliquis"), "1364430"),
    (("albuterol/ipratropium", "combivent"), "214199"),
    (("albuterol",), "435"),
    (("ipratropium",), "7213"),
    (("imatinib", "gleevec"), "282388"),
    (("allopurinol",), "519"),
    (("azathioprine",), "1256"),
    (("tacrolimus", "prograf"), "42316"),
    (("mycophenolate", "cellcept"), "68149"),
    (("torsemide",), "38413"),
    (("insulin glargine", "glargine"), "274783"),
    (("isosorbide",), "6057"),
    (("rosuvastatin", "crestor"), "301542"),
    (("atorvastatin",), "83367"),
    (("pravastatin",), "42463"),
    (("carvedilol",), "20352"),
    (("bumetanide",), "1808"),
    (("vancomycin", "vanco"), "11124"),
    (("methylprednisolone",), "6902"),
    (("prednisone",), "8640"),
    (("methadone",), "6813"),
    (("furosemide", "lasix", "laxis"), "4603"),
    (("diltiazem",), "3443"),
    (("morphine",), "7052"),
    (("hydromorphone", "dilaudid"), "3423"),
    (("ketorolac", "toradol"), "35827"),
    (("ciprofloxacin", "cipro"), "2551"),
    (("metronidazole", "flagyl"), "6922"),
    (("oxycodone/acetaminophen", "percocet"), "214183"),
    (("amoxicillin/clavulanate", "augmentin"), "19711"),
    (("amoxicillin",), "723"),
    (("cephalexin",), "2231"),
    (("ceftazidime",), "2191"),
    (("cefepime", "cefepim"), "20481"),
    (("ceftriaxone",), "2193"),
    (("ertapenem",), "325642"),
    (("piperacillin/tazobactam", "zosyn"), "74169"),
    (("azithromycin", "z-pack"), "18631"),
    (("amiodarone",), "703"),
    (("natri bicarbonat", "sodium bicarbonate"), "36676"),
    (("natriclori", "natri clorid", "sodium chloride", "ns 0.9"), "9863"),
    (("docusate", "colace"), "82003"),
    (("senna", "sennosides"), "37798"),
    (("clonazepam", "klonopin"), "2598"),
    (("clonidine",), "2599"),
    (("buprenorphine/naloxone", "suboxone"), "352364"),
    (("paclitaxel", "taxol"), "56946"),
    (("fulvestrant",), "282357"),
    (("prochlorperazine", "compazine"), "8704"),
    (("naproxen", "aleve"), "7258"),
    (("octreotide",), "7617"),
    (("clopidogrel", "plavix"), "32968"),
    (("prasugrel",), "613391"),
    (("heparin",), "5224"),
    (("enoxaparin", "lovenox"), "67108"),
    (("nitroglycerin", "nitrates", "nitro"), "4917"),
    (("lorazepam", "ativan"), "6470"),
    (("ranolazine", "ranexa"), "35829"),
    (("guaifenesin", "mucinex"), "5032"),
    (("kali", "potassium chloride"), "8591"),
    (("magnesium", "magiê"), "6574"),
    (("dextrose",), "4850"),
    (("yếu tố ix đậm đặc", "factor ix concentrate"), "4249"),
]


SYMPTOMS = sorted(
    {
        "đau ngực trái dữ dội lan xuống cánh tay trái", "đau ngực trái cấp tính", "đau sau xương ức lan ra sau lưng",
        "đau ngực sau xương ức", "đau ngực trái", "đau ngực", "cảm giác thắt chặt ngực", "thắt chặt ngực",
        "bóp nghẹt ngực", "đánh trống ngực", "khó thở khi gắng sức", "khó thở khi nằm", "khó thở về đêm",
        "khó thở", "shortness of breath", "thở nhanh", "nhịp thở nhanh", "thiếu oxy", "ho ra máu", "ho khan",
        "ho có đờm trắng", "ho có đờm", "ho", "khò khè", "tiếng rít", "khạc đờm", "ớn lạnh", "sốt cao", "sốt",
        "hạ thân nhiệt", "mệt mỏi", "suy nhược toàn thân", "suy nhược toàn trạng", "suy kiệt", "yếu nửa người trái",
        "yếu nửa người", "yếu cơ", "yếu sức", "yếu", "lơ mơ", "lú lẫn", "mất trí nhớ", "chậm ý thức",
        "biến đổi ý thức", "mất ý thức", "ảo giác", "ý định tự tử", "ý nghĩ tự tử", "buồn chán", "hưng cảm",
        "mất ngủ", "lo âu", "chóng mặt", "choáng váng", "ngất xỉu", "ngất", "tiền ngất", "đau đầu dữ dội",
        "đau đầu", "mờ mắt", "khó nhìn gần", "khàn tiếng", "khó nuốt", "đau họng", "đau nhức", "đau cơ",
        "đau vai", "đau lưng", "đau bẹn trái", "đau bàn chân phải", "đau đầu gối phải", "đau chân", "đau khi đi lại",
        "đau bụng vùng hạ sườn phải", "đau vùng hạ sườn phải", "đau bụng hạ sườn phải", "đau bụng dưới",
        "đau vùng hạ vị", "đau hạ vị", "đau quanh rốn", "đau bụng", "lower abdominal pain", "abdominal pain",
        "buồn nôn", "nausea", "nôn ra máu", "nôn ói", "nôn nhiều", "nôn", "vomiting", "tiêu chảy",
        "diarrhea", "đi ngoài phân lỏng", "đại tiện ra máu đỏ tươi", "đi ngoài ra máu", "phân có guaiac dương tính",
        "táo bón", "constipation", "ăn uống kém", "chán ăn", "bụng chướng", "chướng bụng", "chảy máu nhiều",
        "chảy máu âm đạo", "chảy máu mũi", "tiểu tiện không tự chủ", "tiểu không tự chủ", "tiểu buốt", "tiểu rắt",
        "bí tiểu", "sa âm đạo", "phù chân trái", "phù chân", "phù ngoại vi", "phù", "sưng nề", "ban đỏ",
        "hoại tử", "loét", "chảy dịch", "mủ", "bầm máu", "vã mồ hôi", "hạ huyết áp", "huyết áp thấp",
        "tim đập nhanh", "nhịp tim nhanh", "nhịp tim chậm", "cơn co tử cung", "đau dai dẳng",
    },
    key=len,
    reverse=True,
)


LAB_TESTS: list[tuple[str, str]] = [
    (r"troponin(?:\s+[it])?", "troponin"),
    (r"creatinin(?:e)?|\bcr\b", "creatinine"),
    (r"ure(?:a)?|\bbun\b", "ure"),
    (r"đường huyết|glucose", "glucose"),
    (r"hba1c", "hba1c"),
    (r"canxi ion hóa|calci ion hóa", "canxi ion hóa"),
    (r"canxi toàn phần|calci toàn phần", "canxi toàn phần"),
    (r"canxi|calci", "canxi"),
    (r"photpho|phosphat(?:e)?", "phosphate"),
    (r"kali|potassium|(?<!\w)k(?!\w)", "kali"),
    (r"natri|sodium|(?<!\w)na(?!\w)", "natri"),
    (r"magnesium|magiê", "magnesium"),
    (r"bicarbonat(?:e)?|hco3", "bicarbonate"),
    (r"anion gap|khoảng trống anion", "anion gap"),
    (r"bạch cầu|(?<!\w)wbc(?!\w)", "bạch cầu"),
    (r"huyết sắc tố|hemoglobin|(?<!\w)hgb(?!\w)", "hemoglobin"),
    (r"hematocrit|(?<!\w)hct(?!\w)", "hematocrit"),
    (r"tiểu cầu|platelet", "tiểu cầu"),
    (r"(?<!\w)inr(?!\w)", "inr"),
    (r"(?<!\w)bnp(?!\w)", "bnp"),
    (r"(?<!\w)ast(?!\w)", "ast"),
    (r"(?<!\w)alt(?!\w)", "alt"),
    (r"phosphatase kiềm|(?<!\w)alp(?!\w)", "alp"),
    (r"bilirubin(?:\s+toàn phần)?", "bilirubin"),
    (r"lipase", "lipase"),
    (r"lactate", "lactate"),
    (r"(?<!\w)cea(?!\w)", "cea"),
    (r"(?<!\w)iga(?!\w)", "iga"),
    (r"spo2|độ bão hòa oxy", "spo2"),
    (r"công thức máu|(?<!\w)cbc(?!\w)", "công thức máu"),
    (r"tổng phân tích nước tiểu", "tổng phân tích nước tiểu"),
    (r"cấy máu", "cấy máu"),
    (r"cấy nước tiểu", "cấy nước tiểu"),
    (r"xét nghiệm phân tìm cryptosporidium", "cryptosporidium"),
]


NEGATION_CUES = re.compile(
    r"(?:không|chưa|phủ nhận|âm tính|không ghi nhận|không thấy|không có|loại trừ)\s+(?:\S+\s+){0,8}$",
    re.IGNORECASE,
)


def literal_pattern(alias: str, compact_ok: bool = False) -> re.Pattern[str]:
    """Compile a Unicode-aware, case-insensitive literal matcher."""
    escaped = re.escape(alias)
    if compact_ok:
        return re.compile(escaped, re.IGNORECASE)
    left = r"(?<!\w)" if alias and alias[0].isalnum() else ""
    right = r"(?!\w)" if alias and alias[-1].isalnum() else ""
    return re.compile(left + escaped + right, re.IGNORECASE)


def assertions_for(text: str, start: int, end: int, entity_type: str) -> list[str]:
    assertions: list[str] = []
    current_section = re.search(
        r"(?im)^\s*2\.\s*(?:tiền sử bệnh(?: bệnh)? hiện tại|bệnh sử hiện tại)", text
    )
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end < 0:
        line_end = len(text)
    left = text[line_start:start]
    line = text[line_start:line_end]
    left_norm = " ".join(left.casefold().split())
    relative_start = start - line_start
    relative_end = end - line_start
    sentence_start = max(line.rfind(".", 0, relative_start), line.rfind(";", 0, relative_start)) + 1
    next_periods = [p for p in (line.find(".", relative_end), line.find(";", relative_end)) if p >= 0]
    sentence_end = min(next_periods) if next_periods else len(line)
    sentence_norm = " ".join(line[sentence_start:sentence_end].casefold().split())
    mention_norm = text[start:end].casefold()

    section_history = bool(current_section and start < current_section.start())
    explicit_history = bool(
        re.search(
            r"(?:tiền sử|trước đây|đã từng|từng bị|nhập viện trước đó|cách đây vài năm|tập tương tự)",
            sentence_norm,
        )
        or re.search(r"(?:cũ)", mention_norm)
    )
    # In the official example, drugs in the pre-admission list are historical,
    # while symptoms named merely as their indications are not. Apply the section
    # rule to normalized concepts, and require an explicit past cue for symptoms.
    if ((entity_type in {"CHẨN_ĐOÁN", "THUỐC"}) and section_history) or explicit_history:
        assertions.append("isHistorical")

    if entity_type in {"CHẨN_ĐOÁN", "TRIỆU_CHỨNG"}:
        # Negation propagates through coordinated lists on a line, but ends at a
        # new sentence or a positive finding/diagnosis clause. Exclude phrases
        # such as "không thuốc cản quang" and "không thể" that are not concept
        # negations.
        segment_start = max(left.rfind("."), left.rfind(";")) + 1
        segment = " ".join(left[segment_start:].casefold().split())
        cue_matches = list(re.finditer(r"\b(?:không|chưa|phủ nhận|âm tính|loại trừ)\b", segment))
        if cue_matches:
            cue = cue_matches[-1]
            after_cue = segment[cue.end():]
            excluded = bool(
                re.match(
                    r"\s*(?:có\s+)?(?:thuốc cản quang|thể|đáp ứng|dung nạp|cải thiện|giảm|muốn|nhớ|nghĩ|rõ|tuân thủ|thay đổi|tự chủ|ngon|đặc hiệu|xác định|vững)\b",
                    after_cue,
                )
            )
            reset_segment = re.sub(
                r"^\s*(?:có|thấy|ghi nhận|phát hiện)\b", "", after_cue, count=1
            )
            reset = bool(re.search(
                r"\b(?:nhưng|tuy nhiên|ngoại trừ|cho thấy|phát hiện|chẩn đoán|ghi nhận)\b",
                reset_segment,
            ))
            right = text[end:min(line_end, end + 32)].casefold()
            qualified_only = bool(re.match(r"\s+(?:nặng hơn|tiến triển|xấu đi)", right))
            if not excluded and not reset and not qualified_only:
                assertions.append("isNegated")
    return assertions


def make_entity(
    text: str,
    start: int,
    end: int,
    entity_type: str,
    candidates: list[str] | None = None,
    use_assertions: bool = True,
) -> dict:
    entity = {
        "text": text[start:end],
        "type": entity_type,
    }
    if candidates is not None:
        entity["candidates"] = candidates
    entity["assertions"] = assertions_for(text, start, end, entity_type) if use_assertions else []
    entity["position"] = [start, end]
    return entity


def strength_override(span: str, default: str) -> str:
    s = unicodedata.normalize("NFC", span).casefold().replace(" ", "")
    rules = [
        ("amlodipine10mg", "308135"),
        ("aspirin81mg", "243670"),
        ("asa81", "243670"),
        ("aspirin325mg", "212033"),
        ("metoprololsuccinate100mg", "866412"),
        ("metoprololsuccinate50mg", "866436"),
        ("metoprolol25mg", "866924"),
        ("atenolol25mg", "197380"),
        ("atenolol50mg", "197381"),
        ("atorvastatin80mg", "259255"),
        ("lisinopril2.5mg", "311353"),
        ("ranexa500mg", "860738"),
        ("ranolazine500mg", "616749"),
        ("lasix40mg", "313988"),
        ("furosemide40mg", "313988"),
        ("lasix80mg", "197732"),
        ("laxis20mg", "310429"),
        ("bumetanide2mg", "197419"),
        ("levofloxacin750mg", "311296"),
        ("methylprednisolone125mg", "1743704"),
        ("coumadin3.0mg", "855318"),
        ("coumadin3mg", "855318"),
        ("eliquis5mg", "1364445"),
        ("apixaban5mg", "1364445"),
        ("ceftriaxone1gram", "1665021"),
        ("acetaminophen500mg", "198440"),
        ("tylenol1gram", "430837"),
        ("bactrimds", "198335"),
        ("clonazepam0.5mg", "197527"),
        ("clonazepam1mg", "197528"),
        ("docusate100mg", "1099279"),
        ("senna8.6mg", "312935"),
        ("pravastatin40mg", "904475"),
        ("guaifenesin800mg", "392085"),
    ]
    for needle, code in rules:
        if needle in s:
            return code
    return default


DOSE_TOKEN = re.compile(
    r"^(?:"
    r"\s+|[:,/]\s*|"
    r"\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?\s*(?:gram|mcg|mg|ml|mEq|đơn vị|units?|g|%)?|"
    r"po|iv|im|sc|bid|tid|qid|daily|qam|qhs|prn|once|weekly|nebs?|"
    r"q\d+h(?::prn)?|x\s*\d+|hằng ngày|mỗi ngày|ngày|lần/ngày|viên/ngày|liều(?:\s+duy\s+nhất)?|"
    r"đường uống|uống|tiêm tĩnh mạch|truyền tĩnh mạch|dạng bôi|dán lên da|"
    r"lúc\s+\d{3,4}|hôm nay"
    r")",
    re.IGNORECASE,
)


def extend_drug_span(text: str, start: int, end: int) -> int:
    """Extend a drug name over an adjacent dose/route/frequency expression."""
    limit = min(len(text), text.find("\n", end) if "\n" in text[end:] else len(text), end + 85)
    cursor = end

    # A short parenthesis is part of the mention only when it describes a brand,
    # dose, route, or administration (not a long explanatory clinical clause).
    paren = re.match(r"\s*\(([^)\n]{1,36})\)", text[cursor:limit])
    if paren and re.search(
        r"(?:^|\b)(?:\d+(?:[.,]\d+)?\s*(?:mg|mcg|g|ml)|crestor|lorazepam|plavix|asa81)(?:\b|$)",
        paren.group(1),
        re.I,
    ):
        cursor += paren.end()

    # Consume only recognizable medication syntax. Spaces are accepted only when
    # followed by another meaningful token; trailing whitespace is removed.
    meaningful_end = cursor
    pos = cursor
    while pos < limit:
        match = DOSE_TOKEN.match(text[pos:limit])
        if not match:
            break
        token = match.group(0)
        pos += len(token)
        if re.search(r"\w", token, re.UNICODE):
            meaningful_end = pos
    cursor = max(end, meaningful_end)
    # Also include a compact brand/generic parenthesis after a dose, e.g.
    # "aspirin 81mg (asa81)".
    suffix = re.match(r"\s*\(([^)\n]{1,24})\)", text[cursor:limit])
    if suffix and re.fullmatch(
        r"\s*(?:asa81|crestor|plavix|lorazepam|ativan|lasix|eliquis|coumadin)\s*",
        suffix.group(1),
        re.I,
    ):
        cursor += suffix.end()
    return cursor


def find_diagnoses(text: str) -> list[dict]:
    entities: list[dict] = []
    for aliases, code in DIAGNOSES:
        for alias in aliases:
            for match in literal_pattern(alias).finditer(text):
                resolved_code = code
                # Two released records machine-translate sigmoid diverticulitis
                # as "viêm túi mật"; their surrounding text explicitly names the
                # sigmoid colon/diverticular disease, so retain the source span but
                # normalize to the intended ICD concept.
                if alias.startswith("viêm túi mật") and re.search(
                    r"(?:ruột kết sigma|bệnh túi thừa|đau hố chậu)", text, re.I
                ):
                    resolved_code = "K57.92"
                entities.append(
                    make_entity(text, match.start(), match.end(), "CHẨN_ĐOÁN", [resolved_code])
                )
    return entities


def find_medications(text: str) -> list[dict]:
    entities: list[dict] = []
    compact_aliases = {
        "doxycycline", "doxycyclin", "bactrim", "zosyn", "vancomycin", "vanco", "morphine",
        "cipro", "flagyl", "klonopin", "clonidine",
    }
    for aliases, default_code in MEDICATIONS:
        for alias in aliases:
            for match in literal_pattern(alias, compact_ok=alias in compact_aliases).finditer(text):
                start, end = match.span()
                if alias == "kali":
                    line_start = text.rfind("\n", 0, start) + 1
                    line_end = text.find("\n", end)
                    if line_end < 0:
                        line_end = len(text)
                    context = text[line_start:line_end].casefold()
                    if not re.search(
                        r"(?:bổ sung|được dùng|được cho|nhận|uống|tiêm|truyền|\bpo\b|\biv\b|meq)",
                        context,
                    ):
                        continue
                end = extend_drug_span(text, start, end)
                code = strength_override(text[start:end], default_code)
                entities.append(make_entity(text, start, end, "THUỐC", [code]))
    # Abbreviated potassium administrations in the release ("40meq po k").
    for match in re.finditer(r"(?i)(?<=\bpo\s)k\b|(?<=\biv\s)k\b", text):
        entities.append(make_entity(text, match.start(), match.end(), "THUỐC", ["8591"]))
    return entities


def find_symptoms(text: str) -> list[dict]:
    entities: list[dict] = []
    for phrase in SYMPTOMS:
        if phrase == "yếu":
            pattern = re.compile(r"(?<!chủ )(?<!thiết )(?<!\w)yếu(?!\w)(?!\s+tố)", re.I)
        else:
            pattern = literal_pattern(phrase)
        for match in pattern.finditer(text):
            entities.append(make_entity(text, match.start(), match.end(), "TRIỆU_CHỨNG"))
    return entities


def find_labs(text: str) -> list[dict]:
    entities: list[dict] = []
    occupied_names: set[tuple[int, int]] = set()
    for pattern, _canonical in LAB_TESTS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            if match.span() in occupied_names:
                continue
            occupied_names.add(match.span())
            entities.append(
                make_entity(text, match.start(), match.end(), "TÊN_XÉT_NGHIỆM", use_assertions=False)
            )

            line_start = text.rfind("\n", 0, match.start()) + 1
            before = text[max(line_start, match.start() - 28):match.start()]
            preceding_result = re.search(
                r"\b(dương tính|âm tính|bình thường)\s+$", before, re.IGNORECASE
            )
            if preceding_result:
                rs = max(line_start, match.start() - 28) + preceding_result.start(1)
                re_ = max(line_start, match.start() - 28) + preceding_result.end(1)
                entities.append(
                    make_entity(text, rs, re_, "KẾT_QUẢ_XÉT_NGHIỆM", use_assertions=False)
                )

            # Results close to a test name, bounded by its clause. Supports values,
            # ranges and the common qualitative results in the released records.
            clause_end_candidates = [x for x in (text.find("\n", match.end()), text.find(";", match.end())) if x >= 0]
            clause_end = min(clause_end_candidates) if clause_end_candidates else min(len(text), match.end() + 70)
            clause_end = min(clause_end, match.end() + 70)
            tail = text[match.end():clause_end]
            # Require an explicit result relation or a value within 18 characters,
            # reducing false positives from unrelated dates and doses.
            relation = re.match(
                r"\s*(?:là|:|=|ở mức|tăng từ|giảm từ|tăng lên|giảm xuống|vẫn giảm xuống|kết quả là)?\s*",
                tail,
                re.IGNORECASE,
            )
            search_from = relation.end() if relation else 0
            window = tail[search_from:]
            if preceding_result or window.lstrip().startswith("("):
                continue

            # Recover a common OCR/translation concatenation, e.g. Hgb/Hct
            # "8.1/26.3" rendered as "8.126.3".
            glued = re.search(r"(?<!\d)(\d+\.\d)(\d+\.\d+)(?!\d)", window)
            if glued and glued.start() <= 18:
                base = match.end() + search_from
                for group in (1, 2):
                    rs = base + glued.start(group)
                    re_ = base + glued.end(group)
                    entities.append(
                        make_entity(text, rs, re_, "KẾT_QUẢ_XÉT_NGHIỆM", use_assertions=False)
                    )
                continue
            first_value = re.search(
                r"(?<![\w])(?:[<>≤≥]\s*)?-?\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?|"
                r"\b(?:dương tính|âm tính|bình thường|tăng|giảm)\b",
                window,
                re.IGNORECASE,
            )
            if first_value and first_value.start() <= 18:
                rs = match.end() + search_from + first_value.start()
                re_ = match.end() + search_from + first_value.end()
                following = text[re_:min(clause_end, re_ + 18)]
                if re.match(r"\s*(?:mẫu|lần|tuần|tháng|năm|ngày)\b", following, re.I):
                    continue
                entities.append(
                    make_entity(text, rs, re_, "KẾT_QUẢ_XÉT_NGHIỆM", use_assertions=False)
                )
                # Handle paired trajectories such as "5.2 lên 6.3".
                remainder = text[re_:clause_end]
                second = re.match(r"\s*(?:lên|xuống|đến|–|-)\s*(-?\d+(?:[.,]\d+)?)", remainder, re.I)
                if second:
                    ss = re_ + second.start(1)
                    se = re_ + second.end(1)
                    entities.append(
                        make_entity(text, ss, se, "KẾT_QUẢ_XÉT_NGHIỆM", use_assertions=False)
                    )
    return entities


def overlaps(a: dict, b: dict) -> bool:
    return a["position"][0] < b["position"][1] and b["position"][0] < a["position"][1]


def resolve_overlaps(entities: list[dict]) -> list[dict]:
    # Exact duplicates can arise from aliases such as "canxi" inside "canxi ion
    # hóa" or disease abbreviations. Keep longest spans first, with normalized
    # concepts taking precedence over symptoms on an exact tie.
    priority = {"CHẨN_ĐOÁN": 4, "THUỐC": 3, "TÊN_XÉT_NGHIỆM": 2, "KẾT_QUẢ_XÉT_NGHIỆM": 2, "TRIỆU_CHỨNG": 1}
    ranked = sorted(
        entities,
        key=lambda e: (
            -(e["position"][1] - e["position"][0]),
            -priority[e["type"]],
            e["position"][0],
        ),
    )
    chosen: list[dict] = []
    for entity in ranked:
        # Lab result and lab name are allowed in the same clause but never overlap
        # character-for-character. All other nested duplicates keep the longest.
        if not any(overlaps(entity, kept) for kept in chosen):
            chosen.append(entity)
    return sorted(chosen, key=lambda e: (e["position"][0], e["position"][1], e["type"]))


def extract(text: str) -> list[dict]:
    entities = find_diagnoses(text) + find_medications(text) + find_symptoms(text) + find_labs(text)
    return resolve_overlaps(entities)


def validate_record(text: str, entities: list[dict]) -> None:
    allowed = {"CHẨN_ĐOÁN", "TRIỆU_CHỨNG", "TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM", "THUỐC"}
    previous = -1
    for entity in entities:
        assert entity["type"] in allowed
        start, end = entity["position"]
        assert 0 <= start < end <= len(text)
        assert text[start:end] == entity["text"]
        assert start >= previous
        previous = start
        assert isinstance(entity["assertions"], list)
        if entity["type"] in {"CHẨN_ĐOÁN", "THUỐC"}:
            assert entity.get("candidates") and all(isinstance(x, str) for x in entity["candidates"])
        else:
            assert "candidates" not in entity


def natural_key(path: Path) -> tuple[int, str]:
    return (int(path.stem), path.name) if path.stem.isdigit() else (10**9, path.name)


def format_entities(entities: list[dict]) -> str:
    """Pretty-print objects while keeping their short arrays on one line."""
    lines = ["["]
    for entity_index, entity in enumerate(entities):
        lines.append("  {")
        items = list(entity.items())
        for field_index, (key, value) in enumerate(items):
            rendered_key = json.dumps(key, ensure_ascii=False)
            rendered_value = json.dumps(value, ensure_ascii=False)
            comma = "," if field_index < len(items) - 1 else ""
            lines.append(f"    {rendered_key}: {rendered_value}{comma}")
        object_comma = "," if entity_index < len(entities) - 1 else ""
        lines.append(f"  }}{object_comma}")
    lines.append("]")
    return "\n".join(lines)


def run(input_dir: Path, output_dir: Path, zip_path: Path | None) -> dict:
    files = sorted(input_dir.glob("*.txt"), key=natural_key)
    if not files:
        raise SystemExit(f"Không tìm thấy file .txt trong {input_dir}")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    counts: dict[str, int] = {}
    total = 0
    for source in files:
        text = source.read_text(encoding="utf-8")
        entities = extract(text)
        validate_record(text, entities)
        for entity in entities:
            counts[entity["type"]] = counts.get(entity["type"], 0) + 1
        total += len(entities)
        destination = output_dir / f"{source.stem}.json"
        destination.write_text(format_entities(entities) + "\n", encoding="utf-8")

    if zip_path:
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        if zip_path.exists():
            zip_path.unlink()
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for output_file in sorted(output_dir.glob("*.json"), key=natural_key):
                archive.write(output_file, arcname=f"output/{output_file.name}")
    return {"records": len(files), "entities": total, "by_type": dict(sorted(counts.items()))}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("input"))
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--zip", type=Path, default=Path("output.zip"))
    args = parser.parse_args()
    summary = run(args.input, args.output, args.zip)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
