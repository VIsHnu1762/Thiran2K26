
import React, { useState } from 'react';
import {
  Bell,
  Lock,
  Zap,
  User,
  Eye,
  ShieldCheck,
  BrainCircuit,
  Settings as SettingsIcon,
  ChevronRight,
  RotateCcw
} from 'lucide-react';

const Settings: React.FC = () => {
  const [threshold, setThreshold] = useState(85);
  const [autoSave, setAutoSave] = useState(true);

  const Toggle = ({ active, onToggle }: any) => (
    <button
      onClick={onToggle}
      className={`tap-effect w-12 h-6 rounded-full p-1 transition-all duration-300 ${active ? 'bg-blue-600 shadow-[0_0_15px_rgba(37,99,235,0.4)]' : 'bg-white/10'}`}
    >
      <div className={`w-4 h-4 bg-white rounded-full transition-all duration-300 ${active ? 'translate-x-6' : 'translate-x-0 shadow-sm'}`} />
    </button>
  );

  const SettingRow = ({ icon: Icon, title, desc, children }: any) => (
    <div className="flex items-center justify-between py-6 border-b border-white/5 last:border-0">
      <div className="flex gap-4">
        <div className="p-3 bg-white/5 rounded-2xl text-slate-400">
          <Icon size={20} />
        </div>
        <div>
          <h3 className="text-sm font-bold text-white">{title}</h3>
          <p className="text-xs text-slate-500 mt-0.5">{desc}</p>
        </div>
      </div>
      {children}
    </div>
  );

  const handleReset = () => {
    setThreshold(85);
    setAutoSave(true);
  };

  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div>
        <h1 className="text-3xl font-bold text-white tracking-tight">System Configuration</h1>
        <p className="text-white/40">Calibrate neural logic and privacy gates</p>
      </div>

      <div className="space-y-8">
        <section className="glass-card p-9">
          <h2 className="text-lg font-bold text-white/90 mb-8 flex items-center gap-3">
            <BrainCircuit className="text-blue-400" size={20} />
            Agentic Parameters
          </h2>

          <div className="space-y-2">
            <SettingRow
              icon={ShieldCheck}
              title="Confidence Threshold"
              desc="Bills scoring above this threshold will be auto-verified."
            >
              <div className="flex items-center gap-4">
                <input
                  type="range"
                  min="50"
                  max="100"
                  value={threshold}
                  onChange={(e) => setThreshold(parseInt(e.target.value))}
                  className="w-32 h-1.5 bg-white/10 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
                <span className="text-sm font-bold text-blue-400 w-8">{threshold}%</span>
              </div>
            </SettingRow>

            <SettingRow
              icon={Zap}
              title="Auto-Commit Neural Extracts"
              desc="Automatically store bills that pass Error Agent math checks."
            >
              <Toggle active={autoSave} onToggle={() => setAutoSave(!autoSave)} />
            </SettingRow>

            <SettingRow
              icon={Eye}
              title="Visual Ambiguity Highlighting"
              desc="Color-code items where OCR confidence is under 80%."
            >
              <Toggle active={true} onToggle={() => { }} />
            </SettingRow>
          </div>
        </section>

        <section className="glass-card p-9">
          <h2 className="text-lg font-bold text-white/90 mb-8">Security & Access</h2>
          <div className="space-y-4">
            <button className="tap-effect w-full flex items-center justify-between p-5 bg-white/5 rounded-[24px] hover:bg-white/10 transition-all text-left border border-white/5">
              <div className="flex items-center gap-4">
                <div className="p-2.5 bg-blue-500/20 text-blue-400 rounded-xl">
                  <User size={18} />
                </div>
                <div>
                  <p className="text-sm font-bold text-white/90">Authentication Profile</p>
                  <p className="text-xs text-white/40">Biometrics, recovery keys, and multi-factor</p>
                </div>
              </div>
              <ChevronRight size={18} className="text-white/20" />
            </button>

            <button className="tap-effect w-full flex items-center justify-between p-5 bg-white/5 rounded-[24px] hover:bg-white/10 transition-all text-left border border-white/5">
              <div className="flex items-center gap-4">
                <div className="p-2.5 bg-rose-500/20 text-rose-400 rounded-xl">
                  <Lock size={18} />
                </div>
                <div>
                  <p className="text-sm font-bold text-white/90">API Management</p>
                  <p className="text-xs text-white/40">Neural engine keys and webhook endpoints</p>
                </div>
              </div>
              <ChevronRight size={18} className="text-white/20" />
            </button>
          </div>
        </section>

        <div className="flex justify-between items-center pt-4">
          <button
            onClick={handleReset}
            className="tap-effect flex items-center gap-2 px-6 py-3 rounded-xl text-rose-400 hover:bg-rose-500/10 transition-all font-bold"
          >
            <RotateCcw size={18} />
            <span>Reset Defaults</span>
          </button>

          <div className="flex gap-4">
            <button className="tap-effect px-7 py-3 rounded-xl text-white/40 hover:text-white transition-colors font-bold">Discard</button>
            <button className="gem-button px-10 py-4 shadow-blue-500/30">Save Neural State</button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Settings;
