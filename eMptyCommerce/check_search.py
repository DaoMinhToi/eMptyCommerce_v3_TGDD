with open('ui_components.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'text_input' in line or 'search_btn' in line or 'do_search' in line or 'rerun' in line:
        print(f'Line {i+1}: {line.rstrip()}')
