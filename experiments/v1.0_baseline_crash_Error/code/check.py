import json, glob

errors = 0
for f in glob.glob('output/*.json'):
    data = json.load(open(f, encoding='utf-8'))
    for item in data:
        if 'text' not in item or type(item['text']) is not str:
            print('Lỗi text:', f)
            errors += 1
        if 'type' not in item or item['type'] not in ['THUỐC', 'TRIỆU_CHỨNG', 'CHẨN_ĐOÁN']:
            print('Lỗi type:', f)
            errors += 1
        if 'candidates' not in item or type(item['candidates']) is not list:
            print('Lỗi candidates:', f)
            errors += 1
        if 'assertions' not in item or type(item['assertions']) is not list:
            print('Lỗi assertions:', f)
            errors += 1
        if 'position' not in item or type(item['position']) is not list or len(item['position']) != 2:
            print('Lỗi position:', f)
            errors += 1

print('Tổng số lỗi định dạng sau khi fix:', errors)
