
import React from 'react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  Cell
} from 'recharts';
import { Bill } from '../types';

const Analytics: React.FC<{ bills: Bill[] }> = ({ bills }) => {
  // Aggregate items across all bills
  const itemMap: Record<string, number> = {};
  bills.forEach(bill => {
    bill.items.forEach(item => {
      const name = item.name.toLowerCase().trim();
      itemMap[name] = (itemMap[name] || 0) + item.total;
    });
  });

  const chartData = Object.entries(itemMap)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([name, total]) => ({ name, total }));

  const COLORS = ['#3b82f6', '#06b6d4', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#6366f1'];

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold text-white">Advanced Analytics</h1>
        <p className="text-slate-400">Deep dive into sales patterns and agentic accuracy</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="matte-card p-8 rounded-3xl">
          <h2 className="text-xl font-bold text-white mb-8">Top Revenue Items</h2>
          <div className="h-[400px]" style={{ minHeight: '400px' }}>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" hide />
                <YAxis 
                  dataKey="name" 
                  type="category" 
                  axisLine={false} 
                  tickLine={false} 
                  width={100}
                  tick={{fill: '#94a3b8', fontSize: 12}} 
                />
                <Tooltip 
                  cursor={{fill: 'rgba(255,255,255,0.05)'}}
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '12px' }}
                />
                <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                  {chartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="matte-card p-8 rounded-3xl">
          <h2 className="text-xl font-bold text-white mb-8">System Efficiency</h2>
          <div className="space-y-8">
            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Automatic Correction Success</span>
                <span className="text-emerald-400 font-bold">94.2%</span>
              </div>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-emerald-500 w-[94.2%]" />
              </div>
              <p className="text-xs text-slate-500 italic">Error Detection Agent flagged 12 math errors this week; all corrected successfully.</p>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Handwriting Recognition Accuracy</span>
                <span className="text-blue-400 font-bold">88.7%</span>
              </div>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500 w-[88.7%]" />
              </div>
              <p className="text-xs text-slate-500 italic">User-Assisted Learning Agent improved this by 5.2% after your recent corrections.</p>
            </div>

            <div className="space-y-3">
              <div className="flex justify-between items-center text-sm">
                <span className="text-slate-400">Time Saved (Manual vs Agent)</span>
                <span className="text-amber-400 font-bold">14.5 Hours</span>
              </div>
              <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-amber-500 w-[72%]" />
              </div>
              <p className="text-xs text-slate-500 italic">Processing time reduced from 3 mins/bill to 12 seconds/bill.</p>
            </div>

            <div className="p-4 bg-emerald-500/10 rounded-2xl border border-emerald-500/20">
              <p className="text-sm font-bold text-emerald-400 mb-1">Agent Suggestion</p>
              <p className="text-xs text-slate-300">"Your store #12 shows a 15% price variance for 'Apples' across different vendors. Consider consolidating suppliers for better margins."</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Analytics;
