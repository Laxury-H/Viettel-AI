import os
import json
import re
import requests
import time
from tqdm import tqdm
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Configuration
INPUT_DIR = "input/input"
OUTPUT_DIR = "output"
MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Regex utilities for RxNorm matching
def clean_drug_name(drug_string):
    """
    Remove dosage, route, frequency from drug string to improve RxNorm matching.
    Example: 'amlodipine 10 mg po daily' -> 'amlodipine'
    """
    # Convert to lowercase
    s = drug_string.lower()
    
    # Remove common dosage forms and routes
    patterns_to_remove = [
        r'\b\d+(\.\d+)?\s*(mg|g|mcg|ml|l|units|iu)\b', # Dosages: 10 mg, 5.5 ml
        r'\b(po|iv|im|sc|sl|pr)\b', # Routes: po (by mouth), iv, etc.
        r'\b(daily|bid|tid|qid|q\d+h|prn|qam|qhs)\b', # Frequencies
        r'\b(tablet|capsule|suspension|oral|injection|syrup)\b', # Forms
        r'điều trị.*', # Vietnamese reasons: "điều trị táo bón"
        r'[:\-]' # Punctuation
    ]
    
    for p in patterns_to_remove:
        s = re.sub(p, ' ', s)
        
    s = re.sub(r'\s+', ' ', s).strip()
    return s if s else drug_string.lower()

def get_rxnorm_cui_robust(drug_string):
    """Robust RxNorm query using exact match then fallback to cleaned string."""
    def query(name):
        url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={requests.utils.quote(name)}&search=2"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if "idGroup" in data and "rxnormId" in data["idGroup"]:
                    return data["idGroup"]["rxnormId"][0]
        except:
            pass
        return None
        
    # 1. Try exact string
    cui = query(drug_string)
    if cui: return cui
    
    # 2. Try cleaned string
    cleaned = clean_drug_name(drug_string)
    if cleaned != drug_string.lower():
        cui = query(cleaned)
        if cui: return cui
        
    # 3. Try splitting by space and taking first 1-2 words (usually the generic name)
    words = cleaned.split()
    if len(words) > 1:
        cui = query(words[0])
        if cui: return cui
        
    return None

# 2. LLM Inference Setup
def setup_llm():
    print(f"Loading {MODEL_ID} in 4-bit quantization...")
    quantization_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16
    )
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        quantization_config=quantization_config,
        device_map="auto"
    )
    return model, tokenizer

def generate_extraction(model, tokenizer, text):
    system_prompt = """Bạn là một chuyên gia y tế trích xuất thực thể từ hồ sơ bệnh án tiếng Việt.
Bạn cần trích xuất chính xác các thực thể thuộc 3 loại: THUỐC, TRIỆU_CHỨNG, CHẨN_ĐOÁN.
Đồng thời xác định xem thực thể đó có nằm trong bệnh sử/tiền sử không (isHistorical).

Yêu cầu BẮT BUỘC:
- Trích xuất CHÍNH XÁC chuỗi con (substring) xuất hiện trong văn bản. Đừng thay đổi dấu câu hay viết hoa.
- Chỉ trả về ĐÚNG ĐỊNH DẠNG JSON MẢNG (List of Objects), không kèm theo văn bản giải thích nào khác.
- Các thuộc tính bắt buộc: "text", "type", "assertions".
- "assertions": Nếu thực thể nằm trong bệnh sử/tiền sử (ví dụ: "tiền sử", "trước nhập viện", "bệnh cũ"), gán ["isHistorical"]. Nếu là hiện tại, gán [].

Ví dụ Input:
'Danh sách thuốc trước nhập viện chính xác và đầy đủ. 1. amlodipine 10 mg po daily điều trị huyết áp 2. ho nhiều'

Ví dụ Output (JSON):
[
  {
    "text": "amlodipine 10 mg po daily",
    "type": "THUỐC",
    "assertions": ["isHistorical"]
  },
  {
    "text": "huyết áp",
    "type": "CHẨN_ĐOÁN",
    "assertions": ["isHistorical"]
  },
  {
    "text": "ho nhiều",
    "type": "TRIỆU_CHỨNG",
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
        do_sample=False
    )
    generated_ids = [
        output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
    ]
    
    response = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    
    # Extract JSON
    match = re.search(r'\[.*\]', response, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except:
            pass
    return []

# 3. Post-processing & Formatting
def process_file(model, tokenizer, file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
        
    entities = generate_extraction(model, tokenizer, text)
    
    formatted_entities = []
    for item in entities:
        # Find position
        ext_text = item.get("text", "")
        start_idx = text.find(ext_text)
        if start_idx == -1:
            continue # Skip if hallucinated
            
        end_idx = start_idx + len(ext_text)
        
        # Enforce type constraints
        etype = item.get("type", "TRIỆU_CHỨNG")
        if etype not in ["THUỐC", "TRIỆU_CHỨNG", "CHẨN_ĐOÁN"]:
            etype = "TRIỆU_CHỨNG"
            
        new_item = {
            "text": ext_text,
            "type": etype
        }
        
        # RxNorm matching for THUỐC
        if etype == "THUỐC":
            cui = get_rxnorm_cui_robust(ext_text)
            if cui:
                new_item["candidates"] = [cui]
                
        # Assertions
        asts = item.get("assertions", [])
        if "isHistorical" in asts:
            new_item["assertions"] = ["isHistorical"]
        else:
            new_item["assertions"] = []
            
        new_item["position"] = [start_idx, end_idx]
        formatted_entities.append(new_item)
        
    return formatted_entities

def dump_strict_json(data, out_path):
    lines = ["[\n"]
    for i, item in enumerate(data):
        lines.append("  {\n")
        lines.append(f'    "text": {json.dumps(item["text"], ensure_ascii=False)},\n')
        lines.append(f'    "type": {json.dumps(item["type"], ensure_ascii=False)},\n')
        
        if item.get("type") == "THUỐC" and "candidates" in item:
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
    model, tokenizer = setup_llm()
    
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')]
    for fname in tqdm(files, desc="Processing files"):
        in_path = os.path.join(INPUT_DIR, fname)
        out_path = os.path.join(OUTPUT_DIR, fname.replace('.txt', '.json'))
        
        entities = process_file(model, tokenizer, in_path)
        dump_strict_json(entities, out_path)
        
    print("Done! You can now zip the output folder.")

if __name__ == "__main__":
    main()
