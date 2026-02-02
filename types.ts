
export enum Page {
  Dashboard = 'dashboard',
  Process = 'process',
  History = 'history',
  Analytics = 'analytics',
  Settings = 'settings',
  Upgrade = 'upgrade',
  Profile = 'profile',
  Login = 'login'
}

export interface BillItem {
  name: string;
  quantity: number;
  price: number;
  total: number;
  confidence: number;
}

export interface AgentReport {
  agentName: string;
  verdict: 'OK' | 'WARNING' | 'CRITICAL';
  reasoning: string;
}

export interface BusinessInsight {
  type: 'TREND' | 'ALERT' | 'RECOMMENDATION' | 'STORY';
  title: string;
  content: string;
  impact: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
  actionable?: string;
}

export interface Bill {
  id: string;
  date: string;
  imageUrl: string;
  items: BillItem[];
  grandTotal: number;
  status: 'PENDING' | 'VERIFIED' | 'FLAGGED';
  overallConfidence: number;
  agents: AgentReport[];
  vendorName?: string;
}

export interface DashboardStats {
  totalProcessed: number;
  todaySales: number;
  errorRate: number;
  accuracyTrend: number;
}
