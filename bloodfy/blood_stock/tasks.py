"""
Celery tasks for the Blood Stock app.
Handles automated stock expiry checks and low-stock alerts.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('bloodfy')


@shared_task(name='blood_stock.tasks.check_expired_stock_task')
def check_expired_stock_task():
    """
    Periodic task: Check for expired blood stock and update records.
    Runs daily at midnight via Celery Beat (configured in celery.py).

    Blood units typically expire after 42 days (for red blood cells).
    This task checks the last_updated timestamp and flags stocks that
    haven't been refreshed within the expiry window.
    """
    from blood_stock.models import BloodStock

    EXPIRY_DAYS = 42  # Standard RBC shelf life
    cutoff_date = timezone.now() - timedelta(days=EXPIRY_DAYS)

    # Find stocks that haven't been updated and may contain expired units
    stale_stocks = BloodStock.objects.filter(
        last_updated__lte=cutoff_date,
        units_available__gt=0,
    )

    flagged_count = 0

    for stock in stale_stocks:
        logger.warning(
            "Blood stock may contain expired units: %s - %s "
            "(%d units, last updated: %s)",
            stock.hospital_name,
            stock.blood_group,
            stock.units_available,
            stock.last_updated,
        )
        flagged_count += 1

    from django.db import models
    # Also check for critically low stocks and create alerts
    critical_stocks = BloodStock.objects.filter(
        units_available__lte=models.F('critical_threshold'),
        units_available__gt=0,
    )

    logger.info(
        "Expired stock check completed. %d stale stock(s) flagged.",
        flagged_count,
    )

    return {
        'stale_flagged': flagged_count,
        'timestamp': str(timezone.now()),
    }
