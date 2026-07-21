import json, glob
errs = 0
for f in glob.glob('output/*.json'):
    for item in json.load(open(f, encoding='utf-8')):
        pos = item.get('position')
        if type(pos) is not list or len(pos) != 2 or type(pos[0]) is not int or type(pos[1]) is not int:
            print('Bad pos:', pos)
            errs += 1
print('Total bad pos:', errs)
