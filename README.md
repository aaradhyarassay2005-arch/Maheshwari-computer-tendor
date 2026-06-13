# Tender Intelligence Platform

Tender Intelligence Platform is an enterprise workflow system for railway and government tenders. It ingests tender documents, extracts structured fields, scores risk, checks qualification, matches technical requirements against past capability data, and turns the result into an AI-assisted decision brief.

## What It Does

The product is built to help a bid team answer three questions quickly:

1. Should we bid on this tender?
2. If yes, what are the technical, financial, and compliance risks?
3. What explanation can we give management or leadership about the decision?

The system combines a reviewer-friendly web app, a FastAPI backend, PostgreSQL for structured data, and Qdrant/vector search for semantic matching. If no external Qdrant service is configured, the backend can use the local `data/qdrant` storage path.

## System Overview

- Frontend: Next.js App Router with a dashboard, tender explorer, review screens, and admin tools.
- Backend: FastAPI, SQLAlchemy 2, Alembic, async APIs, and service/repository layers.
- Database: PostgreSQL for tenders, users, reviews, documents, and audit data.
- Vector search: Qdrant for similarity search across technical capabilities and tender text.
- AI layer: Gemini-backed services with validation and confidence scores for extracted fields.
- Observability: Prometheus-style metrics, OpenTelemetry, and optional Sentry.

## Quick Start On Windows

This repository includes a one-command launcher for local development.

### Prerequisites

- Docker Desktop running locally.
- Python 3.10 or newer.
- Node.js 18 or newer.

### Run Everything

1. Open PowerShell in the project root.
2. Start the full stack:

```powershell
.\run.ps1
```

That script will:

- Start PostgreSQL in Docker when Docker is available.
- Create or update the backend virtual environment in `backend\.venv`.
- Install Python dependencies from `backend\requirements.txt`.
- Run Alembic migrations.
- Launch the FastAPI server on `http://localhost:8000`.
- Launch the Next.js frontend on `http://localhost:3000`.
- Open the browser to the frontend automatically.

If you only want the database, you can start it separately with:

```powershell
docker compose up -d db
```

## Manual Setup

Use this flow if you want to run each service yourself instead of using `run.ps1`.

### 1. Start PostgreSQL

```powershell
docker compose up -d db
```

### 2. Set Up The Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\alembic upgrade head
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Set Up The Frontend

```powershell
cd frontend
npm install
npm run dev
```

## Environment Variables

The local setup works with the built-in defaults, but these are the important settings if you want to customize or deploy the app.

### Backend Defaults

The backend reads from `backend\.env` when present. The main settings are:

- `ENV` - dev, test, or prod.
- `DATABASE_URL` - defaults to `postgresql+asyncpg://postgres:postgres@localhost:5432/tender_db`.
- `QDRANT_URL` - optional external Qdrant endpoint.
- `QDRANT_API_KEY` - optional API key for Qdrant.
- `QDRANT_PATH` - local storage path, default `data/qdrant`.
- `GEMINI_API_KEY` - optional Gemini access key.
- `SECRET_KEY` - JWT signing secret.
- `SENTRY_DSN` - optional error tracking.
- `OTLP_ENDPOINT` - telemetry endpoint.
- `ENABLE_METRICS` - turns metrics on or off.

For production, copy `.env.backend.prod.example` to `.env.backend.prod` and fill in real values.

### Frontend Defaults

The frontend uses `NEXT_PUBLIC_API_URL` and falls back to `http://localhost:8000/api/v1`.

For production, copy `.env.frontend.prod.example` to `.env.frontend.prod` and point it at the deployed API URL.

## How To Explain This To A Company

This project is not just a tender search website. It is a decision-support platform for a bid team.

The flow is:

1. A tender document is uploaded or ingested.
2. The backend extracts structured data and stores it in PostgreSQL.
3. The risk engine flags clauses that can affect delivery, margin, or compliance.
4. The qualification engine checks whether the bidder can satisfy turnover and net-worth requirements.
5. The matching engine compares the tender against historical capability evidence using embeddings.
6. The review process lets humans verify, correct, approve, or reject the AI output.
7. The analyst service turns the result into a management-ready summary.

In business terms, the platform reduces manual review time, standardizes bid evaluation, and creates a traceable explanation for why a tender should or should not be pursued.

## Main Screens

- Executive dashboard for KPIs and operational summaries.
- Tender explorer for searching and filtering tenders.
- Review workflow for AI-extracted data and corrections.
- Risk, qualification, and BOQ analysis views.
- Admin controls for users, system health, and telemetry.

## Testing And Validation

Backend tests:

```powershell
cd backend
.venv\Scripts\python -m pytest
```

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

## Production Notes

For deployment, use `docker-compose.prod.yml` together with the production env templates and `nginx.conf`.

The production stack includes:

- Nginx as the public entry point.
- Frontend and backend containers.
- PostgreSQL for persistent relational data.
- Qdrant for vector search.

## Access

- Register a new account at `http://localhost:3000/register`.
- The first registered user can be promoted to `ADMIN` or `SUPER_ADMIN` from the database or admin tooling.

## Useful Files

- [run.ps1](run.ps1)
- [docker-compose.yml](docker-compose.yml)
- [docker-compose.prod.yml](docker-compose.prod.yml)
- [.env.backend.prod.example](.env.backend.prod.example)
- [.env.frontend.prod.example](.env.frontend.prod.example)
