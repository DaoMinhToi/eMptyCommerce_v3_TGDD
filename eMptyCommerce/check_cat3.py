import pandas as pd

# So sanh 2 file
df1 = pd.read_csv('data/book_data.csv')
df2 = pd.read_csv('data/clean_book_data.csv')

# Tim cac category chi xuat hien 1-2 lan (likely la ten sach bi nham)
cat_counts = df2['category'].value_counts()
rare_cats = cat_counts[cat_counts <= 2]
print('Category xuat hien <= 2 lan (co the bi nham):')
print(rare_cats.head(20))
print()
print('Tong so category hiem:', len(rare_cats))
print('Tong so category nhieu hon 5 lan:', len(cat_counts[cat_counts > 5]))
