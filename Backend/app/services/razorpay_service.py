"""Razorpay API integration — webhook verification and order/payment lookups."""
import hashlib
import hmac
import razorpay
from app.core.config import settings
from app.core.exceptions import RazorpayAPIError
from app.core.logging import get_logger

logger = get_logger("razorpay_service")


class RazorpayService:
    def __init__(self):
        self._client = None
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
            self._client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    @property
    def configured(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> "razorpay.Client":
        if self._client is None:
            raise RazorpayAPIError("Razorpay credentials are not configured (set RAZORPAY_KEY_ID/SECRET).")
        return self._client

    def verify_webhook_signature(self, raw_body: str, signature: str) -> bool:
        if not signature or not settings.RAZORPAY_WEBHOOK_SECRET:
            logger.error("webhook_secret_or_signature_missing")
            return False

        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
            raw_body.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    def create_order(self, amount: int, currency: str = "INR", receipt: str | None = None) -> dict:
        try:
            return self.client.order.create({
                "amount": amount,
                "currency": currency,
                "receipt": receipt,
                "payment_capture": 1,
            })
        except Exception as e:
            logger.error("razorpay_create_order_failed", error=str(e))
            raise RazorpayAPIError(str(e)) from e

    def fetch_payment(self, razorpay_payment_id: str) -> dict:
        try:
            return self.client.payment.fetch(razorpay_payment_id)
        except Exception as e:
            logger.error("razorpay_fetch_payment_failed", error=str(e))
            raise RazorpayAPIError(str(e)) from e

    def check_payment_status_safely(self, razorpay_payment_id: str) -> dict:
        if not razorpay_payment_id:
            return {"status": "unknown", "safe_to_retry": False}
        if not self.configured:
            return {"status": "unknown", "safe_to_retry": False, "note": "Razorpay API keys not set"}
        try:
            payment = self.fetch_payment(razorpay_payment_id)
        except RazorpayAPIError as e:
            return {"status": "unknown", "safe_to_retry": False, "error": str(e)}
        status = payment.get("status", "unknown")
        return {"status": status, "safe_to_retry": status in ("failed", "created")}

    def create_payment_link(
        self,
        amount: int,
        currency: str = "INR",
        description: str = "Payment Recovery Link",
        customer_name: str | None = None,
        customer_email: str | None = None,
        customer_phone: str | None = None,
    ) -> dict:
        if not self.configured or amount <= 0:
            return {}
        try:
            payload = {
                "amount": amount,
                "currency": currency,
                "description": description,
                "notify": {"sms": False, "email": False},
                "reminder_enable": False,
            }
            cust = {}
            if customer_name:
                cust["name"] = customer_name
            if customer_email:
                cust["email"] = customer_email
            if customer_phone:
                cust["contact"] = customer_phone
            if cust:
                payload["customer"] = cust

            return self.client.payment_link.create(payload)
        except Exception as e:
            logger.error("razorpay_create_payment_link_failed", error=str(e))
            return {}
