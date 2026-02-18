"""
MedAssist AI - Notification Service
Handles appointment confirmations, reminders via email/SMS (Twilio) and in-app
Falls back to in-app logging when external services are not configured
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

from app.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Multi-channel notification service.
    Supports: in-app logs, email (SMTP), SMS (Twilio), WhatsApp (Twilio)
    Gracefully degrades if external services not configured.
    """

    def __init__(self):
        self._twilio_client = None
        self._smtp_configured = False
        self._init_providers()

    def _init_providers(self):
        """Initialize available notification providers"""
        # Twilio SMS/WhatsApp
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            try:
                from twilio.rest import Client
                self._twilio_client = Client(
                    settings.TWILIO_ACCOUNT_SID,
                    settings.TWILIO_AUTH_TOKEN,
                )
                logger.info("Twilio SMS/WhatsApp notifications enabled")
            except Exception as e:
                logger.warning(f"Twilio initialization failed: {e}")

        # SMTP Email
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            self._smtp_configured = True
            logger.info("Email notifications enabled")

    # ─── Appointment Notifications ─────────────────
    
    async def send_appointment_confirmation(
        self,
        patient_name: str,
        patient_phone: str,
        patient_email: Optional[str],
        doctor_name: str,
        department: str,
        date_time: datetime,
        appointment_id: str,
    ):
        """Send appointment booking confirmation"""
        time_str = date_time.strftime("%A, %B %d, %Y at %I:%M %p")
        
        message = (
            f"✅ Appointment Confirmed!\n\n"
            f"Dear {patient_name},\n"
            f"Your appointment has been booked:\n\n"
            f"👨‍⚕️ Doctor: Dr. {doctor_name}\n"
            f"🏥 Department: {department}\n"
            f"📅 Date & Time: {time_str}\n"
            f"🔖 Ref: {appointment_id[:8].upper()}\n\n"
            f"Please arrive 15 minutes early.\n"
            f"To reschedule, contact us at {settings.EMERGENCY_PHONE}.\n\n"
            f"— MedAssist AI, City General Hospital"
        )

        await self._send_multi_channel(
            phone=patient_phone,
            email=patient_email,
            subject=f"Appointment Confirmed - {time_str}",
            message=message,
            notification_type="APPOINTMENT_CONFIRMATION",
        )

    async def send_appointment_reschedule(
        self,
        patient_name: str,
        patient_phone: str,
        patient_email: Optional[str],
        doctor_name: str,
        old_time: datetime,
        new_time: datetime,
        appointment_id: str,
    ):
        """Send appointment reschedule notification"""
        old_str = old_time.strftime("%b %d at %I:%M %p")
        new_str = new_time.strftime("%A, %B %d, %Y at %I:%M %p")

        message = (
            f"🔄 Appointment Rescheduled\n\n"
            f"Dear {patient_name},\n"
            f"Your appointment with Dr. {doctor_name} has been rescheduled:\n\n"
            f"❌ Old: {old_str}\n"
            f"✅ New: {new_str}\n"
            f"🔖 Ref: {appointment_id[:8].upper()}\n\n"
            f"Please arrive 15 minutes early.\n"
            f"— MedAssist AI, City General Hospital"
        )

        await self._send_multi_channel(
            phone=patient_phone,
            email=patient_email,
            subject=f"Appointment Rescheduled - {new_str}",
            message=message,
            notification_type="APPOINTMENT_RESCHEDULE",
        )

    async def send_appointment_cancellation(
        self,
        patient_name: str,
        patient_phone: str,
        patient_email: Optional[str],
        doctor_name: str,
        date_time: datetime,
        appointment_id: str,
    ):
        """Send appointment cancellation confirmation"""
        time_str = date_time.strftime("%b %d at %I:%M %p")

        message = (
            f"❌ Appointment Cancelled\n\n"
            f"Dear {patient_name},\n"
            f"Your appointment with Dr. {doctor_name} on {time_str} "
            f"has been cancelled.\n\n"
            f"🔖 Ref: {appointment_id[:8].upper()}\n\n"
            f"To rebook, visit our website or call {settings.EMERGENCY_PHONE}.\n"
            f"— MedAssist AI, City General Hospital"
        )

        await self._send_multi_channel(
            phone=patient_phone,
            email=patient_email,
            subject=f"Appointment Cancelled - Ref {appointment_id[:8].upper()}",
            message=message,
            notification_type="APPOINTMENT_CANCELLATION",
        )

    async def send_appointment_reminder(
        self,
        patient_name: str,
        patient_phone: str,
        patient_email: Optional[str],
        doctor_name: str,
        date_time: datetime,
    ):
        """Send appointment reminder (24h before)"""
        time_str = date_time.strftime("%I:%M %p")

        message = (
            f"⏰ Appointment Reminder\n\n"
            f"Dear {patient_name},\n"
            f"Reminder: Your appointment with Dr. {doctor_name} "
            f"is tomorrow at {time_str}.\n\n"
            f"📝 Please bring:\n"
            f"• Your ID and insurance card\n"
            f"• Previous medical records\n"
            f"• List of current medications\n\n"
            f"— MedAssist AI, City General Hospital"
        )

        await self._send_multi_channel(
            phone=patient_phone,
            email=patient_email,
            subject=f"Appointment Reminder - Tomorrow at {time_str}",
            message=message,
            notification_type="APPOINTMENT_REMINDER",
        )

    # ─── Emergency Notifications ───────────────────

    async def send_emergency_alert(
        self,
        staff_phone: str,
        patient_info: str,
        severity: str,
        department: str,
    ):
        """Send emergency alert to staff"""
        message = (
            f"🚨 EMERGENCY ALERT\n\n"
            f"Severity: {severity}\n"
            f"Department: {department}\n"
            f"Patient: {patient_info}\n\n"
            f"Respond immediately."
        )

        await self._send_sms(staff_phone, message)
        logger.warning(f"Emergency alert sent to {staff_phone}")

    # ─── Channel Implementations ───────────────────

    async def _send_multi_channel(
        self,
        phone: str,
        email: Optional[str],
        subject: str,
        message: str,
        notification_type: str,
    ):
        """Send notification via all available channels"""
        sent_via = []

        # SMS via Twilio
        if self._twilio_client and phone:
            try:
                await self._send_sms(phone, message)
                sent_via.append("SMS")
            except Exception as e:
                logger.error(f"SMS send failed: {e}")

        # WhatsApp via Twilio
        if self._twilio_client and settings.WHATSAPP_NUMBER and phone:
            try:
                await self._send_whatsapp(phone, message)
                sent_via.append("WhatsApp")
            except Exception as e:
                logger.error(f"WhatsApp send failed: {e}")

        # Email via SMTP
        if self._smtp_configured and email:
            try:
                await self._send_email(email, subject, message)
                sent_via.append("Email")
            except Exception as e:
                logger.error(f"Email send failed: {e}")

        # Always log in-app
        sent_via.append("InApp")
        logger.info(
            f"Notification [{notification_type}] sent via: {', '.join(sent_via)} "
            f"to phone={phone}, email={email}"
        )

    async def _send_sms(self, to_phone: str, message: str):
        """Send SMS via Twilio"""
        if not self._twilio_client:
            logger.debug(f"SMS (not configured): {message[:80]}...")
            return

        self._twilio_client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to_phone,
        )

    async def _send_whatsapp(self, to_phone: str, message: str):
        """Send WhatsApp message via Twilio"""
        if not self._twilio_client or not settings.WHATSAPP_NUMBER:
            return

        self._twilio_client.messages.create(
            body=message,
            from_=settings.WHATSAPP_NUMBER,
            to=f"whatsapp:{to_phone}",
        )

    async def _send_email(self, to_email: str, subject: str, body: str):
        """Send email via SMTP"""
        if not self._smtp_configured:
            logger.debug(f"Email (not configured): {subject}")
            return

        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)


# Global singleton
notification_service = NotificationService()
