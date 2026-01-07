import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.db.models import Q, F
from datetime import datetime

# Import the Product model (and other models)
from .models import Customer, Product, Order  # Make sure Product is imported
from .filters import CustomerFilter, ProductFilter, OrderFilter

# GraphQL Types
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        filterset_class = CustomerFilter
        interfaces = (graphene.relay.Node,)


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        filterset_class = ProductFilter
        interfaces = (graphene.relay.Node,)
    
    # Optional: Add computed fields if needed
    is_low_stock = graphene.Boolean()
    
    def resolve_is_low_stock(self, info):
        # Consider stock < 10 as low stock
        return self.stock < 10 if self.stock is not None else False


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        filterset_class = OrderFilter
        interfaces = (graphene.relay.Node,)


# Input type for order_by sorting
class OrderByInput(graphene.InputObjectType):
    field = graphene.String(required=True)


# Types for low-stock update response
class UpdatedProductType(graphene.ObjectType):
    id = graphene.ID()
    name = graphene.String()
    sku = graphene.String()
    old_stock = graphene.Int()
    new_stock = graphene.Int()
    category = graphene.String()


class UpdateLowStockProductsResponse(graphene.ObjectType):
    success = graphene.Boolean()
    message = graphene.String()
    updated_count = graphene.Int()
    updated_products = graphene.List(UpdatedProductType)
    timestamp = graphene.String()


# Query class with all existing queries plus hello
class Query(graphene.ObjectType):
    hello = graphene.String(default_value="Hello from CRM!")
    
    all_customers = DjangoFilterConnectionField(CustomerType, order_by=graphene.String())
    all_products = DjangoFilterConnectionField(ProductType, order_by=graphene.String())
    all_orders = DjangoFilterConnectionField(OrderType, order_by=graphene.String())
    
    # Add a specific query for low-stock products
    low_stock_products = DjangoFilterConnectionField(
        ProductType, 
        order_by=graphene.String(),
        threshold=graphene.Int(required=False, default_value=10)
    )

    def resolve_hello(self, info):
        return "CRM GraphQL endpoint is healthy"
    
    def resolve_all_customers(self, info, order_by=None, **kwargs):
        qs = Customer.objects.all()
        if order_by:
            qs = qs.order_by(order_by)
        return qs

    def resolve_all_products(self, info, order_by=None, **kwargs):
        qs = Product.objects.all()
        if order_by:
            qs = qs.order_by(order_by)
        return qs

    def resolve_all_orders(self, info, order_by=None, **kwargs):
        qs = Order.objects.all()
        if order_by:
            qs = qs.order_by(order_by)
        return qs
    
    def resolve_low_stock_products(self, info, threshold=10, order_by=None, **kwargs):
        """Return products with stock below the threshold"""
        qs = Product.objects.filter(stock__lt=threshold)
        if order_by:
            qs = qs.order_by(order_by)
        return qs


# --- Mutations ---

class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()

    # Return fields
    id = graphene.ID()
    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        if Customer.objects.filter(email=email).exists():
            raise Exception("Email already exists")

        customer = Customer(name=name, email=email, phone=phone)
        customer.save()

        return CreateCustomer(
            id=customer.id,
            customer=customer,
            message="Customer created successfully"
        )


class UpdateLowStockProducts(graphene.Mutation):
    class Arguments:
        threshold = graphene.Int(default_value=10)
        increment_by = graphene.Int(default_value=10)
        dry_run = graphene.Boolean(default_value=False)
    
    Output = UpdateLowStockProductsResponse
    
    def mutate(self, info, threshold=10, increment_by=10, dry_run=False):
        # Get current timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
        
        try:
            # Query products with stock below threshold
            low_stock_products = Product.objects.filter(stock__lt=threshold)
            
            updated_products_data = []
            updated_count = 0
            
            if dry_run:
                # Simulate update without saving
                for product in low_stock_products:
                    updated_products_data.append({
                        'id': product.id,
                        'name': product.name,
                        'sku': product.sku if hasattr(product, 'sku') else 'N/A',
                        'old_stock': product.stock,
                        'new_stock': product.stock + increment_by,
                        'category': str(product.category) if hasattr(product, 'category') and product.category else None
                    })
                
                return UpdateLowStockProductsResponse(
                    success=True,
                    message=f"Dry run: Would update {len(updated_products_data)} products below stock threshold {threshold}",
                    updated_count=len(updated_products_data),
                    updated_products=updated_products_data,
                    timestamp=timestamp
                )
            
            # Actually update the products
            for product in low_stock_products:
                try:
                    old_stock = product.stock
                    product.stock = F('stock') + increment_by
                    product.save()
                    
                    # Refresh to get the updated value
                    product.refresh_from_db()
                    
                    updated_products_data.append({
                        'id': product.id,
                        'name': product.name,
                        'sku': product.sku if hasattr(product, 'sku') else 'N/A',
                        'old_stock': old_stock,
                        'new_stock': product.stock,
                        'category': str(product.category) if hasattr(product, 'category') and product.category else None
                    })
                    updated_count += 1
                    
                except Exception as e:
                    # Log individual product errors but continue with others
                    print(f"Error updating product {product.id}: {str(e)}")
                    continue
            
            message = f"Successfully updated {updated_count} low-stock products"
            if updated_count == 0:
                message = "No products found below the stock threshold"
            
            return UpdateLowStockProductsResponse(
                success=True,
                message=message,
                updated_count=updated_count,
                updated_products=updated_products_data,
                timestamp=timestamp
            )
            
        except Exception as e:
            return UpdateLowStockProductsResponse(
                success=False,
                message=f"Error updating low-stock products: {str(e)}",
                updated_count=0,
                updated_products=[],
                timestamp=timestamp
            )


# Single Mutation class containing all mutations
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    update_low_stock_products = UpdateLowStockProducts.Field()


# Schema definition
schema = graphene.Schema(query=Query, mutation=Mutation)