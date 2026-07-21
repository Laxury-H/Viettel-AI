import json, os, glob

for f in glob.glob('output/*.json'):
    with open(f, 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    changed = False
    for item in data:
        ast = item.get('assertions')
        if isinstance(ast, dict):
            item['assertions'] = [k for k, v in ast.items() if v]
            changed = True
        elif isinstance(ast, str):
            item['assertions'] = [ast]
            changed = True
        elif ast is None:
            item['assertions'] = []
            changed = True
    
    if changed:
        with open(f, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

print('Done fixing assertions!')
