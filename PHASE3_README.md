# Phase 3: Agentic Pipeline - Implementation Summary

**BillAgent Pro** - AI-Powered Bill Processing Pipeline  
**Phase**: 3 of 7  
**Status**: ✅ Complete  
**Last Updated**: 3 February 2026

---

## 📋 Overview

Phase 3 implements the complete agentic pipeline for bill processing with:

- **AuditorAgent** - Strict validation with 100% math accuracy
- **ControllerAgent** - Duplicate detection and deduplication
- **AccountantAgent** - GL code assignment with learning capability
- **BillProcessingService** - Full pipeline orchestration

All monetary calculations use `Decimal` precision to ensure accurate financial validation.

---

## 🏗️ Architecture

### Agent Pipeline Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Bill Processing Pipeline                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Stage 1: DIGITIZATION (DigitizerAgent)                                 │
│  • OCR extraction with Mistral + GPT-4o fallback                        │
│  • Extract vendor, invoice #, dates, line items                         │
│  • Generate confidence scores and bounding boxes                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Save to Database (status = PROCESSING)                                 │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Stage 2: VALIDATION (AuditorAgent)                                     │
│  • Rule 1: Line items sum = Subtotal                                    │
│  • Rule 2: Subtotal + Tax = Total                                       │
│  • Rule 3: Date validation (reasonable range)                           │
│  • Rule 4: Line item math (qty × price = total)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Stage 3: DUPLICATE CHECK (ControllerAgent)                             │
│  • Check vendor + invoice number + amount                               │
│  • Score potential duplicates (0.0 - 1.0)                               │
│  • Flag high-confidence duplicates                                      │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Stage 4: GL ASSIGNMENT (AccountantAgent)                               │
│  • Priority 1: Vendor default GL code                                   │
│  • Priority 2: Vendor history lookup                                    │
│  • Priority 3: Keyword matching (13 categories)                         │
│  • Priority 4: LLM classification (OpenAI)                              │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Final Status Determination                                             │
│  • APPROVED - All validations passed                                    │
│  • NEEDS_REVIEW - Validation errors or low confidence                   │
│  • DUPLICATE - High-confidence duplicate found                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 New File Structure

```
backend/
├── agents/
│   ├── __init__.py              # Updated with all agent exports
│   ├── digitizer.py             # Agent 1: OCR extraction (Phase 2)
│   ├── auditor.py               # Agent 2: Validation (NEW)
│   ├── controller.py            # Agent 3: Duplicate detection (NEW)
│   ├── accountant.py            # Agent 4: GL code assignment (NEW)
│   ├── error_agent.py           # Legacy (kept for compatibility)
│   ├── confidence_agent.py      # Confidence scoring
│   ├── learning_agent.py        # Pattern learning
│   └── workflow_agent.py        # Workflow orchestration
├── app/
│   └── services/
│       ├── __init__.py          # Updated with BillProcessingService
│       ├── bill_service.py      # Pipeline orchestration (NEW)
│       └── ocr/                  # OCR services (Phase 2)
```

---

## 🔍 Agent Details

### Agent 2: AuditorAgent (`backend/agents/auditor.py`)

The Auditor validates bill data with strict mathematical checks using `Decimal` precision.

#### Validation Rules

| Rule | Description | Tolerance |
|------|-------------|-----------|
| Rule 1 | Sum of line item totals = Subtotal | ±$0.01 |
| Rule 2 | Subtotal + Tax = Total | ±$0.01 |
| Rule 3 | Invoice date within 2 years past / 7 days future | N/A |
| Rule 3 | Due date ≥ Invoice date | N/A |
| Rule 4 | Qty × Unit Price = Line Total (per item) | ±$0.01 |

#### Usage

```python
from agents.auditor import AuditorAgent

auditor = AuditorAgent(tolerance=Decimal("0.01"))

result = auditor.validate({
    "subtotal": Decimal("100.00"),
    "tax_amount": Decimal("10.00"),
    "total_amount": Decimal("110.00"),
    "invoice_date": date(2026, 1, 15),
    "due_date": date(2026, 2, 15),
    "line_items": [
        {"description": "Widget A", "quantity": 2, "unit_price": 25.00, "total_price": 50.00},
        {"description": "Widget B", "quantity": 1, "unit_price": 50.00, "total_price": 50.00},
    ]
})

if result.is_valid:
    print("✓ All validations passed")
else:
    for error in result.errors:
        print(f"✗ {error.field}: {error.message}")
```

#### Output: ValidationResult

```python
@dataclass
class ValidationResult:
    is_valid: bool                    # True if no errors
    errors: List[ValidationError]     # List of errors
    warnings: List[ValidationError]   # List of warnings
    suggested_status: str             # "APPROVED" or "NEEDS_REVIEW"
    validation_summary: Dict          # Summary statistics
```

---

### Agent 3: ControllerAgent (`backend/agents/controller.py`)

The Controller detects duplicate bills using multi-criteria matching with confidence scoring.

#### Duplicate Detection Criteria

| Match Type | Criteria | Score |
|------------|----------|-------|
| Exact Match | Vendor + Invoice # + Amount | 1.00 |
| High Confidence | Vendor + Invoice # | 0.85 |
| Medium Confidence | Vendor + Amount (within 30 days) | 0.60 |
| Low Confidence | Invoice # + Amount | 0.50 |

#### Thresholds

| Threshold | Score | Action |
|-----------|-------|--------|
| Duplicate | ≥ 0.80 | Mark as DUPLICATE |
| Review | ≥ 0.50 | Mark as NEEDS_REVIEW |
| Clear | < 0.50 | Proceed normally |

#### Usage

```python
from agents.controller import ControllerAgent

controller = ControllerAgent(
    amount_tolerance=Decimal("0.01"),
    duplicate_threshold=0.8,
    review_threshold=0.5,
)

result = await controller.check_duplicate(
    bill_data={
        "vendor_id": vendor_uuid,
        "invoice_number": "INV-001",
        "total_amount": Decimal("500.00"),
        "invoice_date": date(2026, 1, 15),
    },
    db=db_session,
    exclude_bill_id=current_bill_id,  # Exclude self
)

if result.is_duplicate:
    print(f"⚠ Duplicate found: {result.potential_duplicates[0].bill_id}")
    print(f"  Match score: {result.highest_match_score:.0%}")
```

#### Output: DuplicateCheckResult

```python
@dataclass
class DuplicateCheckResult:
    is_duplicate: bool                        # True if score >= 0.8
    potential_duplicates: List[DuplicateMatch]  # Matching bills
    highest_match_score: float                # 0.0 to 1.0
    suggested_status: str                     # "DUPLICATE", "NEEDS_REVIEW", "APPROVED"
    message: str                              # Human-readable message
```

---

### Agent 4: AccountantAgent (`backend/agents/accountant.py`)

The Accountant assigns GL codes to line items using a priority-based approach.

#### GL Code Assignment Priority

1. **Vendor Default** (confidence: 0.95) - Use vendor's default GL code
2. **Vendor History** (confidence: 0.90) - Learn from past approved bills
3. **Keyword Match** (confidence: 0.50-0.90) - Match description to keywords
4. **LLM Classification** (confidence: 0.75) - Use OpenAI for unknown items
5. **Default** (confidence: 0.30) - Fallback to "5099 - Miscellaneous"

#### Pre-configured GL Codes

| Code | Category | Keywords |
|------|----------|----------|
| 5001 | Office Supplies | office, paper, pen, stationery, printer, ink |
| 5002 | Travel & Transportation | travel, fuel, taxi, uber, flight, parking |
| 5003 | Utilities | electric, water, internet, phone, broadband |
| 5004 | Professional Services | consulting, legal, accounting, audit |
| 5005 | Maintenance & Repairs | maintenance, repair, cleaning, plumbing |
| 5006 | Raw Materials | raw, material, ingredient, component |
| 5007 | Inventory Purchases | inventory, stock, goods, merchandise |
| 5008 | Marketing & Advertising | marketing, advertising, promotion, media |
| 5009 | Insurance | insurance, premium, coverage, policy |
| 5010 | Rent & Lease | rent, lease, rental, property, warehouse |
| 5011 | Equipment | equipment, machine, computer, furniture |
| 5012 | Software & Subscriptions | software, license, saas, cloud, hosting |
| 5099 | Miscellaneous | misc, other, general, sundry |

#### Usage

```python
from agents.accountant import AccountantAgent

accountant = AccountantAgent(
    use_llm_fallback=True,
    default_gl_code="5099",
)

result = await accountant.assign_gl_codes(
    line_items=[
        {"description": "HP Printer Ink Cartridge", "gl_code": None},
        {"description": "Uber ride to airport", "gl_code": None},
        {"description": "Custom widget XYZ-123", "gl_code": None},
    ],
    vendor_id=vendor_uuid,
    db=db_session,
)

for assignment in result.assignments:
    print(f"{assignment.description}: {assignment.gl_code} ({assignment.source.value})")
# Output:
# HP Printer Ink Cartridge: 5001 (keyword)
# Uber ride to airport: 5002 (keyword)
# Custom widget XYZ-123: 5099 (default)
```

#### Learning from Corrections

```python
# When user manually corrects a GL code, the agent learns
await accountant.learn_from_correction(
    vendor_id=vendor_uuid,
    old_gl_code="5099",
    new_gl_code="5006",
    db=db_session,
)
# After 3+ corrections to same GL code, it becomes the vendor default
```

---

### Pipeline Orchestration: BillProcessingService (`backend/app/services/bill_service.py`)

The service chains all agents and manages the complete workflow.

#### Pipeline Stages

| Stage | Agent | Action |
|-------|-------|--------|
| 1 | DigitizerAgent | OCR extraction from image |
| 2 | - | Save bill to DB (status=PROCESSING) |
| 3 | AuditorAgent | Validate math and business rules |
| 4 | ControllerAgent | Check for duplicates |
| 5 | AccountantAgent | Assign GL codes |
| 6 | - | Determine final status |
| 7 | - | Create audit logs |

#### Usage

```python
from app.services.bill_service import BillProcessingService

service = BillProcessingService()

result = await service.process_bill(
    image_bytes=image_data,
    image_url="/uploads/bill_001.jpg",
    db=db_session,
    user_id="user_123",
    task_id="celery_task_456",
)

print(f"Bill ID: {result.bill_id}")
print(f"Status: {result.status}")
print(f"Processing time: {result.total_processing_time_ms}ms")
print(f"Stages completed: {result.stages_completed}")

if result.errors:
    for error in result.errors:
        print(f"  ✗ {error['field']}: {error['message']}")
```

#### Reprocessing Bills

```python
# Reprocess after manual corrections (skips OCR)
result = await service.reprocess_bill(
    bill_id=bill_uuid,
    db=db_session,
    skip_digitization=True,
)
```

#### Output: ProcessingResult

```python
@dataclass
class ProcessingResult:
    bill_id: Optional[UUID]           # Created bill ID
    status: str                       # Final status
    stages_completed: List[str]       # ["digitization", "validation", ...]
    stage_results: List[ProcessingStepResult]  # Detailed results per stage
    total_processing_time_ms: int     # Total time
    errors: List[Dict]                # All errors
    warnings: List[Dict]              # All warnings
```

---

## 🔌 Module Exports

### agents/__init__.py

```python
from .digitizer import DigitizerAgent, DigitizationResult, DigitizationStatus
from .auditor import AuditorAgent, ValidationResult, ValidationError, ValidationSeverity
from .controller import ControllerAgent, DuplicateCheckResult, DuplicateMatch
from .accountant import AccountantAgent, AccountantResult, GLCodeAssignment, GLCodeSource
```

### app/services/__init__.py

```python
from .bill_service import (
    BillProcessingService,
    ProcessingResult,
    ProcessingStage,
    ProcessingStepResult,
)
```

---

## ✅ Tasks Completed

### 3.1 AuditorAgent
- [x] Use `Decimal` for all monetary calculations
- [x] Implement Rule 1: Line items sum check
- [x] Implement Rule 2: Subtotal + Tax = Total
- [x] Implement Rule 3: Date validation
- [x] Implement Rule 4: Line item math
- [x] Generate specific error messages with field names
- [x] Return structured ValidationResult with errors/warnings

### 3.2 ControllerAgent
- [x] Write duplicate detection SQL queries
- [x] Check vendor + invoice_number + total_amount
- [x] Score potential duplicates (0.0 - 1.0)
- [x] Return list of potential duplicates with IDs
- [x] Mark high-confidence matches as DUPLICATE

### 3.3 AccountantAgent
- [x] Implement vendor default GL code lookup
- [x] Add vendor history lookup (learn from past)
- [x] Implement keyword-based GL code mapping
- [x] Integrate OpenAI for unknown items
- [x] Update line items with assigned GL codes
- [x] Learn from manual corrections

### 3.4 Pipeline Orchestration
- [x] Chain all 4 agents in sequence
- [x] Handle errors at each stage
- [x] Update bill status based on agent results
- [x] Create audit log entries for each step
- [x] Implement reprocess_bill() for corrections

---

## 🧪 Testing

```bash
# Run all tests
cd backend
pytest tests/ -v

# Test specific agent
pytest tests/test_auditor.py -v
pytest tests/test_controller.py -v
pytest tests/test_accountant.py -v
```

---

## 📊 Deliverables

| Deliverable | Status |
|-------------|--------|
| AuditorAgent with 4 validation rules | ✅ Complete |
| ControllerAgent with duplicate detection | ✅ Complete |
| AccountantAgent with GL code assignment | ✅ Complete |
| BillProcessingService orchestration | ✅ Complete |
| 100% math validation with Decimal | ✅ Complete |
| Audit logging for each stage | ✅ Complete |

---

## 🔜 Next Steps (Phase 4)

Phase 4 will implement:
- REST API endpoints for bill processing
- Background task processing with Celery
- Webhook notifications for status changes
- Batch bill upload support
