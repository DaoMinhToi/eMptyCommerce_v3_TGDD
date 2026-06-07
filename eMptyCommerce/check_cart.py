import sqlite3

conn = sqlite3.connect('emptycm_store.db')
cursor = conn.cursor()

# Get carts
print("=== Recent Carts ===")
cursor.execute("SELECT cart_id, customer_id, session_id, is_active FROM carts ORDER BY created_at DESC LIMIT 3")
for row in cursor.fetchall():
    session_preview = row[2][:8] if row[2] else 'None'
    print(f"Cart ID: {row[0]}, Customer: {row[1]}, Session: {session_preview}..., Active: {row[3]}")

# Get cart items
print("\n=== Cart Items ===")
cursor.execute("SELECT cart_id, product_id, quantity FROM cart_items ORDER BY added_at DESC LIMIT 10")
for row in cursor.fetchall():
    print(f"Cart {row[0]}: Product {row[1]}, Qty {row[2]}")

conn.close()
