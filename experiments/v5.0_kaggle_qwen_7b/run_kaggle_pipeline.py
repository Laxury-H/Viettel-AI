import os
import json
import re
import zipfile
import shutil
import time
from tqdm import tqdm
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import unicodedata

# ---------------------------------------------------------
# Configuration for Kaggle
# ---------------------------------------------------------
# In Kaggle, input datasets are typically mounted in /kaggle/input
INPUT_DIR = os.environ.get("KAGGLE_INPUT_DIR", "/kaggle/input/datasets/laxurie/data-main/input")
# We write output to /kaggle/working
OUTPUT_DIR = os.environ.get("KAGGLE_WORKING_DIR", "/kaggle/working/output")
ZIP_PATH = os.environ.get("KAGGLE_ZIP_PATH", "/kaggle/working/output.zip")
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# Import offline knowledge base from V4
DIAGNOSES = (
    {"aliases": ("thiếu men G6PD", "thiếu hụt men G6PD"), "code": "D75.A"},
    {"aliases": ("thiếu máu tan huyết", "thiếu máu do tan huyết"), "codes": ("D59.9", "D55.0")},
    {"aliases": ("thiếu máu",), "code": "D64.9"},
    {"aliases": ("bại não",), "code": "G80.9"},
    {"aliases": ("bệnh Kawasaki", "Kawasaki"), "code": "M30.3"},
    {"aliases": ("viêm tim", "viêm cơ tim"), "code": "I51.4"},
    {"aliases": ("phình giãn động mạch vành", "phình động mạch vành"), "code": "I25.41"},
    {"aliases": ("nhồi máu cơ tim",), "code": "I21.9"},
    {"aliases": ("nhồi máu cơ tim ST chênh", "STEMI"), "code": "I21.3"},
    {"aliases": ("nhồi máu không ST chênh", "NSTEMI"), "code": "I21.4"},
    {"aliases": ("suy tim không do thiếu máu cơ tim", "suy tim, không đặc hiệu", "suy tim"), "code": "I50.9"},
    {"aliases": ("hội chứng Parkinson", "bệnh Parkinson"), "code": "G20"},
    {"aliases": ("đau thắt ngực không ổn định", "cơn đau thắt ngực không ổn định"), "code": "I20.0"},
    {"aliases": ("đau thắt ngực ổn định",), "code": "I20.89"},
    {"aliases": ("hội chứng vành cấp",), "code": "I24.9"},
    {"aliases": ("bệnh ba thân động mạch vành nghiêm trọng", "bệnh ba thân động mạch vành", "bệnh mạch vành", "BỆNH MẠCH VÀNH", "xơ vữa động mạch vành", "bệnh động mạch vành"), "code": "I25.10"},
    {"aliases": ("bệnh tim mạch do xơ vữa động mạch", "xơ vữa động mạch"), "code": "I70.90"},
    {"aliases": ("bệnh tim mạch",), "code": "I51.9"},
    {"aliases": ("hội chứng ruột kích thích",), "code": "K58.9"},
    {"aliases": ("loét tá tràng",), "code": "K26.9"},
    {"aliases": ("viêm thực quản độ C", "viêm thực quản"), "code": "K20.90"},
    {"aliases": ("loét thực quản",), "code": "K22.10"},
    {"aliases": ("viêm dạ dày ruột do virus",), "code": "A08.4"},
    {"aliases": ("cryptosporidiosis", "nhiễm cryptosporidium", "cryptosporidium"), "code": "A07.2"},
    {"aliases": ("ung thư tuyến giáp",), "code": "C73"},
    {"aliases": ("hội chứng buồng trứng đa nang",), "code": "E28.2"},
    {"aliases": ("vô sinh",), "code": "N97.9"},
    {"aliases": ("vô sinh thứ phát",), "code": "N46.9"},
    {"aliases": ("ung thư biểu mô tế bào mật", "ung thư đường mật", "cholangiocarcinoma"), "code": "C22.1"},
    {"aliases": ("tăng huyết áp nguyên phát", "bệnh tăng HA vô căn", "tăng huyết áp", "ăng huyết áp"), "code": "I10"},
    {"aliases": ("tăng cholesterol máu đơn thuần",), "code": "E78.00"},
    {"aliases": ("rối loạn lipid máu", "tăng lipid máu"), "code": "E78.5"},
    {"aliases": ("Tiểu đường loại 1 đái tháo đường", "tiểu đường loại 1", "đái tháo đường type 1", "đái tháo đường típ 1"), "code": "E10.9"},
    {"aliases": ("đái tháo đường típ 2", "đái tháo đường typ II", "đái tháo đường type 2", "tiểu đường type 2", "đái tháo đường", "tiểu đường"), "code": "E11.9"},
    {"aliases": ("xuất huyết dưới màng nhện", "xuất huyết dưới nhện"), "code": "I60.9"},
    {"aliases": ("bầm dập nhu mô", "dập não"), "code": "S06.33"},
    {"aliases": ("nang màng nhện",), "code": "G93.0"},
    {"aliases": ("tụ máu dưới màng cứng mạn tính", "khối máu tụ dưới màng cứng"), "code": "I62.03"},
    {"aliases": ("tụ máu ngoài màng cứng phải cấp tính", "tụ máu ngoài màng cứng"), "code": "S06.4"},
    {"aliases": ("bệnh bàn chân bẹt", "bàn chân bẹt bẩm sinh", "bàn chân bẹt"), "code": "Q66.50"},
    {"aliases": ("rối loạn cảm xúc (trầm cảm)", "trầm cảm"), "code": "F32.9"},
    {"aliases": ("rối loạn lo âu",), "code": "F41.9"},
    {"aliases": ("Lạm dụng chất kích thích, chất gây nghiện opioid", "lạm dụng chất gây nghiện opioid", "lạm dụng opioid", "nghiện opioid", "chất gây nghiện opioid"), "code": "F11.10"},
    {"aliases": ("hội chứng nghiện rượu", "nghiện rượu", "lệ thuộc rượu"), "code": "F10.20"},
    {"aliases": ("bệnh lý chất trắng",), "code": "R90.82"},
    {"aliases": ("bệnh phổi kẽ", "bệnh phổi mô kẽ", "viêm phổi kẽ"), "code": "J84.9"},
    {"aliases": ("hội chứng kháng enzym tổng hợp protein", "hội chứng kháng synthetase", "hội chứng antisynthetase"), "code": "D89.89"},
    {"aliases": ("béo phì",), "code": "E66.9"},
    {"aliases": ("suy giảm miễn dịch do sử dụng corticoid kéo dài", "suy giảm miễn dịch do sử dụng corticoid"), "code": "D84.821"},
    {"aliases": ("viêm mô tế bào",), "code": "L03.90"},
    {"aliases": ("nhiễm virus Herpes simplex", "Herpes simplex", "HSV"), "code": "B00.9"},
    {"aliases": ("bệnh thủy đậu/Zona", "herpes zoster", "Zona"), "code": "B02.9"},
    {"aliases": ("bệnh dại",), "code": "A82.9"},
    {"aliases": ("mày đay vô căn", "MÀY ĐAY VÔ CĂN", "bệnh lý mày đay vô căn"), "code": "L50.1"},
    {"aliases": ("mày đay mạn tính", "MÀY ĐAY MẠN TÍNH", "mày đay mạn"), "code": "L50.8"},
    {"aliases": ("bệnh bạch cầu dòng tủy mãn tính", "bạch cầu dòng tủy mạn tính", "CML"), "code": "C92.10"},
    {"aliases": ("bệnh thận mạn giai đoạn 4", "bệnh thận mạn tính Giai đoạn 4", "CKD4"), "code": "N18.4"},
    {"aliases": ("suy thận mạn giai đoạn V", "suy thận mạn giai đoạn 5", "bệnh thận mạn giai đoạn 5", "CKD5"), "code": "N18.5"},
    {"aliases": ("bệnh thận mạn tính", "bệnh thận mạn", "suy thận mạn", "CKD"), "code": "N18.9"},
    {"aliases": ("tăng sản lành tính tuyến tiền liệt", "tăng sản tuyến tiền liệt", "phì đại tuyến tiền liệt", "BPH"), "code": "N40.0"},
    {"aliases": ("hẹp ống sống C4-5, C5-6, C6-7", "hẹp ống sống cổ"), "code": "M48.02"},
    {"aliases": ("hẹp ống sống",), "code": "M48.00"},
    {"aliases": ("giả gout", "giả gút", "pseudogout"), "code": "M11.2"},
    {"aliases": ("viêm quanh răng", "viêm nha chu"), "code": "K05.30"},
    {"aliases": ("thiếu canxi",), "code": "E58"},
    {"aliases": ("thiếu hụt vitamin K",), "code": "E56.1"},
    {"aliases": ("loãng xương",), "code": "M81.0"},
    {"aliases": ("sâu răng",), "code": "K02.9"},
    {"aliases": ("viêm khớp dạng thấp",), "code": "M06.9"},
    {"aliases": ("bệnh mạch máu ngoại biên", "bệnh động mạch ngoại biên"), "code": "I73.9"},
    {"aliases": ("đợt cấp COPD",), "code": "J44.1"},
    {"aliases": ("bệnh phổi tắc nghẽn mạn tính", "COPD"), "code": "J44.9"},
    {"aliases": ("ngưng thở khi ngủ do tắc nghẽn", "ngừng thở khi ngủ do tắc nghẽn", "OSA"), "code": "G47.33"},
    {"aliases": ("ngưng thở khi ngủ", "ngừng thở khi ngủ"), "code": "G47.30"},
    {"aliases": ("ung thư biểu mô tế bào vảy xâm nhập của dương vật", "ung thư biểu mô tế bào vảy dương vật", "ung thư dương vật"), "code": "C60.9"},
    {"aliases": ("viêm túi mật cấp",), "code": "K81.0"},
    {"aliases": ("sỏi mật",), "code": "K80.20"},
    {"aliases": ("bệnh amyloidosis chuỗi nhẹ",), "code": "E85.81"},
    {"aliases": ("amyloidosis di truyền hoặc gia đình",), "code": "E85.2"},
    {"aliases": ("rối loạn chuyển hóa tinh bột (amyloidosis)", "bệnh thoái hóa tinh bột", "bệnh amyloidosis", "amyloidosis"), "code": "E85.9"},
    {"aliases": ("viêm hang vị sung huyết", "viêm sung huyết hang vị dạ dày", "viêm dạ dày"), "code": "K29.70"},
    {"aliases": ("sỏi đoạn cuối ống mật chủ", "sỏi ống dẫn mật chung đoạn cuối", "sỏi ống mật chủ"), "code": "K80.50"},
    {"aliases": ("não úng tuỷ từ thời kỳ sơ sinh", "não úng thủy bẩm sinh"), "code": "Q03.9"},
    {"aliases": ("não úng thủy", "não úng tuỷ"), "code": "G91.9"},
    {"aliases": ("phù gai thị",), "code": "H47.10"},
    {"aliases": ("tăng nhãn áp", "glôcôm", "glaucoma"), "code": "H40.9"},
    {"aliases": ("viêm tụy", "viêm tuỵ"), "code": "K85.90"},
    {"aliases": ("rung nhĩ kèm đáp ứng thất nhanh", "rung nhĩ"), "code": "I48.91"},
    {"aliases": ("u ác của tuyến tiền liệt", "ung thư tuyến tiền liệt"), "code": "C61"},
    {"aliases": ("rối loạn cảm xúc lưỡng cực", "rối loạn lưỡng cực"), "code": "F31.9"},
    {"aliases": ("rối loạn cảm xúc",), "code": "F39"},
    {"aliases": ("viêm phổi hoại tử",), "code": "J85.0"},
    {"aliases": ("áp xe phổi", "áp-xe phổi"), "code": "J85.2"},
    {"aliases": ("nhiễm khuẩn huyết do tụ cầu vàng nhạy cảm methicillin",), "code": "A41.01"},
    {"aliases": ("nhiễm trùng huyết", "nhiễm khuẩn huyết", "nhiễm trùng máu"), "code": "A41.9"},
    {"aliases": ("giãn thừng tinh",), "code": "I86.1"},
    {"aliases": ("bệnh đau nửa đầu Migraine", "bệnh lý đau nửa đầu", "đau nửa đầu", "Migraine"), "code": "G43.909"},
    {"aliases": ("mụn trứng cá",), "code": "L70.9"},
    {"aliases": ("nhiễm khuẩn đường tiết niệu, vị trí không xác định", "nhiễm khuẩn đường tiết niệu", "nhiễm trùng đường tiết niệu", "UTI"), "code": "N39.0"},
    {"aliases": ("hội chứng thận hư",), "code": "N04.9"},
    {"aliases": ("viêm cầu thận mạn",), "code": "N03.9"},
    {"aliases": ("nốt sần tuyến giáp", "nốt tuyến giáp", "nhân tuyến giáp"), "code": "E04.1"},
    {"aliases": ("dị tật thiểu sản vành tai", "thiểu sản vành tai"), "code": "Q17.2"},
    {"aliases": ("tịt ống tai ngoài bẩm sinh", "tịt ống tai ngoài"), "code": "Q16.1"},
    {"aliases": ("ung thư biểu mô tuyến đại tràng", "ung thư đại tràng"), "code": "C18.9"},
    {"aliases": ("xơ gan do rượu",), "code": "K70.30"},
    {"aliases": ("viêm phổi bệnh viện",), "code": "J18.9"},
    {"aliases": ("viêm phổi thùy dưới phải", "RLL PNA", "viêm phổi"), "code": "J18.9"},
    {"aliases": ("nhịp nhanh trên thất", "cơn tim nhanh nhĩ", "cơn nhịp nhanh", "SVT"), "code": "I47.1"},
    {"aliases": ("ngoại tâm thu nhĩ",), "code": "I49.1"},
    {"aliases": ("ngoại tâm thu thất",), "code": "I49.3"},
    {"aliases": ("xẹp phổi",), "code": "J98.11"},
    {"aliases": ("tràn dịch màng phổi", "tràn dịch màng phổi hai bên"), "code": "J90"},
    {"aliases": ("xuất huyết tiêu hóa",), "code": "K92.2"},
    {"aliases": ("ung thư vú di căn", "ung thư vú"), "code": "C50.919"},
    {"aliases": ("tràn dịch màng ngoài tim", "tràn dịch màng tim"), "code": "I31.39"},
    {"aliases": ("ung thư di căn theo đường bạch huyết ở hai phổi",), "code": "C78.00"},
    {"aliases": ("rụng tóc từng mảng", "rụng tóc từng vùng"), "code": "L63.9"},
    {"aliases": ("phù phổi cấp",), "code": "J81.0"},
    {"aliases": ("hở van hai lá", "hở hai lá", "HoHL"), "code": "I34.0"},
    {"aliases": ("hở van động mạch chủ", "hở chủ"), "code": "I35.1"},
    {"aliases": ("hở van ba lá", "hở ba lá"), "code": "I36.1"},
    {"aliases": ("tim to", "bóng tim to"), "code": "I51.7"},
    {"aliases": ("tăng áp lực động mạch phổi", "tăng áp động mạch phổi"), "code": "I27.20"},
    {"aliases": ("ghép thận thất bại", "thất bại ghép thận"), "code": "T86.12"},
    {"aliases": ("bệnh Graves", "Graves"), "code": "E05.00"},
    {"aliases": ("u xơ tuyến vú", "fibroadenoma"), "code": "D24.9"},
    {"aliases": ("u nang tuyến vú", "nang tuyến vú"), "code": "N60.09"},
    {"aliases": ("thuyên tắc phổi hai bên", "thuyên tắc phổi", "tắc mạch phổi"), "code": "I26.99"},
    {"aliases": ("bệnh vảy nến", "vảy nến"), "code": "L40.9"},
    {"aliases": ("viêm nang lông",), "code": "L73.9"},
    {"aliases": ("viêm loét đại tràng", "viêm đại tràng xuất huyết"), "code": "K51.90"},
    {"aliases": ("nấm bẹn",), "code": "B35.6"},
    {"aliases": ("nhiễm nấm da",), "code": "B35.9"},
    {"aliases": ("u ác trực tràng", "khối u trực tràng", "ung thư trực tràng"), "code": "C20"},
    {"aliases": ("u tuyến trực tràng", "adenoma trực tràng", "u tuyến"), "code": "D12.8"},
    {"aliases": ("đa u tủy", "đa u tủy xương", "multiple myeloma"), "code": "C90.00"},
    {"aliases": ("bệnh gout mạn tính", "gút mạn tính", "gout mạn tính"), "code": "M1A.9XX1"},
    {"aliases": ("bệnh gút", "bệnh gout", "gút", "gout"), "code": "M10.9"},
    {"aliases": ("hội chứng tăng đông", "thrombophilia", "bệnh tăng đông máu"), "code": "D68.59"},
    {"aliases": ("tiền sản giật",), "code": "O14.90"},
    {"aliases": ("sỏi niệu quản",), "code": "N20.1"},
    {"aliases": ("táo bón mãn tính", "táo bón mạn tính"), "code": "K59.09"},
    {"aliases": ("nhiễm trùng đường hô hấp trên",), "code": "J06.9"},
    {"aliases": ("loét tì đè giai đoạn IV mãn tính", "loét tì đè giai đoạn IV"), "code": "L89.94"},
    {"aliases": ("nhiễm trùng huyết đường vào tiết niệu",), "code": "A41.9"},
    {"aliases": ("hẹp 80% động mạch thận trái", "tắc hẹp 80% động mạch thận trái L", "hẹp động mạch thận"), "code": "I70.1"},
    {"aliases": ("u dây thần kinh số VIII", "u thần kinh thính giác"), "code": "D33.3"},
    {"aliases": ("trĩ",), "code": "K64.9"},
    {"aliases": ("tàn nhang",), "code": "L81.2"},
    {"aliases": ("tâm phế mạn",), "code": "I27.81"},
    {"aliases": ("nhiễm khuẩn đường tiêu hóa",), "code": "A09"},
    {"aliases": ("nhịp chậm xoang",), "code": "R00.1"},
    {"aliases": ("trào ngược dạ dày thực quản", "bệnh trào ngược dạ dày - thực quản", "GERD"), "codes": ("K21.0", "K21.9")},
    {"aliases": ("dị tật còn ống động mạch", "còn ống động mạch"), "code": "Q25.0"},
    {"aliases": ("bệnh lý thần kinh ngoại biên", "bệnh thần kinh ngoại biên"), "code": "G62.9"},
    {"aliases": ("tăng kali máu",), "code": "E87.5"},
    {"aliases": ("viêm xương tủy", "viêm xương tuỷ", "viêm tủy xương"), "code": "M86.9"},
    {"aliases": ("suy thận cấp", "tổn thương thận cấp"), "code": "N17.9"},
    {"aliases": ("suy thận",), "code": "N19"},
    {"aliases": ("viêm gan cấp tính do virus B thể thông thường điển hình mức độ nặng giai đoạn toàn phát", "viêm gan cấp tính do virus B", "viêm gan B cấp"), "code": "B16.9"},
    {"aliases": ("nhiễm virus viêm gan B, C",), "codes": ("B19.1", "B19.2")},
    {"aliases": ("nhiễm virus viêm gan B",), "code": "B19.1"},
    {"aliases": ("nhiễm virus viêm gan C",), "code": "B19.2"},
    {"aliases": ("viêm tuyến mồ hôi",), "code": "L73.2"},
    {"aliases": ("thiếu máu cơ tim cục bộ", "thiếu máu cơ tim"), "code": "I25.9"},
    {"aliases": ("nhiễm trùng răng miệng",), "code": "K12.2"},
    {"aliases": ("tổn thương cầu thận mạn tính",), "code": "N03.9"},
    {"aliases": ("viêm họng cấp",), "code": "J02.9"},
    {"aliases": ("viêm nhiễm ngoài da", "nhiễm trùng chi dưới bên phải"), "code": "L08.9"},
    {"aliases": ("suy hô hấp",), "code": "J96.90"},
    {"aliases": ("giãn phế quản",), "code": "J47.9"},
    {"aliases": ("xơ gan mất bù",), "code": "K72.90"},
    {"aliases": ("tăng áp lực tĩnh mạch cửa", "tăng áp cửa"), "code": "K76.6"},
    {"aliases": ("cổ trướng",), "code": "R18.8"},
    {"aliases": ("bệnh gan do rượu",), "code": "K70.9"},
    {"aliases": ("ĐTD typ II", "ĐTĐ typ II"), "code": "E11.9"},
    {"aliases": ("hội chứng Turner", "Turner"), "code": "Q96.9"},
    {"aliases": ("bàng quang thần kinh",), "code": "N31.9"},
    {"aliases": ("liệt hai chi dưới",), "code": "G82.20"},
    {"aliases": ("huyết khối tĩnh mạch sâu", "DVT"), "code": "I82.409"},
    {"aliases": ("viêm bể thận",), "code": "N12"},
    {"aliases": ("viêm phế quản",), "code": "J40"},
    {"aliases": ("áp xe trong ổ bụng", "áp xe ổ bụng"), "code": "K65.1"},
    {"aliases": ("đại tràng giãn", "megacolon"), "code": "K59.39"},
    {"aliases": ("chèn ép tim",), "code": "I31.4"},
    {"aliases": ("rối loạn chức năng tâm thu thất trái", "giảm chức năng tâm thu thất trái"), "code": "I51.89"},
    {"aliases": ("gãy xương",), "code": "T14.8XXA"},
)

MEDICATIONS = (
    {"aliases": ("aspirin", "ASA"), "code": "1191"},
    {"aliases": ("Vastarel (trimetazidin)", "Vastarel", "trimetazidine", "trimetazidin"), "code": "10826"},
    {"aliases": ("omeprazole", "Omez"), "code": "7646"},
    {"aliases": ("levothyroxine", "Berlthyrox"), "code": "10582"},
    {"aliases": ("nhôm hydroxid", "aluminum hydroxide"), "code": "612"},
    {"aliases": ("magie hydroxid", "magnesium hydroxide"), "code": "6581"},
    {"aliases": ("Alverin citrate", "alverine citrate"), "code": "17627"},
    {"aliases": ("Simethicon", "simethicone"), "code": "9796"},
    {"aliases": ("metoclopramide", "Pimperan", "Pimperam"), "code": "6915"},
    {"aliases": ("seroquel",), "code": "83553"},
    {"aliases": ("quetiapine",), "code": "51272"},
    {"aliases": ("metoprolol",), "code": "6918"},
    {"aliases": ("doxycycline", "doxycyclin"), "code": "3640"},
    {"aliases": ("atenolol",), "code": "1202"},
    {"aliases": ("bactrim",), "code": "151399"},
    {"aliases": ("cotrimoxazol", "cotrimoxazole", "trimethoprim-sulfamethoxazole"), "code": "10831"},
    {"aliases": ("gleevec",), "code": "282386"},
    {"aliases": ("imatinib",), "code": "282388"},
    {"aliases": ("bumetanide",), "code": "1808"},
    {"aliases": ("vancomycin", "vanco"), "code": "11124"},
    {"aliases": ("levofloxacin", "levafloxacin"), "code": "82122"},
    {"aliases": ("tylenol",), "code": "202433"},
    {"aliases": ("acetaminophen", "paracetamol"), "code": "161"},
    {"aliases": ("compazine",), "code": "203546"},
    {"aliases": ("aleve",), "code": "215101"},
    {"aliases": ("morphine",), "code": "7052"},
    {"aliases": ("lorazepam", "ativan"), "code": "6470"},
    {"aliases": ("eliquis",), "code": "1364436"},
    {"aliases": ("apixaban",), "code": "1364430"},
    {"aliases": ("nitroglycerin", "Nitramyl", "NTG"), "code": "4917"},
    {"aliases": ("cephalexin",), "code": "2231"},
    {"aliases": ("methadone",), "code": "6813"},
    {"aliases": ("lasix",), "code": "202991"},
    {"aliases": ("furosemide", "furosemid"), "code": "4603"},
    {"aliases": ("dilaudid",), "code": "224913"},
    {"aliases": ("hydromorphone",), "code": "3423"},
    {"aliases": ("diltiazem",), "code": "3443"},
    {"aliases": ("allopurinol",), "code": "519"},
    {"aliases": ("Glucose 5%", "dextrose 5%"), "code": "4850"},
    {"aliases": ("Vitamin 3B", "vitamin B complex"), "code": "11251"},
    {"aliases": ("medrol", "methylprednisolone"), "code": "6902"},
    {"aliases": ("zestril", "lisinopril"), "code": "29046"},
    {"aliases": ("ceftriaxone",), "code": "2193"},
    {"aliases": ("cefepime", "cefepim"), "code": "20481"},
    {"aliases": ("albuterolipratropium", "albuterol-ipratropium", "ipratropium/albuterol"), "code": "214199"},
    {"aliases": ("albuterol",), "code": "435"},
    {"aliases": ("ipratropium",), "code": "7213"},
    {"aliases": ("torsemide",), "code": "38413"},
    {"aliases": ("insulin glargine", "glargine"), "code": "274783"},
    {"aliases": ("isosorbide",), "code": "6057"},
    {"aliases": ("rosuvastatin", "crestor"), "code": "301542"},
    {"aliases": ("carvedilol",), "code": "20352"},
    {"aliases": ("coumadin", "warfarin"), "code": "11289"},
    {"aliases": ("tretinoin",), "code": "10753"},
    {"aliases": ("klonopin", "clonazepam"), "code": "2598"},
    {"aliases": ("clonidine",), "code": "2599"},
    {"aliases": ("mucinex d",), "code": "214599"},
    {"aliases": ("guaifenesin", "mucinex"), "code": "5032"},
    {"aliases": ("NAC", "acetylcysteine"), "code": "197"},
    {"aliases": ("Augmentin (amoxicillin/acid clavulanic)", "Augmentin"), "code": "19711"},
    {"aliases": ("azithromycin",), "code": "18631"},
    {"aliases": ("suboxone",), "code": "352364"},
    {"aliases": ("Implanon",), "code": "389221"},
    {"aliases": ("etonogestrel",), "code": "14584"},
    {"aliases": ("zosyn", "piperacillin-tazobactam"), "code": "74169"},
    {"aliases": ("NS 0.9 %", "NS 0.9%"), "code": "9863"},
)


os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---------------------------------------------------------
# 1. Offline Knowledge Mapping
# ---------------------------------------------------------
def normalize_alias(alias: str) -> str:
    return unicodedata.normalize("NFC", alias).casefold()

def candidates_from(entry: dict) -> list[str]:
    value = entry.get("codes", entry.get("code", ()))
    if isinstance(value, str):
        return [value]
    return [str(code) for code in value]

def aliases_from(entry: object) -> tuple[str, ...]:
    if isinstance(entry, str):
        return (entry,)
    if isinstance(entry, dict):
        aliases = entry.get("aliases", ())
        if isinstance(aliases, str):
            return (aliases,)
        return tuple(str(alias) for alias in aliases)
    if isinstance(entry, (tuple, list)):
        return tuple(str(alias) for alias in entry)
    return ()

def get_code_offline(text: str, entity_type: str) -> list[str]:
    if entity_type not in ["CHẨN_ĐOÁN", "THUỐC"]:
        return []
    
    entries = DIAGNOSES if entity_type == "CHẨN_ĐOÁN" else MEDICATIONS
    norm_text = normalize_alias(text.strip())
    
    # 1. Exact match
    for entry in entries:
        for alias in aliases_from(entry):
            if norm_text == normalize_alias(alias):
                return candidates_from(entry)
                
    # 2. Substring match
    for entry in entries:
        for alias in aliases_from(entry):
            norm_alias = normalize_alias(alias)
            if norm_alias in norm_text or norm_text in norm_alias:
                return candidates_from(entry)
    
    return []

# ---------------------------------------------------------
# 2. LLM Inference Setup
# ---------------------------------------------------------
def setup_llm():
    print(f"Loading {MODEL_ID} in 4-bit quantization...")
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=quantization_config,
        device_map="auto"
    )
    return model, tokenizer

def generate_extraction(model, tokenizer, text):
    system_prompt = """Bạn là chuyên gia y tế trích xuất thực thể từ hồ sơ bệnh án tiếng Việt.
Bạn cần trích xuất chính xác các thực thể thuộc 5 loại sau:
- THUỐC (Tên thuốc, có thể kèm liều lượng)
- TRIỆU_CHỨNG (Dấu hiệu lâm sàng)
- CHẨN_ĐOÁN (Tên bệnh, hội chứng)
- TÊN_XÉT_NGHIỆM (Tên phương pháp xét nghiệm, chụp chiếu, chỉ số)
- KẾT_QUẢ_XÉT_NGHIỆM (Trị số, kết quả âm tính/dương tính của xét nghiệm)

Thuộc tính "assertions" (Mảng chứa các nhãn sau nếu có):
- "isHistorical": Nếu thực thể thuộc về tiền sử, quá khứ, hoặc thuốc đã dùng trước nhập viện.
- "isFamily": Nếu thực thể thuộc về tiền sử bệnh của gia đình (bố, mẹ, anh chị em).
- "isNegated": Nếu thực thể bị phủ định (ví dụ: "không ho", "chưa phát hiện khối u", "âm tính").
- Nếu không có, gán mảng rỗng [].

Yêu cầu BẮT BUỘC:
- Trích xuất CHÍNH XÁC chuỗi con (substring) xuất hiện trong văn bản gốc. Đừng thay đổi hay viết hoa.
- Chỉ trả về ĐÚNG ĐỊNH DẠNG JSON MẢNG (List of Objects), không kèm văn bản giải thích.
- Thuộc tính bắt buộc: "text", "type", "assertions".

Ví dụ Output:
[
  {
    "text": "ho",
    "type": "TRIỆU_CHỨNG",
    "assertions": ["isNegated"]
  },
  {
    "text": "tiểu đường",
    "type": "CHẨN_ĐOÁN",
    "assertions": ["isHistorical", "isFamily"]
  },
  {
    "text": "amlodipine 10mg",
    "type": "THUỐC",
    "assertions": ["isHistorical"]
  },
  {
    "text": "WBC",
    "type": "TÊN_XÉT_NGHIỆM",
    "assertions": []
  },
  {
    "text": "12.5",
    "type": "KẾT_QUẢ_XÉT_NGHIỆM",
    "assertions": []
  }
]"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Văn bản:\n{text}"}
    ]
    
    text_input = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    model_inputs = tokenizer([text_input], return_tensors="pt").to(model.device)
    
    generated_ids = model.generate(
        **model_inputs,
        max_new_tokens=2048,
        temperature=0.01,
        do_sample=False,
        pad_token_id=tokenizer.eos_token_id
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    # Extract JSON robustly
    match = re.search(r'\[\s*\{.*?\}\s*\]', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    return []

# ---------------------------------------------------------
# 3. Post-processing & Formatting
# ---------------------------------------------------------
def process_file(model, tokenizer, file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
        
    entities = generate_extraction(model, tokenizer, text)
    
    formatted_entities = []
    seen = set()
    
    for item in entities:
        ext_text = item.get("text", "")
        start_idx = text.find(ext_text)
        
        # Avoid duplication or hallucination
        if start_idx == -1:
            continue
            
        end_idx = start_idx + len(ext_text)
        
        # Enforce type
        etype = item.get("type", "TRIỆU_CHỨNG")
        valid_types = ["THUỐC", "TRIỆU_CHỨNG", "CHẨN_ĐOÁN", "TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"]
        if etype not in valid_types:
            etype = "TRIỆU_CHỨNG"
            
        # Assertions
        valid_assertions = ["isHistorical", "isFamily", "isNegated"]
        raw_asts = item.get("assertions", [])
        asts = list(set([a for a in raw_asts if a in valid_assertions]))
        
        # Deduplicate identical spans
        pos_key = (start_idx, end_idx, etype)
        if pos_key in seen:
            continue
        seen.add(pos_key)
        
        new_item = {
            "text": ext_text,
            "type": etype,
            "position": [start_idx, end_idx],
            "assertions": asts
        }
        
        # TÊN_XÉT_NGHIỆM và KẾT_QUẢ_XÉT_NGHIỆM không được phép có assertions
        if etype in ["TÊN_XÉT_NGHIỆM", "KẾT_QUẢ_XÉT_NGHIỆM"]:
            new_item["assertions"] = []
            
        # Offline ICD-10 & RxNorm Mapping
        if etype in ["CHẨN_ĐOÁN", "THUỐC"]:
            cands = get_code_offline(ext_text, etype)
            if cands:
                new_item["candidates"] = cands
                
        formatted_entities.append(new_item)
        
    # Sort correctly
    formatted_entities.sort(key=lambda x: (x["position"][0], x["position"][1]))
    return formatted_entities

def dump_strict_json(data, out_path):
    lines = ["[\n"]
    for i, item in enumerate(data):
        lines.append("  {\n")
        lines.append(f'    "text": {json.dumps(item["text"], ensure_ascii=False)},\n')
        lines.append(f'    "type": {json.dumps(item["type"], ensure_ascii=False)},\n')
        
        if item.get("type") in ["CHẨN_ĐOÁN", "THUỐC"] and "candidates" in item:
            lines.append(f'    "candidates": {json.dumps(item["candidates"], ensure_ascii=False)},\n')
            
        lines.append(f'    "assertions": {json.dumps(item.get("assertions", []), ensure_ascii=False)},\n')
        lines.append(f'    "position": {json.dumps(item["position"])}\n')
        
        if i == len(data) - 1:
            lines.append("  }\n")
        else:
            lines.append("  },\n")
    lines.append("]")
    
    with open(out_path, 'w', encoding='utf-8') as out_f:
        out_f.writelines(lines)

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"ERROR: Input directory {INPUT_DIR} does not exist. (For local testing, please adjust KAGGLE_INPUT_DIR)")
        return
        
    model, tokenizer = setup_llm()
    
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')]
    for fname in tqdm(files, desc="Processing files"):
        in_path = os.path.join(INPUT_DIR, fname)
        out_path = os.path.join(OUTPUT_DIR, fname.replace('.txt', '.json'))
        
        entities = process_file(model, tokenizer, in_path)
        dump_strict_json(entities, out_path)
        
    print(f"Creating zip archive at {ZIP_PATH} ...")
    with zipfile.ZipFile(ZIP_PATH, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for fname in os.listdir(OUTPUT_DIR):
            if fname.endswith('.json'):
                zipf.write(os.path.join(OUTPUT_DIR, fname), arcname=f"output/{fname}")
                
    print("Done! Submission file is ready.")

if __name__ == "__main__":
    main()
