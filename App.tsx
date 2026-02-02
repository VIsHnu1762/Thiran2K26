
import React, { useState, useEffect } from 'react';
import { 
  LayoutDashboard, 
  FileUp, 
  History, 
  BarChart3, 
  Settings as SettingsIcon,
  Bell,
  Zap,
  Moon,
  Sun,
  Menu,
  X
} from 'lucide-react';
import { Page, Bill } from './types';
import Dashboard from './components/Dashboard';
import BillUpload from './components/BillUpload';
import BillHistory from './components/BillHistory';
import Analytics from './components/Analytics';
import Settings from './components/Settings';
import UpgradePro from './components/UpgradePro';
import Profile from './components/Profile';
import Login from './components/Login';

const App: React.FC = () => {
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [currentPage, setCurrentPage] = useState<Page>(Page.Dashboard);
  const [bills, setBills] = useState<Bill[]>([]);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem('billagent_data');
    if (saved) {
      setBills(JSON.parse(saved));
    }
    const savedAuth = localStorage.getItem('billagent_auth');
    if (savedAuth === 'true') setIsLoggedIn(true);

    const savedTheme = (localStorage.getItem('billagent_theme') as 'dark' | 'light') || 'dark';
    setTheme(savedTheme);
    document.documentElement.className = savedTheme;
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('billagent_theme', newTheme);
    document.documentElement.className = newTheme;
  };

  const handleLogin = (businessDetails: any) => {
    setIsLoggedIn(true);
    localStorage.setItem('billagent_auth', 'true');
    localStorage.setItem('billagent_business', JSON.stringify(businessDetails));
    setCurrentPage(Page.Dashboard);
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    localStorage.removeItem('billagent_auth');
    setCurrentPage(Page.Login);
  };

  const saveBills = (newBills: Bill[]) => {
    setBills(newBills);
    localStorage.setItem('billagent_data', JSON.stringify(newBills));
  };

  if (!isLoggedIn) {
    return <Login onLogin={handleLogin} />;
  }

  const NavItem = ({ page, icon: Icon, label }: { page: Page, icon: any, label: string }) => (
    <button
      onClick={() => {
        setCurrentPage(page);
        setIsMobileMenuOpen(false);
      }}
      className={`tap-effect flex items-center gap-2 px-5 py-2.5 rounded-2xl transition-all duration-500 ${
        currentPage === page 
          ? 'bg-blue-600 text-white shadow-[0_0_20px_rgba(37,99,235,0.4)]' 
          : 'text-white/60 hover:text-white hover:bg-white/10'
      }`}
    >
      <Icon size={18} />
      <span className="font-semibold text-sm whitespace-nowrap tracking-tight">{label}</span>
    </button>
  );

  const renderPage = () => {
    switch (currentPage) {
      case Page.Dashboard:
        return <Dashboard bills={bills} onNavigate={setCurrentPage} />;
      case Page.Process:
        return <BillUpload onComplete={(newBill) => saveBills([newBill, ...bills])} />;
      case Page.History:
        return <BillHistory bills={bills} />;
      case Page.Analytics:
        return <Analytics bills={bills} />;
      case Page.Settings:
        return <Settings />;
      case Page.Upgrade:
        return <UpgradePro />;
      case Page.Profile:
        return <Profile onLogout={handleLogout} />;
      default:
        return <Dashboard bills={bills} onNavigate={setCurrentPage} />;
    }
  };

  return (
    <div className="flex flex-col min-h-screen transition-colors duration-500 pb-20">
      {/* Floating Glassy Top Navigation */}
      <nav className="nav-glass px-6 py-4 flex items-center justify-between lg:grid lg:grid-cols-3 gap-4">
        {/* Left: Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-tr from-blue-600 to-indigo-600 rounded-2xl flex items-center justify-center shadow-lg shadow-blue-500/20">
            <Zap className="text-white fill-white" size={20} />
          </div>
          <span className="text-xl font-bold tracking-tight text-white/90 whitespace-nowrap">
            BillAgent<span className="text-blue-500">.</span>
          </span>
        </div>

        {/* Center: Desktop Links (Centred Boxes) */}
        <div className="hidden lg:flex items-center justify-center">
          <div className="flex items-center bg-white/5 p-1 rounded-[1.8rem] border border-white/10">
            <NavItem page={Page.Dashboard} icon={LayoutDashboard} label="Dashboard" />
            <NavItem page={Page.Process} icon={FileUp} label="Process" />
            <NavItem page={Page.History} icon={History} label="History" />
            <NavItem page={Page.Analytics} icon={BarChart3} label="Analytics" />
            <NavItem page={Page.Settings} icon={SettingsIcon} label="Settings" />
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center justify-end gap-3">
          <div className="hidden sm:flex items-center gap-1.5 bg-white/5 p-1.5 rounded-2xl border border-white/10">
            <button onClick={toggleTheme} className="tap-effect p-2 text-white/60 hover:text-white hover:bg-white/10 rounded-xl transition-all">
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button className="tap-effect relative p-2 text-white/60 hover:text-white hover:bg-white/10 rounded-xl transition-all">
              <Bell size={18} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-rose-500 rounded-full border-2 border-[#030712]" />
            </button>
          </div>

          <button 
            onClick={() => setCurrentPage(Page.Profile)}
            className="tap-effect flex items-center gap-3 p-1 bg-white/5 rounded-2xl border border-white/10 transition-all hover:bg-white/10"
          >
            <div className="text-right hidden md:block pl-3">
              <p className="text-xs font-bold text-white/90 leading-tight">Alex Chen</p>
              <p className="text-[10px] text-white/40 font-medium">Pro Member</p>
            </div>
            <img src="https://picsum.photos/40/40" className="w-9 h-9 rounded-xl border border-white/20" alt="Avatar" />
          </button>

          <button onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)} className="tap-effect lg:hidden p-2.5 text-white/60 hover:text-white bg-white/5 rounded-2xl border border-white/10">
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </div>
      </nav>

      {/* Mobile Drawer */}
      {isMobileMenuOpen && (
        <div className="fixed inset-x-6 top-28 z-50 lg:hidden glass-card p-6 flex flex-col gap-3 animate-in fade-in slide-in-from-top-4">
          <NavItem page={Page.Dashboard} icon={LayoutDashboard} label="Dashboard" />
          <NavItem page={Page.Process} icon={FileUp} label="Process Bill" />
          <NavItem page={Page.History} icon={History} label="History" />
          <NavItem page={Page.Analytics} icon={BarChart3} label="Analytics" />
          <NavItem page={Page.Settings} icon={SettingsIcon} label="Settings" />
          <div className="h-px bg-white/10 my-2" />
          <button 
            onClick={() => { setCurrentPage(Page.Upgrade); setIsMobileMenuOpen(false); }}
            className="gem-button py-4 w-full flex items-center justify-center gap-2"
          >
            <Zap size={18} fill="currentColor" /> Upgrade to Pro
          </button>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 w-full max-w-7xl mx-auto px-6 mt-8">
        {renderPage()}
      </main>

      {/* Floating Bottom Nav for Mobile */}
      <div className="fixed bottom-8 left-1/2 -translate-x-1/2 lg:hidden z-50">
        <button 
          onClick={() => setCurrentPage(Page.Process)}
          className="gem-button w-16 h-16 flex items-center justify-center shadow-2xl shadow-blue-500/50"
        >
          <FileUp size={28} />
        </button>
      </div>
    </div>
  );
};

export default App;
