from fastapi import HTTPException, status


class WebhookSignatureError(HTTPException):
    def __init__(self, detail: str = "Invalid webhook signature"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class DuplicateEventError(HTTPException):
    def __init__(self, detail: str = "Duplicate event"):
        super().__init__(status_code=status.HTTP_200_OK, detail=detail)


class RecoveryExhaustedError(Exception):
    pass


class PolicyViolationError(Exception):
    def __init__(self, action: str, reason: str):
        self.action = action
        self.reason = reason
        super().__init__(f"Policy violation: {action} - {reason}")


class PaymentSafetyError(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Payment safety violation: {reason}")


class LLMFallbackError(Exception):
    def __init__(self, original_error: Exception):
        self.original_error = original_error
        super().__init__(f"LLM failed, falling back to deterministic rules: {original_error}")


class RazorpayAPIError(Exception):
    def __init__(self, detail: str):
        super().__init__(detail)