# Phase 7: Production Deployment

**Status:** ✅ Complete  
**Goal:** Production-ready containerization, CI/CD pipeline, comprehensive testing, and monitoring

---

## 📋 Overview

Phase 7 transforms BillAgent Pro into a production-ready application with:

- **Containerization**: Multi-stage Docker builds for frontend and backend
- **Orchestration**: Production-ready docker-compose configuration
- **CI/CD**: Automated testing and deployment via GitHub Actions
- **Testing**: Comprehensive test suites (pytest + vitest)
- **Monitoring**: Health checks, metrics, and error tracking with Sentry
- **Logging**: Structured JSON logging for production observability
- **Database**: Automated backup and restore scripts

---

## 🐳 Docker Setup

### Frontend Container

**File:** `frontend/Dockerfile`

Multi-stage build with:
- **Stage 1 (Builder)**: Node.js 20 Alpine - builds React app
- **Stage 2 (Production)**: Nginx 1.25 Alpine - serves static files

**Features:**
- Optimized image size (~15MB)
- Non-root user for security
- Health check endpoint
- Build-time environment configuration

```bash
# Build frontend
docker build -t billagent-frontend -f frontend/Dockerfile .

# Run locally
docker run -p 80:80 billagent-frontend
```

### Backend Container

**File:** `backend/Dockerfile`

Multi-stage build with:
- **Base**: Python 3.11-slim with system dependencies
- **Dependencies**: Isolated layer for pip packages
- **Production**: Optimized image with non-root user

**Features:**
- OCR dependencies (OpenCV, Tesseract)
- Health check on `/health` endpoint
- Volume mounts for uploads and storage
- Uvicorn ASGI server

```bash
# Build backend
docker build -t billagent-backend backend/

# Run locally
docker run -p 8000:8000 \
  -e POSTGRES_HOST=localhost \
  -e REDIS_HOST=localhost \
  billagent-backend
```

### Nginx Reverse Proxy

**File:** `frontend/nginx.conf`

Production-grade configuration:
- ✅ GZIP compression for static assets
- ✅ Rate limiting (10 req/s with burst of 20)
- ✅ Security headers (X-Frame-Options, CSP, etc.)
- ✅ API proxying to backend with WebSocket support
- ✅ Static asset caching (1 year for /assets/)
- ✅ SPA fallback routing
- ✅ Prometheus metrics endpoint
- ✅ JSON access logs for log aggregation

**Key Routes:**
- `/` → React SPA
- `/api/` → Proxied to backend:8000
- `/health` → Frontend health check
- `/nginx-status` → Nginx metrics (internal only)

---

## 🚀 Production Deployment

### Quick Start

1. **Configure Environment**
   ```bash
   cp .env.production.example .env
   # Edit .env with production values
   ```

2. **Build and Start**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Verify Health**
   ```bash
   curl http://localhost/health
   curl http://localhost/api/health
   ```

### Production docker-compose

**File:** `docker-compose.prod.yml`

**Services:**
- `frontend` - Nginx + React (Port 80)
- `backend` - FastAPI + Uvicorn
- `postgres` - PostgreSQL 15
- `redis` - Redis 7
- `celery-worker` - Bill processing workers
- `celery-beat` - Scheduled tasks
- `backup` - Database backup service (profile: backup)

**Features:**
- ✅ Health checks on all services
- ✅ Resource limits (CPU/memory)
- ✅ Restart policies (`always`)
- ✅ Named volumes for persistence
- ✅ Isolated network
- ✅ Environment variable validation

**Resource Allocation:**
```yaml
Backend:  2 CPU, 2GB RAM
Frontend: 0.5 CPU, 256MB RAM
Postgres: 2 CPU, 2GB RAM
Redis:    1 CPU, 768MB RAM
```

### Environment Variables

**Critical (Required):**
```env
POSTGRES_PASSWORD=<strong-password>
SECRET_KEY=<generate-with-secrets-module>
```

**Optional:**
```env
MISTRAL_API_KEY=<for-ocr>
OPENAI_API_KEY=<for-fallback>
SENTRY_DSN=<for-error-tracking>
CORS_ORIGINS=https://yourdomain.com
```

**Generate Secret Key:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

---

## 🧪 Testing Infrastructure

### Backend Tests (pytest)

**Configuration:** `backend/pytest.ini`

**Test Files:**
- `test_health.py` - Health check endpoints
- `test_auth.py` - Login, JWT, protected routes
- `test_bills.py` - Bill CRUD, upload, search
- `test_vendors.py` - Vendor management
- `test_agents.py` - AI agent functionality
- `conftest.py` - Shared fixtures and mocks

**Run Tests:**
```bash
cd backend

# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov=agents --cov-report=html

# Specific test file
pytest tests/test_auth.py -v

# Run only unit tests (fast)
pytest tests/ -v -m unit

# Run integration tests
pytest tests/ -v -m integration
```

**Coverage Thresholds:** 60% minimum

### Frontend Tests (vitest)

**Configuration:** `vitest.config.ts`

**Test Files:**
- `Dashboard.test.tsx` - Dashboard component
- `Login.test.tsx` - Login form
- `BillUpload.test.tsx` - File upload
- `BillReview.test.tsx` - Bill review
- `api.test.ts` - API service
- `ocr.test.ts` - OCR service

**Run Tests:**
```bash
# Watch mode
npm run test

# Single run
npm run test:run

# With coverage
npm run test:coverage

# UI mode
npm run test:ui
```

**Coverage Thresholds:** 50% minimum

---

## 🔄 CI/CD Pipeline

### GitHub Actions Workflows

#### 1. Backend Tests (`.github/workflows/backend-tests.yml`)

**Triggers:**
- Push to `main` or `develop`
- Pull requests targeting `main` or `develop`
- Changes in `backend/` directory

**Jobs:**
1. **Lint**
   - Black (formatter check)
   - isort (import sorting)
   - Ruff (linting)
   - MyPy (type checking)

2. **Test**
   - PostgreSQL 15 + Redis 7 services
   - Run pytest with coverage
   - Upload coverage to Codecov

3. **Security**
   - Bandit security scan
   - Upload security report

4. **Build**
   - Docker image build test

#### 2. Frontend Tests (`.github/workflows/frontend-tests.yml`)

**Triggers:**
- Push to `main` or `develop`
- Pull requests
- Changes in `components/`, `services/`, `tests/`

**Jobs:**
1. **Lint**
   - ESLint
   - TypeScript type check

2. **Test**
   - Run vitest with coverage
   - Upload coverage to Codecov

3. **Build**
   - Vite production build
   - Upload build artifacts

4. **Docker**
   - Build frontend Docker image

#### 3. Production Deploy (`.github/workflows/deploy.yml`)

**Triggers:**
- Push to `main` branch
- Manual workflow dispatch

**Jobs:**
1. **Test** - Run test suites
2. **Build Backend** - Build and push to GitHub Container Registry
3. **Build Frontend** - Build and push to GitHub Container Registry
4. **Deploy** - Deploy to production environment
5. **Release** - Create GitHub release with changelog

**Container Registry:**
```
ghcr.io/<your-org>/billagent-backend:latest
ghcr.io/<your-org>/billagent-frontend:latest
```

**Notifications:**
- Slack webhooks for deployment status
- GitHub release creation

---

## 📊 Monitoring & Observability

### Health Check Endpoints

**File:** `backend/app/api/v1/monitoring.py`

| Endpoint | Purpose | Response Time |
|----------|---------|---------------|
| `GET /monitoring/health` | Basic health status | ~5ms |
| `GET /monitoring/health/detailed` | All components + metrics | ~50ms |
| `GET /monitoring/ready` | Kubernetes readiness probe | ~30ms |
| `GET /monitoring/live` | Kubernetes liveness probe | ~2ms |
| `GET /monitoring/metrics` | System resource metrics | ~20ms |
| `GET /monitoring/prometheus` | Prometheus metrics format | ~40ms |
| `GET /monitoring/info` | App version & config | ~3ms |

**Example Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "uptime_seconds": 86400,
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 12.5
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 5.2,
      "connected_clients": 8
    },
    "celery": {
      "status": "healthy",
      "workers": 4,
      "active_tasks": 2
    }
  }
}
```

### Structured Logging

**File:** `backend/app/logging_config.py`

**Features:**
- ✅ JSON-formatted logs for production
- ✅ Request ID correlation
- ✅ User ID tracking
- ✅ Automatic PII redaction
- ✅ Log level configuration
- ✅ Colored console output (development)

**Usage:**
```python
from app.logging_config import get_logger, LogContext

logger = get_logger(__name__)

# Basic logging
logger.info("Processing bill", bill_id=123, vendor="Acme Corp")

# With context
with LogContext(request_id="abc-123", user_id=456):
    logger.info("User action", action="bill_upload")
```

**Log Format (Production):**
```json
{
  "timestamp": "2026-02-03T10:30:45.123456Z",
  "level": "info",
  "message": "Processing bill",
  "logger": "billagent.ocr",
  "request_id": "abc-123",
  "user_id": 456,
  "bill_id": 123,
  "vendor": "Acme Corp"
}
```

### Sentry Error Tracking

**File:** `backend/app/monitoring.py`

**Setup:**
```env
SENTRY_DSN=https://xxx@sentry.io/xxx
```

**Features:**
- ✅ Automatic exception capture
- ✅ Performance monitoring (APM)
- ✅ User context tracking
- ✅ Breadcrumbs for debugging
- ✅ PII filtering
- ✅ Environment-specific sampling

**Usage:**
```python
from app.monitoring import (
    capture_exception,
    capture_message,
    set_user_context,
    add_breadcrumb,
    track_performance
)

# Capture exceptions
try:
    process_bill(bill_id)
except Exception as e:
    capture_exception(
        e,
        context={"bill_id": bill_id},
        tags={"service": "ocr"}
    )

# Track performance
@track_performance("process_bill", "task")
async def process_bill(bill_id: int):
    ...
```

---

## 💾 Database Backup

**File:** `scripts/backup_db.sh`

### Features
- ✅ Compressed backups (gzip)
- ✅ Automatic rotation (7 days default)
- ✅ Latest symlink for easy restore
- ✅ Restore with confirmation
- ✅ List available backups

### Usage

**Create Backup:**
```bash
./scripts/backup_db.sh
# Output: backups/billagent_20260203_103045.dump.gz
```

**Restore Latest:**
```bash
./scripts/backup_db.sh --restore latest
```

**List Backups:**
```bash
./scripts/backup_db.sh --list
```

**Cleanup Old Backups:**
```bash
./scripts/backup_db.sh --cleanup
```

### Docker Backup Service

```bash
# Run one-time backup
docker-compose -f docker-compose.prod.yml run --rm backup

# Schedule with cron
0 2 * * * cd /opt/billagent && docker-compose -f docker-compose.prod.yml run --rm backup
```

---

## 🔧 Code Quality Tools

### Linting & Formatting

**Backend:**
```bash
# Format with Black
cd backend && black .

# Sort imports
cd backend && isort .

# Lint with Ruff
cd backend && ruff check .

# Type check with MyPy
cd backend && mypy app --ignore-missing-imports
```

**Frontend:**
```bash
# Lint with ESLint
npm run lint

# Fix auto-fixable issues
npm run lint:fix

# Format with Prettier
npm run format

# Type check
npm run typecheck
```

### Pre-commit Hooks

Install pre-commit (optional):
```bash
pip install pre-commit
pre-commit install
```

This will run linting and formatting on every commit.

---

## 📈 Metrics & Monitoring

### Prometheus Integration

**Endpoint:** `GET /monitoring/prometheus`

**Metrics Exported:**
- `billagent_up` - Service health (1 = healthy)
- `billagent_uptime_seconds` - Service uptime
- `billagent_database_up` - Database connection status
- `billagent_database_latency_ms` - Database query latency
- `billagent_redis_up` - Redis connection status
- `billagent_celery_workers` - Number of active workers
- `billagent_cpu_percent` - CPU usage
- `billagent_memory_percent` - Memory usage
- `billagent_memory_used_bytes` - Memory used
- `billagent_disk_percent` - Disk usage

**Prometheus Configuration:**
```yaml
scrape_configs:
  - job_name: 'billagent'
    scrape_interval: 15s
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /monitoring/prometheus
```

### Grafana Dashboard

Sample metrics to monitor:
- Request rate (req/s)
- Error rate (%)
- Response time (p50, p95, p99)
- Database query latency
- Celery queue depth
- Worker utilization
- Memory/CPU usage

---

## 🚨 Troubleshooting

### Service Won't Start

**Check logs:**
```bash
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f frontend
```

**Check health:**
```bash
docker-compose -f docker-compose.prod.yml ps
curl http://localhost/monitoring/health/detailed
```

### Database Connection Issues

**Verify database is running:**
```bash
docker-compose -f docker-compose.prod.yml exec postgres pg_isready
```

**Check connection string:**
```bash
docker-compose -f docker-compose.prod.yml exec backend env | grep POSTGRES
```

**Manual connection test:**
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U billagent -d billagent
```

### High Memory Usage

**Check container stats:**
```bash
docker stats
```

**Restart Celery workers:**
```bash
docker-compose -f docker-compose.prod.yml restart celery-worker
```

**Adjust resource limits:**
Edit `docker-compose.prod.yml` and adjust `deploy.resources.limits`

### Test Failures

**Backend tests:**
```bash
# Run with verbose output
cd backend && pytest tests/ -vv

# Run specific test
pytest tests/test_auth.py::TestLogin::test_login_success -vv

# Skip slow tests
pytest tests/ -v -m "not slow"
```

**Frontend tests:**
```bash
# Run with debugging
npm run test -- --reporter=verbose

# Update snapshots
npm run test -- -u
```

---

## 📚 Additional Resources

### Files Created in Phase 7

**Docker:**
- `frontend/Dockerfile` - Frontend container
- `frontend/nginx.conf` - Nginx configuration
- `docker-compose.prod.yml` - Production orchestration
- `.env.production.example` - Environment template

**CI/CD:**
- `.github/workflows/backend-tests.yml` - Backend testing
- `.github/workflows/frontend-tests.yml` - Frontend testing
- `.github/workflows/deploy.yml` - Deployment pipeline

**Testing:**
- `backend/pytest.ini` - Pytest config
- `backend/tests/conftest.py` - Test fixtures
- `backend/tests/test_*.py` - Test suites
- `vitest.config.ts` - Vitest config
- `tests/setup.ts` - Test setup
- `tests/*.test.tsx` - Component tests

**Monitoring:**
- `backend/app/logging_config.py` - Structured logging
- `backend/app/monitoring.py` - Sentry integration
- `backend/app/api/v1/monitoring.py` - Health endpoints

**Utilities:**
- `scripts/backup_db.sh` - Database backup script
- `.eslintrc.yml` - ESLint config
- `.prettierrc.yml` - Prettier config
- `backend/requirements-dev.txt` - Dev dependencies

### Deployment Checklist

- [ ] Update `.env` with production values
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Generate secure `SECRET_KEY`
- [ ] Configure `SENTRY_DSN` (optional)
- [ ] Add OCR API keys (`MISTRAL_API_KEY`, etc.)
- [ ] Set correct `CORS_ORIGINS`
- [ ] Review resource limits in docker-compose
- [ ] Set up SSL/TLS (via load balancer or Certbot)
- [ ] Configure domain DNS
- [ ] Set up database backups
- [ ] Configure monitoring/alerting
- [ ] Review security headers
- [ ] Enable rate limiting
- [ ] Test disaster recovery procedure

---

## 🎯 Next Steps

With Phase 7 complete, your application is production-ready! Consider:

1. **Infrastructure as Code**: Terraform/Pulumi for cloud resources
2. **Kubernetes**: For advanced orchestration and scaling
3. **CDN**: CloudFlare or AWS CloudFront for static assets
4. **WAF**: Web Application Firewall for security
5. **Auto-scaling**: Based on CPU/memory metrics
6. **Multi-region**: For high availability
7. **Disaster Recovery**: Cross-region backups
8. **Performance Testing**: Load testing with k6 or Locust

---

## 📞 Support

For issues or questions:
- Review logs: `docker-compose -f docker-compose.prod.yml logs`
- Check health: `curl http://localhost/monitoring/health/detailed`
- View metrics: `curl http://localhost/monitoring/metrics`
- Database status: `docker-compose -f docker-compose.prod.yml exec postgres pg_isready`

**Happy Deploying! 🚀**
