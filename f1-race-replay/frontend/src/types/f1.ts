export interface SessionOption {
  code: string;
  session_type: string;
  name: string;
  label: string;
  available: boolean;
  scheduled_date?: string | null;
}

export interface EventSummary {
  year: number;
  round_number: number;
  event_name: string;
  circuit_name: string;
  location: string;
  country: string;
  date: string;
  event_date: string;
  event_format: string;
  is_sprint_weekend: boolean;
  session_types: string[];
  sessions: SessionOption[];
  has_cached_data?: boolean;
}

export interface DriverInfo {
  code: string;
  driver_number: string;
  full_name: string;
  team?: string | null;
  team_name?: string | null;
  color: string;
}

export interface DrsZone {
  start: { x: number; y: number; index: number };
  end: { x: number; y: number; index: number };
}

export interface TrackGeometry {
  x_ref: number[];
  y_ref: number[];
  x_inner: number[];
  y_inner: number[];
  x_outer: number[];
  y_outer: number[];
  x_min: number;
  x_max: number;
  y_min: number;
  y_max: number;
  rotation_deg: number;
  circuit_length_m?: number | null;
  drs_zones: DrsZone[];
}

export interface SessionMetadata {
  year: number;
  round_number: number;
  event_name: string;
  circuit_name: string;
  country: string;
  date: string;
  session_type: string;
  session_name: string;
  total_laps: number;
  total_frames: number;
  duration_s: number;
  circuit_length_m?: number | null;
  circuit_rotation?: number;
  data_source: string;
  drivers: DriverInfo[];
}

export interface DriverFrameState {
  x: number;
  y: number;
  dist: number;
  rel_dist: number;
  lap: number;
  position: number;
  speed: number;
  gear: number;
  drs: number;
  throttle: number;
  brake: number;
  tyre: number;
  tyre_compound_name?: string;
  tyre_life?: number;
  in_pit?: boolean;
  status?: string;
}

export interface SafetyCarState {
  active?: boolean;
  status_code?: string;
  phase: string;
  x: number;
  y: number;
  dist: number;
  rel_dist: number;
  alpha: number;
  is_simulated: boolean;
}

export interface WeatherSnapshot {
  track_temp?: number | null;
  air_temp?: number | null;
  humidity?: number | null;
  wind_speed?: number | null;
  wind_direction?: string | null;
  rain_state?: string | null;
}

export interface ReplayFrame {
  frame_index?: number;
  t: number;
  lap: number;
  drivers: Record<string, DriverFrameState>;
  weather?: WeatherSnapshot | null;
  safety_car?: SafetyCarState | null;
  track_status?: string;
  track_status_label?: string;
}

export interface TrackStatusPeriod {
  status: string;
  label?: string;
  start_time: number;
  end_time?: number | null;
  start_lap?: number | null;
  end_lap?: number | null;
}

export interface TimelineEventMarker {
  type: string;
  label: string;
  frame: number;
  end_frame?: number | null;
  lap?: number | null;
}

export interface RaceControlMessage {
  time: number;
  lap?: number;
  category: string;
  message: string;
  flag?: string | null;
  scope?: string | null;
  sector?: string | null;
}

export interface LeaderboardEntry {
  position: number;
  code: string;
  full_name: string;
  team?: string | null;
  color: string;
  lap: number;
  tyre: number;
  tyre_compound: string;
  tyre_life: number;
  in_pit: boolean;
  is_out: boolean;
  speed_kph: number;
  gear: number;
  drs_active: boolean;
  gap_to_leader_s: number;
  interval_s: number;
  last_lap_s?: number | null;
  best_lap_s?: number | null;
}

export interface LeaderboardSnapshot {
  frame_index: number;
  time_s: number;
  lap: number;
  total_laps?: number | null;
  track_status: string;
  track_status_label: string;
  entries: LeaderboardEntry[];
}

export interface LapSectorEntry {
  lap: number;
  time_s?: number | null;
  sector1_s?: number | null;
  sector2_s?: number | null;
  sector3_s?: number | null;
  sector1_status?: string;
  sector2_status?: string;
  sector3_status?: string;
  tyre: number;
  tyre_compound: string;
  tyre_life: number;
  is_pit_entry: boolean;
  is_out_lap: boolean;
  is_pit_affected: boolean;
  is_outlier: boolean;
  official_gap_to_leader_s?: number | null;
  moving_avg_3_s?: number | null;
}

export interface DriverLapSummary {
  code: string;
  color: string;
  best_lap_s?: number | null;
  theoretical_best_s?: number | null;
  best_sectors: {
    sector1_s?: number | null;
    sector2_s?: number | null;
    sector3_s?: number | null;
  };
  laps: LapSectorEntry[];
}

export interface TyreStint {
  stint_number: number;
  compound: string;
  compound_int: number;
  start_lap: number;
  end_lap: number;
  lap_count: number;
  max_tyre_life: number;
}

export interface TyreDegradationHealth {
  driver_code: string;
  compound: string;
  laps_on_tyre: number;
  health_pct: number;
  expected_delta_s: number;
  degradation_rate_s_per_lap: number;
  overdriving: boolean;
  uncertainty_s: number;
  summary_text: string;
}

export interface DriverStrategySummary {
  code: string;
  position?: number | null;
  color: string;
  pit_stops: number;
  stints: TyreStint[];
  degradation?: TyreDegradationHealth | null;
}

export interface TelemetrySample {
  t: number;
  dist_m: number;
  rel_dist: number;
  speed_kph: number;
  throttle_pct: number;
  brake_pct: number;
  gear: number;
  drs: number;
}

export interface DriverTelemetrySeries {
  code: string;
  color: string;
  mode: string;
  lap?: number | null;
  segment?: string | null;
  lap_time_s?: number | null;
  sector1_s?: number | null;
  sector2_s?: number | null;
  sector3_s?: number | null;
  compound?: string | null;
  max_speed_kph?: number | null;
  min_speed_kph?: number | null;
  samples: TelemetrySample[];
}

export interface TelemetryComparisonResponse {
  mode: string;
  primary: DriverTelemetrySeries;
  comparison?: DriverTelemetrySeries | null;
  delta_summary?: {
    primary_driver: string;
    comparison_driver: string;
    lap_time_delta_s?: number | null;
    max_speed_delta_kph?: number | null;
    sector1_delta_s?: number | null;
    sector2_delta_s?: number | null;
    sector3_delta_s?: number | null;
  } | null;
}

export interface ReplayPayload {
  season: number;
  session: SessionMetadata;
  track_geometry: TrackGeometry;
  driver_colors: Record<string, string>;
  track_status: TrackStatusPeriod[];
  track_statuses: TrackStatusPeriod[];
  timeline_events: TimelineEventMarker[];
  race_control_messages: RaceControlMessage[];
  strategies: DriverStrategySummary[];
  lap_summaries: {
    session_best_sectors: Record<
      string,
      { time_s?: number | null; holders: string[] }
    >;
    drivers: Record<string, DriverLapSummary>;
  };
  live_driver_standings?: Record<string, number>;
  live_constructor_standings?: Record<string, number>;
  frames: ReplayFrame[];
}

export interface ChatSource {
  id: string;
  title: string;
  category: string;
  source: string;
  score?: number;
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  source_details: ChatSource[];
  verified_session_facts: string[];
  calculated_metrics: string[];
  general_f1_knowledge: string[];
  uncertainties: string[];
  suggested_followups: string[];
  model: string;
  provider_mode: string;
}
