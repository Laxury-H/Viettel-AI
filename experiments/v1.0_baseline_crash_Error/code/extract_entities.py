import os
import json
import re
import requests
import time
from tqdm import tqdm
from google import genai
from google.genai import types

INPUT_DIR = r"d:\Project\Viettel AI\input\input"
OUTPUT_DIR = r"d:\Project\Viettel AI\output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Initialize Groq API Key
import dotenv
dotenv.load_dotenv(r"d:\Project\Game\Lax's Studio\.env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

def get_rxnorm_cui(drug_string):
    """Query RxNorm API to get CUI for a drug string."""
    # Try the exact string first
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={requests.utils.quote(drug_string)}&search=2"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "idGroup" in data and "rxnormId" in data["idGroup"]:
                return data["idGroup"]["rxnormId"][0]
    except Exception:
        pass
    
    # Try just the first word (often the main drug name)
    first_word = drug_string.split()[0]
    url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={requests.utils.quote(first_word)}&search=2"
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "idGroup" in data and "rxnormId" in data["idGroup"]:
                return data["idGroup"]["rxnormId"][0]
    except Exception:
        pass
        
    return None

def extract_entities(text):
    if not GROQ_API_KEY:
        print("GROQ_API_KEY not found.")
        return []
    
    prompt = """
    You are an expert medical entity extractor. Analyze the following medical text and extract all entities of the following types:
    - THUỐC (Medications, drugs, dosages, etc.)
    - TRIỆU_CHỨNG (Symptoms)
    - CHẨN_ĐOÁN (Diagnoses, conditions)
    
    Extract the EXACT substring from the text. 
    Also, identify if the entity has any assertions (e.g. "isHistorical" if it is a past medical history event, or empty if it's current).
    Return the output as a JSON array of objects with the following format:
    [
      {
        "text": "exact substring from text",
        "type": "THUỐC" or "TRIỆU_CHỨNG" or "CHẨN_ĐOÁN",
        "assertions": ["isHistorical"] or []
      }
    ]
    
    Make sure the "text" field is an EXACT match of the text found in the input. ONLY output the JSON array, no markdown formatting.
    """
    
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": "Text:\n" + text}
            ],
            "response_format": {"type": "json_object"}
        }
        
        # We wrap the prompt since json_object requires the prompt to specify outputting a JSON object.
        # So we wrap the array in an object {"data": [...]}
        data["messages"][0]["content"] += "\nOutput JSON object with a 'data' key containing the array."
        
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            res_json = response.json()
            content = res_json["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return parsed.get("data", [])
        else:
            print("Groq API error:", response.text)
            return []
    except Exception as e:
        print(f"Error during extraction: {e}")
        return []

def process_file(file_path, output_path):
    # Skip if already successfully processed (file exists and is not empty array)
    if os.path.exists(output_path):
        try:
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
                if len(existing_data) > 0:
                    print(f"Skipping {os.path.basename(file_path)}, already processed.")
                    return
        except Exception:
            pass

    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    entities = extract_entities(text)
    
    final_output = []
    
    # Keep track of search start index to handle multiple occurrences
    search_start = 0
    
    for ent in entities:
        ent_text = ent.get("text", "")
        ent_type = ent.get("type", "")
        assertions = ent.get("assertions", [])
        
        # Find position
        start_idx = text.find(ent_text, search_start)
        if start_idx == -1:
            # If not found after search_start, try from beginning in case LLM output was out of order
            start_idx = text.find(ent_text)
            if start_idx == -1:
                continue
        else:
            # Update search_start to after this entity to find the next occurrence later
            search_start = start_idx + len(ent_text)
        
        end_idx = start_idx + len(ent_text)
        
        # RxNorm matching for THUỐC
        candidates = []
        if ent_type == "THUỐC":
            cui = get_rxnorm_cui(ent_text)
            if cui:
                candidates.append(str(cui))
        
        final_output.append({
            "text": ent_text,
            "type": ent_type,
            "candidates": candidates,
            "assertions": assertions,
            "position": [start_idx, end_idx]
        })
        
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, ensure_ascii=False, indent=2)

def main():
    if not os.path.exists(INPUT_DIR):
        print(f"Input dir {INPUT_DIR} does not exist.")
        return
        
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.txt')]
    for file in tqdm(files):
        file_path = os.path.join(INPUT_DIR, file)
        output_path = os.path.join(OUTPUT_DIR, file.replace('.txt', '.json'))
        process_file(file_path, output_path)
        time.sleep(1) # Rate limiting for safety

if __name__ == "__main__":
    main()
