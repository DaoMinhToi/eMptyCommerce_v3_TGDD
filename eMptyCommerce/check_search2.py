with open('ui_components.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if i < 50:
        print(f'Line {i+1}: {line.rstrip()}')
