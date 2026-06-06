# Tender Intelligence Platform

An enterprise-grade intelligence platform for railway and government tenders. Powered by Next.js, FastAPI, PostgreSQL, and Qdrant vector search, the platform automates tender document ingestion, compliance risk analysis, financial bidder qualification, and AI-driven bidding recommendation narratives.

---

## 🛠 Tech Stack

*   **Frontend**: Next.js (App Router), Tailwind CSS, Framer Motion, Recharts, Lucide Icons.
*   **Backend**: FastAPI, SQLAlchemy 2.0 (asyncio), Alembic Migrations, Uvicorn.
*   **Vector Engine**: Qdrant Vector DB (supports local storage folder fallback).
*   **Relational Database**: PostgreSQL.
*   **Generative AI**: Gemini LLM integration (via abstract providers with simulator fallback).
*   **Observability**: OpenTelemetry instrumentation, Prometheus Metrics exporter.

---

## 🚀 Key Features & Pages

*   **Executive Dashboard**: Key performance telemetry metrics, dynamic charts tracking tender distribution and recommendation breakdown, manual tender registration, and drag-and-drop Excel spreadsheets uploader.
*   **Tender Explorer**: Interactive paginated database table supporting debounced keyword searches, department filters, status sorting, and PDF download links.
*   **Technical Project Matching**: Real-time semantic analysis comparing tender technical eligibility statements against historical corporate capability certificates using Qdrant vector embeddings.
*   **Financial Qualification Engine**: Mathematical verification checking bidder turnover averages (150% estimated tender value threshold) and positive net worth metrics.
*   **Compliance Risk Engine**: Extracts risk-critical clauses (EMD, penalty fees, liquidating damages, short work periods) and offers actionable risk mitigations.
*   **AI Bidding Analyst**: Gemini-powered executive summaries, management briefs, and compliance explanations compiled from structured engine parameters.
*   **Verification & Human Review Board**: Collaborative queue where operators can review AI-extracted parameters, apply corrections, change status (`PARSED` -> `APPROVED` / `REJECTED`), and commit reviews.
*   **Super Admin Control Center**: Telemetry dashboards tracking CPU/RAM load, Postgres/Qdrant health signals, API hit frequency, user directory directories with role assignment triggers, and transaction-differential security logs.

---

## 🏁 How to Run & Test (Windows PowerShell)

We provide a single PowerShell launch utility (`run.ps1`) to spin up all services locally.

### Prerequisites

1.  **Docker Desktop** (must be active to run local PostgreSQL).
2.  **Node.js v18+** (for frontend server).
3.  **Python 3.10+** (for backend server).

### Execution Steps

1.  Open **PowerShell** at the root of the project.
2.  Execute the launch script:
    ```powershell
    .\run.ps1
    ```
    This script will:
    *   Start the local PostgreSQL database in Docker.
    *   Configure the Python virtual environment (`backend/.venv`) and install `requirements.txt`.
    *   Apply SQLAlchemy migrations via Alembic.
    *   Spawn the FastAPI Uvicorn developer server (port `8000`) in a new terminal window.
    *   Spawn the Next.js developer server (port `3000`) in a new terminal window.
    *   Open your browser to `http://localhost:3000` automatically.

---

## 🔐 Credentials & Registration

*   **New Accounts**: Navigate to `http://localhost:3000/register` to register a new account.
*   **Super Admin Panels**: The first user registered can be modified to `ADMIN` or `SUPER_ADMIN` via the DB or the user directory inspector once logged in to access the control panel under the **Admin** tab.