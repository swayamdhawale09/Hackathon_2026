import React from 'react';
import { Zap, Droplets, Flame, DollarSign, Sparkles } from 'lucide-react';

export default function OverviewCards({ 
  telemetry = [], 
  anomalies = [], 
  proposals = [] 
}) {
  // Compute per-resource stats
  const resources = [
    {
      key: 'electricity',
      name: 'Electricity',
      unit: 'kWh',
      icon: Zap,
      accentColor: 'text-emerald-400',
      bgGlow: 'from-emerald-500/10 to-teal-500/5',
      borderColor: 'border-emerald-500/20',
      isSimulated: true,
      simulationLabel: 'Campus Synthetic (672h)',
      tariffRate: 0.14,
      co2Rate: 0.42,
    },
    {
      key: 'water',
      name: 'Domestic Water',
      unit: 'L',
      icon: Droplets,
      accentColor: 'text-sky-400',
      bgGlow: 'from-sky-500/10 to-blue-500/5',
      borderColor: 'border-sky-500/20',
      isSimulated: true,
      simulationLabel: 'Simulated Hydronic Flow',
      tariffRate: 0.004,
      co2Rate: 0.0003,
    },
    {
      key: 'fuel',
      name: 'Natural Gas / Fuel',
      unit: 'L',
      icon: Flame,
      accentColor: 'text-amber-400',
      bgGlow: 'from-amber-500/10 to-orange-500/5',
      borderColor: 'border-amber-500/20',
      isSimulated: true,
      simulationLabel: 'Simulated Heating Loop',
      tariffRate: 0.85,
      co2Rate: 2.68,
    },
  ];

  // Calculate totals and metrics
  const cardData = resources.map((r) => {
    // Readings for this resource
    const resReadings = telemetry.filter((t) => t.resource_type === r.key);
    const latestReading = resReadings.length > 0 ? resReadings[resReadings.length - 1] : null;
    
    // Anomalies for this resource
    const resAnomalies = anomalies.filter((a) => a.resource_type === r.key);
    const criticalAnomalies = resAnomalies.filter((a) => a.severity === 'critical' || a.severity === 'high');
    const totalExcess = resAnomalies.reduce((acc, a) => acc + (a.excess_consumption || 0), 0);
    const estimatedSavingsUsd = totalExcess * r.tariffRate;

    return {
      ...r,
      latestValue: latestReading ? latestReading.consumption.toFixed(1) : '—',
      totalAnomalies: resAnomalies.length,
      criticalCount: criticalAnomalies.length,
      totalExcess: totalExcess.toFixed(1),
      estimatedSavingsUsd: estimatedSavingsUsd.toFixed(2),
    };
  });

  // Calculate aggregate recovery impact
  const totalApproved = proposals.filter((p) => p.status === 'approved').length;
  const totalEstimatedUsd = cardData.reduce((acc, c) => acc + parseFloat(c.estimatedSavingsUsd || 0), 0);
  const totalExcessCo2 = cardData.reduce((acc, c) => acc + (parseFloat(c.totalExcess || 0) * c.co2Rate), 0);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cardData.map((res) => {
        const IconComponent = res.icon;
        return (
          <div 
            key={res.key}
            className={`relative overflow-hidden rounded-xl bg-slate-800/80 border ${res.borderColor} p-4 shadow-sm hover:border-slate-600 transition-all`}
          >
            {/* Background accent glow */}
            <div className={`absolute -right-6 -bottom-6 w-28 h-28 rounded-full bg-gradient-to-br ${res.bgGlow} blur-2xl pointer-events-none`} />

            {/* Header: Title, Icon, and Simulated Tag */}
            <div className="flex items-start justify-between">
              <div>
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{res.name}</span>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-300 border border-slate-600/40">
                    {res.simulationLabel}
                  </span>
                </div>
              </div>
              <div className={`p-2 rounded-lg bg-slate-900/60 border border-slate-700/60 ${res.accentColor}`}>
                <IconComponent className="w-4 h-4" />
              </div>
            </div>

            {/* Primary KPI: Latest Measured Demand */}
            <div className="mt-3.5">
              <div className="text-xs text-slate-400 font-medium">Current Demand Rate</div>
              <div className="flex items-baseline gap-1.5 mt-0.5">
                <span className="text-2xl font-mono font-bold text-slate-100">{res.latestValue}</span>
                <span className="text-xs font-mono font-semibold text-slate-400">{res.unit}</span>
              </div>
            </div>

            {/* Sub-metrics: Detected Anomalies & Recoverable Cost */}
            <div className="mt-4 pt-3 border-t border-slate-700/50 flex items-center justify-between text-xs">
              <div>
                <span className="text-slate-400">Anomalies: </span>
                <span className="font-semibold text-slate-200">{res.totalAnomalies}</span>
                {res.criticalCount > 0 && (
                  <span className="ml-1 text-red-400 font-medium" title="Critical or High severity">
                    ({res.criticalCount} high)
                  </span>
                )}
              </div>
              <div className="font-mono text-emerald-400 font-semibold" title="Potential recoverable cost">
                ~${res.estimatedSavingsUsd}
              </div>
            </div>
          </div>
        );
      })}

      {/* 4th Card: Overall Recoverable Savings & AI Actions */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-slate-800/90 to-slate-900/90 border border-emerald-500/30 p-4 shadow-sm hover:border-emerald-500/50 transition-all">
        <div className="absolute -right-6 -bottom-6 w-28 h-28 rounded-full bg-emerald-500/10 blur-2xl pointer-events-none" />

        <div className="flex items-start justify-between">
          <div>
            <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Mitigation Impact</span>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                <Sparkles className="w-2.5 h-2.5" />
                Gemini HITL
              </span>
            </div>
          </div>
          <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
            <DollarSign className="w-4 h-4" />
          </div>
        </div>

        <div className="mt-3.5">
          <div className="text-xs text-slate-400 font-medium">Total Recoverable Waste</div>
          <div className="flex items-baseline gap-1 mt-0.5">
            <span className="text-2xl font-mono font-bold text-emerald-300">
              ${totalEstimatedUsd.toFixed(2)}
            </span>
            <span className="text-xs text-slate-400 font-medium">USD</span>
          </div>
        </div>

        <div className="mt-4 pt-3 border-t border-slate-700/50 flex items-center justify-between text-xs">
          <div className="text-slate-400">
            Carbon Avoidance: <span className="text-emerald-400 font-mono font-semibold">{totalExcessCo2.toFixed(1)} kg</span>
          </div>
          <div className="text-slate-300">
            Approved: <span className="font-semibold text-emerald-400 font-mono">{totalApproved}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
