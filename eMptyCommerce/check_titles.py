import pandas as pd
df = pd.read_csv('data/clean_book_data.csv')
print('Tong so sach:', len(df))
print('Vi du 5 ten sach dau:')
for title in df['title'].head().tolist():
    print(' -', title)
