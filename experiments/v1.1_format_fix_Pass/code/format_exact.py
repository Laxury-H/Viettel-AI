import json, glob, os

os.makedirs('output', exist_ok=True)

for f in glob.glob('temp_zip_check/output/*.json'):
    j = json.load(open(f, encoding='utf-8'))
    lines = ["[\n"]
    for i, item in enumerate(j):
        lines.append("  {\n")
        
        text_val = json.dumps(item["text"], ensure_ascii=False)
        lines.append(f'    "text": {text_val},\n')
        
        type_val = json.dumps(item["type"], ensure_ascii=False)
        lines.append(f'    "type": {type_val},\n')
        
        if item.get("type") == "THUỐC" and "candidates" in item:
            cands_val = json.dumps(item["candidates"], ensure_ascii=False)
            lines.append(f'    "candidates": {cands_val},\n')
            
        asts = item.get("assertions", [])
        if "isHistorical" in asts:
            asts = ["isHistorical"]
        else:
            asts = []
        asts_val = json.dumps(asts, ensure_ascii=False)
        lines.append(f'    "assertions": {asts_val},\n')
        
        pos_val = json.dumps(item["position"])
        lines.append(f'    "position": {pos_val}\n')
        
        if i == len(j) - 1:
            lines.append("  }\n")
        else:
            lines.append("  },\n")
    lines.append("]")
    
    out_path = f.replace('temp_zip_check\\', '').replace('temp_zip_check/', '')
    with open(out_path, 'w', encoding='utf-8') as out_f:
        out_f.writelines(lines)

print("Formatting complete!")
