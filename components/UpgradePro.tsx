
import React from 'react';
import { Check, Zap, Rocket, Building2, Crown } from 'lucide-react';

const UpgradePro: React.FC = () => {
  const plans = [
    {
      name: "Starter",
      price: "$0",
      description: "Perfect for tiny neighborhood kiosks.",
      features: ["50 Bills/month", "Standard OCR", "1 Agent analysis", "Basic Analytics"],
      icon: Rocket,
      color: "blue",
      current: true
    },
    {
      name: "Pro",
      price: "$49",
      description: "For scaling retail shops and busy vendors.",
      features: ["Unlimited Bills", "Advanced Agentic OCR", "4 Specialized Agents", "Real-time Dashboards", "CSV/PDF Exports"],
      icon: Zap,
      color: "indigo",
      popular: true
    },
    {
      name: "Enterprise",
      price: "Custom",
      description: "Multi-location inventory and supply chain tracking.",
      features: ["Multi-store support", "Dedicated GPU for OCR", "Custom Agent workflows", "ERP Integrations", "24/7 Priority Support"],
      icon: Crown,
      color: "purple"
    }
  ];

  return (
    <div className="max-w-6xl mx-auto py-12 animate-in fade-in slide-in-from-bottom-8 duration-700">
      <div className="text-center mb-16">
        <h1 className="text-4xl font-extrabold text-slate-900 dark:text-white mb-4">Supercharge Your Business</h1>
        <p className="text-lg text-slate-600 dark:text-slate-400 max-w-2xl mx-auto">
          Upgrade to unlock multi-agent reasoning, deep inventory patterns, and unlimited bill processing power.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        {plans.map((plan) => (
          <div 
            key={plan.name} 
            className={`matte-card rounded-[2.5rem] p-8 relative flex flex-col ${
              plan.popular ? 'border-blue-500 ring-2 ring-blue-500/20 scale-105 z-10' : ''
            }`}
          >
            {plan.popular && (
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-blue-600 text-white px-4 py-1 rounded-full text-xs font-bold uppercase tracking-widest">
                Most Popular
              </div>
            )}
            
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-6 bg-${plan.color}-500/20 text-${plan.color}-500`}>
              <plan.icon size={28} />
            </div>

            <h3 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">{plan.name}</h3>
            <p className="text-slate-500 dark:text-slate-400 text-sm mb-6 min-h-[40px]">{plan.description}</p>
            
            <div className="flex items-baseline gap-1 mb-8">
              <span className="text-4xl font-bold text-slate-900 dark:text-white">{plan.price}</span>
              <span className="text-slate-500 text-sm">{plan.price !== 'Custom' && '/mo'}</span>
            </div>

            <ul className="space-y-4 mb-10 flex-1">
              {plan.features.map((feature) => (
                <li key={feature} className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-300">
                  <div className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center flex-shrink-0">
                    <Check size={12} />
                  </div>
                  {feature}
                </li>
              ))}
            </ul>

            <button className={`w-full py-4 rounded-2xl font-bold transition-all active:scale-[0.98] ${
              plan.current 
                ? 'bg-slate-200 dark:bg-white/5 text-slate-400 cursor-default' 
                : 'bg-blue-600 text-white hover:bg-blue-500 shadow-xl shadow-blue-500/20'
            }`}>
              {plan.current ? 'Current Plan' : 'Get Started'}
            </button>
          </div>
        ))}
      </div>

      <div className="mt-20 p-8 glass rounded-[2.5rem] flex flex-col md:flex-row items-center gap-8 border border-border">
        <div className="p-6 bg-blue-600/10 rounded-3xl text-blue-500">
          <Building2 size={40} />
        </div>
        <div className="flex-1 text-center md:text-left">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white mb-2">Need something special for a multi-store franchise?</h2>
          <p className="text-slate-500 dark:text-slate-400">Our team can build custom agents trained specifically on your custom handwritten forms and logistics documents.</p>
        </div>
        <button className="px-8 py-3 border-2 border-blue-600 text-blue-600 hover:bg-blue-600 hover:text-white transition-all rounded-xl font-bold">
          Contact Sales
        </button>
      </div>
    </div>
  );
};

export default UpgradePro;
