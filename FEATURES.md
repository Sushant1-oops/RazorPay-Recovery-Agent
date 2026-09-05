# Key Features & Capabilities

## 1. Autonomous Webhook Ingestion & Deduplication
* **Cryptographic Verification**: Rejects any tampered or spoofed webhooks by computing HMAC-SHA256 digests against `RAZORPAY_WEBHOOK_SECRET`.
* **Idempotency Safeguard**: Ensures repeated webhooks for the same payment event never trigger duplicate recovery jobs or double charges.
* **Unified Recovery Lifecycle**: Consolidates multiple retry attempts under a single parent recovery entity, tracking the end-to-end journey from failure to resolution.

---

## 2. Dual-Tier Failure Root Cause Diagnosis
* **LLM Reasoning (Groq)**: Analyzes multi-attribute context (error code, gateway error description, customer history, payment method, and amount) to detect nuance (e.g., temporary bank downtime vs. permanent account closure).
* **Deterministic Fallback Classifier**: Instant pattern matching on known Razorpay codes (`gateway_error`, `bad_request_error`, `server_error`, `3ds_timeout`) ensuring 100% uptime even during network outages.
* **Confidence Rating**: Assigns a calibrated certainty rating (0.0 to 1.0 / 0% to 100%) to every diagnosis, color-coded in the UI for operators.

---

## 3. Objective Recoverability Scoring Engine (0–100)
A mathematical scoring function evaluates the statistical likelihood of saving a failed payment:
* **Base Score**: 50.0 points baseline.
* **Root Cause Adjustment**:
  * Temporary Bank Error: `+35` points
  * Network Timeout: `+30` points
  * UPI Failure: `+25` points
  * Insufficient Funds: `+15` points
  * Bank Decline: `+5` points
  * Suspected Fraud/Risk: `-30` points (Hard stop)
  * Invalid Payment Details: `-20` points
* **AI Confidence Factor**: Adds proportional points based on diagnostic certainty.
* **Diminishing Returns Penalty**: Applies a penalty of `min(attempts * 15, 45)` to prevent futile loops.
* **Customer Loyalty Multiplier**: Bonus points for returning customers with high historical success rates.

---

## 4. Policy Guardrails & Safe Autonomous Actions
Autonomous agents must not act recklessly. The built-in **Policy Engine** strictly enforces safety rules:
* **Max Attempt Cap**: Hard-limited to 3 attempts. Any further execution triggers immediate human escalation.
* **Cooling-Off Periods**: Mandates exponential backoff intervals between retries to give banking switches time to recover.
* **Duplicate Charge Prevention**: Retries are forbidden on pending or unsettled authorizations.
* **Playbook Selection**:
  * `temporary_failure`: Wait and schedule smart gateway retry.
  * `upi_failure`: Send deep-link push notification for alternative VPA / instant app retry.
  * `notify_alternative`: Generate alternative payment link (Card/Netbanking) when original method is unrecoverable.
  * `escalate`: Immediately halt automation and assign to human review.

---

## 5. Human-in-the-Loop (HITL) Review Portal
* **Automated Escalation**: Low score (<33), high risk, or exhausted recoveries enter the `escalated` state.
* **Review Interface**: Operators see complete AI reasoning, root cause analysis, customer value, and failure history in a side drawer.
* **One-Click Actions**:
  * **Approve Retry**: Overrides system constraints and triggers an intentional retry cycle.
  * **Reject**: Closes the recovery as unrecoverable (`exhausted`).
  * **Resolve**: Manually marks the transaction resolved via offline or alternative settlement.
* **Audit Log**: Captures operator identity, decision timestamps, and custom notes.

---

## 6. Real-Time Operations Command Dashboard
* **KPI Metric Cards**: Real-time totals for Payments, Failed Pool, Recovered Count, Recovery Rate (%), and Total Recovered Revenue (₹).
* **Failure Root-Cause Chart**: Interactive Recharts breakdown showing the distribution of failures across categories.
* **Strategy Performance Matrix**: Live table tracking execution count and success rate for each recovery playbook.
* **Live Agent Feed**: Chronological stream of recovery runs with:
  * Payment identifier link
  * Diagnosed root cause
  * Color-coded confidence progress bar
  * Status badge (`Observing`, `Executing`, `Recovered`, `Escalated`, `Exhausted`)
  * Attempt counter (`x / 3`)
  * Last updated timestamp
