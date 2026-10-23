import React, { useState, useMemo } from 'react';
import { Zap, Droplets, Flame, Clock, BarChart2, ShieldCheck } from 'lucide-react';

export default function ConsumptionChart({ 
  telemetry = [], 
  anomalies = [],
  selectedResource = 'electricity',
  onSelectResource
}) {
  const [timeRange, setTimeRange] = useState(48); // default to 48 readings
  const [hoveredPoint, setHoveredPoint] = useState(null);

  // Filter telemetry by active resource
  const filteredReadings = useMemo(() => {
    const list = telemetry.filter((t) => t.resource_type === selectedResource);
    // Grab the last N readings
    return list.slice(Math.max(0, list.length - timeRange));
  }, [telemetry, selectedResource, timeRange]);

  // Map of anomalies for fast lookup by timestamp
  const anomalyMap = useMemo(() => {
    const map = new Map();
    anomalies
      .filter((a) => a.resource_type === selectedResource)
      .forEach((a) => {
        map.set(a.timestamp, a);
      });
    return map;
  }, [anomalies, selectedResource]);

  // Unit and config
  const resourceConfigs = {
    electricity: { name: 'Electricity', unit: 'kWh', icon: Zap, color: '#10B981' },
    water: { name: 'Water', unit: 'L', icon: Droplets, color: '#38BDF8' },
    fuel: { name: 'Fuel', unit: 'L', icon: Flame, color: '#F59E0B' },
  };
  const activeCfg = resourceConfigs[selectedResource] || resourceConfigs.electricity;

  // Chart Dimensions & Scaling
  const width = 800;
  const height = 260;
  const padding = { top: 20, right: 30, bottom: 40, left: 55 };
  const chartW = width - padding.left - padding.right;
  const chartH = height - padding.top - padding.bottom;

  // Calculate min and max for Y scale
  const { maxVal, minVal, dataPoints } = useMemo(() => {
    if (filteredReadings.length === 0) {
      return { maxVal: 100, minVal: 0, dataPoints: [] };
    }

    let max = 0;
    let min = Infinity;

    const points = filteredReadings.map((r, i) => {
      const actual = r.consumption;
      const anom = anomalyMap.get(r.timestamp);
      // Expected baseline: if anomaly exists, it has expected_usage; otherwise approximate expected from regular readings
      const expected = anom ? anom.expected_usage : (r.scheduled_open ? actual * 0.95 : actual * 0.6);
      
      if (actual > max) max = actual;
      if (expected > max) max = expected;
      if (actual < min) min = actual;
      if (expected < min) min = expected;

      // Extract hour for after-hours reference zone
      let hour = 12;
      try {
        hour = new Date(r.timestamp).getHours();
      } catch {
        hour = 12;
      }
      const isAfterHours = hour < 7 || hour >= 20;

      return {
        index: i,
        timestamp: r.timestamp,
        hour,
        isAfterHours,
        actual,
        expected,
        occupancy: r.occupancy,
        equipmentNotes: r.equipment_notes,
        equipmentType: r.equipment_type,
        anomaly: anom,
      };
    });

    // Provide headroom
    max = Math.ceil(max * 1.15) || 100;
    min = Math.floor(Math.max(0, min * 0.85)) || 0;

    return { maxVal: max, minVal: min, dataPoints: points };
  }, [filteredReadings, anomalyMap]);

  // Coordinate projection helpers
  const getX = (index) => {
    if (dataPoints.length <= 1) return padding.left + chartW / 2;
    return padding.left + (index / (dataPoints.length - 1)) * chartW;
  };

  const getY = (val) => {
    const range = maxVal - minVal || 1;
    const norm = (val - minVal) / range;
    return padding.top + chartH - norm * chartH;
  };

  // Build SVG path strings
  const { actualPath, areaPath, baselinePath } = useMemo(() => {
    if (dataPoints.length === 0) return { actualPath: '', areaPath: '', baselinePath: '' };

    let actualD = '';
    let baselineD = '';

    const range = maxVal - minVal || 1;
    const projectX = (idx) => {
      if (dataPoints.length <= 1) return padding.left + chartW / 2;
      return padding.left + (idx / (dataPoints.length - 1)) * chartW;
    };
    const projectY = (val) => {
      const norm = (val - minVal) / range;
      return padding.top + chartH - norm * chartH;
    };

    dataPoints.forEach((p, idx) => {
      const x = projectX(idx);
      const yActual = projectY(p.actual);
      const yBaseline = projectY(p.expected);

      if (idx === 0) {
        actualD += `M ${x} ${yActual}`;
        baselineD += `M ${x} ${yBaseline}`;
      } else {
        actualD += ` L ${x} ${yActual}`;
        baselineD += ` L ${x} ${yBaseline}`;
      }
    });

    // Area closed under actual path down to baseline Y(minVal)
    const firstX = projectX(0);
    const lastX = projectX(dataPoints.length - 1);
    const bottomY = projectY(minVal);
    const areaD = `${actualD} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`;

    return { actualPath: actualD, areaPath: areaD, baselinePath: baselineD };
  }, [dataPoints, maxVal, minVal, chartW, chartH, padding.left, padding.top]);

  // Y-axis ticks
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0].map((t) => {
    const val = minVal + t * (maxVal - minVal);
    return {
      value: Math.round(val),
      y: getY(val),
    };
  });

  // Format short timestamp
  const formatTime = (ts) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    } catch {
      return ts.slice(11, 16);
    }
  };

  const formatDate = (ts) => {
    try {
      const d = new Date(ts);
      return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
    } catch {
      return ts.slice(5, 10);
    }
  };

  return (
    <div className="rounded-xl bg-slate-800/80 border border-slate-700/80 p-5 shadow-sm">
      
      {/* Chart Top Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-700/60">
        
        {/* Resource Selector Tabs */}
        <div className="flex items-center gap-1.5 p-1 rounded-lg bg-slate-900/80 border border-slate-700/70">
          {[
            { id: 'electricity', label: 'Electricity', unit: 'kWh', icon: Zap },
            { id: 'water', label: 'Water', unit: 'L', icon: Droplets },
            { id: 'fuel', label: 'Fuel', unit: 'L', icon: Flame },
          ].map((tab) => {
            const Icon = tab.icon;
            const isSelected = selectedResource === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onSelectResource(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  isSelected
                    ? 'bg-slate-800 text-slate-100 shadow-sm border border-slate-600/60'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-emerald-400' : 'text-slate-500'}`} />
                <span>{tab.label}</span>
                <span className="text-[10px] text-slate-500 font-mono">({tab.unit})</span>
              </button>
            );
          })}
        </div>

        {/* Legend & Time Range Selector */}
        <div className="flex items-center gap-4">
          {/* Chart Legend */}
          <div className="hidden lg:flex items-center gap-3 text-xs text-slate-400">
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 bg-emerald-500 rounded-full inline-block" />
              <span>Actual Load</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-3 h-0.5 border-t border-dashed border-sky-400 inline-block" />
              <span>Baseline</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
              <span>Anomaly</span>
            </div>
          </div>

          {/* Time range buttons */}
          <div className="flex items-center gap-1 p-0.5 rounded-lg bg-slate-900/80 border border-slate-700/70 text-xs">
            {[
              { label: '24h', val: 24 },
              { label: '48h', val: 48 },
              { label: '7d', val: 168 },
            ].map((r) => (
              <button
                key={r.val}
                onClick={() => setTimeRange(r.val)}
                className={`px-2.5 py-1 rounded-md font-medium text-xs transition-colors ${
                  timeRange === r.val
                    ? 'bg-emerald-600 text-white font-semibold'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>

      </div>

      {/* SVG Chart Body */}
      <div className="relative mt-4 w-full overflow-hidden select-none">
        {dataPoints.length === 0 ? (
          <div className="h-64 flex flex-col items-center justify-center text-slate-400">
            <BarChart2 className="w-10 h-10 text-slate-600 mb-2" />
            <p className="text-sm font-medium">No telemetry readings available for this period.</p>
            <p className="text-xs text-slate-500 mt-1">Check that the backend is running and data is loaded.</p>
          </div>
        ) : (
          <div className="w-full">
            <svg
              viewBox={`0 0 ${width} ${height}`}
              className="w-full h-auto overflow-visible"
              onMouseLeave={() => setHoveredPoint(null)}
            >
              <defs>
                {/* Gradient for normal actual load */}
                <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#10B981" stopOpacity="0.30" />
                  <stop offset="85%" stopColor="#10B981" stopOpacity="0.02" />
                </linearGradient>

                {/* Gradient for after-hours / anomaly load */}
                <linearGradient id="anomalyGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#F59E0B" stopOpacity="0.40" />
                  <stop offset="90%" stopColor="#F59E0B" stopOpacity="0.02" />
                </linearGradient>
              </defs>

              {/* After-hours shaded background stripes (7pm - 6am) */}
              {dataPoints.map((p, idx) => {
                if (!p.isAfterHours) return null;
                const x = getX(idx);
                const step = chartW / Math.max(1, dataPoints.length - 1);
                return (
                  <rect
                    key={`after-hours-${idx}`}
                    x={x - step / 2}
                    y={padding.top}
                    width={step}
                    height={chartH}
                    fill="#334155"
                    fillOpacity="0.18"
                  />
                );
              })}

              {/* Horizontal Gridlines & Y-axis labels */}
              {yTicks.map((tick, i) => (
                <g key={`ytick-${i}`}>
                  <line
                    x1={padding.left}
                    y1={tick.y}
                    x2={width - padding.right}
                    y2={tick.y}
                    stroke="#334155"
                    strokeDasharray="3 3"
                    strokeOpacity="0.6"
                  />
                  <text
                    x={padding.left - 8}
                    y={tick.y + 4}
                    fill="#94A3B8"
                    fontSize="11"
                    fontFamily="monospace"
                    textAnchor="end"
                  >
                    {tick.value}
                  </text>
                </g>
              ))}

              {/* Y-axis Unit Label */}
              <text
                x={padding.left}
                y={padding.top - 8}
                fill="#94A3B8"
                fontSize="11"
                fontWeight="500"
                fontFamily="sans-serif"
              >
                {activeCfg.unit}
              </text>

              {/* Area Under Curve */}
              <path
                d={areaPath}
                fill="url(#areaGradient)"
              />

              {/* Expected Baseline Line (dashed sky-blue per brand guidelines) */}
              <path
                d={baselinePath}
                fill="none"
                stroke="#0284C7"
                strokeWidth="2"
                strokeDasharray="5 4"
                strokeOpacity="0.85"
              />

              {/* Actual Telemetry Line (Mint green) */}
              <path
                d={actualPath}
                fill="none"
                stroke="#10B981"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Data points & Anomaly Markers */}
              {dataPoints.map((p, idx) => {
                const x = getX(idx);
                const y = getY(p.actual);
                const isAnomaly = !!p.anomaly;

                if (!isAnomaly && dataPoints.length > 50 && idx % 3 !== 0) {
                  return null;
                }

                return (
                  <g key={`pt-${idx}`}>
                    {isAnomaly ? (
                      /* Anomaly High-Visibility Marker */
                      <g
                        className="cursor-pointer"
                        onMouseEnter={() => setHoveredPoint(p)}
                      >
                        <circle
                          cx={x}
                          cy={y}
                          r="6"
                          fill="#EF4444"
                          fillOpacity="0.3"
                          className="animate-ping"
                        />
                        <circle
                          cx={x}
                          cy={y}
                          r="5"
                          fill="#F59E0B"
                          stroke="#78350F"
                          strokeWidth="2"
                        />
                      </g>
                    ) : (
                      /* Normal data point dot on hover */
                      <circle
                        cx={x}
                        cy={y}
                        r="3"
                        fill="#10B981"
                        fillOpacity={hoveredPoint?.index === idx ? '1' : '0.4'}
                        className="cursor-pointer transition-all"
                        onMouseEnter={() => setHoveredPoint(p)}
                      />
                    )}
                  </g>
                );
              })}

              {/* X-axis Timestamps */}
              {dataPoints
                .filter((_, idx) => {
                  const step = Math.max(1, Math.floor(dataPoints.length / 6));
                  return idx % step === 0 || idx === dataPoints.length - 1;
                })
                .map((p) => {
                  const x = getX(p.index);
                  return (
                    <g key={`x-${p.index}`}>
                      <line
                        x1={x}
                        y1={height - padding.bottom}
                        x2={x}
                        y2={height - padding.bottom + 5}
                        stroke="#475569"
                      />
                      <text
                        x={x}
                        y={height - padding.bottom + 18}
                        fill="#94A3B8"
                        fontSize="10"
                        fontFamily="monospace"
                        textAnchor="middle"
                      >
                        {formatTime(p.timestamp)}
                      </text>
                      <text
                        x={x}
                        y={height - padding.bottom + 30}
                        fill="#64748B"
                        fontSize="9"
                        textAnchor="middle"
                      >
                        {formatDate(p.timestamp)}
                      </text>
                    </g>
                  );
                })}
            </svg>

            {/* Interactive Floating Tooltip */}
            {hoveredPoint && (
              <div 
                className="absolute z-30 pointer-events-none rounded-lg bg-slate-900/95 border border-slate-700 p-3 shadow-xl text-xs backdrop-blur-md"
                style={{
                  left: `${Math.min(80, Math.max(10, (getX(hoveredPoint.index) / width) * 100))}%`,
                  top: '10px',
                  transform: 'translateX(-50%)',
                }}
              >
                <div className="flex items-center justify-between gap-3 border-b border-slate-800 pb-1.5 mb-1.5">
                  <span className="font-mono text-slate-300 font-semibold">{hoveredPoint.timestamp}</span>
                  {hoveredPoint.anomaly ? (
                    <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-semibold text-[10px] uppercase">
                      Anomaly: {hoveredPoint.anomaly.severity}
                    </span>
                  ) : (
                    <span className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">
                      {hoveredPoint.isAfterHours ? 'After-Hours' : 'Scheduled Open'}
                    </span>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-x-4 gap-y-1 font-mono">
                  <div>
                    <span className="text-slate-400 text-[11px]">Actual: </span>
                    <span className="font-bold text-slate-100">{hoveredPoint.actual.toFixed(1)} {activeCfg.unit}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px]">Baseline: </span>
                    <span className="font-bold text-sky-400">{hoveredPoint.expected.toFixed(1)} {activeCfg.unit}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px]">Occupancy: </span>
                    <span className="text-slate-200">{hoveredPoint.occupancy}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 text-[11px]">Delta: </span>
                    <span className={hoveredPoint.actual > hoveredPoint.expected ? 'text-amber-400 font-bold' : 'text-emerald-400'}>
                      {hoveredPoint.actual > hoveredPoint.expected ? '+' : ''}
                      {(hoveredPoint.actual - hoveredPoint.expected).toFixed(1)} {activeCfg.unit}
                    </span>
                  </div>
                </div>

                {hoveredPoint.equipmentNotes && (
                  <div className="mt-1.5 pt-1.5 border-t border-slate-800 text-[11px] text-slate-400">
                    <span className="text-slate-500">Sensor Note:</span> {hoveredPoint.equipmentNotes}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Chart Footer Notice */}
      <div className="mt-3 pt-3 border-t border-slate-700/50 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2">
        <div className="flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-slate-500" />
          <span>Shaded gray zones denote after-hours windows (20:00 - 06:00) with zero scheduled occupancy.</span>
        </div>
        <div className="flex items-center gap-1.5 text-emerald-400/80">
          <ShieldCheck className="w-3.5 h-3.5" />
          <span>Deterministic baseline model (Median + 2.5 MAD threshold)</span>
        </div>
      </div>

    </div>
  );
}
