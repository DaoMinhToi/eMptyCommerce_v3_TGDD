with open('evaluate.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'read_csv' in line or 'clean_reviews' in line:
        print(f'Line {i+1}: {line.rstrip()}')
