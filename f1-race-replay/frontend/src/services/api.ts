import {
  ChatResponse,
  DriverLapSummary,
  DriverStrategySummary,
  EventSummary,
  LeaderboardSnapshot,
  RaceControlMessage,
  ReplayFrame,
  ReplayPayload,
  SessionOption,
  TelemetryComparisonResponse,
  TrackStatusPeriod,
} from '../types/f1';

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  'https://f1-2025-race-replay.onrender.com'
).replace(/\/+$/, '');


async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const errBody = await response.json();
      if (errBody?.detail) {
        detail = typeof errBody.detail === 'string' ? errBody.detail : JSON.stringify(errBody.detail);
      }
    } catch {
      // ignore JSON parse error
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}

export async function fetch2025Events(): Promise<EventSummary[]> {
  const data = await requestJson<{ year: number; events: EventSummary[] }>('/events?year=2025');
  return data.events;
}

export async function fetchEventSessions(roundNumber: number): Promise<SessionOption[]> {
  const data = await requestJson<{ sessions: SessionOption[] }>(
    `/events/${roundNumber}/sessions?year=2025`
  );
  return data.sessions;
}

export async function fetchReplayPayload(
  roundNumber: number,
  sessionType: string,
  includeFrames = true,
  refresh = false
): Promise<ReplayPayload> {
  return requestJson<ReplayPayload>(
    `/sessions/2025/${roundNumber}/replay?session_type=${encodeURIComponent(
      sessionType
    )}&include_frames=${includeFrames}&refresh=${refresh}`
  );
}

export async function fetchFrameChunk(
  roundNumber: number,
  sessionType: string,
  startFrame: number,
  endFrame: number,
  step = 1
): Promise<{
  start_frame: number;
  end_frame: number;
  total_frames: number;
  step: number;
  frames: ReplayFrame[];
}> {
  return requestJson(
    `/sessions/2025/${roundNumber}/frames?session_type=${encodeURIComponent(
      sessionType
    )}&start_frame=${startFrame}&end_frame=${endFrame}&step=${step}`
  );
}

export async function fetchLeaderboardSnapshot(
  roundNumber: number,
  sessionType: string,
  frameIndex: number
): Promise<LeaderboardSnapshot> {
  return requestJson<LeaderboardSnapshot>(
    `/sessions/2025/${roundNumber}/leaderboard?session_type=${encodeURIComponent(
      sessionType
    )}&frame_index=${frameIndex}`
  );
}

export async function fetchTelemetryComparison(params: {
  roundNumber: number;
  sessionType: string;
  driver: string;
  compareWith?: string;
  mode?: 'lap' | 'time' | 'quali_segment' | 'best_lap';
  lap?: number;
  startTime?: number;
  endTime?: number;
  segment?: string;
}): Promise<TelemetryComparisonResponse> {
  const query = new URLSearchParams({
    session_type: params.sessionType,
    driver: params.driver,
    mode: params.mode || 'lap',
  });
  if (params.compareWith) query.set('compare_with', params.compareWith);
  if (params.lap !== undefined) query.set('lap', String(params.lap));
  if (params.startTime !== undefined) query.set('start_time', String(params.startTime));
  if (params.endTime !== undefined) query.set('end_time', String(params.endTime));
  if (params.segment) query.set('segment', params.segment);

  return requestJson<TelemetryComparisonResponse>(
    `/sessions/2025/${params.roundNumber}/telemetry?${query.toString()}`
  );
}

export async function fetchSessionStrategy(
  roundNumber: number,
  sessionType: string
): Promise<{ total_laps: number; strategies: DriverStrategySummary[] }> {
  return requestJson(
    `/sessions/2025/${roundNumber}/strategy?session_type=${encodeURIComponent(sessionType)}`
  );
}

export async function fetchSessionLaps(
  roundNumber: number,
  sessionType: string
): Promise<{
  session_best_sectors: {
    s1?: number | null;
    s1_driver?: string | null;
    s2?: number | null;
    s2_driver?: string | null;
    s3?: number | null;
    s3_driver?: string | null;
    ideal_lap_s?: number | null;
    ideal_lap_fmt?: string | null;
  };
  status_laps: TrackStatusPeriod[];
  drivers: Record<string, DriverLapSummary>;
}> {
  return requestJson(
    `/sessions/2025/${roundNumber}/laps?session_type=${encodeURIComponent(sessionType)}`
  );
}

export async function fetchRaceControl(
  roundNumber: number,
  sessionType: string,
  upToTime?: number
): Promise<{
  track_status_periods: TrackStatusPeriod[];
  race_control_messages: RaceControlMessage[];
  safety_car_note: string;
}> {
  const q = upToTime !== undefined ? `&up_to_time=${upToTime}` : '';
  return requestJson(
    `/sessions/2025/${roundNumber}/race-control?session_type=${encodeURIComponent(sessionType)}${q}`
  );
}

export async function sendChatQuestion(params: {
  message: string;
  roundNumber?: number;
  sessionType?: string;
  currentFrameIndex?: number;
  currentLap?: number;
  selectedDriver?: string;
  compareDriver?: string;
  history?: Array<{ role: string; content: string }>;
}): Promise<ChatResponse> {
  return requestJson<ChatResponse>('/chat', {
    method: 'POST',
    body: JSON.stringify({
      message: params.message,
      year: 2025,
      round_number: params.roundNumber ?? 1,
      session_type: params.sessionType ?? 'R',
      current_frame_index: params.currentFrameIndex ?? null,
      current_lap: params.currentLap ?? null,
      selected_driver: params.selectedDriver ?? null,
      compare_driver: params.compareDriver ?? null,
      history: params.history ?? [],
    }),
  });
}
