# Phase 5: Frontend Upgrade - Split-View Editor with Bounding Box Highlighting

## Overview

Phase 5 focuses on building a production-ready UI with a split-view editor that enables click-to-verify workflows. This phase introduces interactive bill review capabilities with bounding box highlighting, confidence indicators, and a comprehensive API integration layer.

## Timeline
**Week 4** - Frontend Upgrade

## Goals
- Build split-view editor with bounding box highlighting
- Create reusable UI component library
- Implement real-time status polling
- Add bill filtering and search capabilities
- Enable click-to-verify workflow

---

## 5.1 TypeScript Types

### File Modified
- `types.ts`

### New Types Added

```typescript
// Bounding box for OCR field highlighting
interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

// Validation error from backend
interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'warning';
  suggestedValue?: string;
}

// Vendor information
interface Vendor {
  id: string;
  name: string;
  address?: string;
  taxId?: string;
  email?: string;
  phone?: string;
}

// GL Code for accounting
interface GLCode {
  id: string;
  code: string;
  description: string;
  category: string;
}

// Bill status enum
type BillStatus = 'PROCESSING' | 'NEEDS_REVIEW' | 'APPROVED' | 'POSTED' | 'FAILED' | 'PENDING' | 'VERIFIED' | 'FLAGGED';

// Task status for polling
interface TaskStatus {
  taskId: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress: number;
  message?: string;
  result?: Bill;
  error?: string;
}

// Filter options for bill history
interface BillFilters {
  status?: BillStatus[];
  vendorId?: string;
  invoiceNumber?: string;
  dateFrom?: string;
  dateTo?: string;
  minAmount?: number;
  maxAmount?: number;
  searchQuery?: string;
}
```

### Extended Interfaces

```typescript
interface BillItem {
  // ... existing fields
  boundingBox?: BoundingBox;
  glCode?: GLCode;
  isVerified?: boolean;
}

interface Bill {
  // ... existing fields
  vendor?: Vendor;
  invoiceNumber?: string;
  invoiceDate?: string;
  dueDate?: string;
  validationErrors?: ValidationError[];
  taskId?: string;
  processingProgress?: number;
}
```

---

## 5.2 New UI Components

### Directory Structure
```
components/
└── ui/
    ├── index.ts          # Barrel export
    ├── button.tsx        # Reusable button component
    ├── input.tsx         # Input with confidence indicators
    ├── card.tsx          # Card components
    └── badge.tsx         # Badge & status indicators
```

### Button Component (`button.tsx`)

**Features:**
- Multiple variants: `default`, `primary`, `secondary`, `outline`, `ghost`, `danger`, `success`
- Size options: `sm`, `md`, `lg`, `icon`
- Loading state with spinner
- Left/right icon support

**Usage:**
```tsx
import { Button } from './ui/button';

<Button variant="primary" size="md" isLoading={false}>
  Save Changes
</Button>

<Button variant="danger" leftIcon={<Trash2 size={16} />}>
  Delete
</Button>
```

### Input Component (`input.tsx`)

**Features:**
- Label with optional confidence indicator
- Error/hint text display
- Left/right icon slots
- Low confidence highlighting (< 85% shows red border)

**Usage:**
```tsx
import { Input } from './ui/input';

<Input 
  label="Vendor Name"
  confidence={78}
  error="Invalid vendor"
  leftIcon={<Search size={18} />}
/>
```

### Card Component (`card.tsx`)

**Features:**
- Variants: `default`, `glass`, `matte`, `elevated`
- Padding options: `none`, `sm`, `md`, `lg`
- Hoverable option
- Sub-components: `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`

**Usage:**
```tsx
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';

<Card variant="glass" padding="lg" hoverable>
  <CardHeader>
    <CardTitle>Bill Summary</CardTitle>
  </CardHeader>
  <CardContent>
    {/* content */}
  </CardContent>
</Card>
```

### Badge Component (`badge.tsx`)

**Features:**
- Variants: `default`, `success`, `warning`, `danger`, `info`, `confidence`
- Size options: `sm`, `md`, `lg`
- Specialized badges: `ConfidenceBadge`, `StatusBadge`

**Usage:**
```tsx
import { Badge, ConfidenceBadge, StatusBadge } from './ui/badge';

<Badge variant="warning">Needs Review</Badge>
<ConfidenceBadge value={85} showIcon />
<StatusBadge status="APPROVED" />
```

---

## 5.3 Core Components

### ImageViewer (`ImageViewer.tsx`)

**Purpose:** Left panel of split-view editor displaying bill image with interactive bounding boxes.

**Features:**
- ✅ Zoom in/out controls (25% increments, 0.5x - 4x range)
- ✅ Rotate image (90° increments)
- ✅ Pan/drag navigation
- ✅ Mouse wheel zoom
- ✅ Reset view button
- ✅ Download image
- ✅ Bounding box overlays with confidence-based colors
  - Green: ≥85% confidence
  - Yellow: 70-84% confidence
  - Red: <70% confidence
- ✅ Click bounding box to select item
- ✅ Auto-zoom to selected bounding box
- ✅ Legend showing confidence levels

**Props:**
```typescript
interface ImageViewerProps {
  imageUrl: string;
  items: BillItem[];
  selectedItemIndex?: number | null;
  onItemClick?: (index: number) => void;
  className?: string;
}
```

### BillForm (`BillForm.tsx`)

**Purpose:** Right panel of split-view editor with editable form fields.

**Features:**
- ✅ Collapsible sections (Vendor, Items, Summary, Validation)
- ✅ Validation errors banner
- ✅ Vendor information editing
- ✅ Line items with:
  - Confidence badges per field
  - Low confidence highlighting (<85%)
  - Edit/verify/delete actions
  - Auto-calculate totals
- ✅ Add new line items
- ✅ Grand total calculation
- ✅ Notes field
- ✅ Edit/Cancel/Save workflow
- ✅ Approve/Reject actions

**Props:**
```typescript
interface BillFormProps {
  bill: Bill;
  onUpdate: (bill: Bill) => void;
  onApprove: () => void;
  onReject?: () => void;
  selectedItemIndex?: number | null;
  onItemSelect?: (index: number | null) => void;
  isLoading?: boolean;
  className?: string;
}
```

### BillReview (`BillReview.tsx`)

**Purpose:** Main split-view editor component combining ImageViewer and BillForm.

**Features:**
- ✅ 2-column resizable layout
- ✅ Draggable resize handle
- ✅ Fullscreen image mode
- ✅ Header with status badge and review count
- ✅ Error banner with dismiss
- ✅ Loading/error states
- ✅ Auto-fetch bill data if not provided
- ✅ Synchronized item selection between panels
- ✅ Navigation back to history

**Props:**
```typescript
interface BillReviewProps {
  billId?: string;
  bill?: Bill;
  onNavigate: (page: Page) => void;
  onBillUpdate?: (bill: Bill) => void;
}
```

---

## 5.4 API Integration

### File Created
- `services/api.ts`

### API Client Features

```typescript
// Centralized API client with:
// - Configurable base URL (via VITE_API_URL env var)
// - 30 second timeout
// - Automatic retry (3 attempts with exponential backoff)
// - Error handling for 4xx/5xx responses

const client = new ApiClient(API_BASE_URL);
```

### Available Methods

```typescript
export const api = {
  // Bill Operations
  uploadBill(file: File): Promise<ApiResponse<{ taskId: string }>>,
  getTaskStatus(taskId: string): Promise<ApiResponse<TaskStatus>>,
  getBill(billId: string): Promise<ApiResponse<Bill>>,
  getBills(filters?, page?, pageSize?): Promise<ApiResponse<PaginatedResponse<Bill>>>,
  updateBill(billId: string, bill: Partial<Bill>): Promise<ApiResponse<Bill>>,
  deleteBill(billId: string): Promise<ApiResponse<void>>,
  approveBill(billId: string): Promise<ApiResponse<Bill>>,
  rejectBill(billId: string, reason?: string): Promise<ApiResponse<Bill>>,
  
  // Vendor Operations
  getVendors(): Promise<ApiResponse<Vendor[]>>,
  
  // Stats
  getDashboardStats(): Promise<ApiResponse<DashboardStats>>,
  
  // Health
  healthCheck(): Promise<ApiResponse<{ status: string }>>,
};
```

### Polling Hook

```typescript
function usePolling(
  taskId: string | null,
  onComplete: (bill: Bill) => void,
  onError: (error: string) => void,
  options?: {
    interval?: number;      // Default: 2000ms
    maxAttempts?: number;   // Default: 60
  }
): {
  status: TaskStatus | null;
  isPolling: boolean;
  progress: number;
  message: string;
  startPolling: () => void;
  stopPolling: () => void;
}
```

---

## 5.5 Updated Components

### BillUpload Enhancements

**New Features:**
- ✅ Toggle between local and backend processing
- ✅ Progress bar during backend processing
- ✅ Real-time status message updates
- ✅ Cancel processing button
- ✅ Error display with details

**New Props:**
```typescript
interface BillUploadProps {
  onComplete: (bill: Bill) => void;
  useBackendProcessing?: boolean; // Toggle processing mode
}
```

### Dashboard Enhancements

**New Features:**
- ✅ "Pending Review" stat card with count
- ✅ Average confidence display
- ✅ Pending Review section showing bills needing attention
- ✅ Click-to-review functionality
- ✅ Bill preview cards with status badges

**New Props:**
```typescript
interface DashboardProps {
  bills: Bill[];
  onNavigate: (page: Page) => void;
  onSelectBill?: (billId: string) => void; // NEW
}
```

### BillHistory Enhancements

**New Features:**
- ✅ Search by vendor, invoice number, or item names
- ✅ Multi-select status filter
- ✅ Date range filter (from/to)
- ✅ Filter count badge
- ✅ Clear all filters button
- ✅ Results count and summary
- ✅ View/Delete actions with callbacks
- ✅ Confidence badges in table

**New Props:**
```typescript
interface BillHistoryProps {
  bills: Bill[];
  onViewBill?: (billId: string) => void;   // NEW
  onDeleteBill?: (billId: string) => void; // NEW
}
```

---

## 5.6 App Integration

### Updated App.tsx

**New State:**
```typescript
const [selectedBillId, setSelectedBillId] = useState<string | null>(null);
```

**New Handlers:**
```typescript
const handleBillUpdate = (updatedBill: Bill) => { /* ... */ };
const handleSelectBill = (billId: string) => { /* ... */ };
const handleDeleteBill = (billId: string) => { /* ... */ };
```

**New Route:**
```typescript
case Page.BillReview:
  return (
    <BillReview
      billId={selectedBillId}
      bill={selectedBill}
      onNavigate={setCurrentPage}
      onBillUpdate={handleBillUpdate}
    />
  );
```

---

## User Workflows

### 1. Bill Review Workflow
```
Dashboard → Click "Needs Review" bill → BillReview Page
                                              ↓
                              ImageViewer ←→ BillForm
                                   ↓              ↓
                            Click bounding   Edit fields
                               box           with low
                                   ↓        confidence
                              Zoom to            ↓
                              region        Verify/Save
                                                 ↓
                                            Approve/Reject
```

### 2. Filtering Workflow
```
History Page → Open Filters Panel
                     ↓
              Enter search query
              Select status filters
              Set date range
                     ↓
              View filtered results
                     ↓
              Clear filters or Export
```

### 3. Processing Workflow (Backend Mode)
```
Upload Image → API Upload → Get Task ID
                                 ↓
                          Start Polling
                                 ↓
                    ┌────────────┴────────────┐
                    ↓                         ↓
              Progress Updates           Completion
              (2s intervals)                  ↓
                    ↓                    Review Page
              Cancel Option
```

---

## Configuration

### Environment Variables

```env
# Backend API URL (defaults to http://localhost:8000)
VITE_API_URL=http://localhost:8000
```

### Theming

The UI components use the existing theme system with CSS classes:
- `glass-card` - Glassmorphism effect
- `matte-card` - Matte finish
- `tap-effect` - Touch/click feedback
- `gem-button` - Gradient button style

---

## Testing Checklist

### UI Components
- [ ] Button renders all variants correctly
- [ ] Input shows confidence indicator
- [ ] Card variants display properly
- [ ] Badge colors match status

### ImageViewer
- [ ] Image loads and displays
- [ ] Zoom controls work (scroll & buttons)
- [ ] Pan/drag works smoothly
- [ ] Bounding boxes render at correct positions
- [ ] Clicking box selects item
- [ ] Auto-zoom to selected item works

### BillForm
- [ ] All sections expand/collapse
- [ ] Fields are editable in edit mode
- [ ] Low confidence fields highlighted
- [ ] Totals recalculate on changes
- [ ] Save/Cancel work correctly
- [ ] Approve/Reject call correct APIs

### BillReview
- [ ] Split view renders correctly
- [ ] Resize handle works
- [ ] Selection syncs between panels
- [ ] Fullscreen mode works
- [ ] Navigation works

### API Integration
- [ ] Upload returns task ID
- [ ] Polling updates progress
- [ ] Completion triggers callback
- [ ] Errors display correctly
- [ ] Retry logic works

### Filters
- [ ] Search filters correctly
- [ ] Status filter works
- [ ] Date range filter works
- [ ] Clear filters resets all
- [ ] Results count updates

---

## Deliverables

✅ Production-ready UI with split-view editor  
✅ Click-to-verify workflow  
✅ Bounding box highlighting with confidence colors  
✅ Reusable UI component library  
✅ Centralized API client with retry logic  
✅ Real-time polling for processing status  
✅ Advanced filtering and search  
✅ Full TypeScript type coverage  

---

## Next Steps (Phase 6)

- Backend API implementation for all endpoints
- WebSocket support for real-time updates
- Batch processing UI
- Export reports (PDF, detailed Excel)
- User preferences storage
- Keyboard shortcuts for power users
