# Copilot Instructions for BillAgent Pro

## Project Overview
BillAgent Pro is a multi-agent AI system for digitizing, validating, and analyzing handwritten bills. It uses Python (FastAPI, Celery, SQLAlchemy) for the backend and React 19 + TypeScript for the frontend. The backend orchestrates several specialized agents for OCR, validation, deduplication, and accounting logic.

## Key Architectural Patterns
- **Multi-Agent Orchestration:** Core agents (Digitizer, Auditor, Controller, Accountant) are coordinated by `BillProcessingService` (see `process_bill()` in backend/tasks/process_bill.py).
- **Async Processing:** Long-running jobs (OCR, validation) are handled via Celery tasks and Redis queues.
- **Strict Validation:** Auditor agent enforces 14+ business and math rules using Python `Decimal` for precision.
- **Fallbacks:** Digitizer agent uses Mistral OCR 3 by default, with GPT-4o Vision as fallback.
- **Audit Trail:** All actions are logged in the `audit_logs` table (see backend/app/models/audit_log.py).
- **Database:** PostgreSQL with async SQLAlchemy models (see backend/app/models/).
- **Frontend:** React components in `components/` interact with backend via REST API endpoints (see backend/app/api/v1/).

## Developer Workflows
- **Start Dev Environment:**
  - Use Docker Compose for PostgreSQL and Redis: `docker-compose up -d postgres redis`
  - Backend: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
  - Frontend: `npm run dev`
- **Run Migrations:**
  - `alembic upgrade head` (from backend directory)
- **Testing:**
  - Backend: Pytest tests in `backend/tests/`
  - Frontend: Vitest tests in `tests/`
- **API Keys:**
  - Required for OCR (Mistral, OpenAI). Add to `.env`.
- **CI/CD:**
  - Automated via GitHub Actions (see `.github/workflows/` if present)

## Project-Specific Conventions
- **Agents:** Each agent is a single Python file in `backend/agents/` and exposes a main class/function (e.g., `DigitizerAgent`, `AuditorAgent`).
- **Error Handling:** Errors are reported with severity (ERROR/WARNING) and logged for audit.
- **Data Models:** All financial data uses `Decimal` for accuracy.
- **Frontend API Calls:** Use `services/api.ts` for HTTP requests; authentication via JWT.
- **Component Structure:** UI components are in `components/`, with ShadcnUI in `components/ui/`.

## Integration Points
- **Celery:** Background tasks for OCR and bill processing.
- **Redis:** Used as Celery broker and cache.
- **PostgreSQL:** Main data store for bills, vendors, audit logs.
- **External OCR:** Mistral OCR 3 and GPT-4o Vision (via API keys).

## Examples
- To add a new agent, create a Python file in `backend/agents/` and update orchestration logic in `process_bill.py`.
- To add a validation rule, modify `AuditorAgent` in `backend/agents/auditor.py`.
- To extend frontend, add a React component in `components/` and connect via `services/api.ts`.

## References
- [README.md](../../README.md) — Big picture, architecture, and setup
- [backend/agents/](../../backend/agents/) — All agent implementations
- [backend/app/models/](../../backend/app/models/) — ORM models
- [backend/app/services/](../../backend/app/services/) — Business logic
- [components/](../../components/) — React UI
- [services/api.ts](../../services/api.ts) — Frontend API integration

---
**For AI agents:** Always follow existing agent orchestration and validation patterns. Reference audit logging and error handling conventions. Use async/await for database and task operations. When in doubt, check the README and backend/agents/ for examples.