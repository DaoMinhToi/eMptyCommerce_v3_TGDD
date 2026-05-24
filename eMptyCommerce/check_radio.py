with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print('=== Dòng liên quan customer_type và radio ===')
for i, line in enumerate(lines):
    if any(k in line for k in ['customer_type', 'radio', 'do_search', 'rerun', 'search_query']):
        print(f'Line {i+1}: {line.rstrip()}')
