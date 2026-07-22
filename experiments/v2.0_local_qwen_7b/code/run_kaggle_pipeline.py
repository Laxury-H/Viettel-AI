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
INPUT_DIR = os.environ.get("KAGGLE_INPUT_DIR", "/kaggle/input/input_turn2_vong1/input")
# We write output to /kaggle/working
OUTPUT_DIR = os.environ.get("KAGGLE_WORKING_DIR", "/kaggle/working/output")
ZIP_PATH = os.environ.get("KAGGLE_ZIP_PATH", "/kaggle/working/output.zip")
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

# Import offline knowledge base from V4
try:
    from knowledge_base import DIAGNOSES, MEDICATIONS
except ImportError:
    print("WARNING: knowledge_base.py not found. Offline mapping will be skipped.")
    DIAGNOSES = []
    MEDICATIONS = []

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
