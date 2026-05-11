import pandas as pd
df_clean = pd.read_csv('data/clean_book_data.csv')
print('Category trong clean_book_data.csv:')
print(df_clean['category'].value_counts().head(20))
print()
print('Tong so category unique:', df_clean['category'].nunique())
