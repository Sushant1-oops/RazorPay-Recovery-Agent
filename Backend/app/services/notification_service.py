"""Notification delivery service - mock provider by default, pluggable for real ones."""
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import Notification
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("notification_service")


class NotificationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def send_notification(
        self,
        recovery_id: int | None,
        channel: str,
        recipient: str,
        message: str,
        template: str | None = None,
        payment_url: str | None = None,
    ) -> Notification:
        """Send (or mock-send) a customer notification and persist a record of it."""
        notification = Notification(
            recovery_id=recovery_id,
            channel=channel,
            recipient=recipient,
            template=template,
            status="pending",
        )
        self.session.add(notification)
        await self.session.flush()

        try:
            provider_response = await self._dispatch(channel, recipient, message, payment_url=payment_url)
            notification.status = "sent"
            notification.provider_response = provider_response
            notification.sent_at = datetime.now(timezone.utc)
        except Exception as e:
            notification.status = "failed"
            notification.provider_response = str(e)
            logger.error("notification_send_failed", channel=channel, error=str(e))

        await self.session.flush()
        return notification

    async def _dispatch(self, channel: str, recipient: str, message: str, payment_url: str | None = None) -> str:
        """Send via the configured provider, falling back to a mock/log provider."""
        if settings.EMAIL_PROVIDER == "smtp" and channel in ("email", "smtp"):
            return await self._dispatch_smtp(recipient, message, payment_url=payment_url)

        if settings.EMAIL_PROVIDER == "mock" or channel == "mock":
            logger.info("notification_mock_sent", channel=channel, recipient=recipient, message=message, payment_url=payment_url)
            return "mock_provider_ok"

        # Plug a real provider (SendGrid/SES/Twilio/etc) in here.
        logger.warning("notification_provider_not_implemented", provider=settings.EMAIL_PROVIDER)
        return "provider_not_configured"

    async def _dispatch_smtp(self, recipient: str, message: str, payment_url: str | None = None) -> str:
        """Send real email via SMTP."""
        import asyncio
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        target_email = recipient.strip() if recipient else ""
        # Fallback to configured SMTP user if recipient is empty, placeholder, or Razorpay test dummy
        if not target_email or "@" not in target_email or target_email in ("void@razorpay.com", "customer@example.com"):
            target_email = settings.SMTP_USER or settings.EMAIL_FROM

        def _send():
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Payment Recovery Notification: Action Required for Your Order"
            from_addr = settings.EMAIL_FROM or settings.SMTP_USER
            msg["From"] = f"Recovery Agent <{from_addr}>"
            msg["To"] = target_email

            plain_body = message
            if payment_url:
                plain_body += f"\n\nClick the link below to complete your payment:\n{payment_url}"

            button_html = ""
            if payment_url:
                button_html = f"""
                <div style="text-align: center; margin: 30px 0 16px 0;">
                    <a href="{payment_url}" target="_blank" style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); color: #ffffff; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 16px; display: inline-block; box-shadow: 0 4px 10px rgba(79, 70, 229, 0.35);">
                        Complete Payment Now →
                    </a>
                </div>
                <p style="text-align: center; font-size: 12px; color: #64748b; margin-top: 8px;">
                    Or copy this payment link:<br/>
                    <a href="{payment_url}" style="color: #4f46e5; word-break: break-all;">{payment_url}</a>
                </p>
                """

            html_content = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 20px auto; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff; overflow: hidden; box-shadow: 0 4px 12px -2px rgba(0, 0, 0, 0.08);">
                <div style="background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); padding: 24px; color: #ffffff;">
                    <h2 style="margin: 0; font-size: 20px; font-weight: 600;">Autonomous Payment Recovery</h2>
                    <p style="margin: 4px 0 0 0; opacity: 0.9; font-size: 14px;">Payment Assistance Notification</p>
                </div>
                <div style="padding: 24px;">
                    <p style="color: #334155; font-size: 15px; line-height: 1.6; margin-top: 0;">
                        {message.replace(chr(10), '<br/>')}
                    </p>
                    {button_html}
                </div>
                <div style="background-color: #f8fafc; padding: 16px 24px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
                    This is an automated notification from the Autonomous Payment Recovery Agent.
                </div>
            </div>
            """

            text_part = MIMEText(plain_body, "plain", "utf-8")
            html_part = MIMEText(html_content, "html", "utf-8")
            msg.attach(text_part)
            msg.attach(html_part)

            host = settings.SMTP_HOST or "smtp.gmail.com"
            port = settings.SMTP_PORT or 587
            user = settings.SMTP_USER
            pwd = (settings.SMTP_PASSWORD or "").replace(" ", "")

            server = smtplib.SMTP(host, port, timeout=15)
            server.starttls()
            if user and pwd:
                server.login(user, pwd)
            server.sendmail(from_addr, [target_email], msg.as_string())
            server.quit()
            logger.info("smtp_email_sent", recipient=target_email, with_button=bool(payment_url))
            return f"smtp_sent_to_{target_email}"

        return await asyncio.to_thread(_send)
