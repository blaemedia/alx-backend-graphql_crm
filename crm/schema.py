import re
from datetime import datetime
from django.db import transaction, IntegrityError
from graphene_django import DjangoObjectType
import graphene
from graphql import GraphQLError
from decimal import Decimal

from .models import Customer, Product, Order


class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello, GraphQL!")
    
    # Add customer queries
    customers = graphene.List(lambda: CustomerType)
    customer = graphene.Field(lambda: CustomerType, id=graphene.ID(required=True))
    
    # Add product queries
    products = graphene.List(lambda: ProductType)
    product = graphene.Field(lambda: ProductType, id=graphene.ID(required=True))
    
    # Add order queries
    orders = graphene.List(lambda: OrderType)
    order = graphene.Field(lambda: OrderType, id=graphene.ID(required=True))
    
    def resolve_customers(self, info):
        return Customer.objects.all()
    
    def resolve_customer(self, info, id):
        try:
            return Customer.objects.get(id=id)
        except Customer.DoesNotExist:
            raise GraphQLError(f"Customer with ID {id} does not exist")
    
    def resolve_products(self, info):
        return Product.objects.all()
    
    def resolve_product(self, info, id):
        try:
            return Product.objects.get(id=id)
        except Product.DoesNotExist:
            raise GraphQLError(f"Product with ID {id} does not exist")
    
    def resolve_orders(self, info):
        return Order.objects.all()
    
    def resolve_order(self, info, id):
        try:
            return Order.objects.get(id=id)
        except Order.DoesNotExist:
            raise GraphQLError(f"Order with ID {id} does not exist")


# Define Object Types
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = "__all__"


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = "__all__"


class OrderType(DjangoObjectType):
    products = graphene.List(ProductType)
    
    class Meta:
        model = Order
        fields = "__all__"
    
    def resolve_products(self, info):
        return self.products.all()


# Input Types
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int()


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime()


def validate_phone(phone):
    """Validate phone format (e.g., +1234567890 or 123-456-7890)"""
    if phone is None or phone == "":
        return True
    # Accept both +1234567890 and 123-456-7890 formats
    pattern = r"^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$"
    return re.match(pattern, phone)


class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    @classmethod
    def mutate(cls, root, info, input):
        try:
            # Validate email uniqueness
            if Customer.objects.filter(email=input.email).exists():
                raise GraphQLError("Email already exists")
            
            # Validate phone format
            if input.phone and not validate_phone(input.phone):
                raise GraphQLError(
                    "Invalid phone format. Use +1234567890 or 123-456-7890"
                )
            
            # Create and save customer
            customer = Customer.objects.create(
                name=input.name,
                email=input.email,
                phone=input.phone
            )
            
            return CreateCustomer(
                customer=customer,
                message="Customer created successfully"
            )
            
        except GraphQLError as e:
            raise e
        except Exception as e:
            raise GraphQLError(f"Error creating customer: {str(e)}")


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        inputs = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    @classmethod
    def mutate(cls, root, info, inputs):
        created_customers = []
        errors = []
        
        try:
            with transaction.atomic():
                for idx, input_data in enumerate(inputs):
                    try:
                        # Validate required fields
                        if not input_data.name or not input_data.email:
                            errors.append(f"Row {idx + 1}: Name and email are required")
                            continue
                        
                        # Validate email uniqueness
                        if Customer.objects.filter(email=input_data.email).exists():
                            errors.append(f"Row {idx + 1}: Email '{input_data.email}' already exists")
                            continue
                        
                        # Validate phone format
                        if input_data.phone and not validate_phone(input_data.phone):
                            errors.append(
                                f"Row {idx + 1}: Invalid phone format '{input_data.phone}'. "
                                f"Use +1234567890 or 123-456-7890"
                            )
                            continue
                        
                        # Create customer
                        customer = Customer.objects.create(
                            name=input_data.name,
                            email=input_data.email,
                            phone=input_data.phone if input_data.phone else None
                        )
                        created_customers.append(customer)
                        
                    except Exception as e:
                        errors.append(f"Row {idx + 1}: {str(e)}")
                
                # Commit transaction only if no errors in validation
                return BulkCreateCustomers(
                    customers=created_customers,
                    errors=errors
                )
                
        except Exception as e:
            raise GraphQLError(f"Transaction error: {str(e)}")


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    @classmethod
    def mutate(cls, root, info, input):
        try:
            # Validate price is positive
            if input.price <= 0:
                raise GraphQLError("Price must be a positive number")
            
            # Validate stock is not negative
            stock = input.stock if input.stock is not None else 0
            if stock < 0:
                raise GraphQLError("Stock cannot be negative")
            
            # Create and save product
            product = Product.objects.create(
                name=input.name,
                price=Decimal(str(input.price)),
                stock=stock
            )
            
            return CreateProduct(product=product)
            
        except GraphQLError as e:
            raise e
        except Exception as e:
            raise GraphQLError(f"Error creating product: {str(e)}")


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)

    @classmethod
    def mutate(cls, root, info, input):
        try:
            # Validate at least one product
            if not input.product_ids or len(input.product_ids) == 0:
                raise GraphQLError("At least one product must be selected")
            
            # Get customer
            try:
                customer = Customer.objects.get(id=input.customer_id)
            except Customer.DoesNotExist:
                raise GraphQLError(f"Customer with ID {input.customer_id} does not exist")
            
            # Get products
            products = []
            total_amount = Decimal('0')
            for product_id in input.product_ids:
                try:
                    product = Product.objects.get(id=product_id)
                    products.append(product)
                    total_amount += Decimal(str(product.price))
                except Product.DoesNotExist:
                    raise GraphQLError(f"Product with ID {product_id} does not exist")
            
            # Validate we have all requested products
            if len(products) != len(input.product_ids):
                raise GraphQLError("One or more product IDs are invalid")
            
            # Create order
            order = Order.objects.create(
                customer=customer,
                total_amount=total_amount,
                order_date=input.order_date if input.order_date else datetime.now()
            )
            
            # Associate products with order
            order.products.set(products)
            
            return CreateOrder(order=order)
            
        except GraphQLError as e:
            raise e
        except Exception as e:
            raise GraphQLError(f"Error creating order: {str(e)}")


class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)