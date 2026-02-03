
export enum Page {
  Dashboard = 'dashboard',
  Process = 'process',
  History = 'history',
  Analytics = 'analytics',
  Settings = 'settings',
  Upgrade = 'upgrade',
  Profile = 'profile',
  Login = 'login',
  BillReview = 'billReview'
}

// User roles for RBAC
export enum UserRole {
  VIEWER = 'viewer',
  ACCOUNTANT = 'accountant',
  APPROVER = 'approver',
  ADMIN = 'admin'
}

// User type for authentication
export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: UserRole;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
  updated_at: string;
  last_login: string | null;
}

// Bounding box for OCR field highlighting
export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

// Validation error from backend
export interface ValidationError {
  field: string;
  message: string;
  severity: 'error' | 'warning';
  suggestedValue?: string;
}

// Vendor information
export interface Vendor {
  id: string;
  name: string;
  address?: string;
  taxId?: string;
  email?: string;
  phone?: string;
}

// GL Code for accounting
export interface GLCode {
  id: string;
  code: string;
  description: string;
  category: string;
}

export interface BillItem {
  id?: string;
  name: string;
  description?: string;
  quantity: number;
  unitPrice?: number;
  price: number;
  total: number;
  confidence: number;
  boundingBox?: BoundingBox;
  glCode?: GLCode;
  isVerified?: boolean;
}

export interface AgentReport {
  agentName: string;
  verdict: 'OK' | 'WARNING' | 'CRITICAL';
  reasoning: string;
  timestamp?: string;
}

export interface BusinessInsight {
  type: 'TREND' | 'ALERT' | 'RECOMMENDATION' | 'STORY';
  title: string;
  content: string;
  impact: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
  actionable?: string;
}

// Bill status enum for better type safety
export type BillStatus = 'PROCESSING' | 'NEEDS_REVIEW' | 'APPROVED' | 'POSTED' | 'FAILED' | 'PENDING' | 'VERIFIED' | 'FLAGGED';

export interface Bill {
  id: string;
  date: string;
  imageUrl: string;
  items: BillItem[];
  grandTotal: number;
  status: BillStatus;
  overallConfidence: number;
  agents: AgentReport[];
  vendorName?: string;
  vendor?: Vendor;
  invoiceNumber?: string;
  invoiceDate?: string;
  dueDate?: string;
  validationErrors?: ValidationError[];
  taskId?: string;
  processingProgress?: number;
  notes?: string;
  createdAt?: string;
  updatedAt?: string;
}

// Task status for polling
export interface TaskStatus {
  taskId: string;
  status: 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
  progress: number;
  message?: string;
  result?: Bill;
  error?: string;
}

// API response types
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// Filter options for bill history
export interface BillFilters {
  status?: BillStatus[];
  vendorId?: string;
  invoiceNumber?: string;
  dateFrom?: string;
  dateTo?: string;
  minAmount?: number;
  maxAmount?: number;
  searchQuery?: string;
}

export interface DashboardStats {
  totalProcessed: number;
  todaySales: number;
  errorRate: number;
  accuracyTrend: number;
  pendingReviewCount?: number;
  processingCount?: number;
  approvedToday?: number;
}
