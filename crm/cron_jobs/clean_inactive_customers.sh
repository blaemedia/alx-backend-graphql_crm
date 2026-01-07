#!/bin/bash

# Path to your Django project
PROJECT_DIR="/mnt/d/ALX/ALxBank-endProdev/alx-backend-graphql_crm"

# Go to project directory
cd "$PROJECT_DIR" || exit 1

# Run Django shell command to delete inactive customers (no orders in the past year)
DELETED_COUNT=$(python3 manage.py shell -c "
from django.utils import timezone
from datetime import timedelta
from crm.models import Customer, Order

one_year_ago = timezone.now() - timedelta(days=365)
inactive_customers = Customer.objects.exclude(order__created_at__gte=one_year_ago)
deleted_count, _ = inactive_customers.delete()
print(deleted_count)
")

# Log the deletion with timestamp
echo \"\$(date '+%Y-%m-%d %H:%M:%S') - Deleted $DELETED_COUNT inactive customers\" >> /tmp/customer_cleanup_log.txt
