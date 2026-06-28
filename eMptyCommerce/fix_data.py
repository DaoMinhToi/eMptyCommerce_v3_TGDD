import pandas as pd

def clean_categories(file_path):
    try:
        df = pd.read_csv(file_path)
        
        # Define mappings from title keyword to correct category
        mappings = {
            'Điện thoại': 'Điện thoại',
            'Laptop': 'Laptop',
            'Đồng hồ': 'Đồng hồ',
            'Máy tính bảng': 'Máy tính bảng'
        }
        
        # Keep track of how many changed
        changes = 0
        for keyword, correct_cat in mappings.items():
            mask = df['title'].str.contains(keyword, na=False, case=False) & (df['category'] != correct_cat)
            changes += mask.sum()
            df.loc[mask, 'category'] = correct_cat
            
        df.to_csv(file_path, index=False)
        print(f"Fixed {changes} rows in {file_path}")
    except Exception as e:
        print(f"Error in {file_path}: {e}")

clean_categories('data/book_data.csv')
clean_categories('data/clean_book_data.csv')
