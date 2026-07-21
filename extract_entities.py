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

# Initialize Gemini Client
import dotenv
dotenv.load_dotenv(r"d:\Project\Game\Lax's Studio\.env")

API_KEYS = [os.environ[k] for k in os.environ if k.startswith("GEMINI_API_KEY") and os.environ[k].strip()]
current_key_idx = 0

def get_client():
    if not API_KEYS:
        return None
    return genai.Client(api_key=API_KEYS[current_key_idx])

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
    global current_key_idx
    
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
    
    Make sure the "text" field is an EXACT match of the text found in the input.
    """
    
    max_retries = len(API_KEYS) if API_KEYS else 1
    attempts = 0
    
    while attempts < max_retries:
        client = get_client()
        if not client:
            return []
            
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, "Text:\n" + text],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
            return json.loads(response.text)
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                print(f"Key {current_key_idx + 1} exhausted quota. Switching to next key...")
                current_key_idx = (current_key_idx + 1) % len(API_KEYS)
                attempts += 1
                time.sleep(2) # brief pause before retry
            else:
                print(f"Error during extraction: {e}")
                return []
    
    print("All keys exhausted or failed.")
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
