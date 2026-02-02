
import React, { useState } from 'react';
import { 
  Zap, 
  ArrowRight, 
  Store, 
  User, 
  Mail, 
  Lock, 
  ShieldCheck,
  CheckCircle2,
  Scan,
  TrendingUp,
  BrainCircuit
} from 'lucide-react';

const Login: React.FC<{ onLogin: (details: any) => void }> = ({ onLogin }) => {
  const [isRegistering, setIsRegistering] = useState(false);
  const [details, setDetails] = useState({
    name: '',
    owner: '',
    email: '',
    password: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // In a real app, perform auth logic. Here we just pass the details.
    onLogin({
      name: details.name || 'Demo Store',
      owner: details.owner || 'Alex Chen',
      email: details.email || 'alex@demo.com'
    });
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row bg-background">
      {/* Left side: Hero & Features */}
      <div className="flex-1 p-12 lg:p-24 bg-gradient-to-tr from-blue-900 via-blue-800 to-indigo-900 text-white flex flex-col justify-between relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/20 rounded-full blur-[100px] -mr-48 -mt-48"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-indigo-500/20 rounded-full blur-[100px] -ml-48 -mb-48"></div>
        
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-16">
            <div className="w-12 h-12 bg-white rounded-2xl flex items-center justify-center text-blue-600 shadow-xl">
              <Zap size={24} className="fill-blue-600" />
            </div>
            <span className="text-2xl font-bold tracking-tight">BillAgent Pro</span>
          </div>

          <h1 className="text-5xl lg:text-7xl font-extrabold mb-8 leading-[1.1]">
            Turn your bills <br /> into <span className="text-blue-400 italic">intelligence.</span>
          </h1>
          <p className="text-xl text-blue-100/70 max-w-lg mb-12">
            The world's first agentic AI bill processor designed for local retail and small vendors. 
            From handwriting to analytics in seconds.
          </p>

          <div className="space-y-6">
            {[
              { icon: Scan, title: "Multimodal Agentic OCR", desc: "Our agents recognize even the messiest handwriting." },
              { icon: BrainCircuit, title: "Autonomous Validation", desc: "4 specialized agents verify every cent automatically." },
              { icon: TrendingUp, title: "Real-time Insights", desc: "Watch your margins grow as the system tracks trends." }
            ].map((feature, i) => (
              <div key={i} className="flex gap-4 p-4 bg-white/5 rounded-3xl border border-white/10 backdrop-blur-md max-w-md hover:bg-white/10 transition-all cursor-default group">
                <div className="w-12 h-12 rounded-2xl bg-blue-400/20 text-blue-400 flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform">
                  <feature.icon size={24} />
                </div>
                <div>
                  <h3 className="font-bold text-white">{feature.title}</h3>
                  <p className="text-sm text-blue-100/50">{feature.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative z-10 pt-12 text-sm text-blue-100/40">
          © 2025 BillAgent AI Systems • Trusted by 5,000+ local vendors
        </div>
      </div>

      {/* Right side: Login Form */}
      <div className="w-full md:w-[500px] lg:w-[600px] p-8 lg:p-24 flex items-center justify-center bg-white dark:bg-slate-950">
        <div className="w-full max-w-md animate-in fade-in slide-in-from-right-8 duration-700">
          <div className="mb-10">
            <h2 className="text-3xl font-extrabold text-slate-900 dark:text-white mb-2">
              {isRegistering ? 'Register Your Business' : 'Welcome Back'}
            </h2>
            <p className="text-slate-500 dark:text-slate-400">
              {isRegistering ? 'Let\'s get your store set up with AI agents.' : 'Log in to manage your digital records.'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {isRegistering && (
              <>
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest ml-1">Store Name</label>
                  <div className="relative">
                    <Store className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input 
                      type="text" 
                      placeholder="e.g. Organic Mart"
                      required
                      className="w-full pl-12 pr-4 py-4 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      value={details.name}
                      onChange={e => setDetails({...details, name: e.target.value})}
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest ml-1">Owner Name</label>
                  <div className="relative">
                    <User className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                    <input 
                      type="text" 
                      placeholder="Full Name"
                      required
                      className="w-full pl-12 pr-4 py-4 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                      value={details.owner}
                      onChange={e => setDetails({...details, owner: e.target.value})}
                    />
                  </div>
                </div>
              </>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest ml-1">Work Email</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input 
                  type="email" 
                  placeholder="alex@organicmart.com"
                  required
                  className="w-full pl-12 pr-4 py-4 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  value={details.email}
                  onChange={e => setDetails({...details, email: e.target.value})}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase tracking-widest ml-1">Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                <input 
                  type="password" 
                  placeholder="••••••••"
                  required
                  className="w-full pl-12 pr-4 py-4 bg-slate-50 dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-2xl text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                  value={details.password}
                  onChange={e => setDetails({...details, password: e.target.value})}
                />
              </div>
            </div>

            <button 
              type="submit"
              className="w-full py-5 bg-blue-600 text-white rounded-[1.25rem] font-bold text-lg hover:bg-blue-500 shadow-2xl shadow-blue-500/20 active:scale-[0.98] transition-all flex items-center justify-center gap-2 group mt-6"
            >
              {isRegistering ? 'Create Account' : 'Sign In'}
              <ArrowRight className="group-hover:translate-x-1 transition-transform" size={20} />
            </button>
          </form>

          <div className="mt-8 text-center">
            <button 
              onClick={() => setIsRegistering(!isRegistering)}
              className="text-slate-500 dark:text-slate-400 hover:text-blue-500 transition-colors text-sm font-medium"
            >
              {isRegistering ? 'Already have an account? Log in' : 'New store? Register your business'}
            </button>
          </div>

          <div className="mt-12 flex items-center gap-2 justify-center text-[10px] text-slate-400 uppercase tracking-[0.2em] font-bold border-t border-slate-100 dark:border-white/5 pt-8">
            <ShieldCheck size={14} className="text-emerald-500" />
            Secured by Agentic Guard
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
