"""
SMS Service - Twilio integration for sending SMS notifications.
Provides both synchronous and asynchronous SMS delivery.
"""

import logging
from django.conf import settings

logger = logging.getLogger('bloodfy')


class TwilioSMSService:
    """
    SMS service using Twilio API.
    Handles sending SMS notifications to donors and recipients.
    Falls back to logging if Twilio is not configured.
    """

    def __init__(self):
        self.account_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
        self.auth_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
        self.from_number = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
        self.client = None

        if self.account_sid and self.auth_token and self.account_sid != 'your_twilio_account_sid':
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                logger.info("Twilio SMS service initialized successfully")
            except ImportError:
                logger.warning("Twilio package not installed. SMS will be logged only.")
            except Exception as e:
                logger.error("Failed to initialize Twilio client: %s", e)
        else:
            logger.info("Twilio not configured. SMS notifications will be logged only.")

    @property
    def is_configured(self):
        """Check if Twilio is properly configured."""
        return self.client is not None

    def send_sms(self, to_phone, message):
        """
        Send an SMS message via Twilio API.

        Args:
            to_phone: Recipient phone number (Pakistani format: +923XXXXXXXXX)
            message: SMS message content

        Returns:
            dict: {'success': bool, 'sid': str, 'error': str}
        """
        # Format phone number for Twilio (Pakistani numbers)
        formatted_phone = self._format_phone_number(to_phone)

        if not formatted_phone:
            return {
                'success': False,
                'error': f'Invalid phone number format: {to_phone}',
            }

        if not self.is_configured:
            # Log-only mode when Twilio is not configured
            logger.info(
                "[SMS LOG] To: %s | Message: %s",
                formatted_phone,
                message[:100],
            )
            return {
                'success': True,
                'sid': f'LOG_{formatted_phone}',
                'mode': 'log_only',
                'message': 'SMS logged (Twilio not configured)',
            }

        try:
            # Send SMS via Twilio
            twilio_message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=formatted_phone,
            )

            logger.info(
                "SMS sent successfully. SID: %s, To: %s, Status: %s",
                twilio_message.sid,
                formatted_phone,
                twilio_message.status,
            )

            return {
                'success': True,
                'sid': twilio_message.sid,
                'status': twilio_message.status,
            }

        except Exception as e:
            logger.error(
                "Twilio SMS failed. To: %s, Error: %s",
                formatted_phone,
                str(e),
            )
            return {
                'success': False,
                'error': str(e),
            }

    def send_emergency_alert(self, donor, blood_request):
        """
        Send an emergency blood request alert to a donor.

        Args:
            donor: Donor model instance
            blood_request: BloodRequest model instance

        Returns:
            dict: SMS delivery result
        """
        message = (
            f"URGENT - Bloodfy Emergency Alert!\n"
            f"Blood Type Needed: {blood_request.blood_group}\n"
            f"Units Required: {blood_request.units_required}\n"
            f"Hospital: {blood_request.hospital_name}, {blood_request.hospital_city}\n"
            f"Please respond ASAP if you can donate.\n"
            f"Reply YES to confirm availability."
        )

        phone = donor.user.phone_number
        return self.send_sms(phone, message)

    def send_donor_approval_sms(self, donor):
        """
        Send SMS notification when a donor registration is approved.
        """
        message = (
            f"Congratulations {donor.user.get_full_name()}!\n"
            f"Your Bloodfy donor registration has been approved.\n"
            f"Blood Group: {donor.blood_group}\n"
            f"You are now eligible to receive donation requests.\n"
            f"Thank you for being a lifesaver!"
        )

        phone = donor.user.phone_number
        return self.send_sms(phone, message)

    def send_reactivation_sms(self, donor):
        """
        Send SMS notification when a donor is reactivated after 90-day cooldown.
        """
        message = (
            f"Hello {donor.user.get_full_name()}!\n"
            f"Your 90-day cooldown period is over.\n"
            f"You are now eligible to donate blood again on Bloodfy.\n"
            f"Thank you for your continued support!"
        )

        phone = donor.user.phone_number
        return self.send_sms(phone, message)

    def _format_phone_number(self, phone):
        """
        Format phone number to international format for Twilio.
        Handles Pakistani phone numbers (03XX → +923XX).
        """
        if not phone:
            return None

        phone = phone.strip().replace(' ', '').replace('-', '')

        # Already in international format
        if phone.startswith('+92'):
            return phone

        # Pakistani format (03XXXXXXXXX)
        if phone.startswith('03') and len(phone) == 11:
            return '+92' + phone[1:]

        # Pakistani format without leading zero
        if phone.startswith('3') and len(phone) == 10:
            return '+92' + phone

        # If it starts with +, assume it's already international
        if phone.startswith('+'):
            return phone

        logger.warning("Could not format phone number: %s", phone)
        return None
