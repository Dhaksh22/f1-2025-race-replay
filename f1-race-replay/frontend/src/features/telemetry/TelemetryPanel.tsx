import React, { useEffect, useState } from 'react';
import { DriverInfo, TelemetryComparisonResponse } from '../../types/f1';
import { fetchTelemetryComparison } from '../../services/api';
import { Activity, Gauge, Zap } from 'lucide-react';

interface TelemetryPanelProps {
  roundNumber: number;
  sessionType: string;
  selectedDriver: string;
  compareDriver: string | null;
  drivers: DriverInfo[];
  currentLap: number;
  onSelectCompareDriver: (code: string) => void;
}

export const TelemetryPanel: React.FC<TelemetryPanelProps> = ({
  roundNumber,
  sessionType,
  selectedDriver,
  compareDriver,
  drivers,
  currentLap,
  onSelectCompareDriver,
}) => {
  const [telemetryMode, setTelemetryMode] = useState<'lap' | 'time' | 'quali_segment' | 'best_lap'>('lap');
  const [selectedLap, setSelectedLap] = useState<number>(currentLap || 1);
  const [telemetryData, setTelemetryData] = useState<TelemetryComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchTelemetryComparison({
      roundNumber,
      sessionType,
      driver: selectedDriver,
      compareWith: compareDriver || undefined,
      mode: telemetryMode,
      lap: selectedLap,
    })
      .then((data) => {
        if (isMounted) setTelemetryData(data);
      })
      .catch((err) => {
        if (isMounted) setError(err.message || 'Failed to load telemetry comparison');
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [roundNumber, sessionType, selectedDriver, compareDriver, telemetryMode, selectedLap]);

  const pSamples = telemetryData?.primary?.samples || [];
  const cSamples = telemetryData?.comparison?.samples || [];
  const pColor = telemetryData?.primary?.color || '#FF8000';
  const cColor = telemetryData?.comparison?.color || '#3671C6';

  // SVG dimensions for sparkline charts
  const width = 720;
  const height = 110;
  const pad = 24;

  const maxDist = Math.max(
    1,
    ...pSamples.map((s) => s.dist_m || 0),
    ...cSamples.map((s) => s.dist_m || 0)
  );

  const renderTrace = (
    samples: typeof pSamples,
    getter: (s: typeof pSamples[0]) => number,
    minVal: number,
    maxVal: number,
    color: string,
    strokeWidth = 1.8
  ) => {
    if (!samples.length) return '';
    const points = samples.map((s) => {
      const x = pad + ((s.dist_m || 0) / maxDist) * (width - pad * 2);
      const val = getter(s);
      const normY = Math.max(0, Math.min(1, (val - minVal) / (maxVal - minVal || 1)));
      const y = height - pad - normY * (height - pad * 2);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    });
    return (
      <polyline
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points.join(' ')}
      />
    );
  };

  return (
    <div className="bg-[#121722] border border-[#263046] rounded-xl p-4 flex flex-col gap-4">
      {/* Top Header & Comparison Selector */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#263046] pb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-[#E10600]" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">
            High-Frequency Telemetry Comparison
          </h3>
        </div>

        {/* Controls: Mode, Lap Selector, Compare Driver Picker */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Mode Switcher */}
          <div className="flex rounded-lg bg-[#192030] p-0.5 border border-[#263046]">
            {(['lap', 'time', 'quali_segment', 'best_lap'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setTelemetryMode(m)}
                className={`px-2.5 py-1 rounded text-[11px] font-mono font-semibold uppercase transition ${
                  telemetryMode === m
                    ? 'bg-[#E10600] text-white'
                    : 'text-slate-400 hover:text-white hover:bg-[#263046]'
                }`}
              >
                {m.replace('_', ' ')}
              </button>
            ))}
          </div>

          {/* Lap Selector (if in lap mode) */}
          {telemetryMode === 'lap' && (
            <div className="flex items-center gap-1 bg-[#192030] px-2 py-1 rounded-lg border border-[#263046] text-xs font-mono">
              <span className="text-slate-400">LAP</span>
              <input
                type="number"
                min={1}
                max={78}
                value={selectedLap}
                onChange={(e) => setSelectedLap(Math.max(1, Number(e.target.value)))}
                className="w-12 bg-transparent text-white font-bold text-center border-b border-slate-600 focus:outline-none focus:border-[#E10600]"
              />
            </div>
          )}

          {/* Compare Driver Picker */}
          <div className="flex items-center gap-1 bg-[#192030] px-2.5 py-1 rounded-lg border border-[#263046] text-xs font-mono">
            <span className="text-slate-400">VS:</span>
            <select
              value={compareDriver || ''}
              onChange={(e) => onSelectCompareDriver(e.target.value)}
              className="bg-transparent text-sky-400 font-bold focus:outline-none cursor-pointer"
            >
              <option value="" className="bg-[#121722] text-slate-400">
                (None)
              </option>
              {drivers
                .filter((d) => d.code !== selectedDriver)
                .map((d) => (
                  <option key={d.code} value={d.code} className="bg-[#121722] text-white">
                    {d.code} — {d.full_name}
                  </option>
                ))}
            </select>
          </div>
        </div>
      </div>

      {/* Driver Legend & Delta Pill Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs font-mono bg-[#192030]/60 p-2.5 rounded-lg border border-[#263046]">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 font-bold">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: pColor }} />
            <span className="text-white">{selectedDriver}</span>
            <span className="text-slate-400 text-[11px]">
              (MAX: {telemetryData?.primary?.max_speed_kph ?? '--'} km/h)
            </span>
          </div>

          {compareDriver && telemetryData?.comparison && (
            <div className="flex items-center gap-1.5 font-bold">
              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: cColor }} />
              <span className="text-white">{compareDriver}</span>
              <span className="text-slate-400 text-[11px]">
                (MAX: {telemetryData.comparison.max_speed_kph ?? '--'} km/h)
              </span>
            </div>
          )}
        </div>

        {telemetryData?.delta_summary && (
          <div className="flex items-center gap-3 text-[11px]">
            <span className="text-slate-400">
              Δ Speed:{' '}
              <strong className="text-amber-300">
                {telemetryData.delta_summary.max_speed_delta_kph ?? 0} km/h
              </strong>
            </span>
            {telemetryData.delta_summary.lap_time_delta_s !== undefined && (
              <span className="text-slate-400">
                Δ Lap:{' '}
                <strong className="text-emerald-400">
                  {telemetryData.delta_summary.lap_time_delta_s}s
                </strong>
              </span>
            )}
          </div>
        )}
      </div>

      {loading && (
        <div className="py-12 text-center text-slate-400 font-mono text-xs animate-pulse">
          Loading calibrated telemetry samples...
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-500/15 border border-red-500/40 rounded-lg text-red-300 text-xs font-mono">
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-3">
          {/* 1. Speed Trace (km/h) */}
          <div className="bg-[#0f131d] rounded-lg border border-[#263046] p-2.5">
            <div className="flex items-center justify-between text-xs font-mono text-slate-300 mb-1">
              <span className="font-bold flex items-center gap-1">
                <Gauge className="w-3.5 h-3.5 text-sky-400" />
                SPEED (KM/H)
              </span>
              <span className="text-slate-500 text-[10px]">0 — 360 km/h</span>
            </div>
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-24 overflow-visible">
              <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#263046" strokeWidth={1} />
              <line x1={pad} y1={pad} x2={width - pad} y2={pad} stroke="#1e2638" strokeDasharray="3 3" strokeWidth={1} />
              {renderTrace(pSamples, (s) => s.speed_kph, 0, 360, pColor)}
              {compareDriver && renderTrace(cSamples, (s) => s.speed_kph, 0, 360, cColor)}
            </svg>
          </div>

          {/* 2. Throttle & Brake Traces (%) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="bg-[#0f131d] rounded-lg border border-[#263046] p-2.5">
              <div className="flex items-center justify-between text-xs font-mono text-slate-300 mb-1">
                <span className="font-bold text-emerald-400">THROTTLE (%)</span>
                <span className="text-slate-500 text-[10px]">0 — 100%</span>
              </div>
              <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-20 overflow-visible">
                <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#263046" strokeWidth={1} />
                {renderTrace(pSamples, (s) => s.throttle_pct, 0, 100, pColor)}
                {compareDriver && renderTrace(cSamples, (s) => s.throttle_pct, 0, 100, cColor)}
              </svg>
            </div>

            <div className="bg-[#0f131d] rounded-lg border border-[#263046] p-2.5">
              <div className="flex items-center justify-between text-xs font-mono text-slate-300 mb-1">
                <span className="font-bold text-red-400">BRAKE (%)</span>
                <span className="text-slate-500 text-[10px]">0 — 100%</span>
              </div>
              <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-20 overflow-visible">
                <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#263046" strokeWidth={1} />
                {renderTrace(pSamples, (s) => s.brake_pct, 0, 100, pColor)}
                {compareDriver && renderTrace(cSamples, (s) => s.brake_pct, 0, 100, cColor)}
              </svg>
            </div>
          </div>

          {/* 3. Gear & DRS Status Strip */}
          <div className="bg-[#0f131d] rounded-lg border border-[#263046] p-2.5">
            <div className="flex items-center justify-between text-xs font-mono text-slate-300 mb-1">
              <span className="font-bold flex items-center gap-1">
                <Zap className="w-3.5 h-3.5 text-amber-400" />
                GEAR & DRS STATUS
              </span>
              <span className="text-slate-500 text-[10px]">Gear 1 — 8</span>
            </div>
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-20 overflow-visible">
              <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#263046" strokeWidth={1} />
              {renderTrace(pSamples, (s) => s.gear, 1, 8, pColor)}
              {compareDriver && renderTrace(cSamples, (s) => s.gear, 1, 8, cColor)}
            </svg>
          </div>
        </div>
      )}
    </div>
  );
};
