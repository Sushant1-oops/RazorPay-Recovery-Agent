from pydantic import BaseModel


class RazorpayWebhookPayload(BaseModel):
    entity: str = "event"
    account_id: str | None = None
    event: str = ""
    contains: list[str] = []
    payload: dict = {}


class WebhookProcessingResult(BaseModel):
    event_id: str
    event_type: str
    status: str
    message: str