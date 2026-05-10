"""
Celery tasks for the Notifications app.
Handles sending SMS via Twilio, email notifications, and reminders.
"""

import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger('bloodfy')


@shared_task(name='notifications.tasks.send_pending_request_reminders_task')
def send_pending_request_reminders_task():
    """
    Periodic task: Send reminder notifications for blood requests
    that have been pending for more than 1 hour without a match.
    Runs every hour via Celery Beat.
    """
    from requests_management.models import BloodRequest
    from notifications.models import AppNotification

    one_hour_ago = timezone.now() - timezone.timedelta(hours=1)

    pending_requests = BloodRequest.objects.filter(
        status='pending',
        requested_at__lte=one_hour_ago,
    ).select_related('recipient__user')

    reminder_count = 0

    for request in pending_requests:
        # Avoid duplicate reminders — check if one was sent recently
        recent_reminder = AppNotification.objects.filter(
            user=request.recipient.user,
            related_id=str(request.id),
            title__icontains='reminder',
            created_at__gte=one_hour_ago,
        ).exists()

        if not recent_reminder:
            AppNotification.objects.create(
                user=request.recipient.user,
                title="Blood Request Reminder",
                message=(
                    f"Your blood request for {request.blood_group} "
                    f"({request.units_required} units) is still pending. "
                    f"Our team is working on finding matching donors."
                ),
                notification_type='warning',
                related_id=str(request.id),
            )
            reminder_count += 1

    logger.info(
        "Pending request reminders task completed. %d reminder(s) sent.",
        reminder_count,
    )

    return {'reminders_sent': reminder_count}


@shared_task(name='notifications.tasks.send_sms_notification_task')
def send_sms_notification_task(notification_id):
    """
    Send an SMS notification via Twilio.
    Called asynchronously when a notification needs to be delivered.
    """
    from notifications.models import NotificationLog
    from notifications.sms_service import TwilioSMSService

    try:
        notification = NotificationLog.objects.get(id=notification_id)
    except NotificationLog.DoesNotExist:
        logger.error("Notification %s not found", notification_id)
        return {'status': 'error', 'message': 'Notification not found'}

    sms_service = TwilioSMSService()
    result = sms_service.send_sms(
        to_phone=notification.recipient_phone,
        message=notification.message_content,
    )

    if result['success']:
        notification.delivery_status = 'delivered'
        notification.external_id = result.get('sid', '')
        notification.sent_at = timezone.now()
        notification.save(update_fields=[
            'delivery_status', 'external_id', 'sent_at', 'updated_at'
        ])
        logger.info(
            "SMS delivered to %s (SID: %s)",
            notification.recipient_phone,
            result.get('sid'),
        )
    else:
        notification.delivery_status = 'failed'
        notification.delivery_error = result.get('error', 'Unknown error')
        notification.retry_count += 1
        notification.save(update_fields=[
            'delivery_status', 'delivery_error', 'retry_count', 'updated_at'
        ])
        logger.error(
            "SMS failed to %s: %s",
            notification.recipient_phone,
            result.get('error'),
        )

        # Retry if allowed
        if notification.can_retry():
            send_sms_notification_task.apply_async(
                args=[str(notification_id)],
                countdown=60 * (notification.retry_count + 1),  # Exponential backoff
            )

    return result
