import os
from datetime import datetime
import subprocess
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
        # Method 1: Try using the gql library if available
        try:
            from gql import gql, Client
            from gql.transport.requests import RequestsHTTPTransport
            
            # Determine the GraphQL endpoint URL
            # Try to get it from settings, or use a default
            graphql_url = getattr(settings, 'GRAPHQL_URL', 'http://localhost:8000/graphql/')
            
            # Create a transport for the GraphQL endpoint
            transport = RequestsHTTPTransport(
                url=graphql_url,
                verify=True,
                retries=3,
            )
            
            # Create a GraphQL client
            client = Client(transport=transport, fetch_schema_from_transport=False)
            
            # Define the GraphQL query
            query = gql("""
                query {
                    hello
                }
            """)
            
            # Execute the query
            result = client.execute(query)
            
            # Append GraphQL status to log
            with open(log_file_path, 'a') as f:
                if 'hello' in result:
                    f.write(f"{current_time} GraphQL endpoint responsive: {result['hello']}\n")
                else:
                    f.write(f"{current_time} GraphQL endpoint responded with unexpected format\n")
            
        except ImportError:
            # gql library not installed, fall back to method 2
            raise ImportError("gql library not available")
            
    except ImportError:
        # Method 2: Fall back to using requests library
        try:
            import requests
            
            # Determine the GraphQL endpoint URL
            graphql_url = getattr(settings, 'GRAPHQL_URL', 'http://localhost:8000/graphql/')
            
            # Prepare the GraphQL query
            query = {
                "query": "query { hello }"
            }
            
            # Make the request
            response = requests.post(
                graphql_url,
                json=query,
                headers={'Content-Type': 'application/json'},
                timeout=5  # 5 second timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                with open(log_file_path, 'a') as f:
                    if 'data' in result and 'hello' in result['data']:
                        f.write(f"{current_time} GraphQL endpoint responsive: {result['data']['hello']}\n")
                    else:
                        f.write(f"{current_time} GraphQL endpoint responded with: {result}\n")
            else:
                with open(log_file_path, 'a') as f:
                    f.write(f"{current_time} GraphQL endpoint returned status: {response.status_code}\n")
                    
        except ImportError:
            # requests library not installed, fall back to method 3
            with open(log_file_path, 'a') as f:
                f.write(f"{current_time} Note: Both gql and requests libraries not available for GraphQL check\n")
                
        except Exception as e:
            # Log any other errors during requests-based GraphQL check
            with open(log_file_path, 'a') as f:
                f.write(f"{current_time} GraphQL check failed (requests): {str(e)}\n")
    
    except Exception as e:
        # Log any other errors during gql-based GraphQL check
        with open(log_file_path, 'a') as f:
            f.write(f"{current_time} GraphQL check failed (gql): {str(e)}\n")
    
    return "Heartbeat logged successfully"

# Alternative implementation using Django's test framework (for completeness)
def check_graphql_via_django_test():
    """
    Alternative method to check GraphQL using Django's test client
    This doesn't require external HTTP calls
    """
    try:
        from django.test import Client as DjangoTestClient
        
        client = DjangoTestClient()
        
        # Query the GraphQL endpoint for the hello field
        query = {
            'query': 'query { hello }'
        }
        
        # Make a POST request to your GraphQL endpoint
        response = client.post(
            '/graphql/',
            data=json.dumps(query),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            result = json.loads(response.content)
            return result
        else:
            return {"error": f"HTTP {response.status_code}"}
            
    except Exception as e:
        return {"error": str(e)}