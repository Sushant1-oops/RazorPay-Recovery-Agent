from fastapi import APIRouter, Request, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.exceptions import WebhookSignatureError, DuplicateEventError
from app.services.webhook_service import WebhookService
from app.core.logging import get_logger

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])
logger = get_logger("api.webhooks")


@router.post("/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive and process Razorpay webhooks.

    This endpoint:
    1. Receives raw request body
    2. Verifies webhook signature
    3. Checks idempotency
    4. Stores the event
    5. Returns 200 quickly
    6. Pushes processing to background worker
    """
    raw_body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if not signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing webhook signature")

    try:
        svc = WebhookService(db)
        result = await svc.ingest_webhook(raw_body.decode("utf-8"), signature)
        return result
    except WebhookSignatureError:
        raise
    except DuplicateEventError:
        return {"status": "duplicate", "message": "Event already processed"}
    except Exception as e:
        logger.error("webhook_processing_error", error=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal error")