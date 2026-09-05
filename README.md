<div align="center"> 

# 🔄 Autonomous Payment Recovery Agent

### An agentic AI system that recovers failed Razorpay payments — autonomously, safely, and with a human always in the loop.

**Built with:** Python, FastAPI, LangGraph, Groq, PostgreSQL, React, and Razorpay.

*Built for the Razorpay Buildathon*

</div> 

Every day, a meaningful share of checkout attempts on Razorpay simply fail — a bank hiccup, an expired OTP, a UPI app that never opened. Left alone, most of that revenue quietly disappears. This project replaces that silence with an autonomous agent built on **LangGraph**: a system that watches every `payment.failed` webhook, diagnoses *why* it failed, calculates the odds of saving it, chooses the safest way to try, and either fixes it automatically or calmly hands it to a human — with its full reasoning attached — the moment it isn't safe to act alone.

**At a glance:**

| Metric | Value |
| :--- | :--- |
| Checkout attempts that fail industry-wide | 15–25% |
| Failed payments this agent targets for recovery | up to 35–50% |
| Recovery playbooks fully automated | 85%+ |
| Max automated retries per payment | 3 (hard cap) |
| Recovery decision window | 24 hours |

---

## Table of Contents

- [The Problem](#the-problem)
- [The Idea](#the-idea)
- [What Makes This Different](#what-makes-this-different)
- [Architecture Overview](#architecture-overview)
- [Service Layer](#service-layer)
- [Database Design](#database-design)
- [The Agent Brain](#the-agent-brain)
- [Recoverability Scoring Engine](#recoverability-scoring-engine)
- [Recovery Playbooks](#recovery-playbooks)
- [Safety and Policy Guardrails](#safety-and-policy-guardrails)
- [Recovery Lifecycle](#recovery-lifecycle)
- [End to End Flow](#end-to-end-flow)
- [Real World Scenarios](#real-world-scenarios)
- [Human in the Loop Review](#human-in-the-loop-review)
- [Command Dashboard](#command-dashboard)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Business Impact](#business-impact)
- [Roadmap](#roadmap)

---

## The Problem

### The silent revenue leak

In ecosystems like Razorpay, **15–25% of checkout attempts fail** — not because customers changed their mind, but because of transient network drops, bank downtime, insufficient funds, an expired OTP, or plain user error. Left alone, merchants tend to handle this in one of three broken ways:

- **Passive loss** — waiting for the customer to try again on their own, which results in **70%+ permanent drop-off**.
- **Blind automated retries** — hammering the gateway with no judgment, which trips anti-fraud blocks, locks cards, or risks duplicate debits.
- **No visibility** — no way to distinguish a *soft* failure (a bank timeout that clears in seconds) from a *hard* one (a stolen or fraud-flagged card) — so every failure gets treated the same, badly.

---

## The Idea

Whenever a `payment.failed` event arrives, the agent runs a six-step pipeline:

1. **Contextual Ingestion** — pulls payment metadata, gateway error codes, and the customer's full purchase history the moment a payment fails.
2. **Dual-Layer Root Cause Classification** — a fast LLM (Groq) diagnoses the failure, backed by a deterministic rule-based classifier that keeps working even if the LLM doesn't.
3. **Deterministic Recoverability Scoring** — a transparent 0–100 formula (not a black box) estimates the odds this specific payment can be saved.
4. **Policy-Enforced Decision Making** — the safest playbook is chosen: smart retry, alternative payment link, customer notification, or immediate escalation.
5. **Human-in-the-Loop (HITL) Guardrail** — ambiguous or high-risk cases pause automatically and wait for a human operator, with full reasoning attached.
6. **Real-Time Command Dashboard** — merchants and finance teams watch recovery rate, recovered revenue, and every agent decision live.

---

## What Makes This Different

- **It explains itself.** Every diagnosis carries a confidence score and a plain-language rationale — never just a black-box verdict.
- **It never guesses blind.** If the LLM is slow, disabled, or offline, a deterministic keyword/regex classifier steps in instantly, so diagnosis never stalls.
- **Safety is a separate vote, not a suggestion.** A rule-based Policy Engine can veto any action the agent proposes — attempt caps, fraud flags, and cooling-off windows are hard-coded, not prompted.
- **Humans keep the final say.** Anything ambiguous, high-risk, or out of automated bounds gets escalated with full context — never silently retried.
- **Nothing is invisible.** Every diagnosis, score, policy check, and action is written to an append-only audit log with timestamps.

---

## Architecture Overview

At the highest level, a failed payment enters through a cryptographically verified webhook, gets handed to an autonomous LangGraph agent, and comes out the other side either **recovered automatically** or **escalated to a human** — with everything in between written to Postgres and streamed live to the dashboard.

```text
┌─────────────────────────┐
│     Razorpay Gateway    │
└────────────┬────────────┘
             │ Webhook: payment.failed (HMAC-SHA256 verified)
             ▼
┌────────────────────────────────────────────────────────┐
│                      FastAPI Backend                   │
│                                                        │
│  ┌──────────────────┐          ┌────────────────────┐  │
│  │ Ingest & History │          │ LangGraph Workflow │  │
│  │ Aggregation      │─────────►│ State Engine       │  │
│  └──────────────────┘          └─────────┬──────────┘  │
│                                          │             │
│            ┌─────────────────────────────┴──────┐      │
│            ▼                                    ▼      │
│    ┌───────────────┐                    ┌────────────┐ │
│    │ Automated     │                    │ Human      │ │
│    │ Execution     │                    │ Review     │ │
│    │ (Retry / SMS) │                    │ Escalation │ │
│    └───────────────┘                    └────────────┘ │
└────────────┬────────────────────────────────────┬──────┘
             │                                    │
             ▼                                    ▼
┌─────────────────────────┐              ┌───────────────────────┐
│  PostgreSQL (Neon Cloud)│◄────────────►│ React Command Center │
│  (ACID Audit Trails)    │              │ (Live Agent Telemetry)│
└─────────────────────────┘              └───────────────────────┘
```

---

## Service Layer

The backend is organized as seven focused services, each owning one slice of domain logic. `RecoveryService` sits at the center, orchestrating everything else.

| Service | File | Responsibility |
| :--- | :--- | :--- |
| `WebhookService` | `services/webhook_service.py` | HMAC-SHA256 signature verification for inbound webhooks |
| `PaymentService` | `services/payment_service.py` | Ingests payloads, upserts payments, matches order-level retries, closes recoveries on capture |
| `RecoveryService` | `services/recovery_service.py` | Orchestrates the recovery lifecycle, launches the LangGraph agent, enforces HITL decisions |
| `CustomerService` | `services/customer_service.py` | Customer profile management and historical reputation scoring |
| `RazorpayService` | `services/razorpay_service.py` | Direct Razorpay API integration — fetch payment state, create payment links |
| `NotificationService` | `services/notification_service.py` | Omnichannel customer communication (email, SMS, WhatsApp) |
| `AnalyticsService` | `services/analytics_service.py` | Real-time KPI computation for the dashboard |

*All paths are relative to `Backend/app/`.*

---

## Database Design

The project uses **PostgreSQL 16** with **SQLAlchemy 2.0 Async** and **asyncpg**.

```text
CUSTOMERS ────< PAYMENTS ────< PAYMENT_EVENTS
                  │
                  ├───< RECOVERIES ────< RECOVERY_ACTIONS
                  │        │
                  │        ├───< NOTIFICATIONS
                  │        └───< AUDIT_LOGS >──── USERS (HITL)
```

The core tables are:
- `customers` — customer identity, contact info, and lifetime purchase history
- `payments` — payment details, amounts, failure codes, and attempt counters
- `payment_events` — immutable raw webhook event audit history
- `recoveries` — master recovery record, current status, root cause, confidence, and strategy
- `recovery_actions` — individual action executions (retries, payment links, notifications)
- `notifications` — customer notifications and dispatch status
- `audit_logs` — complete operational and compliance trace of agent decisions
- `users` — merchant and operator accounts for dashboard access

---

## The Agent Brain

The recovery engine isn't a rigid decision tree — it's a **stateful, directed cyclic graph** built with LangGraph, where nine specialized nodes pass a single `RecoveryState` object between them, each reading and writing to it.

```text
               ┌──────────────────────┐
               │     ingest_event     │
               └──────────┬───────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │    analyze_failure   │◄─── (Groq LLM / Deterministic Classifier)
               └──────────┬───────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │ assess_recoverability│◄─── (0-100 Scoring Engine)
               └──────────┬───────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │    decide_strategy   │
               └──────────┬───────────┘
                          │
                          ▼
               ┌──────────────────────┐
        ┌─────►│     policy_check     │
        │      └──────────┬───────────┘
        │                 │
        │         ┌───────┴────────────────────────┐
        │         │ Policy Passed                  │ Blocked / Final
        │         ▼                                ▼
        │  ┌───────────────┐             ┌───────────────────┐
        │  │ execute_action│             │ finalize_recovery │──► [END]
        │  └──────┬────────┘             └───────────────────┘
        │         │
        │         ▼
        │  ┌───────────────┐
        │  │evaluate_result│
        │  └──────┬────────┘
        │         │
        │         ├────────────────────────────────┐
        │         │ Needs Adaptation (Retry Failed)│ Successful or Terminal
        │         ▼                                ▼
        │  ┌───────────────┐             ┌───────────────────┐
        └──│ adapt_strategy│             │ finalize_recovery │──► [END]
           └───────────────┘             └───────────────────┘
```

| # | Node | File | Role |
| :- | :--- | :--- | :--- |
| 1 | `ingest_event` | `agent/nodes/ingest_event.py` | Fetches the payment record, customer history, and recent payment events; hydrates state |
| 2 | `analyze_failure` | `agent/nodes/analyze_failure.py` | Diagnoses root cause via Groq LLM, falling back to a deterministic classifier |
| 3 | `assess_recoverability` | `agent/nodes/assess_recoverability.py` | Runs the 5-factor scoring formula and categorizes the result |
| 4 | `decide_strategy` | `agent/nodes/decide_strategy.py` | Maps the diagnosis and score to one of seven playbooks |
| 5 | `policy_check` | `agent/nodes/policy_check.py` | Evaluates the action against `RecoveryPolicy` — attempt caps, risk flags, cooling-off, duplicates |
| 6 | `execute_action` | `agent/nodes/execute_action.py` | Executes the concrete action (retry, notify, alternative link, status check) |
| 7 | `evaluate_result` | `agent/nodes/evaluate_result.py` | Checks whether the payment was captured or needs another cycle |
| 8 | `adapt_strategy` | `agent/nodes/adapt_strategy.py` | Switches playbooks (e.g. retry → alternative link) and loops back into `policy_check` |
| 9 | `finalize_recovery` | `agent/nodes/finalize_recovery.py` | Commits the final status, timestamps, and audit log, then ends the graph |

---

## Recoverability Scoring Engine

Instead of asking an LLM to guess a probability, the agent computes one — deterministically, so the same inputs always produce the same score, and every score can be explained line by line.

```text
Score = Base (50) + Cause Weight + (Confidence × 10) − Attempt Penalty + Customer Loyalty Bonus
```

| Root Cause | Weight |
| :--- | :--- |
| Temporary bank error | +35 |
| Network timeout | +30 |
| UPI failure | +25 |
| Insufficient funds | +15 |
| Bank decline | +5 |
| Invalid payment details | −20 |
| Suspected fraud / risk | −30 (hard stop) |

- **Diminishing returns penalty:** `min(attempts × 15, 45)` — repeated failures pull the score down fast, so the agent doesn't loop forever.
- **Customer loyalty bonus:** returning customers with a strong payment history get a score boost.
- **Categories:** High (≥ 66) · Medium (33–65) · Low (< 33) — a Low score auto-routes to the `low_recoverability` playbook and flags the case for human review.

---

## Recovery Playbooks

Seven playbooks translate a diagnosis into a concrete, safe action plan (`Backend/app/recovery/strategies.py`):

| Playbook | Applicable Causes | Execution |
| :--- | :--- | :--- |
| `temporary_failure` | temporary_bank_error, server_error, gateway_error | Exponential backoff (30–60s) → automated retry → switches to `notify_alternative` after 2 failed retries |
| `network_timeout` | network_timeout, timed_out, gateway_timeout | Verifies funds weren't deducted, then triggers a clean gateway retry |
| `upi_failure` | upi_failure, vpa_not_found, collect_request_expired | Deep-link SMS/WhatsApp to reopen the UPI app or enter a new VPA |
| `notify_retry` | insufficient_funds, authentication_failure, otp_expired | Friendly reminder notification + session-resumption link with cart preserved |
| `notify_alternative` | bank_decline, card_failure, invalid_payment_details | Blocks same-card retries; generates an alternative payment link (Netbanking/UPI/EMI) |
| `low_recoverability` | Score < 33, repeated or ambiguous failures | Sends alternatives, then escalates to human review |
| `escalate` | suspected_risk, fraud, attempt_count ≥ 3 | Immediately freezes automation and alerts operations |

---

## Safety and Policy Guardrails

Every action the agent wants to take — before a rupee moves or a message is sent — passes through a separate, deterministic **Policy Engine** (`Backend/app/recovery/policy.py`). The LLM proposes; the policy engine disposes.

1. **Max Attempt Cap** — hard limit of 3 retries per payment. Beyond that, automatic escalation.
2. **Unrecoverable / High-Risk Block** — fraud, blocked, or stolen-card flags get an immediate human escalation, no automated retry, ever.
3. **Duplicate Charge Prevention** — if Razorpay already shows the payment as captured or authorized, retrying is forbidden; it's marked recovered instantly instead.
4. **Cooling-Off Interval** — a minimum gap between retries with exponential backoff (30s / 60s / 120s), giving an overloaded bank switch room to recover.
5. **Terminal State Immutability** — `recovered`, `exhausted`, `unsafe_to_retry`, and `cancelled` can never be silently reopened by the agent.
6. **Max Lifecycle Window** — 24 hours. Anything still unresolved auto-transitions to `exhausted` so the books stay clean.
7. **Operator Override** — a human reviewer approving a retry can override the automated constraints, with full audit logging.

---

## Recovery Lifecycle

The recovery workflow moves through governed finite states:

```text
[pending] ──► [analyzing] ──► [executing] ──► [observing] ──► [recovered]
                   │               │               │
                   ▼               ▼               ▼
              [escalated]     [escalated]     [adapting] ──► [executing]
                   │                               │
                   ├──► [Approve Retry] ──► [pending]
                   ├──► [Reject]        ──► [exhausted]
                   └──► [Resolve]       ──► [recovered]
```

If the payment is risky, unclear, or reaches the retry limit, the workflow moves to **escalated** for human review.

---

## End to End Flow

1. Customer attempts checkout on Razorpay.
2. Razorpay reports a failed payment through an HMAC-verified webhook.
3. The backend verifies and stores the payment information.
4. The LangGraph agent analyzes the failure (Groq LLM + rule fallback).
5. A deterministic recoverability score (0–100) is calculated.
6. The policy engine checks whether an action is safe.
7. The agent retries, sends an alternative payment option, or escalates to a human.
8. The result is stored and streamed live to the command dashboard.

---

## Real World Scenarios

### Scenario A — Transient UPI Network Drop

| Step | Detail |
| :--- | :--- |
| Event | Customer attempts ₹1,499 via UPI; Razorpay reports a network timeout |
| Diagnosis | Groq classifies `network_timeout` at 90% confidence |
| Score | 80.0 / 100 — High recoverability |
| Policy check | Attempt 1 of 3 — allowed |
| Execution | 60s backoff, then a smart retry notification to the customer's UPI app |
| Outcome | ✅ Customer confirms; `payment.captured` received; **recovered in under 90 seconds** |

### Scenario B — Hard Bank Decline

| Step | Detail |
| :--- | :--- |
| Event | ₹12,500 card payment declined — `issuer_decline: do_not_honor` |
| Diagnosis | Root cause `bank_decline` at 95% confidence |
| Score | 27.5 / 100 — Low recoverability |
| Policy check | Automated retry blocked — would risk a card lockout |
| Execution | Alternative Netbanking/UPI payment link sent to the customer |
| Outcome | 🔺 Escalated for human review — operator can reach out directly |

---

## Human in the Loop Review

**Escalation triggers:**

- Recoverability score below 33/100
- An ambiguous or unrecognized failure code
- Maximum automated attempts reached (3/3)
- A fraud or risk flag on the transaction

Once escalated, an operator sees the agent's full diagnosis, its confidence, the customer's payment history, and a timeline of every action already tried — then chooses one of three outcomes:

| Action | Effect |
| :--- | :--- |
| **Approve Retry** | Overrides automated constraints and re-enqueues a controlled retry cycle |
| **Reject** | Closes the case as `exhausted` |
| **Resolve** | Manually marks the payment resolved (e.g. settled offline) |

Every decision — who made it, when, and why — is written to the audit log.

---

## Command Dashboard

A React 18 command center gives merchants and finance teams live visibility into everything the agent is doing:

- **KPI cards** — total payments, failed pool, recovered count, recovery rate (%), and total recovered revenue (₹)
- **Failure root-cause chart** — an interactive Recharts breakdown of *why* payments are failing
- **Strategy performance matrix** — execution volume and success rate for every playbook
- **Live agent feed** — a running stream of every recovery in flight: payment ID, diagnosed cause, a color-coded confidence bar, a status badge (`Observing` / `Executing` / `Recovered` / `Escalated` / `Exhausted`), attempt counter (`x / 3`), and last-updated time

---

## Tech Stack

**Backend**

| Component | Technology |
| :--- | :--- |
| Language / Runtime | Python 3.11+ |
| Web Framework | FastAPI |
| Validation | Pydantic v2 |
| ORM / DB Client | SQLAlchemy 2.0 Async + asyncpg |
| Auth | JWT (HS256) for operators, Passlib PBKDF2-SHA256 for password hashing |
| Webhook Security | Razorpay HMAC-SHA256 signature verification |

**Agentic AI**

| Component | Technology |
| :--- | :--- |
| Agent Framework | LangGraph (directed cyclic graph orchestration) |
| Primary LLM | Groq Cloud — `qwen/qwen3.8-27b` via `langchain-groq` |
| Structured Outputs | Pydantic-enforced schemas |
| Fallback Engine | Deterministic rule-based classifier (error codes, keywords, method heuristics) |

**Database**

| Component | Technology |
| :--- | :--- |
| Database | PostgreSQL 16 on Neon Serverless Cloud |
| Connection | Pooled asyncpg, SSL verified |
| Core Tables | payments, recoveries, recovery_actions, audit_logs, customers, payment_events, notifications |

**Frontend**

| Component | Technology |
| :--- | :--- |
| Framework / Bundler | React 18 + Vite |
| Routing | TanStack Router |
| Data Fetching | TanStack Query v5 |
| Styling | Tailwind CSS v4 + shadcn/ui |
| Icons | Lucide React |
| Charts | Recharts |

**Integrations and Tooling**

| Component | Technology |
| :--- | :--- |
| Payment Gateway | Razorpay Test & Live Webhooks API |
| Local Tunneling | ngrok |
| Containerization | Docker (Python slim image) |

---

## Project Structure

```text
RazorPay-Recovery-Agent/
├── README.md
├── .gitignore
├── Backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── scripts/
│   ├── tests/
│   └── app/
│       ├── main.py
│       ├── core/
│       ├── models/
│       ├── schemas/
│       ├── repositories/
│       ├── services/
│       ├── recovery/
│       └── agent/
│           ├── state.py
│           ├── graph.py
│           ├── tools/
│           └── nodes/
└── Frontend/
    ├── package.json
    ├── vite.config.ts
    ├── components.json
    └── src/
        ├── components/
        ├── routes/
        └── lib/
```

---

## Getting Started

**Prerequisites**

- Python 3.11+
- Node.js 18+
- A PostgreSQL 16 database (a free [Neon](https://neon.tech/) project works well)
- A Razorpay test account (API key, key secret, webhook secret)
- A [Groq](https://groq.com/) API key

**Environment variables** — create a `.env` file in `Backend/`:

```bash
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>/<database>?ssl=require
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
GROQ_API_KEY=your_groq_api_key
JWT_SECRET=your_jwt_signing_secret
```

**Backend**

```bash
cd Backend
# Activate virtual environment
..\.venv\Scripts\activate      # Windows (.venv in project root)
# or python -m venv .venv && source .venv/bin/activate (Linux/Mac)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd Frontend
npm install
npm run dev
```

**Expose your webhook locally**

```bash
ngrok http 8000
```

Register the resulting `https://<id>.ngrok-free.app/api/v1/webhooks/razorpay` URL in your Razorpay Dashboard's webhook settings, subscribed to `payment.failed` and `payment.captured`.

**Key API endpoints**

| Endpoint | Purpose |
| :--- | :--- |
| `POST /api/v1/webhooks/razorpay` | Razorpay webhook ingress (`payment.failed`, `payment.captured`) |
| `POST /api/v1/recoveries/{id}/review` | Operator HITL decision (`approve_retry`, `reject`, `resolve`) |
| `GET /api/v1/recoveries` | Recovery feed and status query |
| `GET /api/v1/analytics/overview` | Dashboard KPI overview metrics |

---

## Business Impact

- **Revenue recapture** — recovers up to **35–50%** of transiently failed payments, without ever asking the customer to restart checkout.
- **Customer protection** — idempotency checks and hard attempt caps remove duplicate-debit risk entirely; no customer is ever charged twice by the agent's own retries.
- **Operational efficiency** — automates **85%+** of standard recovery playbooks, so human operators only ever see the complex or risky exceptions.
- **Full auditability** — every AI diagnosis, confidence score, policy decision, and action is permanently stored with timestamps and a plain-language explanation, ready for compliance review.

---

## Roadmap

- Multi-gateway support (Stripe, Cashfree, PayU) behind the same policy engine
- Adaptive scoring that learns from historical recovery outcomes instead of fixed weights
- Deeper WhatsApp Business API flows for richer alternative-payment conversations
- Per-merchant configurable playbooks (subscriptions vs. one-time checkout)
- A mobile-friendly operator app for on-the-go HITL review

---

<div align="center"> 

**Autonomous where it's safe. Human where it matters.**

</div>
