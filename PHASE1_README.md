# Phase 1: Database Foundation - README

**BillAgent Pro** - Production-Ready Database Layer  
**Phase**: 1 of 7  
**Status**: ✅ Complete  
**Last Updated**: 3 February 2026

---

## 📋 Overview

Phase 1 establishes the complete database foundation for BillAgent Pro, a production-ready AI-powered bill processing system. This phase implements:

- **PostgreSQL 15** database with async support
- **SQLAlchemy 2.0** ORM with Mapped columns
- **Alembic** migrations for schema management
- **Pydantic 2.x** schemas for validation
- **FastAPI** REST API with comprehensive endpoints
- **Repository pattern** for clean database operations

---

## 🏗️ Architecture

### Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| Database | PostgreSQL | 15+ |
| Cache/Queue | Redis | 7+ |
| ORM | SQLAlchemy | 2.0.36+ |
| Migration | Alembic | 1.14.0+ |
| API Framework | FastAPI | 0.128.0+ |
| Validation | Pydantic | 2.12.5+ |
| Python | Python | 3.11+ |

### Database Schema

```
┌─────────────┐
│   vendors   │
│  (UUID PK)  │
└──────┬──────┘
       │
       │ 1:N
       │
┌──────▼──────┐      ┌──────────────┐
│    bills    │──N:1─┤  line_items  │
│  (UUID PK)  │      │   (UUID PK)  │
└──────┬──────┘      └──────────────┘
       │
       │ 1:N
       │
┌──────▼──────┐      ┌──────────────┐
│ audit_logs  │      │   gl_codes   │
│  (UUID PK)  │      │  (Code PK)   │
└─────────────┘      └──────────────┘
```

---

## 📦 Database Models

### 1. **Vendor** (`vendors` table)
- Stores vendor/supplier information
- Fields: name, contact info, default GL code
- Indexed: name (with trigram for fuzzy search)

### 2. **Bill** (`bills` table)
- Core bill processing entity
- Status: `PROCESSING` → `NEEDS_REVIEW` → `APPROVED` → `POSTED`
- Financial fields use `Decimal(12,2)` for precision
- JSONB fields for confidence scores and bounding boxes
- Tracks OCR engine, processing time, and task ID

### 3. **LineItem** (`line_items` table)
- Individual items on a bill
- Quantity: `Decimal(10,3)`
- Prices: `Decimal(12,2)`
- Automatic math validation (`quantity × unit_price = total_price`)
- GL code assignment with source tracking

### 4. **AuditLog** (`audit_logs` table)
- Complete audit trail for all bill changes
- Tracks: action, agent/user, old/new values
- JSONB storage for flexible metadata
- IP address and request ID tracking

### 5. **GLCode** (`gl_codes` table)
- General Ledger codes for expense categorization
- 13 default categories (Office, IT, Travel, etc.)
- Keyword-based matching for auto-assignment
- Categories: Office, IT, Travel, Professional Services, etc.

---

## 🚀 Setup Instructions

### Prerequisites

- **Docker Desktop** (for PostgreSQL & Redis)
- **Python 3.11+**
- **Node.js 18+** (for frontend, optional in Phase 1)

### Quick Start

```bash
# 1. Clone repository (if not already done)
cd /path/to/Agentic-AI-enabled-bill-management-system-final

# 2. Run automated setup
chmod +x setup.sh
./setup.sh
```

The setup script will:
1. ✅ Check Docker is running
2. ✅ Start PostgreSQL and Redis containers
3. ✅ Create Python virtual environment
4. ✅ Install dependencies
5. ✅ Create `.env` from template
6. ✅ Run database migrations
7. ✅ Seed initial data (GL codes & sample vendors)

### Manual Setup (Alternative)

<details>
<summary>Click to expand manual setup steps</summary>

```bash
# 1. Start containers
docker-compose up -d postgres redis

# 2. Create Python environment
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env and add your API keys

# 5. Run migrations
alembic upgrade head

# 6. Seed database
python -m app.scripts.seed_db

cd ..
```
</details>

### Environment Variables

Edit `backend/.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://billagent:billagent123@localhost:5432/billagent_db

# Redis
REDIS_URL=redis://localhost:6379/0

# API Keys (required for Phase 2+)
MISTRAL_API_KEY=your_mistral_key_here
OPENAI_API_KEY=your_openai_key_here
GOOGLE_API_KEY=your_google_key_here

# Security
SECRET_KEY=your-secret-key-here
API_VERSION=1.0.0
ENVIRONMENT=development
DEBUG=true
```

---

## 🎯 Running the Application

### Option 1: Development Script (Recommended)

```bash
chmod +x run-dev.sh
./run-dev.sh
```

This starts:
- Backend API on `http://localhost:8000`
- Frontend on `http://localhost:5173` (if npm deps installed)

### Option 2: Backend Only

```bash
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Using Python Module

```bash
cd backend
source venv/bin/activate
python -m app.main
```

---

## 📡 API Endpoints

### Health & Status

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root endpoint |
| `GET` | `/health` | Health check with DB/Redis status |

### Bills

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/bills/upload` | Upload bill image for processing |
| `GET` | `/api/v1/bills/status/{task_id}` | Poll processing status |
| `GET` | `/api/v1/bills/{bill_id}` | Get bill details with line items |
| `PATCH` | `/api/v1/bills/{bill_id}` | Update bill fields |
| `GET` | `/api/v1/bills` | List bills (paginated, filterable) |
| `POST` | `/api/v1/bills/{bill_id}/approve` | Approve a bill |

### Vendors

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/vendors` | List all vendors |
| `POST` | `/api/v1/vendors` | Create new vendor |
| `GET` | `/api/v1/vendors/{vendor_id}` | Get vendor details |

### GL Codes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/gl-codes` | List GL codes (filterable) |

### Audit Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/bills/{bill_id}/audit-logs` | Get bill audit trail |

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 🧪 Testing the API

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# List bills
curl http://localhost:8000/api/v1/bills

# List vendors
curl http://localhost:8000/api/v1/vendors

# List GL codes
curl http://localhost:8000/api/v1/gl-codes
```

### Using HTTPie

```bash
# Upload a bill (placeholder - full OCR in Phase 2)
http POST http://localhost:8000/api/v1/bills/upload file@bill.jpg

# Get bill details
http GET http://localhost:8000/api/v1/bills/{bill_id}
```

### Using Swagger UI

1. Open http://localhost:8000/docs
2. Click "Try it out" on any endpoint
3. Fill in parameters
4. Click "Execute"

---

## 🗄️ Database Management

### Alembic Migrations

```bash
cd backend

# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

### pgAdmin (Optional)

Access at http://localhost:5050 (if running from docker-compose)

**Credentials**:
- Email: `admin@billagent.com`
- Password: `admin123`

**Connect to PostgreSQL**:
- Host: `postgres` (or `localhost` from host machine)
- Port: `5432`
- Database: `billagent_db`
- Username: `billagent`
- Password: `billagent123`

### Direct Database Access

```bash
# Using Docker
docker exec -it billagent-postgres psql -U billagent -d billagent_db

# Common queries
SELECT * FROM vendors;
SELECT * FROM bills;
SELECT * FROM gl_codes;
SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;
```

---

## 📊 Default Data

### GL Codes (13 categories)

| Code | Category | Example Keywords |
|------|----------|------------------|
| 5100 | Office Supplies | stationery, paper, pens |
| 5200 | Utilities | electricity, water, internet |
| 5300 | Rent | office rent, lease |
| 5400 | IT & Software | software, cloud, SaaS |
| 5500 | Professional Services | legal, consulting |
| 5600 | Marketing | advertising, SEO, social media |
| 5700 | Travel | flights, hotels, taxi |
| 5800 | Meals & Entertainment | restaurant, catering |
| 5900 | Insurance | business insurance |
| 6000 | Equipment | laptops, furniture |
| 6100 | Maintenance | repairs, cleaning |
| 6200 | Salaries | wages, payroll |
| 6300 | Miscellaneous | other expenses |

### Sample Vendors (5 vendors)

- Office Supplies Co.
- Tech Solutions Ltd.
- Cloud Services India
- Professional Services Group
- Marketing Agency Pro

---

## 📁 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Pydantic Settings
│   ├── database.py                # SQLAlchemy setup
│   ├── models/                    # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── vendor.py
│   │   ├── bill.py
│   │   ├── line_item.py
│   │   ├── audit_log.py
│   │   └── gl_code.py
│   ├── schemas/                   # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── common.py
│   │   ├── vendor_schema.py
│   │   ├── bill_schema.py
│   │   ├── line_item_schema.py
│   │   ├── audit_log_schema.py
│   │   └── gl_code_schema.py
│   ├── repositories/              # Database operations
│   │   ├── __init__.py
│   │   ├── bill_repository.py
│   │   ├── vendor_repository.py
│   │   └── gl_code_repository.py
│   └── scripts/
│       ├── __init__.py
│       └── seed_db.py
├── alembic/
│   ├── versions/
│   │   └── 001_initial_schema.py  # Initial migration
│   └── env.py
├── requirements.txt
├── .env.example
└── alembic.ini

docker-compose.yml                  # PostgreSQL + Redis
setup.sh                            # Automated setup
run-dev.sh                          # Development server
```

---

## 🔑 Key Features Implemented

### ✅ Database Layer
- [x] PostgreSQL 15 with async support via asyncpg
- [x] SQLAlchemy 2.0 with modern Mapped columns
- [x] Alembic migrations with auto-generation
- [x] JSONB columns for flexible data (confidence, bounding boxes)
- [x] Proper indexes (vendor name with trigram, foreign keys)
- [x] UUID primary keys throughout

### ✅ Data Validation
- [x] Pydantic 2.x schemas with field validators
- [x] Decimal precision for financial data (no floats!)
- [x] Email validation for vendor contacts
- [x] Date parsing and validation
- [x] Enum-based status management

### ✅ API Layer
- [x] FastAPI with async endpoints
- [x] Comprehensive CRUD operations
- [x] Pagination support
- [x] Filtering and search
- [x] Error handling with standard responses
- [x] Auto-generated API documentation

### ✅ Repository Pattern
- [x] Clean separation of concerns
- [x] Reusable database queries
- [x] Transaction management
- [x] Duplicate detection logic
- [x] Dashboard statistics queries

### ✅ Audit Trail
- [x] Complete change tracking
- [x] Agent/user attribution
- [x] Old/new value comparison
- [x] Metadata support (IP, request ID)
- [x] Timestamp tracking

### ✅ Development Tools
- [x] Automated setup script
- [x] Development server script
- [x] Database seeding script
- [x] Docker Compose for dependencies
- [x] Environment variable management

---

## 🔄 Phase 1 Limitations

The following features are **intentionally deferred** to later phases:

| Feature | Deferred To | Reason |
|---------|-------------|--------|
| OCR Processing | Phase 2 | Mistral OCR integration |
| Background Tasks | Phase 4 | Celery + Redis workers |
| Agent Orchestration | Phase 5 | Multi-agent workflow |
| Authentication | Phase 6 | JWT + user management |
| File Storage | Phase 2 | Azure Blob / local storage |
| ML-based GL Matching | Phase 5 | Learning agent |

**Current behavior**:
- Uploading a bill creates a record but doesn't process it (OCR pending)
- Task status polling works but returns mock progress
- No actual image processing yet

---

## 🐛 Troubleshooting

### Docker Issues

**Problem**: "Cannot connect to database"
```bash
# Check if containers are running
docker ps

# Restart containers
docker-compose restart postgres

# View logs
docker-compose logs postgres
```

**Problem**: "Port 5432 already in use"
```bash
# Stop other PostgreSQL instances
sudo service postgresql stop  # Linux
brew services stop postgresql  # macOS
```

### Migration Issues

**Problem**: "Target database is not up to date"
```bash
cd backend
alembic upgrade head
```

**Problem**: "Can't locate revision"
```bash
# Reset migrations (DANGER: loses data)
alembic downgrade base
alembic upgrade head
```

### Python Environment Issues

**Problem**: "Module not found"
```bash
# Ensure venv is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**Problem**: "asyncpg not installed"
```bash
# Install PostgreSQL development headers first
# Ubuntu/Debian:
sudo apt-get install libpq-dev

# macOS:
brew install postgresql

# Then reinstall
pip install asyncpg
```

---

## 📈 Next Steps (Phase 2)

Phase 2 will implement:

1. **Mistral OCR Integration**
   - Mistral OCR 3 API integration
   - GPT-4o Vision as fallback
   - Image preprocessing pipeline
   - Bounding box extraction

2. **Digitizer Agent**
   - Field extraction logic
   - Confidence scoring
   - Vendor name recognition
   - Invoice number parsing

3. **File Storage**
   - Azure Blob Storage (production)
   - Local filesystem (development)
   - Image upload handling

4. **Enhanced Bill Upload**
   - Actual OCR processing
   - Real-time progress updates
   - Error handling and retry logic

---

## 👥 Contributors

- Development Team: BillAgent Pro
- Phase 1 Completion: 3 February 2026

---

## 📄 License

Copyright © 2026 BillAgent Pro. All rights reserved.

---

## 📞 Support

- **Documentation**: See main [README.md](README.md) and [SPEC.md](SPEC.md)
- **Issues**: Create an issue in the repository
- **API Docs**: http://localhost:8000/docs (when running)

---

**Phase 1 Status**: ✅ **COMPLETE** - Ready for Phase 2!
