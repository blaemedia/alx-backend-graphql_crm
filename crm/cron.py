import os
from datetime import datetime
import json
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
        # Using the simple mutation without arguments for default behavior
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
        
        # Alternative: Mutation with custom parameters
        # mutation = """
        #     mutation UpdateLowStock {
        #         updateLowStockProducts(threshold: 10, incrementBy: 10) {
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
                success = data.get('success', False)
                message = data.get('message', 'No message returned')
                updated_count = data.get('updatedCount', 0)
                updated_products = data.get('updatedProducts', [])
                timestamp = data.get('timestamp', 'Unknown time')
                
                log_message += f"Status: {'SUCCESS' if success else 'FAILED'}\n"
                log_message += f"Message: {message}\n"
                log_message += f"Mutation Timestamp: {timestamp}\n"
                log_message += f"Total Updated: {updated_count}\n\n"
                
                if updated_products:
                    log_message += f"Updated Products:\n"
                    log_message += f"{'-'*60}\n"
                    
                    for product in updated_products:
                        product_name = product.get('name', 'Unknown Product')
                        product_id = product.get('id', 'N/A')
                        old_stock = product.get('oldStock', 'N/A')
                        new_stock = product.get('newStock', 'N/A')
                        
                        log_message += f"  • {product_name} "
                        log_message += f"(ID: {product_id}): "
                        log_message += f"Stock {old_stock} → {new_stock} "
                        log_message += f"(+{new_stock - old_stock if isinstance(new_stock, int) and isinstance(old_stock, int) else 'N/A'})\n"
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
        import traceback
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
    from datetime import datetime
    from django.test import Client
    
    current_time = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    log_file_path = "/tmp/low_stock_updates_log.txt"
    
    # Initialize log
    log_message = f"\n{'='*60}\n"
    log_message += f"Low Stock Update (Django Client) - {current_time}\n"
    log_message += f"{'='*60}\n"
    
    try:
        client = Client()
        
        # GraphQL mutation
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
                success = data.get('success', False)
                message = data.get('message', 'No message returned')
                updated_count = data.get('updatedCount', 0)
                updated_products = data.get('updatedProducts', [])
                
                log_message += f"Status: {'SUCCESS' if success else 'FAILED'}\n"
                log_message += f"Message: {message}\n"
                log_message += f"Total Updated: {updated_count}\n\n"
                
                if updated_products:
                    log_message += f"Updated Products:\n"
                    log_message += f"{'-'*60}\n"
                    
                    for product in updated_products:
                        product_name = product.get('name', 'Unknown Product')
                        product_id = product.get('id', 'N/A')
                        old_stock = product.get('oldStock', 'N/A')
                        new_stock = product.get('newStock', 'N/A')
                        
                        log_message += f"  • {product_name} "
                        log_message += f"(ID: {product_id}): "
                        log_message += f"Stock {old_stock} → {new_stock} "
                        log_message += f"(+{new_stock - old_stock if isinstance(new_stock, int) and isinstance(old_stock, int) else 'N/A'})\n"
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
        import traceback
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
    from datetime import datetime
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
                mutation UpdateLowStock {
                    updateLowStockProducts(dryRun: true) {
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
                        log_message += f"(+{new_stock - old_stock if isinstance(new_stock, int) and isinstance(old_stock, int) else 'N/A'})\n"
                else:
                    log_message += "No low-stock products found.\n"
        else:
            log_message += f"HTTP Error: {response.status_code}\n"
            log_message += f"Response: {response.text[:500]}...\n"
    
    except Exception as e:
        log_message += f"ERROR: {str(e)}\n"
    
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