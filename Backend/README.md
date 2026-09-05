# Autonomous Payment Failure Recovery Agent — Backend API

An autonomous agentic system powered by FastAPI, LangGraph, and Groq to diagnose, score, and recover failed payments via Razorpay webhooks.

## Architecture

```text
Razorpay Webhook (payment.failed)
        │
        ▼
   Ingest Event (Payment & Customer Context)
        │
        ▼
  Analyze Failure (Groq LLM + Deterministic Fallback)
        │
        ▼
Assess Recoverability (Scoring Engine: 0-100)
        │
        ▼
 Decide Strategy (Policy Engine & Safety Guardrails)
        │
 ┌──────┴─────────────────────────┐
 │                                │
 ▼                                ▼
Execute Action            Human-in-the-Loop Review
(Smart Retry, Alternative,   (Ambiguous or Low Score
 Customer Notification)       Recoveries: Escalated)
        │                                │
        ▼                                ▼
 Evaluate Result ──► Adapt Strategy ──► Finalize
```

## Tech Stack
- **Framework**: FastAPI, Pydantic v2
- **Agent Orchestration**: LangGraph, LangChain Groq
- **Database**: PostgreSQL (Neon Serverless) via SQLAlchemy 2.0 Async + asyncpg
- **Payments Gateway**: Razorpay Webhook Integration & HMAC-SHA256 signature verification

## API Endpoints

### Webhooks
- `POST /api/v1/webhooks/razorpay`: Ingest live Razorpay webhook events with signature verification.

### Recovery Management
- `GET /api/v1/recoveries`: List all recovery records with pagination, status filters, and diagnostics.
- `GET /api/v1/recoveries/{id}`: Detailed recovery session with full timeline of agent actions and decisions.
- `POST /api/v1/recoveries/{id}/pause`: Pause an active recovery workflow.
- `POST /api/v1/recoveries/{id}/resume`: Resume a paused recovery.
- `POST /api/v1/recoveries/{id}/review`: Submit Human-in-the-Loop decision (`approve_retry`, `reject`, `resolve`).

### Analytics & Reporting
- `GET /api/v1/analytics/overview`: High-level metrics (recovery rate, recovered revenue, success counts).
- `GET /api/v1/analytics/recovery-rate`: Detailed recovery rate breakdown.
- `GET /api/v1/analytics/failure-breakdown`: Failure distribution categorized by root causes.
- `GET /api/v1/analytics/recovery-strategies`: Performance and success rates of executed recovery strategies.

## Getting Started

### Prerequisites
- Python 3.11+
- Virtualenv

### Setup
```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
# or source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run the API server
uvicorn app.main:app --reload --port 8000
```
