import React from 'react';
import { DriverStrategySummary } from '../../types/f1';
import { Activity, AlertCircle, CircleDot, ShieldCheck, Wrench } from 'lucide-react';

interface TyreStrategyPanelProps {
  strategies: DriverStrategySummary[];
  totalLaps: number;
  selectedDriver: string;
  onSelectDriver: (code: string) => void;
}

const COMPOUND_COLORS: Record<string, string> = {
  SOFT: '#ef4444',
  MEDIUM: '#eab308',
  HARD: '#f8fafc',
  INTERMEDIATE: '#10b981',
  WET: '#0284c7',
};

export const TyreStrategyPanel: React.FC<TyreStrategyPanelProps> = ({
  strategies,
  totalLaps,
  selectedDriver,
  onSelectDriver,
}) => {
  const maxLaps = Math.max(1, totalLaps || 58);
  const selectedStrategy = strategies.find((s) => s.code === selectedDriver);
  const deg = selectedStrategy?.degradation;

  return (
    <div className="bg-[#121722] border border-[#263046] rounded-xl p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-[#263046] pb-3">
        <div className="flex items-center gap-2">
          <CircleDot className="w-4 h-4 text-[#E10600]" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">
            Pirelli Tyre Strategy & Bayesian Degradation
          </h3>
        </div>
        <span className="text-xs font-mono text-slate-400">{maxLaps} Laps Distance</span>
      </div>

      {/* Selected Driver Bayesian Degradation Health Card */}
      {deg && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 bg-[#192030] p-3.5 rounded-lg border border-[#263046] font-mono text-xs">
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm border-2"
              style={{
                borderColor: COMPOUND_COLORS[deg.compound.toUpperCase()] || '#eab308',
                color: COMPOUND_COLORS[deg.compound.toUpperCase()] || '#eab308',
              }}
            >
              {deg.compound[0] || 'M'}
            </div>
            <div>
              <span className="text-slate-400 block text-[10px]">CURRENT COMPOUND</span>
              <span className="font-bold text-white text-sm">{deg.compound}</span>
              <span className="text-slate-400 text-[11px] block">{deg.laps_on_tyre} Laps Used</span>
            </div>
          </div>

          <div>
            <span className="text-slate-400 block text-[10px]">BAYESIAN TYRE HEALTH</span>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex-1 bg-[#0b0e14] h-2 rounded-full overflow-hidden border border-[#263046]">
                <div
                  className={`h-full rounded-full ${
                    deg.health_pct > 65
                      ? 'bg-emerald-400'
                      : deg.health_pct > 35
                      ? 'bg-yellow-400'
                      : 'bg-red-500'
                  }`}
                  style={{ width: `${Math.min(100, Math.max(0, deg.health_pct))}%` }}
                />
              </div>
              <span className="font-bold text-white">{deg.health_pct}%</span>
            </div>
            <span className="text-[10px] text-slate-400">
              Uncertainty: ±{deg.uncertainty_s}s
            </span>
          </div>

          <div>
            <span className="text-slate-400 block text-[10px]">PACE PENALTY & DEG RATE</span>
            <div className="font-bold text-amber-300 text-sm mt-0.5">
              +{deg.expected_delta_s}s / lap
            </div>
            <span className="text-[10px] text-slate-400">
              Deg: {deg.degradation_rate_s_per_lap}s per lap
            </span>
          </div>

          <div>
            <span className="text-slate-400 block text-[10px]">OVERDRIVING DETECTION</span>
            <div className="flex items-center gap-1.5 mt-1">
              {deg.overdriving ? (
                <>
                  <AlertCircle className="w-4 h-4 text-red-400" />
                  <span className="font-bold text-red-400">OVERHEATING / SLIDING</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4 text-emerald-400" />
                  <span className="font-bold text-emerald-400">OPTIMAL MANAGEMENT</span>
                </>
              )}
            </div>
            <span className="text-[10px] text-slate-400 truncate block">
              {deg.summary_text}
            </span>
          </div>
        </div>
      )}

      {/* Horizontal Stint Bars for All Drivers */}
      <div className="max-h-[380px] overflow-y-auto space-y-2 pr-1">
        {strategies.map((strat) => {
          const isSelected = strat.code === selectedDriver;
          return (
            <div
              key={strat.code}
              onClick={() => onSelectDriver(strat.code)}
              className={`p-2 rounded-lg border cursor-pointer transition flex items-center gap-3 ${
                isSelected
                  ? 'bg-[#192030] border-[#E10600]'
                  : 'bg-[#0f131d] border-[#263046] hover:bg-[#161c2a]'
              }`}
            >
              {/* Driver Pill */}
              <div className="w-16 flex items-center gap-1.5 shrink-0 font-mono text-xs">
                <span
                  className="w-1.5 h-4 rounded-full"
                  style={{ backgroundColor: strat.color || '#38bdf8' }}
                />
                <span className="font-bold text-white">{strat.code}</span>
                <span className="text-[10px] text-slate-400">
                  {strat.pit_stops}P
                </span>
              </div>

              {/* Stint Bars Track */}
              <div className="flex-1 h-6 bg-[#0b0e14] rounded border border-[#263046] flex overflow-hidden relative">
                {strat.stints.map((stint, sIdx) => {
                  const widthPct = Math.max(1, (stint.lap_count / maxLaps) * 100);
                  const compColor =
                    COMPOUND_COLORS[stint.compound.toUpperCase()] || '#eab308';

                  return (
                    <div
                      key={sIdx}
                      style={{
                        width: `${widthPct}%`,
                        backgroundColor: compColor,
                      }}
                      className="h-full relative group border-r border-[#0b0e14] flex items-center justify-center text-[10px] font-mono font-bold text-black"
                      title={`${stint.compound} • Laps ${stint.start_lap}-${stint.end_lap} (${stint.lap_count} laps)`}
                    >
                      <span className="truncate px-0.5">
                        {stint.compound[0]}
                        {stint.lap_count >= 6 ? ` (${stint.lap_count})` : ''}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Compound Legend */}
      <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-300 pt-1 border-t border-[#263046]">
        {Object.entries(COMPOUND_COLORS).map(([comp, color]) => (
          <div key={comp} className="flex items-center gap-1.5">
            <span
              className="w-3 h-3 rounded-full border border-black/40"
              style={{ backgroundColor: color }}
            />
            <span>{comp}</span>
          </div>
        ))}
        <span className="text-slate-500 ml-auto flex items-center gap-1">
          <Wrench className="w-3.5 h-3.5" /> Pit Stop Windows indicated by stint boundaries
        </span>
      </div>
    </div>
  );
};
