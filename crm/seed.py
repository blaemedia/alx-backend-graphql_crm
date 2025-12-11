#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'graphql_crm.settings')
django.setup()

from crm.models import Customer, Product, Order, OrderProduct
from decimal import Decimal

def seed_database():
    print("Seeding database...")
    
    # Clear existing data
    OrderProduct.objects.all().delete()
    Order.objects.all().delete()
    Product.objects.all().delete()
    Customer.objects.all().delete()
    
    # Create customers
    customers = [
        Customer(name="Alice Johnson", email="alice@example.com", phone="+1234567890"),
        Customer(name="Bob Smith", email="bob@example.com", phone="123-456-7890"),
        Customer(name="Carol Davis", email="carol@example.com", phone="+0987654321"),
    ]
    for customer in customers:
        customer.save()
    print(f"Created {len(customers)} customers")
    
    # Create products
    products = [
        Product(name="Laptop", price=Decimal("999.99"), stock=10),
        Product(name="Mouse", price=Decimal("29.99"), stock=50),
        Product(name="Keyboard", price=Decimal("79.99"), stock=30),
        Product(name="Monitor", price=Decimal("299.99"), stock=15),
    ]
    for product in products:
        product.save()
    print(f"Created {len(products)} products")
    
    # Create orders
    alice = Customer.objects.get(email="alice@example.com")
    bob = Customer.objects.get(email="bob@example.com")
    
    laptop = Product.objects.get(name="Laptop")
    mouse = Product.objects.get(name="Mouse")
    keyboard = Product.objects.get(name="Keyboard")
    
    # Order 1: Alice buys laptop and mouse
    order1 = Order.objects.create(
        customer=alice,
        total_amount=laptop.price + mouse.price
    )
    OrderProduct.objects.create(order=order1, product=laptop, quantity=1)
    OrderProduct.objects.create(order=order1, product=mouse, quantity=1)
    
    # Order 2: Bob buys keyboard
    order2 = Order.objects.create(
        customer=bob,
        total_amount=keyboard.price
    )
    OrderProduct.objects.create(order=order2, product=keyboard, quantity=1)
    
    print(f"Created {Order.objects.count()} orders")
    print("Database seeded successfully!")

if __name__ == "__main__":
    seed_database()