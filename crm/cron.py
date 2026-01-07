import os
from datetime import datetime
import json
import traceback
from django.conf import settings

def log_crm_heartbeat():
    """
    Logs a heartbeat message every 5 minutes to confirm CRM application health.
    Optionally queries GraphQL endpoint to verify responsiveness.
    """
    
    # Get current timestamp in the specified format
    current_time = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    message = f"{current_time} CRM is alive"
    
    # Log to the specified file
    log_file_path = "/tmp/crm_heartbeat_log.txt"
    
    # Append to file (create if doesn't exist)
    with open(log_file_path, 'a') as f:
        f.write(f"{message}\n")
    
    # Optional: Query GraphQL hello field to verify endpoint
    try:
        import requests
        
        # Determine the GraphQL endpoint URL
        graphql_url = getattr(settings, 'GRAPHQL_URL', 'http://localhost:8000/graphql/')
        
        # Prepare the GraphQL query
        query = {
            "query": "query { hello }"
        }
        
        # Make the request with timeout
        response = requests.post(
            graphql_url,
            json=query,
            headers={'Content-Type': 'application/json'},
            timeout=5  # 5 second timeout
        )
        
        # Log the result
        with open(log_file_path, 'a') as f:
            if response.status_code == 200:
                result = response.json()
                if 'data' in result and 'hello' in result['data']:
                    f.write(f"{current_time} GraphQL endpoint responsive: {result['data']['hello']}\n")
                else:
                    f.write(f"{current_time} GraphQL endpoint responded with unexpected format: {result}\n")
            else:
                f.write(f"{current_time} GraphQL endpoint returned HTTP {response.status_code}\n")
                
    except requests.exceptions.Timeout:
        with open(log_file_path, 'a') as f:
            f.write(f"{current_time} GraphQL endpoint timeout (5 seconds)\n")
    except requests.exceptions.ConnectionError:
        with open(log_file_path, 'a') as f:
            f.write(f"{current_time} GraphQL endpoint connection failed\n")
    except ImportError:
        with open(log_file_path, 'a') as f:
            f.write(f"{current_time} Note: requests library not installed for GraphQL check\n")
    except Exception as e:
        with open(log_file_path, 'a') as f:
            f.write(f"{current_time} GraphQL check failed: {str(e)}\n")
    
    return "Heartbeat logged successfully"


def update_low_stock():
    """
    Cron job that runs every 12 hours to update low-stock products.
    Executes GraphQL mutation and logs the updates.
    """
    
    # Get current timestamp
    current_time = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    log_file_path = "/tmp/low_stock_updates_log.txt"
    
    # Initialize log message
    log_message = f"\n{'='*60}\n"
    log_message += f"Low Stock Update - {current_time}\n"
    log_message += f"{'='*60}\n"
    
    try:
        import requests
        
        # Get GraphQL endpoint URL
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:8000')
        graphql_url = f"{base_url}/graphql/"
        
        # GraphQL mutation to update low stock products
        # Using the updated mutation structure that matches our schema
        mutation = """
            mutation UpdateLowStock {
                updateLowStockProducts {
                    success
                    message
                    updatedCount
                    timestamp
                    updatedProducts {
                        id
                        name
                        oldStock
                        newStock
                    }
                }
            }
        """
        
        # Alternative: Mutation with custom parameters (threshold and incrementBy)
        # mutation = """
        #     mutation UpdateLowStock($threshold: Int, $incrementBy: Int) {
        #         updateLowStockProducts(threshold: $threshold, incrementBy: $incrementBy) {
        #             success
        #             message
        #             updatedCount
        #             timestamp
        #             updatedProducts {
        #                 id
        #                 name
        #                 oldStock
        #                 newStock
        #             }
        #         }
        #     }
        # """
        
        # Make the GraphQL request
        response = requests.post(
            graphql_url,
            json={'query': mutation},
            headers={'Content-Type': 'application/json'},
            timeout=30  # 30 second timeout for potentially many updates
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if 'errors' in result:
                # GraphQL errors
                log_message += f"GraphQL Errors:\n"
                for error in result['errors']:
                    log_message += f"  - {error.get('message', 'Unknown error')}\n"
                    if 'locations' in error:
                        loc = error['locations'][0]
                        log_message += f"    at line {loc.get('line')}, column {loc.get('column')}\n"
            else:
                data = result.get('data', {}).get('updateLowStockProducts', {})
                
                # Handle different response field naming conventions
                # Try camelCase first, then snake_case
                success = data.get('success', data.get('success', False))
                message = data.get('message', data.get('message', 'No message returned'))
                updated_count = data.get('updatedCount', data.get('updated_count', 0))
                updated_products = data.get('updatedProducts', data.get('updated_products', []))
                timestamp = data.get('timestamp', data.get('timestamp', 'Unknown time'))
                
                log_message += f"Status: {'SUCCESS' if success else 'FAILED'}\n"
                log_message += f"Message: {message}\n"
                log_message += f"Mutation Timestamp: {timestamp}\n"
                log_message += f"Total Updated: {updated_count}\n\n"
                
                if updated_products:
                    log_message += f"Updated Products:\n"
                    log_message += f"{'-'*60}\n"
                    
                    for product in updated_products:
                        # Handle both camelCase and snake_case field names
                        product_name = product.get('name', product.get('name', 'Unknown Product'))
                        product_id = product.get('id', product.get('id', 'N/A'))
                        old_stock = product.get('oldStock', product.get('old_stock', 'N/A'))
                        new_stock = product.get('newStock', product.get('new_stock', 'N/A'))
                        
                        log_message += f"  • {product_name} "
                        log_message += f"(ID: {product_id}): "
                        log_message += f"Stock {old_stock} → {new_stock} "
                        
                        # Calculate the increment if both are integers
                        if isinstance(new_stock, (int, float)) and isinstance(old_stock, (int, float)):
                            increment = new_stock - old_stock
                            log_message += f"(+{increment})\n"
                        else:
                            log_message += "\n"
                else:
                    log_message += "No low-stock products were updated.\n"
        else:
            log_message += f"HTTP Error: {response.status_code}\n"
            log_message += f"Response: {response.text[:500]}...\n"  # Truncate long responses
    
    except requests.exceptions.Timeout:
        log_message += f"ERROR: Request timed out after 30 seconds\n"
    except requests.exceptions.ConnectionError:
        graphql_url = getattr(settings, 'GRAPHQL_URL', 'http://localhost:8000/graphql/')
        log_message += f"ERROR: Could not connect to GraphQL endpoint at {graphql_url}\n"
    except ImportError:
        log_message += f"ERROR: requests library not installed. Install with: pip install requests\n"
    except Exception as e:
        log_message += f"ERROR: {str(e)}\n"
        log_message += f"Traceback: {traceback.format_exc()}\n"
    
    # Add execution timestamp at the end
    log_message += f"{'='*60}\n"
    log_message += f"Execution completed at: {datetime.now().strftime('%d/%m/%Y-%H:%M:%S')}\n"
    log_message += f"{'='*60}\n\n"
    
    # Append to log file
    with open(log_file_path, 'a') as f:
        f.write(log_message)
    
    return f"Low stock update completed at {current_time}"


def update_low_stock_django():
    """
    Alternative version using Django's test client (no external HTTP needed).
    This is more efficient as it doesn't require HTTP requests.
    """
    from django.test import Client
    
    current_time = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    log_file_path = "/tmp/low_stock_updates_log.txt"
    
    # Initialize log
    log_message = f"\n{'='*60}\n"
    log_message += f"Low Stock Update (Django Client) - {current_time}\n"
    log_message += f"{'='*60}\n"
    
    try:
        client = Client()
        
        # GraphQL mutation - updated to match schema
        mutation = {
            "query": """
                mutation UpdateLowStock {
                    updateLowStockProducts {
                        success
                        message
                        updatedCount
                        timestamp
                        updatedProducts {
                            id
                            name
                            oldStock
                            newStock
                        }
                    }
                }
            """
        }
        
        # Make the request
        response = client.post(
            '/graphql/',
            data=json.dumps(mutation),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            result = json.loads(response.content)
            
            if 'errors' in result:
                log_message += f"GraphQL Errors:\n"
                for error in result['errors']:
                    log_message += f"  - {error.get('message', 'Unknown error')}\n"
            else:
                data = result.get('data', {}).get('updateLowStockProducts', {})
                
                # Handle both camelCase and snake_case response fields
                success = data.get('success', data.get('success', False))
                message = data.get('message', data.get('message', 'No message returned'))
                updated_count = data.get('updatedCount', data.get('updated_count', 0))
                updated_products = data.get('updatedProducts', data.get('updated_products', []))
                
                log_message += f"Status: {'SUCCESS' if success else 'FAILED'}\n"
                log_message += f"Message: {message}\n"
                log_message += f"Total Updated: {updated_count}\n\n"
                
                if updated_products:
                    log_message += f"Updated Products:\n"
                    log_message += f"{'-'*60}\n"
                    
                    for product in updated_products:
                        # Handle both camelCase and snake_case field names
                        product_name = product.get('name', product.get('name', 'Unknown Product'))
                        product_id = product.get('id', product.get('id', 'N/A'))
                        old_stock = product.get('oldStock', product.get('old_stock', 'N/A'))
                        new_stock = product.get('newStock', product.get('new_stock', 'N/A'))
                        
                        log_message += f"  • {product_name} "
                        log_message += f"(ID: {product_id}): "
                        log_message += f"Stock {old_stock} → {new_stock} "
                        
                        # Calculate the increment if both are integers
                        if isinstance(new_stock, (int, float)) and isinstance(old_stock, (int, float)):
                            increment = new_stock - old_stock
                            log_message += f"(+{increment})\n"
                        else:
                            log_message += "\n"
                else:
                    log_message += "No low-stock products were updated.\n"
        else:
            log_message += f"HTTP Error: {response.status_code}\n"
            try:
                log_message += f"Response: {response.content.decode()}\n"
            except:
                log_message += f"Response: {response.content}\n"
            
    except Exception as e:
        log_message += f"ERROR: {str(e)}\n"
        log_message += f"Traceback: {traceback.format_exc()}\n"
    
    # Add execution timestamp at the end
    log_message += f"{'='*60}\n"
    log_message += f"Execution completed at: {datetime.now().strftime('%d/%m/%Y-%H:%M:%S')}\n"
    log_message += f"{'='*60}\n\n"
    
    # Append to log file
    with open(log_file_path, 'a') as f:
        f.write(log_message)
    
    return f"Low stock update completed at {current_time}"


def test_low_stock_dry_run():
    """
    Test function to simulate low stock update without actually updating.
    Useful for debugging and testing.
    """
    import requests
    
    current_time = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    log_file_path = "/tmp/low_stock_test_log.txt"
    
    log_message = f"\n{'='*60}\n"
    log_message += f"Low Stock DRY RUN Test - {current_time}\n"
    log_message += f"{'='*60}\n"
    
    try:
        graphql_url = getattr(settings, 'GRAPHQL_URL', 'http://localhost:8000/graphql/')
        
        # Mutation with dryRun parameter set to true
        mutation = {
            "query": """
                mutation UpdateLowStock($dryRun: Boolean) {
                    updateLowStockProducts(dryRun: $dryRun) {
                        success
                        message
                        updatedCount
                        timestamp
                        updatedProducts {
                            id
                            name
                            oldStock
                            newStock
                        }
                    }
                }
            """,
            "variables": {
                "dryRun": True
            }
        }
        
        response = requests.post(
            graphql_url,
            json=mutation,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            log_message += f"DRY RUN - No actual updates were made\n\n"
            
            if 'errors' in result:
                log_message += f"GraphQL Errors:\n"
                for error in result['errors']:
                    log_message += f"  - {error.get('message', 'Unknown error')}\n"
            else:
                data = result.get('data', {}).get('updateLowStockProducts', {})
                success = data.get('success', False)
                message = data.get('message', 'No message returned')
                updated_count = data.get('updatedCount', 0)
                updated_products = data.get('updatedProducts', [])
                
                log_message += f"Status: {'SUCCESS' if success else 'FAILED'}\n"
                log_message += f"Message: {message}\n"
                log_message += f"Would update: {updated_count} products\n\n"
                
                if updated_products:
                    log_message += f"Products that would be updated:\n"
                    log_message += f"{'-'*60}\n"
                    
                    for product in updated_products:
                        product_name = product.get('name', 'Unknown Product')
                        product_id = product.get('id', 'N/A')
                        old_stock = product.get('oldStock', 'N/A')
                        new_stock = product.get('newStock', 'N/A')
                        
                        log_message += f"  • {product_name} "
                        log_message += f"(ID: {product_id}): "
                        log_message += f"Stock {old_stock} → {new_stock} "
                        
                        if isinstance(new_stock, (int, float)) and isinstance(old_stock, (int, float)):
                            log_message += f"(+{new_stock - old_stock})\n"
                        else:
                            log_message += "\n"
                else:
                    log_message += "No low-stock products found.\n"
        else:
            log_message += f"HTTP Error: {response.status_code}\n"
            log_message += f"Response: {response.text[:500]}...\n"
    
    except Exception as e:
        log_message += f"ERROR: {str(e)}\n"
        log_message += f"Traceback: {traceback.format_exc()}\n"
    
    # Append to log file
    with open(log_file_path, 'a') as f:
        f.write(log_message)
    
    print(f"Dry run test completed. Check {log_file_path} for results.")
    return "Dry run test completed"


# Quick test function
def test_cron_functions():
    """Test both cron functions and print results."""
    print("Testing CRM Heartbeat...")
    result1 = log_crm_heartbeat()
    print(f"Heartbeat: {result1}")
    
    print("\nTesting Low Stock Update (Django Client)...")
    result2 = update_low_stock_django()
    print(f"Low Stock Update: {result2}")
    
    print("\nCheck log files:")
    print("  Heartbeat: /tmp/crm_heartbeat_log.txt")
    print("  Low Stock: /tmp/low_stock_updates_log.txt")
    
    return "Test completed successfully"


def check_low_stock_products():
    """
    Check which products are currently low in stock without updating them.
    Returns a list of low-stock products.
    """
    try:
        import requests
        
        graphql_url = getattr(settings, 'GRAPHQL_URL', 'http://localhost:8000/graphql/')
        
        # Query to get low stock products
        query = {
            "query": """
                query GetLowStockProducts($threshold: Int) {
                    lowStockProducts(threshold: $threshold) {
                        edges {
                            node {
                                id
                                name
                                stock
                                price
                            }
                        }
                    }
                }
            """,
            "variables": {
                "threshold": 10
            }
        }
        
        response = requests.post(
            graphql_url,
            json=query,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if 'errors' in result:
                print(f"GraphQL Errors: {result['errors']}")
                return []
            
            data = result.get('data', {})
            products = data.get('lowStockProducts', {}).get('edges', [])
            
            low_stock_products = []
            for edge in products:
                node = edge.get('node', {})
                low_stock_products.append({
                    'id': node.get('id'),
                    'name': node.get('name'),
                    'stock': node.get('stock'),
                    'price': node.get('price')
                })
            
            return low_stock_products
        
        return []
        
    except Exception as e:
        print(f"Error checking low stock products: {e}")
        return []


def test_graphql_schema():
    """
    Test the GraphQL schema to ensure it's working correctly.
    """
    try:
        import requests
        
        graphql_url = getattr(settings, 'GRAPHQL_URL', 'http://localhost:8000/graphql/')
        
        # Test query
        test_query = {
            "query": """
                query TestSchema {
                    hello
                    __schema {
                        types {
                            name
                        }
                    }
                }
            """
        }
        
        response = requests.post(
            graphql_url,
            json=test_query,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if 'errors' in result:
                print(f"Schema test errors: {result['errors']}")
                return False
            
            # Check if our mutations are in the schema
            schema_query = {
                "query": """
                    query CheckMutations {
                        __type(name: "Mutation") {
                            fields {
                                name
                            }
                        }
                    }
                """
            }
            
            response2 = requests.post(
                graphql_url,
                json=schema_query,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response2.status_code == 200:
                result2 = response2.json()
                if not 'errors' in result2:
                    mutation_fields = result2.get('data', {}).get('__type', {}).get('fields', [])
                    mutation_names = [field['name'] for field in mutation_fields]
                    
                    print(f"Available mutations: {mutation_names}")
                    
                    if 'updateLowStockProducts' in mutation_names:
                        print("✓ updateLowStockProducts mutation is available")
                        return True
                    else:
                        print("✗ updateLowStockProducts mutation NOT found")
                        return False
            
            return True
            
        return False
        
    except Exception as e:
        print(f"Error testing GraphQL schema: {e}")
        return False


def setup_cron_test_environment():
    """
    Setup a test environment for cron jobs.
    Creates necessary directories and files.
    """
    import os
    
    # Create log files if they don't exist
    log_files = [
        "/tmp/crm_heartbeat_log.txt",
        "/tmp/low_stock_updates_log.txt",
        "/tmp/low_stock_test_log.txt"
    ]
    
    for log_file in log_files:
        if not os.path.exists(log_file):
            with open(log_file, 'w') as f:
                f.write(f"Log file created at: {datetime.now().strftime('%d/%m/%Y-%H:%M:%S')}\n")
                f.write(f"{'='*60}\n\n")
            print(f"Created log file: {log_file}")
        else:
            print(f"Log file already exists: {log_file}")
    
    print("\nTo test the cron functions, run:")
    print("  python manage.py shell")
    print("  >>> from crm.cron import test_cron_functions")
    print("  >>> test_cron_functions()")
    print("\nOr test individually:")
    print("  >>> from crm.cron import log_crm_heartbeat, update_low_stock_django")
    print("  >>> log_crm_heartbeat()")
    print("  >>> update_low_stock_django()")
    
    return "Test environment setup complete"