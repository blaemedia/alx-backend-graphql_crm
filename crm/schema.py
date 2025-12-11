import re
from datetime import datetime
from django.db import transaction, IntegrityError
from graphene_django import DjangoObjectType
import graphene

from .models import Customer, Product, Order

class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello, GraphQL!")

schema = graphene.Schema(query=Query)


def validate_phone(phone):
    if phone is None or phone == "":
        return True
    pattern = r"^\+?\d{7,15}$"
    return re.match(pattern, phone)


class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer


class ProductType(DjangoObjectType):
    class Meta:
        model = Product


class OrderType(DjangoObjectType):
    class Meta:
        model = Order


class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    @staticmethod
    def mutate(root, info, name, email, phone=None):
        # Email must be unique
        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists")

        # Validate phone format
        if phone and not validate_phone(phone):
            raise Exception("Invalid phone format. Use +1234567890")

        customer = Customer.objects.create(
            name=name,
            email=email,
            phone=phone
        )

        return CreateCustomer(
            customer=customer,
            message="Customer created successfully"
        )


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(
            graphene.JSONString, required=True,
            description="List of customer dictionaries"
        )

    created_customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @staticmethod
    def mutate(root, info, customers):
        created = []
        errors = []

        # Transaction ensures each successful record is saved independently
        for index, data in enumerate(customers):
            try:
                name = data.get("name")
                email = data.get("email")
                phone = data.get("phone", None)

                if not name or not email:
                    errors.append(f"Row {index}: name and email are required")
                    continue

                if Customer.objects.filter(email=email).exists():
                    errors.append(f"Row {index}: email already exists")
                    continue

                if phone and not validate_phone(phone):
                    errors.append(f"Row {index}: invalid phone format")
                    continue

                with transaction.atomic():
                    customer = Customer.objects.create(
                        name=name,
                        email=email,
                        phone=phone
                    )
                    created.append(customer)

            except Exception as e:
                errors.append(f"Row {index}: {str(e)}")

        return BulkCreateCustomers(
            created_customers=created,
            errors=errors
        )



class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Float(required=True)
        stock = graphene.Int(default_value=0)

    product = graphene.Field(ProductType)

    @staticmethod
    def mutate(root, info, name, price, stock=0):
        if price <= 0:
            raise Exception("Price must be a positive number")

        if stock < 0:
            raise Exception("Stock cannot be negative")

        product = Product.objects.create(
            name=name,
            price=price,
            stock=stock
        )

        return CreateProduct(product=product)



class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.Int(required=True)
        product_ids = graphene.List(graphene.Int, required=True)
        order_date = graphene.DateTime()

    order = graphene.Field(OrderType)

    @staticmethod
    def mutate(root, info, customer_id, product_ids, order_date=None):

        # Validate customer
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            raise Exception("Customer does not exist")

        if not product_ids:
            raise Exception("At least one product must be selected")

        # Validate products
        products = Product.objects.filter(id__in=product_ids)
        if products.count() != len(product_ids):
            raise Exception("One or more product IDs are invalid")

        # Calculate total
        total_amount = sum([p.price for p in products])

        order = Order.objects.create(
            customer=customer,
            order_date=order_date or datetime.now(),
            total_amount=total_amount
        )

        order.products.set(products)

        return CreateOrder(order=order)



class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

# Create a single customer
mutation {
  createCustomer(input:{
    name: "Alice",
    email: "alice@example.com",
    phone: "+1234567890"
  }) {
    customer {
      id
      name
      email
      phone
    }
    message
  }
}

# Bulk create customers
mutation {
  bulkCreateCustomers(input:[
    { name: "Bob", email: "bob@example.com", phone: "123-456-7890" },
    { name: "Carol", email: "carol@example.com" }
  ]) {
    customers {
      id
      name
      email
    }
    errors
  }
}

# Create a product
mutation {
  createProduct(input: {
    name: "Laptop",
    price: 999.99,
    stock: 10
  }) {
    product {
      id
      name
      price
      stock
    }
  }
}

# Create an order with products
mutation {
  createOrder(input: {
    customerId: "1",
    productIds: ["1", "2"]
  }) {
    order {
      id
      customer {
        name
      }
      products {
        name
        price
      }
      totalAmount
      orderDate
    }
  }
}