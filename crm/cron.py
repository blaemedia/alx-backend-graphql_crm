import requests
from datetime import datetime

def log_crm_heartbeat():
    timestamp = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
    with open("/tmp/crm_heartbeat_log.txt", "a") as f:
        f.write(f"{timestamp} CRM is alive\n")

    # Optional GraphQL check
    try:
        response = requests.post(
            "http://localhost:8000/graphql",
            json={"query": "{ hello }"},
            timeout=5
        )
        with open("/tmp/crm_heartbeat_log.txt", "a") as f:
            if response.status_code == 200:
                f.write(f"{timestamp} GraphQL hello query successful\n")
            else:
                f.write(f"{timestamp} GraphQL hello query failed (status {response.status_code})\n")
    except Exception as e:
        with open("/tmp/crm_heartbeat_log.txt", "a") as f:
            f.write(f"{timestamp} Error querying GraphQL: {e}\n")
