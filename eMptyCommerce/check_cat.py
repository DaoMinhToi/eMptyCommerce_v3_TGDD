import pandas as pd
df = pd.read_csv('data/book_data.csv')
print('Cac gia tri unique trong cot category:')
print(df['category'].value_counts().head(20))
print()
print('Tong so category unique:', df['category'].nunique())
