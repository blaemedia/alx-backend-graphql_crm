#!/usr/bin/env python3

from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport
from datetime import datetime, timedelta

# GraphQL endpoint
GRAPHQL_URL = "http://localhost:8000/graphql"

# Transport
transport = RequestsHTTPTransport(url=GRAPHQL_URL, verify=True, retries=3)
client = Client(transport=transport, fetch_schema_from_transport=True)

# Calculate date 7 days ago
seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

# GraphQL query to get pending orders in the last 7 days
query = gql(
    """
    query getRecentOrders($date: Date!) {
        orders(orderDate_Gte: $date) {
            id
            customer {
                email
            }
            orderDate
        }
    }
    """
)

params = {"date": seven_days_ago}

try:
    result = client.execute(query, variable_values=params)
    orders = result.get("orders", [])
except Exception as e:
    print(f"Error fetching orders: {e}")
    orders = []

# Log each order to a file
with open("/tmp/order_reminders_log.txt", "a") as log_file:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for order in orders:
        order_id = order["id"]
        email = order["customer"]["email"]
        log_file.write(f"{timestamp} - Order ID: {order_id}, Customer Email: {email}\n")

print("Order reminders processed!")
