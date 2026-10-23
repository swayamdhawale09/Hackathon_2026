import React, { useState, useMemo } from 'react';
import { 
  AlertTriangle, 
  Sparkles, 
  Zap, 
  Droplets, 
  Flame, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  Layers, 
  ChevronRight,
  Search
} from 'lucide-react';

export default function AnomalyFeed({ 
  anomalies = [], 
  proposals = [],
  onInvestigate,
  investigatingId,
}) {
  const [resourceFilter, setResourceFilter] = useState('all');
  const [severityFilter, setSeverityFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Map proposals by anomaly_id for quick status lookup
  const proposalsByAnomaly = useMemo(() => {
    const map = new Map();
    proposals.forEach((p) => {
      map.set(p.anomaly_id, p);
    });
    return map;
  }, [proposals]);

  // Filtered list
  const filteredAnomalies = useMemo(() => {
    return anomalies.filter((a) => {
      if (resourceFilter !== 'all' && a.resource_type !== resourceFilter) return false;
      if (severityFilter !== 'all' && a.severity !== severityFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesId = a.anomaly_id.toLowerCase().includes(q);
        const matchesEquip = (a.supporting_evidence?.equipment_type || '').toLowerCase().includes(q);
        const matchesNotes = (a.supporting_evidence?.equipment_notes || '').toLowerCase().includes(q);
        if (!matchesId && !matchesEquip && !matchesNotes) return false;
      }
      return true;
    });
  }, [anomalies, resourceFilter, severityFilter, searchQuery]);

  // Severity styling helper
  const getSeverityBadge = (sev) => {
    switch (sev) {
      case 'critical':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-red-500/15 text-red-400 border border-red-500/30 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
            Critical
          </span>
        );
      case 'high':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-orange-500/15 text-orange-400 border border-orange-500/30">
            High
          </span>
        );
      case 'medium':
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wider bg-amber-500/15 text-amber-300 border border-amber-500/30">
            Medium
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[11px] font-medium uppercase tracking-wider bg-sky-500/15 text-sky-400 border border-sky-500/30">
            Low
          </span>
        );
    }
  };

  // Resource Icon helper
  const getResourceIcon = (type) => {
    switch (type) {
      case 'electricity':
        return <Zap className="w-3.5 h-3.5 text-emerald-400" />;
      case 'water':
        return <Droplets className="w-3.5 h-3.5 text-sky-400" />;
      case 'fuel':
        return <Flame className="w-3.5 h-3.5 text-amber-400" />;
      default:
        return <Layers className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="rounded-xl bg-slate-800/80 border border-slate-700/80 p-5 shadow-sm">
      
      {/* Header & Filter Controls */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-4 border-b border-slate-700/60">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" />
              Detected Waste Anomalies
            </h2>
            <span className="px-2 py-0.5 rounded-full text-xs font-mono font-semibold bg-slate-700 text-slate-200">
              {filteredAnomalies.length} / {anomalies.length}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Deterministic baseline violations flagged during zero-occupancy and after-hours schedules.
          </p>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs">
          
          {/* Quick Search */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search equipment, notes..."
              className="pl-8 pr-3 py-1 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 w-44"
            />
          </div>

          {/* Resource Filter */}
          <div className="flex items-center gap-1 bg-slate-900/80 border border-slate-700/70 rounded-lg p-1">
            {['all', 'electricity', 'water', 'fuel'].map((r) => (
              <button
                key={r}
                onClick={() => setResourceFilter(r)}
                className={`px-2.5 py-1 rounded-md capitalize transition-colors font-medium ${
                  resourceFilter === r
                    ? 'bg-slate-800 text-slate-100 font-semibold border border-slate-600/50'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {r === 'all' ? 'All Resources' : r}
              </button>
            ))}
          </div>

          {/* Severity Filter */}
          <div className="flex items-center gap-1 bg-slate-900/80 border border-slate-700/70 rounded-lg p-1">
            {['all', 'critical', 'high', 'medium'].map((s) => (
              <button
                key={s}
                onClick={() => setSeverityFilter(s)}
                className={`px-2.5 py-1 rounded-md capitalize transition-colors font-medium ${
                  severityFilter === s
                    ? 'bg-slate-800 text-slate-100 font-semibold border border-slate-600/50'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Anomalies List */}
      <div className="mt-4 divide-y divide-slate-700/50 max-h-[500px] overflow-y-auto pr-1">
        {filteredAnomalies.length === 0 ? (
          <div className="py-12 flex flex-col items-center justify-center text-slate-400 text-center">
            <CheckCircle2 className="w-10 h-10 text-emerald-500/60 mb-2" />
            <p className="text-sm font-medium text-slate-300">No anomalies matching selected filters.</p>
            <p className="text-xs text-slate-500 mt-1">Try resetting the search or filters above.</p>
          </div>
        ) : (
          filteredAnomalies.map((anom) => {
            const prop = proposalsByAnomaly.get(anom.anomaly_id);
            const isInvestigatingThis = investigatingId === anom.anomaly_id;
            const evidence = anom.supporting_evidence || {};

            return (
              <div 
                key={anom.anomaly_id}
                className="py-3.5 px-2 hover:bg-slate-750/50 rounded-lg transition-colors flex flex-col sm:flex-row sm:items-center justify-between gap-3 group"
              >
                {/* Left info column */}
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Resource tag */}
                    <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-slate-900/80 border border-slate-700 text-slate-300 text-xs font-medium capitalize">
                      {getResourceIcon(anom.resource_type)}
                      <span>{anom.resource_type}</span>
                    </div>

                    {/* Severity Badge */}
                    {getSeverityBadge(anom.severity)}

                    {/* Timestamp */}
                    <span className="text-xs font-mono text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {anom.timestamp}
                    </span>

                    {/* ID */}
                    <span className="text-[11px] font-mono text-slate-500 hidden md:inline">
                      ({anom.anomaly_id})
                    </span>
                  </div>

                  {/* Measurement Metrics Row */}
                  <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
                    <div>
                      <span className="text-slate-400">Actual: </span>
                      <span className="font-mono font-bold text-slate-200">
                        {anom.actual_usage.toFixed(1)} {anom.unit}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400">Baseline: </span>
                      <span className="font-mono font-medium text-sky-400">
                        {anom.expected_usage.toFixed(1)} {anom.unit}
                      </span>
                    </div>

                    <div>
                      <span className="text-slate-400">Excess: </span>
                      <span className="font-mono font-bold text-amber-400">
                        +{anom.excess_consumption.toFixed(1)} {anom.unit}
                        {evidence.ratio_to_baseline ? ` (+${Math.round((evidence.ratio_to_baseline - 1) * 100)}%)` : ''}
                      </span>
                    </div>

                    {evidence.occupancy !== undefined && (
                      <div className="text-slate-400">
                        Occupancy: <span className="font-mono font-medium text-slate-300">{evidence.occupancy}</span>
                      </div>
                    )}
                  </div>

                  {/* Supporting Context / Equipment notes snippet */}
                  {(evidence.equipment_type || evidence.equipment_notes) && (
                    <div className="mt-1 text-xs text-slate-400 line-clamp-1">
                      <span className="text-slate-500">Equipment:</span>{' '}
                      <span className="text-slate-300 font-medium">{evidence.equipment_type}</span>
                      {evidence.equipment_notes && (
                        <span className="text-slate-400 italic"> — "{evidence.equipment_notes}"</span>
                      )}
                    </div>
                  )}
                </div>

                {/* Right Action / Proposal Status column */}
                <div className="flex items-center gap-2 self-start sm:self-center shrink-0">
                  {prop ? (
                    /* Already has a proposal / investigated */
                    <div className="flex items-center gap-2">
                      <span className={`px-2.5 py-1 rounded-md text-xs font-medium border flex items-center gap-1 ${
                        prop.status === 'approved'
                          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                          : prop.status === 'rejected'
                          ? 'bg-red-500/10 border-red-500/30 text-red-300'
                          : 'bg-amber-500/10 border-amber-500/30 text-amber-300'
                      }`}>
                        {prop.status === 'approved' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />}
                        {prop.status === 'rejected' && <XCircle className="w-3.5 h-3.5 text-red-400" />}
                        {prop.status === 'pending_review' && <Clock className="w-3.5 h-3.5 text-amber-400" />}
                        <span className="capitalize">{prop.status.replace('_', ' ')}</span>
                      </span>

                      <button
                        onClick={() => onInvestigate(anom)}
                        className="px-2.5 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-650 text-slate-200 text-xs font-medium border border-slate-600 transition-colors flex items-center gap-1"
                        title="Review investigation proposal"
                      >
                        <span>View</span>
                        <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                      </button>
                    </div>
                  ) : (
                    /* Needs investigation */
                    <button
                      onClick={() => onInvestigate(anom)}
                      disabled={isInvestigatingThis}
                      className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 active:from-emerald-700 active:to-teal-700 text-white text-xs font-semibold shadow-sm shadow-emerald-950/40 border border-emerald-400/30 flex items-center gap-1.5 transition-all disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                    >
                      <Sparkles className={`w-3.5 h-3.5 text-emerald-200 ${isInvestigatingThis ? 'animate-spin' : ''}`} />
                      <span>{isInvestigatingThis ? 'Investigating...' : 'Investigate with AI'}</span>
                    </button>
                  )}
                </div>

              </div>
            );
          })
        )}
      </div>

    </div>
  );
}
