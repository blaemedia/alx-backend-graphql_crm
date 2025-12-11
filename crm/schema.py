# tests/test_schema.py
from django.test import TestCase
from unittest.mock import patch, MagicMock
from decimal import Decimal
import graphene
from graphql import GraphQLError

from your_app.models import Customer, Product, Order
from your_app.schema import CreateCustomer, CreateProduct, CreateOrder


class TestCreateCustomerMutation(TestCase):
    """Test the CreateCustomer mutation"""
    
    def test_create_customer_success(self):
        """Test successful customer creation"""
        # Get initial count
        initial_count = Customer.objects.count()
        
        # Execute mutation
        mutation = CreateCustomer()
        result = mutation.mutate(
            None,  # root
            None,  # info
            MagicMock(
                name="Test Customer",
                email="test@example.com",
                phone="+1234567890"
            )
        )
        
        # Verify customer was created
        self.assertEqual(Customer.objects.count(), initial_count + 1)
        self.assertEqual(result.customer.name, "Test Customer")
        self.assertEqual(result.customer.email, "test@example.com")
        self.assertEqual(result.message, "Customer created successfully")
    
    def test_create_customer_duplicate_email(self):
        """Test customer creation fails with duplicate email"""
        # Create a customer first
        Customer.objects.create(
            name="Existing Customer",
            email="existing@example.com",
            phone="+1234567890"
        )
        
        # Try to create another customer with same email
        with self.assertRaises(GraphQLError) as context:
            mutation = CreateCustomer()
            mutation.mutate(
                None,
                None,
                MagicMock(
                    name="New Customer",
                    email="existing@example.com",  # Same email!
                    phone="+0987654321"
                )
            )
        
        # Verify error
        self.assertIn("Email already exists", str(context.exception))
    
    def test_create_customer_invalid_phone(self):
        """Test customer creation fails with invalid phone"""
        with self.assertRaises(GraphQLError) as context:
            mutation = CreateCustomer()
            mutation.mutate(
                None,
                None,
                MagicMock(
                    name="Test Customer",
                    email="test@example.com",
                    phone="invalid-phone"
                )
            )
        
        # Verify error
        self.assertIn("Invalid phone format", str(context.exception))


class TestCreateProductMutation(TestCase):
    """Test the CreateProduct mutation"""
    
    def test_create_product_success(self):
        """Test successful product creation"""
        # Get initial count
        initial_count = Product.objects.count()
        
        # Execute mutation
        mutation = CreateProduct()
        result = mutation.mutate(
            None,  # root
            None,  # info
            MagicMock(
                name="Test Product",
                price=Decimal("29.99"),
                stock=100
            )
        )
        
        # Verify product was created
        self.assertEqual(Product.objects.count(), initial_count + 1)
        self.assertEqual(result.product.name, "Test Product")
        self.assertEqual(result.product.price, Decimal("29.99"))
        self.assertEqual(result.product.stock, 100)
    
    def test_create_product_invalid_price(self):
        """Test product creation fails with negative price"""
        with self.assertRaises(GraphQLError) as context:
            mutation = CreateProduct()
            mutation.mutate(
                None,
                None,
                MagicMock(
                    name="Test Product",
                    price=Decimal("-10.00"),  # Negative price!
                    stock=100
                )
            )
        
        # Verify error
        self.assertIn("Price must be a positive number", str(context.exception))
    
    def test_create_product_negative_stock(self):
        """Test product creation fails with negative stock"""
        with self.assertRaises(GraphQLError) as context:
            mutation = CreateProduct()
            mutation.mutate(
                None,
                None,
                MagicMock(
                    name="Test Product",
                    price=Decimal("10.00"),
                    stock=-5  # Negative stock!
                )
            )
        
        # Verify error
        self.assertIn("Stock cannot be negative", str(context.exception))


class TestCreateOrderMutation(TestCase):
    """Test the CreateOrder mutation"""
    
    def setUp(self):
        # Create test data
        self.customer = Customer.objects.create(
            name="Test Customer",
            email="customer@example.com",
            phone="+1234567890"
        )
        self.product1 = Product.objects.create(
            name="Product 1",
            price=Decimal("10.00"),
            stock=100
        )
        self.product2 = Product.objects.create(
            name="Product 2",
            price=Decimal("20.00"),
            stock=50
        )
    
    def test_create_order_success(self):
        """Test successful order creation"""
        # Get initial count
        initial_count = Order.objects.count()
        
        # Execute mutation
        mutation = CreateOrder()
        result = mutation.mutate(
            None,  # root
            None,  # info
            MagicMock(
                customer_id=str(self.customer.id),
                product_ids=[str(self.product1.id), str(self.product2.id)],
                order_date=None  # Will use datetime.now()
            )
        )
        
        # Verify order was created
        self.assertEqual(Order.objects.count(), initial_count + 1)
        self.assertEqual(result.order.customer.id, self.customer.id)
        self.assertEqual(result.order.total_amount, Decimal("30.00"))  # 10 + 20
        
        # Verify products are associated
        self.assertEqual(result.order.products.count(), 2)
        self.assertIn(self.product1, result.order.products.all())
        self.assertIn(self.product2, result.order.products.all())
    
    def test_create_order_no_products(self):
        """Test order creation fails with no products"""
        with self.assertRaises(GraphQLError) as context:
            mutation = CreateOrder()
            mutation.mutate(
                None,
                None,
                MagicMock(
                    customer_id=str(self.customer.id),
                    product_ids=[],  # Empty list!
                    order_date=None
                )
            )
        
        # Verify error
        self.assertIn("At least one product must be selected", str(context.exception))
    
    def test_create_order_invalid_customer(self):
        """Test order creation fails with invalid customer ID"""
        with self.assertRaises(GraphQLError) as context:
            mutation = CreateOrder()
            mutation.mutate(
                None,
                None,
                MagicMock(
                    customer_id="9999",  # Non-existent customer
                    product_ids=[str(self.product1.id)],
                    order_date=None
                )
            )
        
        # Verify error
        self.assertIn("does not exist", str(context.exception))
    
    def test_create_order_invalid_product(self):
        """Test order creation fails with invalid product ID"""
        with self.assertRaises(GraphQLError) as context:
            mutation = CreateOrder()
            mutation.mutate(
                None,
                None,
                MagicMock(
                    customer_id=str(self.customer.id),
                    product_ids=["9999"],  # Non-existent product
                    order_date=None
                )
            )
        
        # Verify error
        self.assertIn("does not exist", str(context.exception))


class TestIntegration(TestCase):
    """Integration tests using GraphQL client"""
    
    def test_full_graphql_query(self):
        """Test full GraphQL schema works"""
        from your_app.schema import schema
        
        # Create a customer first
        customer = Customer.objects.create(
            name="GraphQL Customer",
            email="graphql@example.com",
            phone="+1234567890"
        )
        
        # Create a product
        product = Product.objects.create(
            name="GraphQL Product",
            price=Decimal("99.99"),
            stock=10
        )
        
        # Create an order
        order = Order.objects.create(
            customer=customer,
            total_amount=Decimal("99.99")
        )
        order.products.add(product)
        
        # Test query
        query = """
            query {
                customers {
                    id
                    name
                    email
                }
                products {
                    id
                    name
                    price
                }
                orders {
                    id
                    totalAmount
                    customer {
                        id
                        name
                    }
                    products {
                        id
                        name
                    }
                }
            }
        """
        
        # Execute query
        result = schema.execute(query)
        
        # Verify no errors
        self.assertIsNone(result.errors)
        
        # Verify data structure
        self.assertIsNotNone(result.data)
        self.assertEqual(len(result.data['customers']), 1)
        self.assertEqual(len(result.data['products']), 1)
        self.assertEqual(len(result.data['orders']), 1)