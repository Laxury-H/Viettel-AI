import json, glob
types = set()
for f in glob.glob('output/*.json'):
    j = json.load(open(f, encoding='utf-8'))
    for item in j:
        types.add(item.get('type'))
print('Unique types:', types)
