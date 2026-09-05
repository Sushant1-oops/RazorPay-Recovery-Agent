# Autonomous Payment Failure Recovery Agent — Dashboard UI

A real-time command dashboard for monitoring, evaluating, and managing autonomous payment recovery workflows. Built with React, Vite, TanStack Router, TanStack Query, and Tailwind CSS.

## Features

- **Live Recovery Stream**: Real-time visibility into AI root-cause diagnosis, confidence ratings, and recovery playbooks.
- **Recovery Analytics**: Track recovery success rates, recovered revenue, and failure breakdown across payment methods.
- **Human-in-the-Loop (HITL)**: Review escalated high-risk cases, approve retries, or manually resolve failures.
- **Auditable History**: Complete trace of agent actions, notifications, and customer interactions.

## Getting Started

### Prerequisites
- Node.js 18+
- npm or bun

### Setup & Run
```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will run at `http://localhost:5173`.
Make sure the backend API is running on `http://localhost:8000`.
