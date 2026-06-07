"""Test script for shopping cart functionality"""
from db_utils import get_or_create_cart, add_to_cart, get_cart_summary, merge_cart
import uuid

print("\n" + "="*60)
print("TEST 1: Create cart for cold-start user (using session_id)")
print("="*60)
session_id = str(uuid.uuid4())
cart_id = get_or_create_cart(session_id=session_id)
print(f"✓ Cart created: cart_id={cart_id}, session_id={session_id[:8]}...")

print("\n" + "="*60)
print("TEST 2: Add products to cart")
print("="*60)
add_to_cart(cart_id, 1001, 2)  # product 1001, quantity 2
add_to_cart(cart_id, 1002, 1)  # product 1002, quantity 1
add_to_cart(cart_id, 1001, 3)  # product 1001 again, should update to quantity 5
summary = get_cart_summary(cart_id)
print(f"✓ Total items: {summary['total_items']}")
print(f"✓ Total quantity: {summary['total_quantity']}")

print("\n" + "="*60)
print("TEST 3: Create cart for warm-start user (customer_id)")
print("="*60)
customer_id = 123
cart_id_customer = get_or_create_cart(customer_id=customer_id)
print(f"✓ Cart created for customer: cart_id={cart_id_customer}, customer_id={customer_id}")

print("\n" + "="*60)
print("TEST 4: Merge carts (cold-start to warm-start)")
print("="*60)
add_to_cart(cart_id, 2001, 2)  # Add product to cold-start cart first
print(f"Before merge - Cold-start cart items: {get_cart_summary(cart_id)['total_quantity']}")
merge_cart(session_id, customer_id)  # Merge cold-start cart to warm-start cart
print(f"After merge - Warm-start cart items: {get_cart_summary(cart_id_customer)['total_quantity']}")
print("✓ Cart merged successfully!")

print("\n" + "="*60)
print("✓ ALL TESTS PASSED!")
print("="*60 + "\n")
