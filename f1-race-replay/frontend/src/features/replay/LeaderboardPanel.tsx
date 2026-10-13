import React, { useState } from 'react';
import { LeaderboardEntry, LeaderboardSnapshot, WeatherSnapshot } from '../../types/f1';
import { CloudRain, Droplets, Flame, Thermometer, Trophy, Wind } from 'lucide-react';

interface LeaderboardPanelProps {
  leaderboard: LeaderboardSnapshot | null;
  weather: WeatherSnapshot | null | undefined;
  liveStandings?: Record<string, number>;
  selectedDriver: string | null;
  compareDriver: string | null;
  onSelectDriver: (code: string) => void;
  onSelectCompareDriver: (code: string) => void;
}

const TYRE_BADGE_COLORS: Record<string, { bg: string; text: string; short: string }> = {
  SOFT: { bg: 'bg-red-500/20 border-red-500', text: 'text-red-400', short: 'S' },
  MEDIUM: { bg: 'bg-yellow-500/20 border-yellow-400', text: 'text-yellow-300', short: 'M' },
  HARD: { bg: 'bg-slate-200/20 border-slate-200', text: 'text-slate-100', short: 'H' },
  INTERMEDIATE: { bg: 'bg-emerald-500/20 border-emerald-400', text: 'text-emerald-300', short: 'I' },
  WET: { bg: 'bg-sky-500/20 border-sky-400', text: 'text-sky-300', short: 'W' },
};

const FIA_POINTS_BY_POS: Record<number, number> = {
  1: 25,
  2: 18,
  3: 15,
  4: 12,
  5: 10,
  6: 8,
  7: 6,
  8: 4,
  9: 2,
  10: 1,
};

export const LeaderboardPanel: React.FC<LeaderboardPanelProps> = ({
  leaderboard,
  weather,
  liveStandings,
  selectedDriver,
  compareDriver,
  onSelectDriver,
  onSelectCompareDriver,
}) => {
  const [gapMode, setGapMode] = useState<'leader' | 'interval'>('leader');
  const [showLivePoints, setShowLivePoints] = useState(false);

  const entries: LeaderboardEntry[] = leaderboard?.entries || [];

  return (
    <div className="bg-[#121722] border border-[#263046] rounded-xl flex flex-col h-full overflow-hidden">
      {/* Weather Telemetry Strip */}
      {weather && (
        <div className="px-3 py-2 bg-[#161c2a] border-b border-[#263046] grid grid-cols-4 gap-1.5 text-[11px] font-mono">
          <div className="flex items-center gap-1 text-slate-300" title="Track Surface Temperature">
            <Flame className="w-3.5 h-3.5 text-orange-400 shrink-0" />
            <span>TRK {weather.track_temp ?? '--'}°C</span>
          </div>
          <div className="flex items-center gap-1 text-slate-300" title="Ambient Air Temperature">
            <Thermometer className="w-3.5 h-3.5 text-sky-400 shrink-0" />
            <span>AIR {weather.air_temp ?? '--'}°C</span>
          </div>
          <div className="flex items-center gap-1 text-slate-300" title="Relative Humidity">
            <Droplets className="w-3.5 h-3.5 text-blue-400 shrink-0" />
            <span>{weather.humidity ?? '--'}%</span>
          </div>
          <div className="flex items-center gap-1 text-slate-300" title="Track Condition / Wind">
            {weather.rain_state === 'RAIN' ? (
              <>
                <CloudRain className="w-3.5 h-3.5 text-sky-400 shrink-0" />
                <span className="text-sky-300 font-bold">WET</span>
              </>
            ) : (
              <>
                <Wind className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                <span>{weather.wind_speed ?? '1.4'}m/s</span>
              </>
            )}
          </div>
        </div>
      )}

      {/* Leaderboard Header with Gap Mode Toggle */}
      <div className="px-3 py-2.5 border-b border-[#263046] flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-[#E10600]" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
            Live Timing Tower
          </h3>
        </div>

        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setGapMode(gapMode === 'leader' ? 'interval' : 'leader')}
            className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-[#192030] hover:bg-[#263046] text-slate-200 border border-[#263046] transition"
            title="Toggle between Gap to Leader (L) and Interval to Car Ahead (I)"
          >
            {gapMode === 'leader' ? 'GAP: LEADER [L]' : 'GAP: INTERVAL [I]'}
          </button>

          <button
            type="button"
            onClick={() => setShowLivePoints(!showLivePoints)}
            className={`p-1 rounded border transition ${
              showLivePoints
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/50'
                : 'bg-[#192030] text-slate-400 border-[#263046] hover:text-white'
            }`}
            title="Show Live FIA Points Awarded"
          >
            <Trophy className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Column Subheaders */}
      <div className="px-3 py-1.5 bg-[#0f131d] border-b border-[#263046] grid grid-cols-12 text-[10px] font-mono text-slate-400 uppercase">
        <span className="col-span-2">POS</span>
        <span className="col-span-3">DRIVER</span>
        <span className="col-span-3 text-right">
          {gapMode === 'leader' ? 'LEADER' : 'INT'}
        </span>
        <span className="col-span-2 text-center">TYRE</span>
        <span className="col-span-2 text-right">{showLivePoints ? 'PTS' : 'SPD'}</span>
      </div>

      {/* Driver Rows */}
      <div className="flex-1 overflow-y-auto divide-y divide-[#1e2638]">
        {entries.map((entry) => {
          const isPrimary = entry.code === selectedDriver;
          const isCompare = entry.code === compareDriver;
          const compoundUpper = (entry.tyre_compound || 'MEDIUM').toUpperCase();
          const tyreStyle = TYRE_BADGE_COLORS[compoundUpper] || TYRE_BADGE_COLORS.MEDIUM;
          const pts = liveStandings?.[entry.code] ?? FIA_POINTS_BY_POS[entry.position] ?? 0;

          const gapText =
            entry.position === 1
              ? 'LEADER'
              : gapMode === 'leader'
              ? `+${entry.gap_to_leader_s.toFixed(1)}s`
              : `+${entry.interval_s.toFixed(1)}s`;

          return (
            <div
              key={entry.code}
              onClick={() => onSelectDriver(entry.code)}
              onContextMenu={(e) => {
                e.preventDefault();
                onSelectCompareDriver(entry.code);
              }}
              className={`px-3 py-1.5 grid grid-cols-12 items-center text-xs font-mono cursor-pointer transition ${
                isPrimary
                  ? 'bg-[#E10600]/15 border-l-2 border-l-[#E10600]'
                  : isCompare
                  ? 'bg-sky-500/15 border-l-2 border-l-sky-400'
                  : 'hover:bg-[#192030]'
              } ${entry.is_out ? 'opacity-45' : ''}`}
              title="Left-click: Primary telemetry driver | Right-click: Comparison driver"
            >
              {/* Position */}
              <div className="col-span-2 flex items-center gap-1.5">
                <span className="w-5 text-slate-300 font-bold">{entry.position}</span>
                <span
                  className="w-1 h-4 rounded-full"
                  style={{ backgroundColor: entry.color || '#38bdf8' }}
                />
              </div>

              {/* Driver Code & Status */}
              <div className="col-span-3 flex items-center gap-1">
                <span className="font-bold text-white">{entry.code}</span>
                {entry.drs_active && (
                  <span className="px-1 py-0.2 rounded text-[9px] bg-emerald-500/20 text-emerald-300 font-bold">
                    DRS
                  </span>
                )}
              </div>

              {/* Gap / Interval / Status */}
              <div className="col-span-3 text-right">
                {entry.is_out ? (
                  <span className="px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 text-[10px] font-bold">
                    OUT
                  </span>
                ) : entry.in_pit ? (
                  <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 text-[10px] font-bold">
                    IN PIT
                  </span>
                ) : (
                  <span className="text-slate-300">{gapText}</span>
                )}
              </div>

              {/* Tyre Compound + Age */}
              <div className="col-span-2 flex items-center justify-center gap-1">
                <span
                  className={`w-4 h-4 rounded-full border flex items-center justify-center text-[10px] font-bold ${tyreStyle.bg} ${tyreStyle.text}`}
                >
                  {tyreStyle.short}
                </span>
                <span className="text-[10px] text-slate-400">{entry.tyre_life}L</span>
              </div>

              {/* Speed or Live Points */}
              <div className="col-span-2 text-right">
                {showLivePoints ? (
                  <span className="text-amber-300 font-bold">
                    {pts > 0 ? `+${pts}` : '-'}
                  </span>
                ) : (
                  <span className="text-slate-400">{Math.round(entry.speed_kph)}</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer helper */}
      <div className="px-3 py-1.5 bg-[#0f131d] border-t border-[#263046] flex items-center justify-between text-[10px] text-slate-400 font-mono">
        <span>L-Click: Primary ({selectedDriver || '-'})</span>
        <span>R-Click: Compare ({compareDriver || '-'})</span>
      </div>
    </div>
  );
};
