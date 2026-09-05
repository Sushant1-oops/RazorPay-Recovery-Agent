# Technology Stack

## 1. Backend Services
* **Language & Runtime**: Python 3.11+
* **Web Framework**: [FastAPI](https://fastapi.tiangolo.com/) (High-performance ASGI framework)
* **Data Validation & Schemas**: Pydantic v2 (Strict validation for webhooks, state objects, and analytics)
* **ORM & Database Client**: SQLAlchemy 2.0 Async + `asyncpg` (Full asynchronous connection pool)
* **Security & Auth**: 
  * JWT (JSON Web Tokens) with HS256 algorithm for operator authentication
  * Passlib with PBKDF2-SHA256 password hashing
  * Razorpay HMAC-SHA256 signature verification for inbound webhook integrity

---

## 2. Agentic AI & Decision Orchestration
* **Agent Framework**: [LangGraph](https://langchain-ai.github.io/langgraph/) (Directed Cyclic Graph orchestration for stateful multi-step reasoning)
* **Primary LLM**: [Groq](https://groq.com/) Cloud Inference
  * Model: `qwen/qwen3.8-27b` (via `langchain-groq`)
  * Structured Outputs: Pydantic-enforced schemas for diagnosis, strategy, and risk assessment
  * Ultra-low latency: Sub-second inference for real-time webhook response
* **Fallback Decision Engine**: Deterministic rule-based classifier using error codes, keywords, and payment method heuristics when offline or in simulation mode.

---

## 3. Database & Persistence
* **Primary Database**: PostgreSQL 16 hosted on [Neon Serverless Cloud](https://neon.tech/)
* **Connection Mode**: Pooled asyncpg connections with SSL verification
* **Data Architecture**:
  * `payments`: Normalized record of all transactions, attempt counters, failure codes, and amounts
  * `recoveries`: Master record of recovery status, root causes, confidence levels, recoverability scores, and strategies
  * `recovery_actions`: Granular record of every action taken (retry, notification, payment link generation)
  * `audit_logs`: Append-only security and operational audit trail
  * `customers`: Purchase histories and baseline success rates

---

## 4. Frontend Command Center
* **Framework & Bundler**: React 18 with [Vite](https://vitejs.dev/)
* **Routing**: [TanStack Router](https://tanstack.com/router) (Fully type-safe client-side routing)
* **Data Fetching & State**: [TanStack Query v5](https://tanstack.com/query) (Automatic caching, refetching, and query invalidation)
* **Styling & Design System**:
  * [Tailwind CSS v4](https://tailwindcss.com/)
  * [shadcn/ui](https://ui.shadcn.com/) accessible component primitives
  * [Lucide React](https://lucide.dev/) icons
* **Data Visualization**: [Recharts](https://recharts.org/) (Failure root-cause breakdown charts, recovery strategy analytics)

---

## 5. Integrations & Tooling
* **Payment Gateway**: Razorpay Test & Live Webhooks API
* **Tunneling**: ngrok for local development and webhook ingress
* **Containerization**: Dockerfile with lightweight Python slim image
