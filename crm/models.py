from django.db import models
from django.core.validators import MinValueValidator, EmailValidator
from django.core.exceptions import ValidationError
import re


class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True, validators=[EmailValidator()])
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        # Custom validation for phone number
        if self.phone:
            pattern = r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$'
            if not re.match(pattern, self.phone):
                raise ValidationError(
                    {'phone': 'Invalid phone format. Use +1234567890 or 123-456-7890'}
                )

    def __str__(self):
        return f"{self.name} ({self.email})"

    class Meta:
        ordering = ['name']


class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ${self.price}"

    class Meta:
        ordering = ['name']


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    order_date = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.customer.name} - ${self.total_amount}"

    class Meta:
        ordering = ['-order_date']


class OrderProduct(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_products')
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order.id} - {self.product.name} x{self.quantity}"

    class Meta:
        unique_together = ['order', 'product']