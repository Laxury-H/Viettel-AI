import json, os, glob

errors = 0
for f in glob.glob('output/*.json'):
    txt_f = f.replace('output\\', 'input\\input\\').replace('.json', '.txt')
    if not os.path.exists(txt_f):
        txt_f = f.replace('output/', 'input/input/').replace('.json', '.txt')
        
    with open(txt_f, 'r', encoding='utf-8') as file:
        text = file.read()
    with open(f, 'r', encoding='utf-8') as file:
        data = json.load(file)
        
    for item in data:
        start, end = item['position']
        extracted = text[start:end]
        if extracted != item['text']:
            print(f"Error in {f}: expected '{item['text']}', got '{extracted}'")
            errors += 1

print(f"Total position errors: {errors}")
