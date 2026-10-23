import React from 'react';
import { 
  Building2, 
  RefreshCw, 
  ShieldCheck, 
  Cpu, 
  Info, 
  Radio
} from 'lucide-react';

export default function Navbar({ 
  healthStatus, 
  isRefreshing, 
  onRefresh 
}) {
  const isHealthy = healthStatus?.status === 'healthy';

  return (
    <header className="border-b border-slate-800 bg-slate-900/90 backdrop-blur-md sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
        
        {/* Brand & Building Header */}
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 flex items-center justify-center shadow-lg shadow-emerald-950/40 border border-emerald-400/30">
            <Cpu className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold text-slate-50 tracking-tight">ResourceShift AI</h1>
              <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                HITL Intelligence
              </span>
            </div>
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Building2 className="w-3.5 h-3.5 text-slate-500" />
              <span className="font-medium text-slate-300">Engineering Hall (ENG_HALL_01)</span>
              <span className="text-slate-600">•</span>
              <span>North Wing Campus Facility</span>
            </div>
          </div>
        </div>

        {/* Status Indicators & Controls */}
        <div className="flex flex-wrap items-center gap-3">
          
          {/* Simulated Telemetry Label */}
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 text-xs font-medium" title="Readings generated deterministically to model campus operations">
            <Info className="w-3.5 h-3.5 text-amber-400" />
            <span>Simulated Telemetry (Elec, Water, Fuel)</span>
          </div>

          {/* Safety Non-Actuation Guarantee */}
          <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-800/80 border border-slate-700/80 text-slate-300 text-xs font-medium" title="Strict architectural invariant: agent only advises human facility staff">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            <span>Advisory Only (No Direct Actuation)</span>
          </div>

          {/* Live Backend Connection Status */}
          <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium border ${
            isHealthy 
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' 
              : 'bg-red-500/10 border-red-500/20 text-red-300'
          }`}>
            <Radio className={`w-3.5 h-3.5 ${isHealthy ? 'text-emerald-400 animate-pulse' : 'text-red-400'}`} />
            <span>{isHealthy ? 'Backend Connected' : 'Disconnected'}</span>
          </div>

          {/* Refresh Button */}
          <button
            onClick={onRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 active:bg-slate-750 border border-slate-700 text-slate-200 text-xs font-medium transition-colors disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-emerald-500/50"
            title="Refresh telemetry and anomalies"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin text-emerald-400' : 'text-slate-400'}`} />
            <span>Refresh</span>
          </button>

        </div>

      </div>
    </header>
  );
}
