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
        # First, try to import necessary GraphQL components
        # This assumes you have graphene-django installed
        from django.test import Client
        import json
        
        client = Client()
        
        # Query the GraphQL endpoint for the hello field
        # Adjust the query based on your actual GraphQL schema
        query = {
            'query': 'query { hello }'
        }
        
        # Make a POST request to your GraphQL endpoint
        # Adjust the endpoint URL if different
        response = client.post(
            '/graphql/', 
            data=json.dumps(query),
            content_type='application/json'
        )
        
        if response.status_code == 200:
            result = json.loads(response.content)
            
            # Append GraphQL status to log
            with open(log_file_path, 'a') as f:
                if 'data' in result and 'hello' in result['data']:
                    f.write(f"{current_time} GraphQL endpoint responsive: {result['data']['hello']}\n")
                else:
                    f.write(f"{current_time} GraphQL endpoint responded with unexpected format\n")
        else:
            with open(log_file_path, 'a') as f:
                f.write(f"{current_time} GraphQL endpoint returned status: {response.status_code}\n")
                
    except ImportError as e:
        # graphene-django not installed or not available
        with open(log_file_path, 'a') as f:
            f.write(f"{current_time} Note: GraphQL check skipped (graphene-django not available)\n")
    except Exception as e:
        # Log any other errors during GraphQL check
        with open(log_file_path, 'a') as f:
            f.write(f"{current_time} GraphQL check failed: {str(e)}\n")
    
    return "Heartbeat logged successfully"

# Alternative implementation if you want to use direct schema execution
def check_graphql_health():
    """
    Alternative method to check GraphQL health by directly executing schema
    """
    try:
        # Import your schema
        from crm.schema import schema
        
        # Execute a simple query
        result = schema.execute('{ hello }')
        
        if result.errors:
            return f"GraphQL errors: {result.errors}"
        else:
            return f"GraphQL data: {result.data}"
            
    except Exception as e:
        return f"GraphQL health check failed: {str(e)}"