import pandas as pd
df = pd.read_csv('data/book_data.csv')
cat_counts = df['category'].value_counts()
valid = cat_counts[cat_counts >= 5]
print('So category hop le (>= 5 lan):', len(valid))
print()
print('Danh sach category:')
for cat in sorted(valid.index.tolist()):
    print(f'  - {cat} ({valid[cat]} sach)')
