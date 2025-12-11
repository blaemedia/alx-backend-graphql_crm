# tests/test_graphql.py
from django.test import TestCase
from graphene.test import Client
from unittest.mock import patch, MagicMock
import json
from decimal import Decimal

from your_app.schema import schema
from your_app.models import Customer, Product, Order


class TestGraphQLMutations(TestCase):
    def setUp(self):
        self.client = Client(schema)
        self.test_customer = Customer.objects.create(
            name="Test Customer",
            email="customer@example.com",
            phone="+1234567890"
        )
        self.test_product = Product.objects.create(
            name="Test Product",
            price=Decimal("29.99"),
            stock=100
        )
    
    def test_create_customer_mutation_save_called(self):
        """Test GraphQL mutation calls save()"""
        with patch.object(Customer, 'save') as mock_save:
            mutation = """
                mutation {
                    createCustomer(input: {
                        name: "John Doe",
                        email: "john@example.com",
                        phone: "+1234567890"
                    }) {
                        customer {
                            id
                            name
                            email
                        }
                        message
                    }
                }
            """
            
            # Execute GraphQL mutation
            result = self.client.execute(mutation)
            
            # Check if save was called
            self.assertTrue(mock_save.called)
            
            # Verify the response
            self.assertIsNotNone(result.get('data'))
            self.assertIsNotNone(result['data']['createCustomer']['customer'])
    
    def test_bulk_create_customers_save_called(self):
        """Test bulk create mutation calls save()"""
        with patch.object(Customer, 'save') as mock_save:
            mutation = """
                mutation {
                    bulkCreateCustomers(inputs: [
                        {
                            name: "Customer 1",
                            email: "customer1@example.com"
                        },
                        {
                            name: "Customer 2",
                            email: "customer2@example.com",
                            phone: "+1234567890"
                        }
                    ]) {
                        customers {
                            id
                            name
                        }
                        errors
                    }
                }
            """
            
            result = self.client.execute(mutation)
            
            # Should call save twice (once for each customer)
            self.assertEqual(mock_save.call_count, 2)
    
    def test_create_product_mutation(self):
        """Test product creation calls save()"""
        with patch.object(Product, 'save') as mock_save:
            mutation = """
                mutation {
                    createProduct(input: {
                        name: "Test Product",
                        price: 29.99,
                        stock: 100
                    }) {
                        product {
                            id
                            name
                            price
                        }
                    }
                }
            """
            
            result = self.client.execute(mutation)
            self.assertTrue(mock_save.called)
    
    def test_create_order_mutation(self):
        """Test order creation calls save() and validates properly"""
        with patch.object(Order, 'save') as mock_save:
            # Prepare mutation with existing customer and product IDs
            mutation = f"""
                mutation {{
                    createOrder(input: {{
                        customerId: "{self.test_customer.id}",
                        productIds: ["{self.test_product.id}"],
                        orderDate: "2024-01-15T10:00:00Z"
                    }}) {{
                        order {{
                            id
                            totalAmount
                            orderDate
                            customer {{
                                id
                                name
                            }}
                            products {{
                                id
                                name
                            }}
                        }}
                    }}
                }}
            """
            
            result = self.client.execute(mutation)
            
            # Check if save was called on Order
            self.assertTrue(mock_save.called)
            
            # Verify response structure
            self.assertIsNotNone(result.get('data'))
            self.assertIsNotNone(result['data']['createOrder']['order'])
            
            # Verify total amount calculation
            order_data = result['data']['createOrder']['order']
            self.assertEqual(order_data['totalAmount'], "29.99")
    
    def test_create_order_with_multiple_products(self):
        """Test order creation with multiple products calls save()"""
        # Create additional product
        product2 = Product.objects.create(
            name="Product 2",
            price=Decimal("15.50"),
            stock=50
        )
        
        with patch.object(Order, 'save') as mock_save:
            mutation = f"""
                mutation {{
                    createOrder(input: {{
                        customerId: "{self.test_customer.id}",
                        productIds: ["{self.test_product.id}", "{product2.id}"],
                        orderDate: "2024-01-15T10:00:00Z"
                    }}) {{
                        order {{
                            id
                            totalAmount
                            products {{
                                id
                                name
                            }}
                        }}
                    }}
                }}
            """
            
            result = self.client.execute(mutation)
            
            # Check if save was called
            self.assertTrue(mock_save.called)
            
            # Verify total amount is sum of both products
            order_data = result['data']['createOrder']['order']
            self.assertEqual(order_data['totalAmount'], "45.49")  # 29.99 + 15.50
    
    def test_create_customer_with_invalid_phone(self):
        """Test customer creation fails with invalid phone and save() is not called"""
        with patch.object(Customer, 'save') as mock_save:
            mutation = """
                mutation {
                    createCustomer(input: {
                        name: "Invalid Phone",
                        email: "invalid@example.com",
                        phone: "invalid-phone"
                    }) {
                        customer {
                            id
                        }
                        message
                    }
                }
            """
            
            result = self.client.execute(mutation)
            
            # save() should NOT be called because validation fails
            self.assertFalse(mock_save.called)
            
            # Should have errors
            self.assertIsNotNone(result.get('errors'))
            
            # Verify error message contains phone validation error
            errors = result['errors'][0]['message']
            self.assertIn("Invalid phone format", errors)
    
    def test_create_product_with_invalid_price(self):
        """Test product creation fails with invalid price and save() is not called"""
        with patch.object(Product, 'save') as mock_save:
            mutation = """
                mutation {
                    createProduct(input: {
                        name: "Invalid Product",
                        price: -10.00,
                        stock: 100
                    }) {
                        product {
                            id
                        }
                    }
                }
            """
            
            result = self.client.execute(mutation)
            
            # save() should NOT be called because price validation fails
            self.assertFalse(mock_save.called)
            
            # Should have errors
            self.assertIsNotNone(result.get('errors'))
            self.assertIn("Price must be a positive number", result['errors'][0]['message'])
    
    def test_create_order_with_invalid_customer(self):
        """Test order creation fails with invalid customer ID and save() is not called"""
        with patch.object(Order, 'save') as mock_save:
            mutation = """
                mutation {
                    createOrder(input: {
                        customerId: "9999",  # Non-existent ID
                        productIds: ["1"]
                    }) {
                        order {
                            id
                        }
                    }
                }
            """
            
            result = self.client.execute(mutation)
            
            # save() should NOT be called because customer doesn't exist
            self.assertFalse(mock_save.called)
            
            # Should have errors
            self.assertIsNotNone(result.get('errors'))
            self.assertIn("does not exist", result['errors'][0]['message'])