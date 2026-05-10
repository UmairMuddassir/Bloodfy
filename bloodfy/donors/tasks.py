"""
Celery tasks for the Donors app.
Handles automated donor reactivation after the 90-day cooldown period
and other scheduled donor management operations.
"""

import logging
from datetime import date, timedelta

from celery import shared_task
from django.db.models import Q

from utils.constants import DONATION_ELIGIBILITY_DAYS

logger = logging.getLogger('bloodfy')


@shared_task(name='donors.tasks.reactivate_eligible_donors_task')
def reactivate_eligible_donors_task():
    """
    Periodic task: Automatically reactivate donors whose 90-day
    cooldown period has expired.

    Runs daily at 6 AM via Celery Beat (configured in celery.py).
    Checks all inactive/ineligible donors and reactivates those
    whose last_donation_date is >= 90 days ago.
    """
    from donors.models import Donor

    today = date.today()
    cutoff_date = today - timedelta(days=DONATION_ELIGIBILITY_DAYS)

    # Find donors who are ineligible but whose cooldown has passed
    donors_to_reactivate = Donor.objects.filter(
        Q(is_eligible=False) | Q(availability_status=False),
        last_donation_date__lte=cutoff_date,
        is_active=True,
    )

    reactivated_count = 0

    for donor in donors_to_reactivate:
        was_ineligible = not donor.is_eligible
        was_unavailable = not donor.availability_status

        # Reactivate eligibility
        donor.is_eligible = True
        donor.availability_status = True
        donor.save(update_fields=['is_eligible', 'availability_status', 'updated_at'])

        reactivated_count += 1

        logger.info(
            "Donor %s (ID: %s) reactivated after 90-day cooldown. "
            "Last donation: %s. Eligibility: %s->True, Availability: %s->True",
            donor.user.get_full_name(),
            donor.id,
            donor.last_donation_date,
            not was_ineligible,
            not was_unavailable,
        )

        # Create in-app notification for the donor
        try:
            from notifications.models import AppNotification
            AppNotification.objects.create(
                user=donor.user,
                title="You're Eligible to Donate Again!",
                message=(
                    f"Your 90-day cooldown period has ended. "
                    f"You are now eligible to donate blood again. "
                    f"Thank you for being a lifesaver!"
                ),
                notification_type='info',
                related_id=str(donor.id),
            )
        except Exception as e:
            logger.error("Failed to create reactivation notification: %s", e)

    logger.info(
        "Donor reactivation task completed. %d donor(s) reactivated out of %d checked.",
        reactivated_count,
        donors_to_reactivate.count(),
    )

    return {
        'reactivated': reactivated_count,
        'date': str(today),
    }


@shared_task(name='donors.tasks.update_all_donor_eligibility_task')
def update_all_donor_eligibility_task():
    """
    Periodic task: Update eligibility status for all active donors.
    This is a safety-net task that ensures eligibility flags stay in sync
    with actual donation dates.
    """
    from donors.models import Donor

    today = date.today()
    donors = Donor.objects.filter(is_active=True)

    updated_count = 0

    for donor in donors:
        old_eligibility = donor.is_eligible
        donor.update_eligibility()

        if donor.is_eligible != old_eligibility:
            updated_count += 1
            logger.info(
                "Donor %s eligibility updated: %s -> %s",
                donor.user.get_full_name(),
                old_eligibility,
                donor.is_eligible,
            )

    logger.info(
        "Eligibility update task completed. %d donor(s) updated.",
        updated_count,
    )

    return {
        'updated': updated_count,
        'total_checked': donors.count(),
        'date': str(today),
    }
