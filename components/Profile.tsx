
import React from 'react';
import { 
  User, 
  Mail, 
  MapPin, 
  Store, 
  Phone, 
  Shield, 
  LogOut, 
  ChevronRight,
  Camera,
  Activity,
  History
} from 'lucide-react';

const Profile: React.FC<{ onLogout: () => void }> = ({ onLogout }) => {
  const businessData = JSON.parse(localStorage.getItem('billagent_business') || '{}');

  const ProfileCard = ({ icon: Icon, label, value }: any) => (
    <div className="flex items-center gap-4 p-4 bg-black/5 dark:bg-white/5 rounded-2xl border border-border">
      <div className="p-3 bg-blue-500/10 text-blue-500 rounded-xl">
        <Icon size={20} />
      </div>
      <div>
        <p className="text-xs text-slate-500 uppercase font-bold tracking-wider">{label}</p>
        <p className="text-slate-900 dark:text-white font-semibold">{value || 'Not Set'}</p>
      </div>
    </div>
  );

  return (
    <div className="max-w-4xl mx-auto animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Business Profile</h1>
        <button 
          onClick={onLogout}
          className="flex items-center gap-2 px-4 py-2 text-rose-500 hover:bg-rose-500/10 rounded-xl transition-all font-semibold"
        >
          <LogOut size={18} /> Logout
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-12 gap-8">
        {/* Left column: Avatar and Stats */}
        <div className="md:col-span-4 space-y-6">
          <div className="matte-card p-8 rounded-[2.5rem] flex flex-col items-center text-center">
            <div className="relative mb-6">
              <img src="https://picsum.photos/120/120" className="w-28 h-28 rounded-[2rem] border-4 border-blue-500/20" alt="Profile" />
              <button className="absolute -bottom-2 -right-2 p-3 bg-blue-600 text-white rounded-2xl shadow-lg hover:bg-blue-500 transition-all">
                <Camera size={18} />
              </button>
            </div>
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">{businessData.owner || 'Alex Chen'}</h2>
            <p className="text-slate-500 dark:text-slate-400 text-sm mb-6">{businessData.name || 'Organic Mart'}</p>
            
            <div className="flex gap-4 w-full pt-6 border-t border-border">
              <div className="flex-1">
                <p className="text-xl font-bold text-slate-900 dark:text-white">1.2k</p>
                <p className="text-[10px] text-slate-500 uppercase font-bold">Bills</p>
              </div>
              <div className="w-px h-8 bg-border"></div>
              <div className="flex-1">
                <p className="text-xl font-bold text-slate-900 dark:text-white">98%</p>
                <p className="text-[10px] text-slate-500 uppercase font-bold">Accuracy</p>
              </div>
            </div>
          </div>

          <div className="matte-card p-6 rounded-[2rem] space-y-4">
            <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-widest mb-2 flex items-center gap-2">
              <Activity size={16} className="text-blue-500" /> Recent Activity
            </h3>
            {[
              { label: 'Login detected', time: '2h ago', icon: Shield },
              { label: 'Exported Analytics', time: 'Yesterday', icon: History },
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="p-2 bg-slate-100 dark:bg-white/5 rounded-lg text-slate-500">
                  <item.icon size={14} />
                </div>
                <div className="flex-1">
                  <p className="text-xs font-semibold text-slate-900 dark:text-white">{item.label}</p>
                  <p className="text-[10px] text-slate-500">{item.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right column: Details and Settings */}
        <div className="md:col-span-8 space-y-6">
          <div className="matte-card p-8 rounded-[2.5rem]">
            <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-6">Store Information</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <ProfileCard icon={Store} label="Store Name" value={businessData.name} />
              <ProfileCard icon={User} label="Owner Name" value={businessData.owner} />
              <ProfileCard icon={Mail} label="Email Address" value={businessData.email} />
              <ProfileCard icon={Phone} label="Contact Phone" value={businessData.phone || '+1 234 567 890'} />
              <div className="sm:col-span-2">
                <ProfileCard icon={MapPin} label="Physical Address" value={businessData.address || '123 Smart Retail Ave, Silicon Valley, CA'} />
              </div>
            </div>
            
            <div className="mt-10 pt-10 border-t border-border">
              <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-6">Preferences</h3>
              <div className="space-y-3">
                <button className="w-full flex items-center justify-between p-4 bg-black/5 dark:bg-white/5 rounded-2xl hover:bg-black/10 dark:hover:bg-white/10 transition-all border border-border">
                  <div className="flex items-center gap-4 text-slate-900 dark:text-white font-medium">
                    <Shield size={20} className="text-blue-500" />
                    Two-Factor Authentication
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">Enabled</span>
                    <ChevronRight size={18} className="text-slate-500" />
                  </div>
                </button>
                <button className="w-full flex items-center justify-between p-4 bg-black/5 dark:bg-white/5 rounded-2xl hover:bg-black/10 dark:hover:bg-white/10 transition-all border border-border">
                  <div className="flex items-center gap-4 text-slate-900 dark:text-white font-medium">
                    <Mail size={20} className="text-blue-500" />
                    Marketing Communications
                  </div>
                  <ChevronRight size={18} className="text-slate-500" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Profile;
