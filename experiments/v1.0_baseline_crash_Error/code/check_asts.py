import json, glob
asts = set()
for f in glob.glob('output/*.json'):
    j = json.load(open(f, encoding='utf-8'))
    for item in j:
        asts.update(item.get('assertions', []))
print('Unique assertions found:', asts)
