import pandas as pd
df = pd.read_csv('data/book_data.csv')
cat_counts = df['category'].value_counts()
valid = cat_counts[cat_counts >= 5]
print('Danh sach category hop le:')
for cat in sorted(valid.index.tolist()):
    print(f'  {cat} ({valid[cat]} sach)')
print()
print('Tong:', len(valid))
