import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  EventSummary,
  LeaderboardEntry,
  LeaderboardSnapshot,
  ReplayFrame,
  ReplayPayload,
  SessionOption,
} from './types/f1';
import { fetch2025Events, fetchReplayPayload } from './services/api';
import { ReplayStreamClient, StreamConnectionMode } from './services/replaySocket';
import { CircuitCanvas } from './features/replay/CircuitCanvas';
import { PlaybackControls } from './features/replay/PlaybackControls';
import { LeaderboardPanel } from './features/replay/LeaderboardPanel';
import { TelemetryPanel } from './features/telemetry/TelemetryPanel';
import { LapSectorPanel } from './features/telemetry/LapSectorPanel';
import { TyreStrategyPanel } from './features/strategy/TyreStrategyPanel';
import { RaceControlPanel } from './features/replay/RaceControlPanel';
import { ChatSidebar } from './features/chat/ChatSidebar';
import {
  Activity,
  AlertCircle,
  Bot,
  Calendar,
  CircleDot,
  Flag,
  Loader2,
  Radio,
  RefreshCw,
  ShieldCheck,
  Timer,
} from 'lucide-react';

function buildClientLeaderboard(
  payload: ReplayPayload,
  frameIndex: number
): LeaderboardSnapshot | null {
  const frames = payload.frames || [];
  if (!frames.length) return null;
  const clamped = Math.max(0, Math.min(frameIndex, frames.length - 1));
  const frame: ReplayFrame = frames[clamped];
  const driversDict = frame.drivers || {};
  const metaMap: Record<string, { full_name: string; team?: string | null; color: string }> = {};
  for (const d of payload.session.drivers || []) {
    metaMap[d.code] = {
      full_name: d.full_name,
      team: d.team || d.team_name,
      color: d.color || '#38bdf8',
    };
  }

  const sorted = Object.entries(driversDict).sort((a, b) => {
    const posDiff = (a[1].position || 99) - (b[1].position || 99);
    if (posDiff !== 0) return posDiff;
    return (b[1].dist || 0) - (a[1].dist || 0);
  });

  const leaderDist = sorted.length ? sorted[0][1].dist || 0 : 0;

  const entries: LeaderboardEntry[] = sorted.map(([code, d], idx) => {
    const pos = idx + 1;
    const distVal = d.dist || 0;
    const rawToLeader = Math.max(0, leaderDist - distVal);
    const gapToLeaderS = idx === 0 ? 0.0 : Number(((rawToLeader / 10.0) / 55.56).toFixed(2));
    const prevDist = idx === 0 ? distVal : sorted[idx - 1][1].dist || 0;
    const rawAhead = Math.max(0, prevDist - distVal);
    const intervalS = idx === 0 ? 0.0 : Number(((rawAhead / 10.0) / 55.56).toFixed(2));

    const tyreMap: Record<number, string> = {
      0: 'SOFT',
      1: 'MEDIUM',
      2: 'HARD',
      3: 'INTERMEDIATE',
      4: 'WET',
    };
    const meta = metaMap[code] || { full_name: code, color: '#38bdf8' };

    return {
      position: pos,
      code,
      full_name: meta.full_name,
      team: meta.team,
      color: meta.color,
      lap: Math.max(1, Math.round(d.lap || 1)),
      tyre: d.tyre ?? 1,
      tyre_compound: d.tyre_compound_name || tyreMap[d.tyre ?? 1] || 'MEDIUM',
      tyre_life: Math.round(d.tyre_life || 1),
      in_pit: Boolean(d.in_pit),
      is_out: d.status === 'OUT' || d.status === 'DNF',
      speed_kph: Number((d.speed || 0).toFixed(1)),
      gear: d.gear || 0,
      drs_active: [10, 12, 14].includes(d.drs || 0),
      gap_to_leader_s: gapToLeaderS,
      interval_s: intervalS,
      last_lap_s: null,
      best_lap_s: payload.lap_summaries?.drivers?.[code]?.best_lap_s ?? null,
    };
  });

  return {
    frame_index: clamped,
    time_s: frame.t || 0,
    lap: frame.lap || 1,
    total_laps: payload.session.total_laps,
    track_status: frame.track_status || '1',
    track_status_label: frame.track_status_label || 'GREEN FLAG',
    entries,
  };
}

export const App: React.FC = () => {
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [selectedRound, setSelectedRound] = useState<number>(1);
  const [selectedSessionType, setSelectedSessionType] = useState<string>('R');
  const [payload, setPayload] = useState<ReplayPayload | null>(null);
  const [loadingSession, setLoadingSession] = useState<boolean>(true);
  const [sessionError, setSessionError] = useState<string | null>(null);

  // Playback state
  const [currentFrameIndex, setCurrentFrameIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [connectionMode, setConnectionMode] =
    useState<StreamConnectionMode>('local-interpolated');
  const [wsLeaderboard, setWsLeaderboard] = useState<LeaderboardSnapshot | null>(null);

  // Selected drivers & Analytics tab
  const [selectedDriver, setSelectedDriver] = useState<string>('NOR');
  const [compareDriver, setCompareDriver] = useState<string | null>('VER');
  const [activeTab, setActiveTab] = useState<
    'telemetry' | 'sectors' | 'strategy' | 'race_control'
  >('telemetry');
  const [chatOpen, setChatOpen] = useState<boolean>(false);

  const wsClientRef = useRef<ReplayStreamClient | null>(null);

  // 1. Load 2025 Event Calendar on startup
  useEffect(() => {
    fetch2025Events()
      .then((evList) => {
        setEvents(evList);
      })
      .catch((err) => {
        setSessionError(err.message || 'Unable to load 2025 Formula 1 calendar');
      });
  }, []);

  const activeEvent = useMemo(
    () => events.find((e) => e.round_number === selectedRound) || null,
    [events, selectedRound]
  );

  const sessionOptions: SessionOption[] = useMemo(() => {
    if (activeEvent?.sessions?.length) return activeEvent.sessions;
    return [
      { code: 'FP1', session_type: 'FP1', name: 'Practice 1', label: 'Practice 1 (FP1)', available: true },
      { code: 'FP2', session_type: 'FP2', name: 'Practice 2', label: 'Practice 2 (FP2)', available: true },
      { code: 'FP3', session_type: 'FP3', name: 'Practice 3', label: 'Practice 3 (FP3)', available: true },
      { code: 'Q', session_type: 'Q', name: 'Qualifying', label: 'Qualifying (Q)', available: true },
      { code: 'R', session_type: 'R', name: 'Race', label: 'Race (R)', available: true },
    ];
  }, [activeEvent]);

  // 2. Load selected 2025 Session Replay Payload
  const loadSession = useCallback(
    async (roundNum: number, sessType: string, refresh = false) => {
      setLoadingSession(true);
      setSessionError(null);
      setIsPlaying(false);
      setCurrentFrameIndex(0);
      setWsLeaderboard(null);

      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
        wsClientRef.current = null;
      }

      try {
        const data = await fetchReplayPayload(roundNum, sessType, true, refresh);
        setPayload(data);
        const drvList = data.session.drivers || [];
        if (drvList.length >= 1 && !drvList.some((d) => d.code === selectedDriver)) {
          setSelectedDriver(drvList[0].code);
        }
        if (drvList.length >= 2 && (!compareDriver || !drvList.some((d) => d.code === compareDriver))) {
          setCompareDriver(drvList[1].code);
        }

        // Connect WebSocket replay stream
        const wsClient = new ReplayStreamClient(roundNum, sessType, {
          onConnectionChange: (mode) => setConnectionMode(mode),
          onFramePacket: (pkt) => {
            if (typeof pkt.frame_index === 'number') {
              setCurrentFrameIndex(pkt.frame_index);
            }
            if (pkt.leaderboard) {
              setWsLeaderboard(pkt.leaderboard);
            }
          },
        });
        wsClient.connect();
        wsClientRef.current = wsClient;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : 'Failed to load 2025 session data';
        setSessionError(msg);
      } finally {
        setLoadingSession(false);
      }
    },
    [selectedDriver, compareDriver]
  );

  useEffect(() => {
    loadSession(selectedRound, selectedSessionType, false);
    return () => {
      if (wsClientRef.current) {
        wsClientRef.current.disconnect();
      }
    };
  }, [selectedRound, selectedSessionType]);

  // 3. Pause playback automatically if browser tab is hidden to save CPU/battery
  useEffect(() => {
    const onVisibilityChange = () => {
      if (document.visibilityState === 'hidden' && isPlaying) {
        setIsPlaying(false);
        wsClientRef.current?.sendCommand({ action: 'pause' });
      }
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, [isPlaying]);

  // 4. Client-side synchronized timer when playing
  useEffect(() => {
    if (!isPlaying || !payload?.frames?.length) return;
    const total = payload.frames.length;
    const intervalMs = Math.max(25, Math.round(120 / Math.max(0.25, playbackSpeed)));
    const frameStep = playbackSpeed >= 8 ? Math.round(playbackSpeed / 4) : 1;

    const timer = window.setInterval(() => {
      setCurrentFrameIndex((prev) => {
        if (prev + frameStep >= total - 1) {
          setIsPlaying(false);
          return total - 1;
        }
        return prev + frameStep;
      });
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [isPlaying, playbackSpeed, payload]);

  const activeFrame: ReplayFrame | null = useMemo(() => {
    if (!payload?.frames?.length) return null;
    const idx = Math.max(0, Math.min(currentFrameIndex, payload.frames.length - 1));
    const raw = payload.frames[idx];
    // Attach active track status code & label if not already on raw frame
    let activeCode = raw.track_status || '1';
    for (const st of payload.track_statuses || []) {
      const sT = st.start_time || 0;
      const eT = st.end_time;
      if (raw.t >= sT && (eT === null || eT === undefined || raw.t < eT)) {
        activeCode = String(st.status || '1');
        break;
      }
    }
    const labelMap: Record<string, string> = {
      '1': 'GREEN FLAG',
      '2': 'YELLOW FLAG',
      '4': 'SAFETY CAR',
      '5': 'RED FLAG',
      '6': 'VIRTUAL SAFETY CAR',
      '7': 'VSC ENDING',
    };
    return {
      ...raw,
      frame_index: idx,
      track_status: activeCode,
      track_status_label: raw.track_status_label || labelMap[activeCode] || 'GREEN FLAG',
    };
  }, [payload, currentFrameIndex]);

  const activeLeaderboard: LeaderboardSnapshot | null = useMemo(() => {
    if (wsLeaderboard && wsLeaderboard.frame_index === currentFrameIndex) {
      return wsLeaderboard;
    }
    if (!payload) return null;
    return buildClientLeaderboard(payload, currentFrameIndex);
  }, [payload, currentFrameIndex, wsLeaderboard]);

  // Transport handlers
  const handleTogglePlay = () => {
    const next = !isPlaying;
    setIsPlaying(next);
    wsClientRef.current?.sendCommand({ action: next ? 'play' : 'pause' });
  };

  const handleSeekFrame = (frameIndex: number) => {
    if (!payload?.frames?.length) return;
    const clamped = Math.max(0, Math.min(frameIndex, payload.frames.length - 1));
    setCurrentFrameIndex(clamped);
    wsClientRef.current?.sendCommand({ action: 'seek', frame_index: clamped });
  };

  const handleSeekToTime = (timeSeconds: number) => {
    if (!payload?.frames?.length) return;
    const idx = payload.frames.findIndex((f) => f.t >= timeSeconds);
    handleSeekFrame(idx >= 0 ? idx : 0);
  };

  const handleStepFrames = (delta: number) => {
    handleSeekFrame(currentFrameIndex + delta);
  };

  const handleChangeSpeed = (speed: number) => {
    setPlaybackSpeed(speed);
    wsClientRef.current?.sendCommand({ action: 'set_speed', speed });
  };

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentFrameIndex(0);
    wsClientRef.current?.sendCommand({ action: 'reset' });
  };

  const totalFrames = payload?.frames?.length || 0;
  const currentLap = activeFrame?.lap || 1;
  const totalLaps = payload?.session?.total_laps || 58;
  const currentTimeS = activeFrame?.t || 0;
  const totalDurationS =
    payload?.session?.duration_s ||
    (payload?.frames?.length ? payload.frames[payload.frames.length - 1].t : 0);

  return (
    <div className="min-h-screen bg-[#0B0E14] text-slate-100 flex flex-col">
      {/* Top Pit-Wall Navigation Bar */}
      <header className="sticky top-0 z-30 bg-[#121722]/95 backdrop-blur-md border-b border-[#263046] px-4 py-2.5">
        <div className="max-w-[1680px] mx-auto flex flex-wrap items-center justify-between gap-3">
          {/* Brand Logo & 2025 Season Restriction Badge */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-[#E10600] flex items-center justify-center font-black text-white tracking-tighter text-sm shadow-md shadow-red-950">
                F1
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-sm font-extrabold tracking-wide uppercase text-white">
                    Pit-Wall Replay & Analytics
                  </h1>
                  <span className="px-2 py-0.5 rounded bg-[#E10600]/20 border border-[#E10600] text-[#ff4d47] font-mono text-[10px] font-bold">
                    2025 SEASON ONLY
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 font-mono">
                  Calibrated FastF1 Telemetry • Bayesian Tyre Model • FIA Grounded RAG
                </p>
              </div>
            </div>
          </div>

          {/* 2025 Grand Prix Event & Session Selectors */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Locked Season Pill */}
            <div
              className="flex items-center gap-1.5 bg-[#192030] px-2.5 py-1.5 rounded-lg border border-[#263046] text-xs font-mono text-slate-300"
              title="Application is strictly locked to the 2025 FIA Formula 1 World Championship"
            >
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span className="font-bold text-white">2025</span>
            </div>

            {/* Grand Prix Selector */}
            <div className="flex items-center gap-1.5 bg-[#192030] px-2.5 py-1.5 rounded-lg border border-[#263046] text-xs font-mono">
              <Calendar className="w-3.5 h-3.5 text-[#E10600]" />
              <select
                aria-label="Select 2025 Grand Prix"
                value={selectedRound}
                onChange={(e) => setSelectedRound(Number(e.target.value))}
                className="bg-transparent text-white font-semibold focus:outline-none cursor-pointer"
              >
                {events.map((ev) => (
                  <option
                    key={ev.round_number}
                    value={ev.round_number}
                    className="bg-[#121722] text-white"
                  >
                    R{String(ev.round_number).padStart(2, '0')} — {ev.event_name} ({ev.circuit_name})
                  </option>
                ))}
              </select>
            </div>

            {/* Session Type Selector */}
            <div className="flex items-center gap-1 bg-[#192030] p-1 rounded-lg border border-[#263046]">
              {sessionOptions.map((opt) => {
                const code = opt.code || opt.session_type;
                const active = selectedSessionType === code;
                return (
                  <button
                    key={code}
                    type="button"
                    onClick={() => setSelectedSessionType(code)}
                    className={`px-2.5 py-1 rounded text-xs font-mono font-bold transition ${
                      active
                        ? 'bg-[#E10600] text-white'
                        : 'text-slate-400 hover:text-white hover:bg-[#263046]'
                    }`}
                    title={opt.name || opt.label}
                  >
                    {code}
                  </button>
                );
              })}
            </div>

            {/* Recompute / Refresh Cache Button */}
            <button
              type="button"
              onClick={() => loadSession(selectedRound, selectedSessionType, true)}
              className="p-2 rounded-lg bg-[#192030] hover:bg-[#263046] border border-[#263046] text-slate-300 hover:text-white transition"
              title="Refresh & Recompute Processed Session Cache"
            >
              <RefreshCw className={`w-4 h-4 ${loadingSession ? 'animate-spin' : ''}`} />
            </button>

            {/* Open F1 Strategist Chatbot Button */}
            <button
              type="button"
              onClick={() => setChatOpen(!chatOpen)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-mono font-bold transition ${
                chatOpen
                  ? 'bg-[#E10600] text-white border-[#E10600]'
                  : 'bg-[#192030] text-slate-200 border-[#263046] hover:border-[#E10600]'
              }`}
            >
              <Bot className="w-4 h-4" />
              <span>AI STRATEGIST</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content Container */}
      <main className="flex-1 max-w-[1680px] w-full mx-auto p-4 flex flex-col gap-4">
        {/* Session Error Banner */}
        {sessionError && (
          <div className="p-4 rounded-xl bg-red-500/15 border border-red-500/40 text-red-200 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2.5 text-xs font-mono">
              <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
              <span>{sessionError}</span>
            </div>
            <button
              type="button"
              onClick={() => loadSession(selectedRound, selectedSessionType, false)}
              className="px-3 py-1 rounded bg-red-500/20 hover:bg-red-500/30 text-xs font-mono font-bold text-red-200"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading State */}
        {loadingSession && (
          <div className="h-[520px] bg-[#121722] border border-[#263046] rounded-xl flex flex-col items-center justify-center gap-3">
            <Loader2 className="w-8 h-8 text-[#E10600] animate-spin" />
            <div className="text-sm font-mono font-bold text-white">
              Preparing 2025 Round {selectedRound} ({selectedSessionType}) Telemetry & Track Geometry...
            </div>
            <p className="text-xs font-mono text-slate-400">
              Loading processed session cache & calibrating driver coordinate frames
            </p>
          </div>
        )}

        {/* Active Replay Workspace */}
        {!loadingSession && payload && (
          <>
            {/* Top Grid: Interactive Circuit Map +Playback Controls (Left 8 cols) & Live Leaderboard (Right 4 cols) */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
              {/* Left 8 Cols: Circuit Canvas + Playback Scrubber */}
              <div className="lg:col-span-8 xl:col-span-9 flex flex-col gap-3">
                <div className="h-[460px] sm:h-[520px]">
                  <CircuitCanvas
                    trackGeometry={payload.track_geometry}
                    frame={activeFrame}
                    drivers={payload.session.drivers || []}
                    selectedDriver={selectedDriver}
                    compareDriver={compareDriver}
                    onSelectDriver={(code) => setSelectedDriver(code)}
                  />
                </div>

                <PlaybackControls
                  currentFrameIndex={currentFrameIndex}
                  totalFrames={totalFrames}
                  currentTimeSeconds={currentTimeS}
                  totalDurationSeconds={totalDurationS}
                  currentLap={currentLap}
                  totalLaps={totalLaps}
                  isPlaying={isPlaying}
                  playbackSpeed={playbackSpeed}
                  timelineEvents={payload.timeline_events || []}
                  connectionMode={connectionMode}
                  onTogglePlay={handleTogglePlay}
                  onSeekFrame={handleSeekFrame}
                  onStepFrames={handleStepFrames}
                  onChangeSpeed={handleChangeSpeed}
                  onReset={handleReset}
                />
              </div>

              {/* Right 4 Cols: Live Leaderboard & Weather HUD */}
              <div className="lg:col-span-4 xl:col-span-3 h-[580px] sm:h-[630px]">
                <LeaderboardPanel
                  leaderboard={activeLeaderboard}
                  weather={activeFrame?.weather}
                  liveStandings={payload.live_driver_standings}
                  selectedDriver={selectedDriver}
                  compareDriver={compareDriver}
                  onSelectDriver={(code) => setSelectedDriver(code)}
                  onSelectCompareDriver={(code) =>
                    setCompareDriver((prev) => (prev === code ? null : code))
                  }
                />
              </div>
            </div>

            {/* Bottom Section: Pit-Wall Analytics Tabs */}
            <div className="flex flex-col gap-3 mt-1">
              {/* Tab Bar */}
              <div className="flex flex-wrap items-center justify-between gap-2 bg-[#121722] p-2 rounded-xl border border-[#263046]">
                <div className="flex flex-wrap items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => setActiveTab('telemetry')}
                    className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-mono font-bold transition ${
                      activeTab === 'telemetry'
                        ? 'bg-[#E10600] text-white'
                        : 'text-slate-300 hover:bg-[#192030]'
                    }`}
                  >
                    <Activity className="w-3.5 h-3.5" />
                    <span>TELEMETRY TRACES</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab('sectors')}
                    className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-mono font-bold transition ${
                      activeTab === 'sectors'
                        ? 'bg-[#E10600] text-white'
                        : 'text-slate-300 hover:bg-[#192030]'
                    }`}
                  >
                    <Timer className="w-3.5 h-3.5" />
                    <span>LAP & SECTOR TIMING</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab('strategy')}
                    className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-mono font-bold transition ${
                      activeTab === 'strategy'
                        ? 'bg-[#E10600] text-white'
                        : 'text-slate-300 hover:bg-[#192030]'
                    }`}
                  >
                    <CircleDot className="w-3.5 h-3.5" />
                    <span>TYRE STRATEGY & BAYESIAN DEG</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveTab('race_control')}
                    className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-mono font-bold transition ${
                      activeTab === 'race_control'
                        ? 'bg-[#E10600] text-white'
                        : 'text-slate-300 hover:bg-[#192030]'
                    }`}
                  >
                    <Radio className="w-3.5 h-3.5" />
                    <span>FIA RACE CONTROL</span>
                  </button>
                </div>

                {/* Data Source Indicator */}
                <div className="flex items-center gap-2 px-2.5 py-1 rounded bg-[#192030] border border-[#263046] text-[11px] font-mono text-slate-400">
                  <Flag className="w-3.5 h-3.5 text-emerald-400" />
                  <span>
                    Source: <strong className="text-slate-200">{payload.session.data_source.toUpperCase()}</strong>
                  </span>
                </div>
              </div>

              {/* Active Analytics Tab Content */}
              {activeTab === 'telemetry' && (
                <TelemetryPanel
                  roundNumber={selectedRound}
                  sessionType={selectedSessionType}
                  selectedDriver={selectedDriver}
                  compareDriver={compareDriver}
                  drivers={payload.session.drivers || []}
                  currentLap={currentLap}
                  onSelectCompareDriver={(code) => setCompareDriver(code || null)}
                />
              )}

              {activeTab === 'sectors' && (
                <LapSectorPanel
                  lapSummaries={payload.lap_summaries}
                  drivers={payload.session.drivers || []}
                  selectedDriver={selectedDriver}
                  onSelectDriver={(code) => setSelectedDriver(code)}
                />
              )}

              {activeTab === 'strategy' && (
                <TyreStrategyPanel
                  strategies={payload.strategies || []}
                  totalLaps={totalLaps}
                  selectedDriver={selectedDriver}
                  onSelectDriver={(code) => setSelectedDriver(code)}
                />
              )}

              {activeTab === 'race_control' && (
                <RaceControlPanel
                  messages={payload.race_control_messages || []}
                  trackStatusPeriods={payload.track_status || []}
                  currentTimeSeconds={currentTimeS}
                  onSeekToTime={handleSeekToTime}
                />
              )}
            </div>
          </>
        )}
      </main>

      {/* Collapsible Formula 1 AI Strategist & Knowledge Chatbot */}
      <ChatSidebar
        roundNumber={selectedRound}
        sessionType={selectedSessionType}
        eventName={payload?.session?.event_name || activeEvent?.event_name || '2025 Grand Prix'}
        currentFrameIndex={currentFrameIndex}
        currentLap={currentLap}
        selectedDriver={selectedDriver}
        compareDriver={compareDriver}
        isOpen={chatOpen}
        onToggleOpen={() => setChatOpen(!chatOpen)}
      />
    </div>
  );
};

export default App;
