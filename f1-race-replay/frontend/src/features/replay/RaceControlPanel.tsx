import React from 'react';
import { RaceControlMessage, TrackStatusPeriod } from '../../types/f1';
import { Flag, Radio, ShieldAlert } from 'lucide-react';

interface RaceControlPanelProps {
  messages: RaceControlMessage[];
  trackStatusPeriods: TrackStatusPeriod[];
  currentTimeSeconds: number;
  onSeekToTime: (timeSeconds: number) => void;
}

export const RaceControlPanel: React.FC<RaceControlPanelProps> = ({
  messages,
  trackStatusPeriods,
  currentTimeSeconds,
  onSeekToTime,
}) => {
  const formatTime = (t: number) => {
    const mins = Math.floor(t / 60);
    const secs = Math.floor(t % 60);
    return `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      {/* Left 2 Columns: Chronological FIA Race Control Stream */}
      <div className="lg:col-span-2 bg-[#121722] border border-[#263046] rounded-xl p-4 flex flex-col gap-3">
        <div className="flex items-center justify-between border-b border-[#263046] pb-2.5">
          <div className="flex items-center gap-2">
            <Radio className="w-4 h-4 text-[#E10600]" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-white">
              FIA Race Control Feed
            </h3>
          </div>
          <span className="text-xs font-mono text-slate-400">
            {messages.length} Official Messages
          </span>
        </div>

        <div className="max-h-[420px] overflow-y-auto space-y-2 pr-1">
          {messages.map((msg, idx) => {
            const isActiveOrPast = msg.time <= currentTimeSeconds;
            const catUpper = (msg.category || '').toUpperCase();
            const flagUpper = (msg.flag || '').toUpperCase();
            const badgeColor =
              catUpper.includes('SAFETY') || flagUpper.includes('SC')
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40'
                : flagUpper.includes('RED')
                ? 'bg-red-500/20 text-red-300 border-red-500/40'
                : flagUpper.includes('YELLOW')
                ? 'bg-yellow-500/20 text-yellow-300 border-yellow-500/40'
                : 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';

            return (
              <div
                key={`${msg.time}-${idx}`}
                onClick={() => onSeekToTime(msg.time)}
                className={`p-3 rounded-lg border transition cursor-pointer flex items-start justify-between gap-3 ${
                  isActiveOrPast
                    ? 'bg-[#192030] border-[#263046] hover:border-slate-500'
                    : 'bg-[#121722]/60 border-[#1e2638] opacity-60 hover:opacity-90'
                }`}
                title="Click to jump replay to this Race Control message timestamp"
              >
                <div className="flex items-start gap-3">
                  <span
                    className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold border shrink-0 mt-0.5 ${badgeColor}`}
                  >
                    {msg.flag || msg.category || 'INFO'}
                  </span>
                  <div>
                    <p className="text-xs font-medium text-slate-100">{msg.message}</p>
                    <span className="text-[10px] font-mono text-slate-400">
                      Category: {msg.category}
                      {msg.sector ? ` • Sector ${msg.sector}` : ''}
                    </span>
                  </div>
                </div>
                <span className="text-xs font-mono text-slate-400 shrink-0">
                  {formatTime(msg.time)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Right Column: Track Status Summary & Safety Car Simulation Note */}
      <div className="bg-[#121722] border border-[#263046] rounded-xl p-4 flex flex-col gap-4">
        <div className="flex items-center gap-2 border-b border-[#263046] pb-2.5">
          <Flag className="w-4 h-4 text-amber-400" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">
            Track Status Periods
          </h3>
        </div>

        <div className="space-y-2 max-h-[260px] overflow-y-auto">
          {trackStatusPeriods.map((period, idx) => (
            <div
              key={`${period.status}-${period.start_time}-${idx}`}
              onClick={() => onSeekToTime(period.start_time)}
              className="p-2.5 rounded-lg bg-[#192030] border border-[#263046] hover:border-slate-500 cursor-pointer flex items-center justify-between text-xs font-mono"
            >
              <div>
                <div className="font-bold text-slate-200">
                  {period.label || `Status ${period.status}`}
                </div>
                <div className="text-[10px] text-slate-400">
                  Lap {period.start_lap ?? 1} → Lap {period.end_lap ?? 'End'}
                </div>
              </div>
              <span className="text-slate-300">{formatTime(period.start_time)}</span>
            </div>
          ))}
        </div>

        {/* Explicit Safety Car Approximation Disclosure */}
        <div className="mt-auto p-3 rounded-lg bg-amber-500/10 border border-amber-500/30 text-xs text-amber-200/90 space-y-1.5">
          <div className="flex items-center gap-1.5 font-bold text-amber-300">
            <ShieldAlert className="w-4 h-4 shrink-0" />
            <span>Approximated Safety Car Telemetry</span>
          </div>
          <p className="text-[11px] leading-relaxed text-amber-100/80">
            Official FIA / FastF1 timing feeds provide track-status deployment timestamps (Code 4
            SC, Code 6 VSC) but do not broadcast real-time GPS coordinates for the Safety Car.
            When deployed, the Safety Car position on the circuit map is deterministically
            simulated ahead of the race leader.
          </p>
        </div>
      </div>
    </div>
  );
};
