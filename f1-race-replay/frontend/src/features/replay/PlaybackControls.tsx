import React from 'react';
import { TimelineEventMarker } from '../../types/f1';
import {
  FastForward,
  Pause,
  Play,
  RotateCcw,
  SkipBack,
  SkipForward,
  Wifi,
} from 'lucide-react';
import { StreamConnectionMode } from '../../services/replaySocket';

interface PlaybackControlsProps {
  currentFrameIndex: number;
  totalFrames: number;
  currentTimeSeconds: number;
  totalDurationSeconds: number;
  currentLap: number;
  totalLaps: number;
  isPlaying: boolean;
  playbackSpeed: number;
  timelineEvents: TimelineEventMarker[];
  connectionMode: StreamConnectionMode;
  onTogglePlay: () => void;
  onSeekFrame: (frameIndex: number) => void;
  onStepFrames: (delta: number) => void;
  onChangeSpeed: (speed: number) => void;
  onReset: () => void;
}

const SPEED_OPTIONS = [0.25, 0.5, 1, 2, 4, 8, 16, 32];

const EVENT_COLORS: Record<string, string> = {
  safety_car: '#f59e0b',
  vsc: '#eab308',
  red_flag: '#ef4444',
  yellow_flag: '#fde047',
  dnf: '#f87171',
};

function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '00:00.0';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (hrs > 0) {
    return `${hrs}:${String(mins).padStart(2, '0')}:${secs.toFixed(1).padStart(4, '0')}`;
  }
  return `${String(mins).padStart(2, '0')}:${secs.toFixed(1).padStart(4, '0')}`;
}

export const PlaybackControls: React.FC<PlaybackControlsProps> = ({
  currentFrameIndex,
  totalFrames,
  currentTimeSeconds,
  totalDurationSeconds,
  currentLap,
  totalLaps,
  isPlaying,
  playbackSpeed,
  timelineEvents,
  connectionMode,
  onTogglePlay,
  onSeekFrame,
  onStepFrames,
  onChangeSpeed,
  onReset,
}) => {
  const maxFrame = Math.max(1, totalFrames - 1);
  const progressPct = Math.min(100, Math.max(0, (currentFrameIndex / maxFrame) * 100));

  return (
    <div className="bg-[#121722] border border-[#263046] rounded-xl p-3 flex flex-col gap-2.5">
      {/* Timeline Scrubber with Event Markers */}
      <div className="relative pt-3 pb-1">
        {/* Event Marker Flags on Timeline */}
        <div className="relative h-3 w-full mb-1">
          {timelineEvents.map((ev, idx) => {
            const leftPct = Math.min(99, Math.max(0.5, (ev.frame / maxFrame) * 100));
            const color = EVENT_COLORS[ev.type] || '#38bdf8';
            return (
              <button
                key={`${ev.type}-${ev.frame}-${idx}`}
                type="button"
                onClick={() => onSeekFrame(ev.frame)}
                style={{ left: `${leftPct}%`, borderColor: color }}
                className="absolute -top-1 -translate-x-1/2 px-1 py-0.2 rounded text-[9px] font-mono font-bold bg-[#192030] border hover:scale-110 transition z-10"
                title={`${ev.label}${ev.lap ? ` (Lap ${ev.lap})` : ''}`}
              >
                <span style={{ color }}>{ev.label}</span>
              </button>
            );
          })}
        </div>

        {/* Range Input Scrubber */}
        <div className="relative flex items-center">
          <div
            className="absolute left-0 h-2 bg-gradient-to-r from-[#E10600] to-amber-500 rounded-l-full pointer-events-none"
            style={{ width: `${progressPct}%` }}
          />
          <input
            type="range"
            min={0}
            max={maxFrame}
            value={currentFrameIndex}
            onChange={(e) => onSeekFrame(Number(e.target.value))}
            className="w-full h-2 bg-[#263046] rounded-lg appearance-none cursor-pointer accent-[#E10600]"
            aria-label="Session replay timeline"
          />
        </div>
      </div>

      {/* Transport Buttons & Telemetry Timing Readout */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onReset}
            className="p-2 rounded-lg bg-[#192030] hover:bg-[#263046] text-slate-200 transition"
            title="Reset Replay to Start"
          >
            <RotateCcw className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => onStepFrames(-10)}
            className="p-2 rounded-lg bg-[#192030] hover:bg-[#263046] text-slate-200 transition"
            title="Step Back 10 Frames"
          >
            <SkipBack className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={onTogglePlay}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#E10600] hover:bg-red-600 text-white font-semibold text-xs transition shadow-md shadow-red-950/50"
          >
            {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            <span>{isPlaying ? 'PAUSE' : 'PLAY'}</span>
          </button>

          <button
            type="button"
            onClick={() => onStepFrames(10)}
            className="p-2 rounded-lg bg-[#192030] hover:bg-[#263046] text-slate-200 transition"
            title="Step Forward 10 Frames"
          >
            <SkipForward className="w-4 h-4" />
          </button>
        </div>

        {/* Session Clock & Lap Progress */}
        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="bg-[#192030] px-3 py-1.5 rounded-lg border border-[#263046]">
            <span className="text-slate-400 mr-1.5">TIME</span>
            <span className="text-white font-bold">{formatDuration(currentTimeSeconds)}</span>
            <span className="text-slate-500"> / {formatDuration(totalDurationSeconds)}</span>
          </div>

          <div className="bg-[#192030] px-3 py-1.5 rounded-lg border border-[#263046]">
            <span className="text-slate-400 mr-1.5">LAP</span>
            <span className="text-emerald-400 font-bold">{currentLap}</span>
            <span className="text-slate-500"> / {totalLaps || '-'}</span>
          </div>

          <div className="hidden sm:flex items-center gap-1.5 bg-[#192030] px-2.5 py-1.5 rounded-lg border border-[#263046]">
            <Wifi
              className={`w-3.5 h-3.5 ${
                connectionMode === 'websocket' ? 'text-emerald-400' : 'text-sky-400'
              }`}
            />
            <span className="text-[11px] text-slate-300">
              {connectionMode === 'websocket' ? 'WS LIVE' : 'CLIENT ENGINE'}
            </span>
          </div>
        </div>

        {/* Speed Selector */}
        <div className="flex items-center gap-1 bg-[#192030] p-1 rounded-lg border border-[#263046]">
          <FastForward className="w-3.5 h-3.5 text-slate-400 ml-1.5 mr-1" />
          {SPEED_OPTIONS.map((spd) => (
            <button
              key={spd}
              type="button"
              onClick={() => onChangeSpeed(spd)}
              className={`px-2 py-1 rounded text-[11px] font-mono font-semibold transition ${
                playbackSpeed === spd
                  ? 'bg-[#E10600] text-white'
                  : 'text-slate-400 hover:text-white hover:bg-[#263046]'
              }`}
            >
              {spd}x
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
