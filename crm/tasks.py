from celery import shared_task
import requests
from datetime import datetime

GRAPHQL_URL = "http://localhost:8000/graphql"

@shared_task
def generate_crm_report():
    """
    Generates a weekly CRM report: total customers, total orders, total revenue.
    Logs it to /tmp/crm_report_log.txt
    """
    query = """
    query {
        totalCustomers: customersCount
        totalOrders: ordersCount
        totalRevenue: ordersAggregate {
            sumTotalAmount
        }
    }
    """

    try:
        response = requests.post(GRAPHQL_URL, json={"query": query}, timeout=10)
        response.raise_for_status()
        data = response.json().get("data", {})

        customers = data.get("totalCustomers", 0)
        orders = data.get("totalOrders", 0)
        revenue = data.get("totalRevenue", {}).get("sumTotalAmount", 0)

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"{timestamp} - Report: {customers} customers, {orders} orders, {revenue} revenue\n"

        with open("/tmp/crm_report_log.txt", "a") as f:
            f.write(log_message)

    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open("/tmp/crm_report_log.txt", "a") as f:
            f.write(f"{timestamp} - Error generating report: {e}\n")
