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
            provider_response = await self._dispatch(channel, recipient, message)
            notification.status = "sent"
            notification.provider_response = provider_response
            notification.sent_at = datetime.now(timezone.utc)
        except Exception as e:
            notification.status = "failed"
            notification.provider_response = str(e)
            logger.error("notification_send_failed", channel=channel, error=str(e))

        await self.session.flush()
        return notification

    async def _dispatch(self, channel: str, recipient: str, message: str) -> str:
        """Send via the configured provider, falling back to a mock/log provider."""
        if settings.EMAIL_PROVIDER == "mock" or channel == "mock":
            logger.info("notification_mock_sent", channel=channel, recipient=recipient, message=message)
            return "mock_provider_ok"

        # Plug a real provider (SendGrid/SES/Twilio/etc) in here.
        logger.warning("notification_provider_not_implemented", provider=settings.EMAIL_PROVIDER)
        return "provider_not_configured"
