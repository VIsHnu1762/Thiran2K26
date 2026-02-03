
import React, { useState, useEffect } from 'react';
import {
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Package,
  ArrowUpRight,
  MoreHorizontal,
  Zap,
  Sparkles,
  Volume2,
  ChevronRight,
  Lightbulb,
  MessageSquareQuote,
  Loader2,
  PlayCircle,
  Clock,
  FileCheck,
  AlertTriangle,
  Eye
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { Bill, Page, BusinessInsight, BillStatus } from '../types';
import { generateBusinessInsights, generateStorytellingAudio } from '../services/ocrService';
import { Button } from './ui/button';
import { Badge, StatusBadge } from './ui/badge';
import { Card } from './ui/card';

const Dashboard: React.FC<{ bills: Bill[], onNavigate: (page: Page) => void, onSelectBill?: (billId: string) => void }> = ({ bills, onNavigate, onSelectBill }) => {
  const [insights, setInsights] = useState<BusinessInsight[]>([]);
  const [isLoadingInsights, setIsLoadingInsights] = useState(false);
  const [isStoryMode, setIsStoryMode] = useState(false);
  const [isPlayingAudio, setIsPlayingAudio] = useState(false);

  useEffect(() => {
    if (bills.length > 0) {
      loadInsights();
    }
  }, [bills]);

  const loadInsights = async () => {
    setIsLoadingInsights(true);
    try {
      const data = await generateBusinessInsights(bills);
      setInsights(data);
    } catch (e) {
      console.error(e);
    } finally {
      setIsLoadingInsights(false);
    }
  };

  const handleStoryNarrate = async () => {
    if (!insights.length) return;
    setIsPlayingAudio(true);
    try {
      const storyText = insights.map(i => `${i.title}. ${i.content}`).join(' ');
      await generateStorytellingAudio(storyText);
      const utterance = new SpeechSynthesisUtterance(storyText);
      utterance.rate = 0.95;
      utterance.pitch = 1;
      window.speechSynthesis.speak(utterance);
      utterance.onend = () => setIsPlayingAudio(false);
    } catch (e) {
      console.error(e);
      setIsPlayingAudio(false);
    }
  };

  // Calculate statistics
  const grandTotalSales = bills.reduce((acc, b) => acc + b.grandTotal, 0);
  const pendingReviewBills = bills.filter(b => b.status === 'NEEDS_REVIEW' || b.status === 'PENDING');
  const processingBills = bills.filter(b => b.status === 'PROCESSING');
  const approvedBills = bills.filter(b => b.status === 'APPROVED' || b.status === 'VERIFIED');
  const flaggedBills = bills.filter(b => b.status === 'FLAGGED' || b.status === 'FAILED');

  // Calculate average confidence
  const avgConfidence = bills.length > 0
    ? bills.reduce((acc, b) => acc + (b.overallConfidence || 0), 0) / bills.length
    : 0;

  const StatCard = ({ title, value, sub, icon: Icon, color }: any) => (
    <div className="tap-effect glass-card p-7 group hover:scale-[1.02] cursor-pointer">
      <div className="flex justify-between items-start mb-5">
        <div className={`p-4 rounded-[20px] ${color} bg-opacity-20 flex items-center justify-center`}>
          <Icon className={color.replace('bg-', 'text-')} size={26} />
        </div>
        <button className="tap-effect text-white/30 hover:text-white transition-colors">
          <MoreHorizontal size={22} />
        </button>
      </div>
      <h3 className="text-white/50 text-sm font-medium tracking-tight uppercase tracking-wider">{title}</h3>
      <div className="flex items-end gap-3 mt-2">
        <span className="text-3xl font-bold text-white/90 tracking-tighter">{value}</span>
        <span className="text-emerald-400 text-sm font-semibold mb-1 flex items-center bg-emerald-500/10 px-2 py-0.5 rounded-full">
          <ArrowUpRight size={14} className="mr-0.5" /> {sub}
        </span>
      </div>
    </div>
  );

  return (
    <div className="space-y-10 animate-in fade-in slide-in-from-bottom-6 duration-700">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <h1 className="text-4xl font-bold text-white/90 tracking-tight">Business Hub</h1>
          <p className="text-white/50 mt-1.5 text-lg">Your agent-driven retail intelligence</p>
        </div>
        <div className="flex gap-4">
          <button
            onClick={() => setIsStoryMode(!isStoryMode)}
            className={`tap-effect flex items-center gap-2.5 px-7 py-4 rounded-[24px] font-bold transition-all duration-500 border ${isStoryMode
              ? 'bg-indigo-600 text-white border-indigo-400/30 shadow-[0_0_30px_rgba(79,70,229,0.4)]'
              : 'bg-white/5 border-white/10 text-white/70 hover:bg-white/10'
              }`}
          >
            <MessageSquareQuote size={20} />
            Business Voice
          </button>
          <button
            onClick={() => onNavigate(Page.Process)}
            className="gem-button flex items-center gap-2.5 px-7 py-4"
          >
            <Package size={20} />
            New Batch
          </button>
        </div>
      </div>

      {isStoryMode && (insights.length > 0) && (
        <div className="glass-card p-10 bg-gradient-to-br from-indigo-600/20 to-blue-600/20 border-indigo-400/20 animate-in slide-in-from-top-6 duration-700">
          <div className="flex items-start justify-between mb-8">
            <div className="flex items-center gap-5">
              <div className="w-16 h-16 bg-gradient-to-tr from-indigo-500 to-purple-500 rounded-[24px] flex items-center justify-center text-white shadow-xl">
                <Sparkles size={32} />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white/90 tracking-tight">Daily Narrative</h2>
                <p className="text-indigo-300 font-medium">Synthesized from 4 active agents</p>
              </div>
            </div>
            <button
              onClick={handleStoryNarrate}
              disabled={isPlayingAudio}
              className="tap-effect p-5 bg-white/10 hover:bg-white/20 rounded-[24px] border border-white/20 text-white transition-all disabled:opacity-50"
            >
              {isPlayingAudio ? <Loader2 className="animate-spin" /> : <Volume2 size={28} />}
            </button>
          </div>
          <div className="space-y-6">
            <p className="text-xl text-white/80 leading-relaxed italic font-medium">
              "Overall efficiency is exceptional. Your revenue flow is peaking around mid-afternoon.
              {insights[0]?.content} {insights[1]?.content} We've noticed {insights.find(i => i.type === 'ALERT')?.title || 'inventory shifts'} that might need your attention soon."
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard title="Processed" value={bills.length} sub="+12%" icon={CheckCircle2} color="bg-blue-500" />
        <StatCard title="Sales Volume" value={`₹${grandTotalSales.toLocaleString()}`} sub="+18%" icon={TrendingUp} color="bg-emerald-500" />
        <StatCard title="Pending Review" value={pendingReviewBills.length} sub={pendingReviewBills.length > 0 ? 'Action needed' : 'All clear'} icon={Clock} color="bg-amber-500" />
        <StatCard title="Precision" value={`${avgConfidence.toFixed(1)}%`} sub="+4%" icon={Zap} color="bg-indigo-500" />
      </div>

      {/* Pending Review Section */}
      {pendingReviewBills.length > 0 && (
        <Card variant="glass" padding="lg" className="border-amber-500/20 bg-amber-500/5">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-amber-500/20 rounded-2xl flex items-center justify-center">
                <AlertTriangle className="text-amber-400" size={24} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white/90">Bills Requiring Review</h2>
                <p className="text-amber-300/70 text-sm">{pendingReviewBills.length} bill(s) need your attention</p>
              </div>
            </div>
            <Button
              variant="outline"
              onClick={() => onNavigate(Page.History)}
              className="border-amber-500/30 text-amber-400 hover:bg-amber-500/10"
            >
              View All
              <ChevronRight size={16} className="ml-1" />
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {pendingReviewBills.slice(0, 3).map((bill) => (
              <div
                key={bill.id}
                className="tap-effect p-4 rounded-xl bg-white/5 border border-white/10 hover:border-amber-500/30 cursor-pointer transition-all group"
                onClick={() => onSelectBill?.(bill.id)}
              >
                <div className="flex items-start gap-3">
                  <div className="w-12 h-12 rounded-lg overflow-hidden bg-white/10 flex-shrink-0">
                    {bill.imageUrl && (
                      <img src={bill.imageUrl} alt="" className="w-full h-full object-cover" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-bold text-white/90 truncate">
                        {bill.vendorName || bill.vendor?.name || 'Unknown Vendor'}
                      </span>
                      <StatusBadge status={bill.status} size="sm" />
                    </div>
                    <p className="text-xs text-white/50 mb-2">
                      {bill.invoiceNumber || bill.id} • {bill.date || bill.invoiceDate}
                    </p>
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-white/70">₹{bill.grandTotal.toFixed(2)}</span>
                      <div className="flex items-center gap-1">
                        <span className={`text-xs font-bold ${bill.overallConfidence >= 85 ? 'text-emerald-400' :
                            bill.overallConfidence >= 70 ? 'text-amber-400' : 'text-rose-400'
                          }`}>
                          {bill.overallConfidence}%
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-white/5 flex items-center justify-between opacity-0 group-hover:opacity-100 transition-opacity">
                  <span className="text-xs text-white/40">Click to review</span>
                  <Eye size={14} className="text-amber-400" />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-8">
          <div className="glass-card p-9">
            <div className="flex items-center justify-between mb-10">
              <h2 className="text-2xl font-bold text-white/90 tracking-tight">Revenue Dynamics</h2>
              <div className="p-1.5 bg-white/5 rounded-2xl flex gap-1.5 border border-white/10">
                <button className="tap-effect px-5 py-2 rounded-xl text-xs font-bold bg-white/10 shadow-lg text-white">7D</button>
                <button className="tap-effect px-5 py-2 rounded-xl text-xs font-bold text-white/40 hover:text-white/70">30D</button>
              </div>
            </div>
            <div className="h-[340px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={[
                  { name: 'Mon', sales: 4000 }, { name: 'Tue', sales: 3000 }, { name: 'Wed', sales: 2000 },
                  { name: 'Thu', sales: 2780 }, { name: 'Fri', sales: 1890 }, { name: 'Sat', sales: 2390 },
                  { name: 'Sun', sales: 3490 },
                ]}>
                  <defs>
                    <linearGradient id="colorSales" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 12 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{ backgroundColor: 'rgba(15, 23, 42, 0.9)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '20px', backdropFilter: 'blur(16px)' }}
                    itemStyle={{ color: '#f8fafc' }}
                  />
                  <Area type="monotone" dataKey="sales" stroke="#3b82f6" fillOpacity={1} fill="url(#colorSales)" strokeWidth={4} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="glass-card p-9">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-2xl font-bold text-white/90 tracking-tight">Agent Intelligence Log</h2>
              <button className="tap-effect text-blue-400 hover:text-blue-300 text-sm font-bold px-2 py-1">Comprehensive Logs</button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-white/10 text-white/40 text-xs uppercase tracking-widest font-bold">
                    <th className="pb-5">Specialized Agent</th>
                    <th className="pb-5">Observation</th>
                    <th className="pb-5">Status</th>
                    <th className="pb-5">Recorded</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {[
                    { agent: 'Error Agent', incident: 'Math check verified on Bill #942', severity: 'Healthy', time: '2m ago' },
                    { agent: 'Validation Agent', incident: 'Resolved ambiguity in SKU #01', severity: 'Alert', time: '15m ago' },
                    { agent: 'Workflow Agent', incident: 'Automatic export complete', severity: 'Healthy', time: '1h ago' },
                  ].map((row, i) => (
                    <tr key={i} className="tap-effect group hover:bg-white/5 transition-colors cursor-pointer">
                      <td className="py-5">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400">
                            <Zap size={16} />
                          </div>
                          <span className="text-sm font-bold text-white/80">{row.agent}</span>
                        </div>
                      </td>
                      <td className="py-5 text-sm text-white/50">{row.incident}</td>
                      <td className="py-5">
                        <span className={`px-3 py-1 rounded-xl text-[10px] font-bold uppercase ${row.severity === 'Alert' ? 'bg-amber-500/10 text-amber-400 border border-amber-400/20' : 'bg-emerald-500/10 text-emerald-400 border border-emerald-400/20'
                          }`}>
                          {row.severity}
                        </span>
                      </td>
                      <td className="py-5 text-sm text-white/30">{row.time}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="space-y-8">
          <div className="glass-card p-9 flex flex-col">
            <div className="flex items-center justify-between mb-10">
              <div className="flex items-center gap-3">
                <Lightbulb className="text-amber-400" size={28} />
                <h2 className="text-2xl font-bold text-white/90 tracking-tight">AI Insights</h2>
              </div>
              {isLoadingInsights && <Loader2 size={22} className="animate-spin text-white/40" />}
            </div>

            <div className="flex-1 space-y-7">
              {insights.length === 0 && !isLoadingInsights ? (
                <div className="flex flex-col items-center justify-center text-center py-24 opacity-30">
                  <PlayCircle size={64} className="mb-6" />
                  <p className="text-white/80 font-medium">Data required for insight generation</p>
                </div>
              ) : (
                insights.map((insight, idx) => (
                  <div key={idx} className="tap-effect group p-5 rounded-[24px] bg-white/5 hover:bg-white/10 transition-all border border-white/10 hover:border-white/20 cursor-pointer">
                    <div className="flex items-start justify-between mb-3">
                      <span className={`px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-widest ${insight.type === 'TREND' ? 'text-blue-400 bg-blue-400/10' :
                        insight.type === 'ALERT' ? 'text-rose-400 bg-rose-400/10' : 'text-emerald-400 bg-emerald-400/10'
                        }`}>
                        {insight.type}
                      </span>
                      <ChevronRight size={18} className="text-white/20 group-hover:text-white/50 transition-colors" />
                    </div>
                    <h3 className="text-base font-bold text-white/90 mb-2">{insight.title}</h3>
                    <p className="text-sm text-white/50 leading-relaxed font-medium">{insight.content}</p>
                    {insight.actionable && (
                      <div className="mt-4 pt-4 border-t border-white/10 flex items-center gap-2 text-[11px] font-bold text-blue-400 uppercase tracking-widest">
                        <Zap size={12} /> {insight.actionable}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>

            <button className="tap-effect mt-8 w-full py-4 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold rounded-[20px] transition-all">
              Full Analytics Report
            </button>
          </div>

          <div className="glass-card p-9">
            <h2 className="text-2xl font-bold text-white/90 tracking-tight mb-8">Inventory Velocity</h2>
            <div className="space-y-8">
              {[
                { name: 'Fresh Produce', level: 85, color: 'bg-emerald-500' },
                { name: 'Dairy Core', level: 32, color: 'bg-amber-500' },
                { name: 'Household Essentials', level: 12, color: 'bg-rose-500' },
              ].map((item, i) => (
                <div key={i} className="space-y-3">
                  <div className="flex justify-between text-sm font-bold tracking-tight">
                    <span className="text-white/80">{item.name}</span>
                    <span className="text-white/40">{item.level}% Stock</span>
                  </div>
                  <div className="h-2.5 bg-white/5 rounded-full overflow-hidden border border-white/5">
                    <div
                      className={`h-full transition-all duration-1000 ${item.color} shadow-[0_0_10px_rgba(255,255,255,0.1)]`}
                      style={{ width: `${item.level}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
