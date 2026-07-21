import json, glob
for f in glob.glob('output/*.json'):
    try:
        j = json.load(open(f, encoding='utf-8'))
        for item in j:
            if item.get('type') != 'THUỐC':
                if 'candidates' in item:
                    del item['candidates']
            if 'assertions' in item:
                if 'isHistorical' in item['assertions']:
                    item['assertions'] = ['isHistorical']
                else:
                    item['assertions'] = []
        with open(f, 'w', encoding='utf-8') as out:
            json.dump(j, out, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error processing {f}: {e}")
print("Formatted perfectly!")
