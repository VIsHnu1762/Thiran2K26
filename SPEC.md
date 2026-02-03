# SPEC.md: BillAgent Pro (Production Specification)

> **Version:** 2.0.0  
> **Last Updated:** February 2026  
> **Mission:** Transform handwritten, messy bills into audit-ready financial records using Agentic AI.  
> **Core Constraint:** Zero tolerance for math errors; strict double-entry accounting compliance.

---

## 1. Project Overview

**BillAgent Pro** is an autonomous financial agent that digitizes high-friction physical documents (handwritten carbon-copy bills) into structured accounting data. Unlike simple OCR tools, it uses a **Multi-Agent System** to validate math, assign General Ledger (GL) codes, detect fraud (duplicates), and prepare data for ERP ingestion.

### 1.1 Key Differentiators

| Feature | Traditional OCR | BillAgent Pro |
|---------|-----------------|---------------|
| Handwriting Support | ❌ Poor | ✅ 89%+ accuracy |
| Math Validation | ❌ None | ✅ Auto-audit |
| Duplicate Detection | ❌ None | ✅ Fraud prevention |
| GL Code Assignment | ❌ Manual | ✅ AI-powered |
| Audit Trail | ❌ None | ✅ Full traceability |

---

## 2. Tech Stack (Locked)

> ⚠️ **Do not deviate from this stack. Use strictly these technologies.**

| Layer | Technology | Version | Rationale |
|-------|------------|---------|-----------|
| **Backend** | Python | 3.11+ | Async support, type hints |
| | FastAPI | Latest | Async-native, auto OpenAPI docs |
| | SQLAlchemy | 2.0+ | ORM with async support |
| | Pydantic | 2.x | Strict data validation |
| **Database** | PostgreSQL | 15+ | ACID compliance for financial data |
| **Task Queue** | Celery | 5.x | Long-running OCR job handling |
| | Redis | 7.x | Message broker & caching |
| **OCR Engine** | Mistral OCR 3 | Latest | Primary - 89% handwriting accuracy |
| | GPT-4o Vision | Latest | Fallback OCR engine |
| **Frontend** | React | 19.x | UI Framework |
| | Vite | 6.x | Build tool |
| | TypeScript | 5.x | Type safety |
| | Tailwind CSS | 3.x | Styling |
| | ShadcnUI | Latest | Component library |

### 2.1 Why This Stack?

- **PostgreSQL over SQLite/MongoDB**: Financial data requires ACID compliance and relational integrity
- **Mistral OCR 3 over Tesseract/EasyOCR**: Tesseract fails on handwritten carbon copies; Mistral preserves table structures
- **Celery + Redis**: OCR is CPU-intensive; async processing prevents API timeouts
- **Pydantic**: Strict validation catches data errors before they hit the database

---

## 3. Database Schema (PostgreSQL)

> ⚠️ **The AI must implement this exact schema to ensure financial integrity.**

### 3.1 Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   vendors   │       │    bills    │       │ line_items  │
├─────────────┤       ├─────────────┤       ├─────────────┤
│ id (PK)     │◄──────│ vendor_id   │       │ id (PK)     │
│ name        │       │ id (PK)     │◄──────│ bill_id     │
│ default_gl  │       │ invoice_num │       │ description │
│ created_at  │       │ invoice_date│       │ quantity    │
└─────────────┘       │ due_date    │       │ unit_price  │
                      │ subtotal    │       │ total_price │
                      │ tax_amount  │       │ gl_code     │
                      │ total_amount│       └─────────────┘
                      │ confidence  │
                      │ status      │       ┌─────────────┐
                      │ image_url   │       │ audit_logs  │
                      │ ocr_raw_data│       ├─────────────┤
                      │ created_at  │◄──────│ bill_id     │
                      └─────────────┘       │ id (PK)     │
                                            │ action      │
                                            │ agent_name  │
                                            │ timestamp   │
                                            └─────────────┘
```

### 3.2 SQL Schema Definition

```sql
-- 1. VENDORS (Who we paid)
CREATE TABLE vendors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    default_gl_code VARCHAR(50),  -- Auto-categorization memory
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_vendors_name ON vendors(name);

-- 2. BILLS (The Header Data)
CREATE TABLE bills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vendor_id UUID REFERENCES vendors(id),
    invoice_number VARCHAR(100),
    invoice_date DATE,
    due_date DATE,
    subtotal DECIMAL(12,2),
    tax_amount DECIMAL(12,2),
    total_amount DECIMAL(12,2),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1),
    status VARCHAR(50) DEFAULT 'PROCESSING' 
        CHECK (status IN ('PROCESSING', 'NEEDS_REVIEW', 'APPROVED', 'POSTED', 'FAILED')),
    image_url TEXT NOT NULL,
    ocr_raw_data JSONB,  -- Store original OCR output for debugging
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_bills_status ON bills(status);
CREATE INDEX idx_bills_vendor ON bills(vendor_id);
CREATE INDEX idx_bills_invoice ON bills(vendor_id, invoice_number, total_amount);

-- 3. LINE_ITEMS (The Granular Data)
CREATE TABLE line_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id UUID REFERENCES bills(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    quantity DECIMAL(10,3),
    unit_price DECIMAL(12,2),
    total_price DECIMAL(12,2),
    gl_code VARCHAR(50),  -- General Ledger Code (e.g., 5001-Office Supplies)
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 1)
);

CREATE INDEX idx_line_items_bill ON line_items(bill_id);

-- 4. AUDIT_LOGS (For Vouching/Tracing)
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id UUID REFERENCES bills(id) ON DELETE CASCADE,
    action VARCHAR(255) NOT NULL,  -- e.g., "Field 'Total' corrected by Human"
    agent_name VARCHAR(100) NOT NULL,  -- "ErrorCorrectionAgent" or Human User
    old_value JSONB,
    new_value JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_bill ON audit_logs(bill_id);
CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp);

-- 5. GL_CODES (General Ledger Reference)
CREATE TABLE gl_codes (
    code VARCHAR(50) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    category VARCHAR(100),  -- EXPENSE, ASSET, LIABILITY, etc.
    is_active BOOLEAN DEFAULT TRUE
);

-- Seed common GL codes
INSERT INTO gl_codes (code, name, category) VALUES
    ('5001', 'Office Supplies', 'EXPENSE'),
    ('5002', 'Travel & Transportation', 'EXPENSE'),
    ('5003', 'Utilities', 'EXPENSE'),
    ('5004', 'Professional Services', 'EXPENSE'),
    ('5005', 'Maintenance & Repairs', 'EXPENSE'),
    ('5006', 'Raw Materials', 'EXPENSE'),
    ('5007', 'Inventory Purchases', 'EXPENSE'),
    ('5008', 'Marketing & Advertising', 'EXPENSE');
```

---

## 4. The Agentic Pipeline (Logic Flow)

> The backend is not just an API; it is a **pipeline of 4 distinct AI Agents**.

### 4.1 Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BILL PROCESSING PIPELINE                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐            │
│   │   IMAGE     │    │  CELERY     │    │  REDIS      │            │
│   │   UPLOAD    │───▶│  TASK       │◀──▶│  BROKER     │            │
│   └─────────────┘    └──────┬──────┘    └─────────────┘            │
│                             │                                        │
│   ┌─────────────────────────▼─────────────────────────────────────┐ │
│   │                    AGENT 1: DIGITIZER                          │ │
│   │  ┌──────────────────────────────────────────────────────────┐ │ │
│   │  │ • Input: Raw Image (JPEG/PDF)                            │ │ │
│   │  │ • Tool: Mistral OCR 3 / GPT-4o Vision                    │ │ │
│   │  │ • Output: Structured JSON with bounding boxes            │ │ │
│   │  │ • Preserves: Table layout, spatial relationships         │ │ │
│   │  └──────────────────────────────────────────────────────────┘ │ │
│   └─────────────────────────┬─────────────────────────────────────┘ │
│                             │                                        │
│   ┌─────────────────────────▼─────────────────────────────────────┐ │
│   │                    AGENT 2: AUDITOR                            │ │
│   │  ┌──────────────────────────────────────────────────────────┐ │ │
│   │  │ • Validation Rules:                                      │ │ │
│   │  │   ✓ Sum(line_items) == Subtotal (±$0.01 tolerance)       │ │ │
│   │  │   ✓ Subtotal + Tax == Total                              │ │ │
│   │  │   ✓ Invoice Date <= Today                                │ │ │
│   │  │   ✓ All quantities > 0                                   │ │ │
│   │  │   ✓ All prices > 0                                       │ │ │
│   │  │ • Failure: Mark status = NEEDS_REVIEW                    │ │ │
│   │  └──────────────────────────────────────────────────────────┘ │ │
│   └─────────────────────────┬─────────────────────────────────────┘ │
│                             │                                        │
│   ┌─────────────────────────▼─────────────────────────────────────┐ │
│   │                    AGENT 3: CONTROLLER                         │ │
│   │  ┌──────────────────────────────────────────────────────────┐ │ │
│   │  │ • Duplicate Detection Query:                             │ │ │
│   │  │   SELECT * FROM bills WHERE                              │ │ │
│   │  │     vendor_id = ? AND invoice_number = ?                 │ │ │
│   │  │     AND total_amount = ?                                 │ │ │
│   │  │ • Impact: Prevents double-payment fraud                  │ │ │
│   │  └──────────────────────────────────────────────────────────┘ │ │
│   └─────────────────────────┬─────────────────────────────────────┘ │
│                             │                                        │
│   ┌─────────────────────────▼─────────────────────────────────────┐ │
│   │                    AGENT 4: ACCOUNTANT                         │ │
│   │  ┌──────────────────────────────────────────────────────────┐ │ │
│   │  │ • Smart GL Code Assignment:                              │ │ │
│   │  │   1. Check vendor history (default_gl_code)              │ │ │
│   │  │   2. If unknown: LLM classification from description     │ │ │
│   │  │   3. Examples:                                           │ │ │
│   │  │      "Fuel" → 5002-Travel                                │ │ │
│   │  │      "Staples" → 5001-Office Supplies                    │ │ │
│   │  └──────────────────────────────────────────────────────────┘ │ │
│   └─────────────────────────┬─────────────────────────────────────┘ │
│                             │                                        │
│                             ▼                                        │
│                    ┌─────────────────┐                              │
│                    │   POSTGRESQL    │                              │
│                    │   (Persisted)   │                              │
│                    └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Agent Specifications

#### Agent 1: The Digitizer (OCR)

```python
class DigitizerAgent:
    """
    Converts raw bill images into structured data.
    Handles handwritten text, carbon copies, and messy layouts.
    """
    
    def __init__(self, primary_engine: str = "mistral"):
        self.primary = MistralOCR() if primary_engine == "mistral" else GPT4Vision()
        self.fallback = GPT4Vision() if primary_engine == "mistral" else MistralOCR()
    
    async def extract(self, image_bytes: bytes) -> OCRResult:
        """
        Returns:
            OCRResult containing:
            - vendor_name: str
            - invoice_number: str
            - invoice_date: date
            - line_items: List[LineItem]
            - subtotal: Decimal
            - tax_amount: Decimal
            - total: Decimal
            - bounding_boxes: Dict[str, BBox]  # For UI highlighting
            - raw_text: str
            - confidence_scores: Dict[str, float]
        """
        pass
```

#### Agent 2: The Auditor (Math & Logic)

```python
class AuditorAgent:
    """
    Validates mathematical and business logic integrity.
    Zero tolerance for errors.
    """
    
    TOLERANCE = Decimal("0.01")  # 1 cent tolerance for rounding
    
    def validate(self, bill: BillSchema) -> ValidationResult:
        errors = []
        warnings = []
        
        # Rule 1: Line items sum to subtotal
        calculated_subtotal = sum(item.total_price for item in bill.line_items)
        if abs(calculated_subtotal - bill.subtotal) > self.TOLERANCE:
            errors.append(ValidationError(
                field="subtotal",
                expected=calculated_subtotal,
                actual=bill.subtotal,
                message=f"Line items sum ({calculated_subtotal}) != Subtotal ({bill.subtotal})"
            ))
        
        # Rule 2: Subtotal + Tax = Total
        calculated_total = bill.subtotal + bill.tax_amount
        if abs(calculated_total - bill.total_amount) > self.TOLERANCE:
            errors.append(ValidationError(
                field="total_amount",
                expected=calculated_total,
                actual=bill.total_amount,
                message=f"Subtotal + Tax ({calculated_total}) != Total ({bill.total_amount})"
            ))
        
        # Rule 3: Invoice date not in future
        if bill.invoice_date > date.today():
            errors.append(ValidationError(
                field="invoice_date",
                message="Invoice date cannot be in the future"
            ))
        
        # Rule 4: Line item math
        for item in bill.line_items:
            expected = item.quantity * item.unit_price
            if abs(expected - item.total_price) > self.TOLERANCE:
                errors.append(ValidationError(
                    field=f"line_item.{item.description}",
                    message=f"Qty ({item.quantity}) × Price ({item.unit_price}) != Total ({item.total_price})"
                ))
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggested_status="APPROVED" if not errors else "NEEDS_REVIEW"
        )
```

#### Agent 3: The Controller (Duplicate Guard)

```python
class ControllerAgent:
    """
    Prevents duplicate bill entry and double-payment fraud.
    """
    
    async def check_duplicate(self, bill: BillSchema, db: AsyncSession) -> DuplicateCheckResult:
        query = select(Bill).where(
            and_(
                Bill.vendor_id == bill.vendor_id,
                Bill.invoice_number == bill.invoice_number,
                Bill.total_amount == bill.total_amount
            )
        )
        
        existing = await db.execute(query)
        duplicates = existing.scalars().all()
        
        if duplicates:
            return DuplicateCheckResult(
                is_duplicate=True,
                matching_bills=[b.id for b in duplicates],
                message="Potential duplicate detected. Manual review required."
            )
        
        return DuplicateCheckResult(is_duplicate=False)
```

#### Agent 4: The Accountant (Smart GL Coding)

```python
class AccountantAgent:
    """
    Assigns General Ledger codes using vendor history and LLM classification.
    """
    
    GL_CODE_MAPPINGS = {
        "office": "5001",
        "supplies": "5001",
        "fuel": "5002",
        "travel": "5002",
        "gas": "5002",
        "electric": "5003",
        "utility": "5003",
        "consulting": "5004",
        "legal": "5004",
        "repair": "5005",
        "maintenance": "5005",
    }
    
    async def assign_gl_codes(
        self, 
        line_items: List[LineItem], 
        vendor: Vendor,
        db: AsyncSession
    ) -> List[LineItem]:
        for item in line_items:
            # Priority 1: Vendor default
            if vendor.default_gl_code:
                item.gl_code = vendor.default_gl_code
                continue
            
            # Priority 2: Keyword matching
            description_lower = item.description.lower()
            for keyword, code in self.GL_CODE_MAPPINGS.items():
                if keyword in description_lower:
                    item.gl_code = code
                    break
            
            # Priority 3: LLM classification (if still unassigned)
            if not item.gl_code:
                item.gl_code = await self._llm_classify(item.description)
        
        return line_items
```

---

## 5. API Endpoints Specification

### 5.1 Endpoint Overview

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/api/v1/bills/upload` | Upload bill image | Required |
| GET | `/api/v1/bills/status/{task_id}` | Poll processing status | Required |
| GET | `/api/v1/bills/{bill_id}` | Get bill details | Required |
| PATCH | `/api/v1/bills/{bill_id}` | Update/approve bill | Required |
| GET | `/api/v1/bills` | List all bills | Required |
| GET | `/api/v1/vendors` | List vendors | Required |
| GET | `/api/v1/analytics/summary` | Dashboard stats | Required |

### 5.2 Detailed Specifications

#### Upload & Process

```http
POST /api/v1/bills/upload
Content-Type: multipart/form-data
Authorization: Bearer <token>

Body:
  file: <image file (JPEG/PNG/PDF)>
  vendor_hint: <optional vendor name>
```

**Response (202 Accepted):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "message": "Bill uploaded successfully. Processing started.",
  "estimated_time_seconds": 15
}
```

#### Status Polling

```http
GET /api/v1/bills/status/{task_id}
Authorization: Bearer <token>
```

**Response (Processing):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "progress": 0.65,
  "current_step": "Running Auditor Agent"
}
```

**Response (Completed):**
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "bill_id": "660e8400-e29b-41d4-a716-446655440001",
  "redirect_url": "/api/v1/bills/660e8400-e29b-41d4-a716-446655440001"
}
```

#### Validation View

```http
GET /api/v1/bills/{bill_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "vendor": {
    "id": "...",
    "name": "Staples Inc."
  },
  "invoice_number": "INV-2024-001234",
  "invoice_date": "2024-01-15",
  "due_date": "2024-02-15",
  "status": "NEEDS_REVIEW",
  "line_items": [
    {
      "id": "...",
      "description": "Printer Paper A4",
      "quantity": 10,
      "unit_price": 5.99,
      "total_price": 59.90,
      "gl_code": "5001",
      "confidence_score": 0.92
    },
    {
      "id": "...",
      "description": "Ballpoint Pens (Box)",
      "quantity": 5,
      "unit_price": 12.00,
      "total_price": 60.00,
      "gl_code": "5001",
      "confidence_score": 0.78  // ⚠️ Low confidence - highlight in red
    }
  ],
  "subtotal": 119.90,
  "tax_amount": 9.59,
  "total_amount": 129.49,
  "overall_confidence": 0.85,
  "validation_errors": [
    {
      "field": "line_items[1].total_price",
      "message": "Low confidence (78%). Please verify."
    }
  ],
  "image_url": "/storage/bills/660e8400.jpg",
  "bounding_boxes": {
    "total_amount": {"x": 450, "y": 320, "width": 80, "height": 20}
  }
}
```

#### Update/Approve Bill

```http
PATCH /api/v1/bills/{bill_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "line_items": [
    {
      "id": "...",
      "total_price": 60.00  // Corrected value
    }
  ],
  "status": "APPROVED"
}
```

**Response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "status": "APPROVED",
  "audit_log": {
    "id": "...",
    "action": "Field 'line_items[1].total_price' corrected from 59.90 to 60.00",
    "agent_name": "user@company.com",
    "timestamp": "2024-01-16T10:30:00Z"
  }
}
```

---

## 6. Frontend Specification

### 6.1 Page Components

| Component | Route | Description |
|-----------|-------|-------------|
| `Dashboard` | `/` | Stats overview, recent bills, quick actions |
| `BillUpload` | `/upload` | Drag-drop upload with preview |
| `BillReview` | `/bills/:id` | Split-view editor (image + form) |
| `BillList` | `/bills` | Searchable, filterable bill history |
| `Analytics` | `/analytics` | Charts, trends, GL breakdowns |
| `Settings` | `/settings` | User preferences, GL code management |

### 6.2 Bill Review UI Requirements

```
┌────────────────────────────────────────────────────────────────────┐
│                        BILL REVIEW - INV-2024-001234               │
├───────────────────────────────┬────────────────────────────────────┤
│                               │                                     │
│   ┌─────────────────────────┐ │  Vendor: Staples Inc.             │
│   │                         │ │  Invoice #: INV-2024-001234       │
│   │    [BILL IMAGE]         │ │  Date: January 15, 2024           │
│   │                         │ │                                    │
│   │   Highlighted regions   │ │  ┌────────────────────────────┐   │
│   │   show clickable        │ │  │ LINE ITEMS                 │   │
│   │   bounding boxes        │ │  ├────────────────────────────┤   │
│   │                         │ │  │ Printer Paper A4           │   │
│   │   [Click field on       │ │  │ Qty: 10 × $5.99 = $59.90  │   │
│   │    right to zoom to     │ │  │ GL: 5001 ✓                 │   │
│   │    that region]         │ │  ├────────────────────────────┤   │
│   │                         │ │  │ Ballpoint Pens ⚠️          │   │
│   └─────────────────────────┘ │  │ Qty: 5 × $12.00 = [$60.00]│   │
│                               │  │ GL: 5001 ✓    [VERIFY]    │   │
│   Zoom: [−] ━━━●━━━ [+]      │  └────────────────────────────┘   │
│                               │                                    │
│                               │  Subtotal: $119.90                 │
│                               │  Tax (8%): $9.59                   │
│                               │  ─────────────────                 │
│                               │  TOTAL: $129.49 ✓                  │
│                               │                                    │
│                               │  [REJECT]  [SAVE DRAFT]  [APPROVE] │
└───────────────────────────────┴────────────────────────────────────┘

Legend:
  ⚠️  = Low confidence (< 85%) - Requires human verification
  ✓  = High confidence or manually verified
  [VERIFY] = Clickable button to mark as verified
```

### 6.3 TypeScript Types

```typescript
// Core Types
interface Vendor {
  id: string;
  name: string;
  defaultGlCode?: string;
}

interface LineItem {
  id: string;
  description: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  glCode: string;
  confidenceScore: number;
  boundingBox?: BoundingBox;
}

interface Bill {
  id: string;
  vendor: Vendor;
  invoiceNumber: string;
  invoiceDate: string;
  dueDate?: string;
  lineItems: LineItem[];
  subtotal: number;
  taxAmount: number;
  totalAmount: number;
  overallConfidence: number;
  status: BillStatus;
  validationErrors: ValidationError[];
  imageUrl: string;
  createdAt: string;
}

type BillStatus = 'PROCESSING' | 'NEEDS_REVIEW' | 'APPROVED' | 'POSTED' | 'FAILED';

interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'warning';
}

interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

// API Response Types
interface TaskResponse {
  taskId: string;
  status: 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress?: number;
  billId?: string;
  error?: string;
}

interface DashboardStats {
  totalBills: number;
  pendingReview: number;
  approvedToday: number;
  totalAmount: number;
  averageConfidence: number;
  processingTime: number; // Average in seconds
}
```

---

## 7. Implementation Roadmap

### Phase 1: The "Clean" Backbone (Week 1)

**Objective:** Set up infrastructure and database.

- [ ] Initialize FastAPI project with async support
- [ ] Configure PostgreSQL with SQLAlchemy 2.0
- [ ] Implement all Pydantic models based on schema
- [ ] Create `/upload` endpoint (save to disk/S3, create DB record)
- [ ] Set up Celery + Redis for async tasks
- [ ] Implement basic health check and OpenAPI docs

**Deliverable:** API that accepts uploads and persists to database.

### Phase 2: The Vision Integration (Week 2)

**Objective:** Integrate OCR and parse bill data.

- [ ] Integrate Mistral OCR 3 API (or GPT-4o Vision)
- [ ] Build OCR response parser → structured JSON
- [ ] Map OCR output to `bills` and `line_items` tables
- [ ] Implement bounding box extraction for UI
- [ ] Add confidence score calculation
- [ ] Test with 50+ handwritten bill samples

**Deliverable:** Accurate bill digitization with >85% accuracy on printed, >75% on handwritten.

### Phase 3: The Agentic Layer (Week 3)

**Objective:** Implement all validation and intelligence agents.

- [ ] **Agent 2 (Auditor):** Math validation with $0.01 tolerance
- [ ] **Agent 3 (Controller):** Duplicate detection SQL queries
- [ ] **Agent 4 (Accountant):** GL code assignment logic
- [ ] Implement audit logging for all actions
- [ ] Add status state machine (PROCESSING → NEEDS_REVIEW/APPROVED)

**Deliverable:** Full agentic pipeline with validation and classification.

### Phase 4: The Interface (Week 4)

**Objective:** Build production-ready frontend.

- [ ] Split-view dashboard (image left, form right)
- [ ] Click-to-verify with bounding box highlighting
- [ ] Low-confidence field highlighting (red < 85%)
- [ ] Real-time status polling during processing
- [ ] Bill history with search/filter
- [ ] Export to CSV/PDF

**Deliverable:** Complete user interface for bill verification workflow.

### Phase 5: Production Hardening (Week 5)

**Objective:** Security, performance, and reliability.

- [ ] JWT authentication with refresh tokens
- [ ] Rate limiting (100 req/min per user)
- [ ] Error monitoring (Sentry integration)
- [ ] Performance optimization (DB indexing, caching)
- [ ] Load testing (target: 1000 bills/hour)
- [ ] Docker containerization
- [ ] CI/CD pipeline

**Deliverable:** Production-ready deployment.

---

## 8. Rules for AI Coding

> ⚠️ **The AI assistant must follow these rules strictly.**

### 8.1 Code Quality

- **Strict Typing:** Always use Python type hints (`def foo(bar: str) -> int:`)
- **Async First:** Use `async def` for all I/O operations
- **Pydantic Validation:** All API inputs/outputs must use Pydantic models
- **No Magic Strings:** Use Enums for status values, GL codes, etc.

### 8.2 Data Integrity

- **No Mock Data:** Connect to real PostgreSQL immediately
- **Transactions:** Use database transactions for multi-table operations
- **Decimal Precision:** Use `Decimal` for all monetary values, never `float`
- **Audit Everything:** Log all data modifications to `audit_logs`

### 8.3 Error Handling

- **Never Fail Silently:** All errors must be logged with full stack trace
- **Graceful Degradation:** If OCR fails, mark status as `FAILED` with error details
- **User-Friendly Errors:** API errors must include actionable messages

### 8.4 Security

- **No Hardcoded Secrets:** All API keys in `.env` file
- **Input Sanitization:** Validate all user inputs
- **SQL Injection Prevention:** Use parameterized queries only
- **CORS Restrictions:** Whitelist specific origins in production

### 8.5 Documentation

- **Docstrings:** All public functions must have docstrings
- **API Docs:** FastAPI auto-generates OpenAPI, keep it current
- **README:** Update with any new setup steps

---

## 9. Performance Specifications

### 9.1 Target Metrics

| Metric | Target | Critical |
|--------|--------|----------|
| OCR Processing Time | < 10 seconds | < 30 seconds |
| API Response (non-OCR) | < 200ms | < 500ms |
| Database Query Time | < 50ms | < 200ms |
| Frontend Load Time | < 2 seconds | < 5 seconds |
| OCR Accuracy (printed) | > 95% | > 85% |
| OCR Accuracy (handwritten) | > 85% | > 75% |
| Math Validation Accuracy | 100% | 100% |
| Concurrent Users | 100 | 50 |
| Bills Processed/Hour | 1000 | 500 |

### 9.2 Scalability Architecture

```
                    ┌─────────────────┐
                    │   Load Balancer │
                    │     (nginx)     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   FastAPI     │   │   FastAPI     │   │   FastAPI     │
│   Instance 1  │   │   Instance 2  │   │   Instance 3  │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                    ┌───────▼───────┐
                    │    Redis      │
                    │   (Broker)    │
                    └───────┬───────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Celery Worker │   │ Celery Worker │   │ Celery Worker │
│      1        │   │      2        │   │      3        │
└───────────────┘   └───────────────┘   └───────────────┘
                            │
                    ┌───────▼───────┐
                    │  PostgreSQL   │
                    │   (Primary)   │
                    └───────────────┘
```

---

## 10. Security Considerations

### 10.1 Authentication & Authorization

```python
# JWT Token Structure
{
  "sub": "user_id",
  "email": "user@company.com",
  "role": "accountant",  # admin, accountant, viewer
  "permissions": ["bills:read", "bills:write", "bills:approve"],
  "exp": 1234567890,
  "iat": 1234567800
}
```

### 10.2 Role-Based Access Control

| Role | Permissions |
|------|-------------|
| Viewer | Read bills, view analytics |
| Accountant | Read, write, correct bills |
| Approver | All above + approve/post bills |
| Admin | All above + manage users, settings |

### 10.3 Data Protection

- **Encryption at Rest:** Database encryption enabled
- **Encryption in Transit:** TLS 1.3 required
- **PII Handling:** Vendor names/addresses treated as PII
- **Retention Policy:** Bills retained for 7 years (configurable)

---

## 11. File Structure

```
billagent-pro/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Settings from .env
│   │   ├── database.py             # SQLAlchemy async setup
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py             # Dependency injection
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── bills.py        # Bill endpoints
│   │   │   │   ├── vendors.py      # Vendor endpoints
│   │   │   │   ├── analytics.py    # Analytics endpoints
│   │   │   │   └── auth.py         # Authentication
│   │   │
│   │   ├── models/                 # SQLAlchemy models
│   │   │   ├── __init__.py
│   │   │   ├── bill.py
│   │   │   ├── vendor.py
│   │   │   ├── line_item.py
│   │   │   └── audit_log.py
│   │   │
│   │   ├── schemas/                # Pydantic schemas
│   │   │   ├── __init__.py
│   │   │   ├── bill.py
│   │   │   ├── vendor.py
│   │   │   └── common.py
│   │   │
│   │   ├── agents/                 # Agentic AI Pipeline
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base agent class
│   │   │   ├── digitizer.py        # Agent 1: OCR
│   │   │   ├── auditor.py          # Agent 2: Math validation
│   │   │   ├── controller.py       # Agent 3: Duplicate detection
│   │   │   └── accountant.py       # Agent 4: GL coding
│   │   │
│   │   ├── services/               # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── ocr_service.py      # OCR integration
│   │   │   ├── bill_service.py     # Bill CRUD
│   │   │   └── audit_service.py    # Audit logging
│   │   │
│   │   └── tasks/                  # Celery tasks
│   │       ├── __init__.py
│   │       └── process_bill.py     # Async bill processing
│   │
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_agents/
│   │   ├── test_api/
│   │   └── test_services/
│   │
│   ├── alembic/                    # Database migrations
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── BillUpload.tsx
│   │   │   ├── BillReview.tsx
│   │   │   ├── BillList.tsx
│   │   │   └── ui/                 # ShadcnUI components
│   │   │
│   │   ├── hooks/
│   │   │   ├── useBills.ts
│   │   │   ├── usePolling.ts
│   │   │   └── useAuth.ts
│   │   │
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   └── auth.ts
│   │   │
│   │   ├── types/
│   │   │   └── index.ts
│   │   │
│   │   ├── App.tsx
│   │   └── main.tsx
│   │
│   ├── package.json
│   ├── tailwind.config.js
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── .env.example
├── .gitignore
├── README.md
├── SPEC.md                         # This file
└── Makefile                        # Common commands
```

---

## 12. Appendix

### 12.1 Sample OCR Response (Mistral)

```json
{
  "document": {
    "vendor_name": "Staples Office Supplies",
    "invoice_number": "INV-2024-001234",
    "invoice_date": "2024-01-15",
    "due_date": "2024-02-15",
    "line_items": [
      {
        "description": "Printer Paper A4 (500 sheets)",
        "quantity": 10,
        "unit_price": 5.99,
        "total": 59.90,
        "bounding_box": {"x": 50, "y": 150, "w": 400, "h": 20}
      }
    ],
    "subtotal": 119.90,
    "tax_rate": 0.08,
    "tax_amount": 9.59,
    "total": 129.49
  },
  "confidence": {
    "overall": 0.91,
    "fields": {
      "vendor_name": 0.95,
      "invoice_number": 0.88,
      "total": 0.94
    }
  }
}
```

### 12.2 Common GL Codes Reference

| Code | Name | Category |
|------|------|----------|
| 5001 | Office Supplies | EXPENSE |
| 5002 | Travel & Transportation | EXPENSE |
| 5003 | Utilities | EXPENSE |
| 5004 | Professional Services | EXPENSE |
| 5005 | Maintenance & Repairs | EXPENSE |
| 5006 | Raw Materials | EXPENSE |
| 5007 | Inventory Purchases | EXPENSE |
| 5008 | Marketing & Advertising | EXPENSE |
| 5009 | Insurance | EXPENSE |
| 5010 | Rent & Lease | EXPENSE |

### 12.3 Error Codes Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| BILL_NOT_FOUND | 404 | Bill ID does not exist |
| INVALID_FILE_TYPE | 400 | Only JPEG, PNG, PDF accepted |
| FILE_TOO_LARGE | 413 | Max file size is 10MB |
| OCR_FAILED | 500 | OCR engine could not process |
| DUPLICATE_DETECTED | 409 | Bill already exists |
| VALIDATION_FAILED | 422 | Math/logic validation failed |
| UNAUTHORIZED | 401 | Invalid or expired token |
| FORBIDDEN | 403 | Insufficient permissions |

---

*This specification is the single source of truth for BillAgent Pro. All development must conform to this document. Update this file when making architectural changes.*

**Last Updated:** February 2026  
**Maintainer:** BillAgent Pro Team
