import requests
from datetime import datetime

def log_crm_heartbeat():
    """
    Logs a heartbeat message every 5 minutes.
    Optionally checks the GraphQL hello field.
    """
    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    log_message = f"{timestamp} CRM is alive\n"

    # Append heartbeat log
    with open("/tmp/crm_heartbeat_log.txt", "a") as f:
        f.write(log_message)

    # Optional: check GraphQL hello field
    try:
        response = requests.post(
            "http://localhost:8000/graphql",
            json={"query": "{ hello }"},
            timeout=5
        )
        if response.status_code == 200:
            with open("/tmp/crm_heartbeat_log.txt", "a") as f:
                f.write(f"{timestamp} GraphQL hello query successful\n")
        else:
            with open("/tmp/crm_heartbeat_log.txt", "a") as f:
                f.write(f"{timestamp} GraphQL hello query failed (status {response.status_code})\n")
    except Exception as e:
        with open("/tmp/crm_heartbeat_log.txt", "a") as f:
            f.write(f"{timestamp} Error querying GraphQL: {e}\n")
