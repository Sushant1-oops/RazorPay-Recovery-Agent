# Autonomous Payment Failure Recovery Agent

An end-to-end autonomous agentic system designed to ingest, classify, score, and execute recovery strategies for failed payments via Razorpay webhooks.

## System Architecture

```text
┌────────────────────────┐
│  Razorpay Payment API  │
└───────────┬────────────┘
            │ webhook (payment.failed)
            ▼
┌────────────────────────┐      ┌────────────────────────┐
│   FastAPI Webhook      │◄────►│  LangGraph AI Engine   │
│   Ingest & Policies    │      │  (Groq LLM + Fallback) │
└───────────┬────────────┘      └────────────────────────┘
            │                               │
            ▼                               ▼
┌────────────────────────┐      ┌────────────────────────┐
│  PostgreSQL Database   │      │ Human-in-the-Loop      │
│  (Neon Cloud Server)   │      │ Review & Escalation    │
└───────────┬────────────┘      └────────────────────────┘
            │
            ▼
┌────────────────────────┐
│  React Ops Dashboard   │
│  (Vite, TanStack, CSS) │
└────────────────────────┘
```

## Core Components

1. **Backend (`Backend`)**:
   - **Agent Engine**: LangGraph state graph with deterministic policy checks and safety rails.
   - **Root Cause Classifier**: Dual-tier classification (Groq LLM + deterministic regex/code rules).
   - **Deterministic Scorer**: Multi-factor 0–100 probability engine (root cause, confidence, previous attempts, customer history).
   - **Safety & HITL**: Automatic escalation on high-risk, ambiguous, or multi-attempt failures.

2. **Frontend (`Frontend`)**:
   - **Operations Dashboard**: Live feed of recovery runs, metrics, and strategy performance.
   - **Interactive Recovery Drawer**: In-depth timeline of every agent thought, rule check, and execution.
   - **Human Review Actions**: Instant approval/rejection for escalated cases.

## Quick Start

### 1. Run Backend
```bash
cd Backend
# Activate virtualenv
..\.venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```

### 2. Run Frontend
```bash
cd Frontend
npm install
npm run dev
```
Dashboard will be live at `http://localhost:5173`.
