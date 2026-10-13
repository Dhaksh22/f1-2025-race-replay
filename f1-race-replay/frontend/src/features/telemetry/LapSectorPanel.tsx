import React, { useState } from 'react';
import { DriverInfo, DriverLapSummary } from '../../types/f1';
import { Clock, Star, Timer } from 'lucide-react';

interface LapSectorPanelProps {
  lapSummaries: {
    session_best_sectors: Record<string, { time_s?: number | null; holders: string[] }>;
    drivers: Record<string, DriverLapSummary>;
  };
  drivers: DriverInfo[];
  selectedDriver: string;
  onSelectDriver: (code: string) => void;
}

export const LapSectorPanel: React.FC<LapSectorPanelProps> = ({
  lapSummaries,
  drivers,
  selectedDriver,
  onSelectDriver,
}) => {
  const [viewTab, setViewTab] = useState<'laps_table' | 'best_sectors'>('laps_table');
  const activeDriverLaps = lapSummaries.drivers[selectedDriver]?.laps || [];
  const driverSummary = lapSummaries.drivers[selectedDriver];
  const sessionBests = lapSummaries.session_best_sectors || {};

  const formatSec = (s?: number | null) => {
    if (s === null || s === undefined) return '-';
    return Number(s).toFixed(3);
  };

  const formatLapTime = (s?: number | null) => {
    if (!s) return '-';
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return `${m}:${sec.toFixed(3).padStart(6, '0')}`;
  };

  const getStatusBadge = (status?: string) => {
    if (status === 'SESSION_BEST') {
      return 'bg-purple-500/25 text-purple-300 font-bold border-purple-500/50';
    }
    if (status === 'PERSONAL_BEST') {
      return 'bg-emerald-500/25 text-emerald-300 font-bold border-emerald-500/50';
    }
    return 'text-slate-300';
  };

  return (
    <div className="bg-[#121722] border border-[#263046] rounded-xl p-4 flex flex-col gap-4">
      {/* Header & Driver Pill Selector */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[#263046] pb-3">
        <div className="flex items-center gap-2">
          <Timer className="w-4 h-4 text-[#E10600]" />
          <h3 className="text-sm font-bold uppercase tracking-wider text-white">
            Official F1 Sector Timing & Lap Analysis
          </h3>
        </div>

        {/* View Switcher: Table vs Theoretical Bests */}
        <div className="flex rounded-lg bg-[#192030] p-0.5 border border-[#263046]">
          <button
            type="button"
            onClick={() => setViewTab('laps_table')}
            className={`px-3 py-1 rounded text-xs font-mono font-semibold transition ${
              viewTab === 'laps_table'
                ? 'bg-[#E10600] text-white'
                : 'text-slate-400 hover:text-white hover:bg-[#263046]'
            }`}
          >
            Lap History
          </button>
          <button
            type="button"
            onClick={() => setViewTab('best_sectors')}
            className={`px-3 py-1 rounded text-xs font-mono font-semibold transition ${
              viewTab === 'best_sectors'
                ? 'bg-[#E10600] text-white'
                : 'text-slate-400 hover:text-white hover:bg-[#263046]'
            }`}
          >
            Ideal Lap Benchmarks
          </button>
        </div>
      </div>

      {/* Driver Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs font-mono">
        {drivers.map((d) => (
          <button
            key={d.code}
            type="button"
            onClick={() => onSelectDriver(d.code)}
            className={`px-2.5 py-1 rounded-lg border transition shrink-0 ${
              d.code === selectedDriver
                ? 'bg-[#E10600]/20 text-white border-[#E10600] font-bold'
                : 'bg-[#192030] text-slate-400 border-[#263046] hover:text-white hover:bg-[#263046]'
            }`}
          >
            {d.code}
          </button>
        ))}
      </div>

      {/* Driver Summary Banner */}
      {driverSummary && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 bg-[#192030]/60 p-3 rounded-lg border border-[#263046] text-xs font-mono">
          <div>
            <span className="text-slate-400 block text-[10px]">PERSONAL BEST LAP</span>
            <span className="text-emerald-400 font-bold text-sm">
              {formatLapTime(driverSummary.best_lap_s)}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px]">THEORETICAL IDEAL LAP</span>
            <span className="text-purple-400 font-bold text-sm">
              {formatLapTime(driverSummary.theoretical_best_s)}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px]">BEST SECTORS (S1 / S2 / S3)</span>
            <span className="text-slate-200">
              {formatSec(driverSummary.best_sectors.sector1_s)} /{' '}
              {formatSec(driverSummary.best_sectors.sector2_s)} /{' '}
              {formatSec(driverSummary.best_sectors.sector3_s)}
            </span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px]">LAPS RECORDED</span>
            <span className="text-white font-bold">{activeDriverLaps.length} Laps</span>
          </div>
        </div>
      )}

      {viewTab === 'laps_table' ? (
        /* Detailed Lap-by-Lap Sector Timing Table */
        <div className="max-h-[380px] overflow-y-auto rounded-lg border border-[#263046]">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead className="bg-[#0f131d] text-slate-400 sticky top-0 border-b border-[#263046] text-[10px] uppercase">
              <tr>
                <th className="py-2 px-3">LAP</th>
                <th className="py-2 px-3">TIME</th>
                <th className="py-2 px-3">SECTOR 1</th>
                <th className="py-2 px-3">SECTOR 2</th>
                <th className="py-2 px-3">SECTOR 3</th>
                <th className="py-2 px-3">TYRE</th>
                <th className="py-2 px-3">GAP TO LEADER</th>
                <th className="py-2 px-3">3L MOVING AVG</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e2638] bg-[#121722]">
              {activeDriverLaps.map((lap) => (
                <tr
                  key={lap.lap}
                  className={`hover:bg-[#192030] transition ${
                    lap.is_pit_entry || lap.is_out_lap ? 'bg-amber-500/5' : ''
                  }`}
                >
                  <td className="py-2 px-3 text-slate-400 font-bold">
                    {lap.lap}
                    {lap.is_pit_entry && (
                      <span className="ml-1 text-[9px] text-amber-400">PIT</span>
                    )}
                  </td>
                  <td className="py-2 px-3 text-white font-bold">
                    {formatLapTime(lap.time_s)}
                  </td>
                  <td className="py-2 px-3">
                    <span
                      className={`px-1.5 py-0.5 rounded border text-[11px] ${getStatusBadge(
                        lap.sector1_status
                      )}`}
                    >
                      {formatSec(lap.sector1_s)}
                    </span>
                  </td>
                  <td className="py-2 px-3">
                    <span
                      className={`px-1.5 py-0.5 rounded border text-[11px] ${getStatusBadge(
                        lap.sector2_status
                      )}`}
                    >
                      {formatSec(lap.sector2_s)}
                    </span>
                  </td>
                  <td className="py-2 px-3">
                    <span
                      className={`px-1.5 py-0.5 rounded border text-[11px] ${getStatusBadge(
                        lap.sector3_status
                      )}`}
                    >
                      {formatSec(lap.sector3_s)}
                    </span>
                  </td>
                  <td className="py-2 px-3 text-slate-300">
                    {lap.tyre_compound} ({lap.tyre_life}L)
                  </td>
                  <td className="py-2 px-3 text-slate-400">
                    {lap.official_gap_to_leader_s !== null && lap.official_gap_to_leader_s !== undefined
                      ? `+${Number(lap.official_gap_to_leader_s).toFixed(1)}s`
                      : '-'}
                  </td>
                  <td className="py-2 px-3 text-slate-400">
                    {formatLapTime(lap.moving_avg_3_s)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        /* Ideal Lap Benchmarks & Session Best Sectors */
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(['sector1_s', 'sector2_s', 'sector3_s'] as const).map((secKey, idx) => {
            const secData = sessionBests[secKey];
            return (
              <div
                key={secKey}
                className="bg-[#0f131d] rounded-lg border border-[#263046] p-4 flex flex-col gap-2"
              >
                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-purple-400 font-bold flex items-center gap-1">
                    <Star className="w-3.5 h-3.5" />
                    SECTOR {idx + 1} BENCHMARK
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-purple-500/20 text-purple-300 text-[10px] font-bold">
                    PURPLE
                  </span>
                </div>
                <div className="text-2xl font-bold font-mono text-white mt-1">
                  {secData?.time_s ? `${secData.time_s.toFixed(3)}s` : '--'}
                </div>
                <div className="text-xs font-mono text-slate-400">
                  Sector Holder: <strong>{secData?.holders?.join(', ') || 'Session Record'}</strong>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Legend Footer */}
      <div className="flex items-center gap-4 text-[11px] font-mono text-slate-400 pt-1">
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-purple-500" />
          Purple: Overall Session Best
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-emerald-500" />
          Green: Personal Driver Best
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-sm bg-yellow-500" />
          Yellow: Normal Lap Sector
        </span>
      </div>
    </div>
  );
};
