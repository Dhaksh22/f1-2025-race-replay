from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class SessionOption(BaseModel):
    code: str = Field(..., description="Session code: FP1, FP2, FP3, SQ, S, Q, R")
    name: str = Field(..., description="Human-readable session name")
    scheduled_date: Optional[str] = None


class EventSummary(BaseModel):
    year: int = 2025
    round_number: int
    event_name: str
    circuit_name: Optional[str] = None
    country: Optional[str] = None
    date: Optional[str] = None
    event_format: str = "conventional"
    session_types: List[str] = Field(default_factory=list)
    sessions: List[SessionOption] = Field(default_factory=list)
    has_cached_data: bool = False


class DriverInfo(BaseModel):
    code: str
    driver_number: Optional[str] = None
    full_name: Optional[str] = None
    team: Optional[str] = None
    color: str = "#FFFFFF"


class DrsZonePoint(BaseModel):
    x: float
    y: float
    index: int


class DrsZone(BaseModel):
    start: DrsZonePoint
    end: DrsZonePoint


class TrackGeometry(BaseModel):
    x_ref: List[float] = Field(default_factory=list)
    y_ref: List[float] = Field(default_factory=list)
    x_inner: List[float] = Field(default_factory=list)
    y_inner: List[float] = Field(default_factory=list)
    x_outer: List[float] = Field(default_factory=list)
    y_outer: List[float] = Field(default_factory=list)
    x_min: float = 0.0
    x_max: float = 1.0
    y_min: float = 0.0
    y_max: float = 1.0
    rotation_deg: float = 0.0
    circuit_length_m: Optional[float] = None
    drs_zones: List[DrsZone] = Field(default_factory=list)


class SessionMetadata(BaseModel):
    year: int = 2025
    round_number: int
    session_type: str
    event_name: str
    circuit_name: Optional[str] = None
    country: Optional[str] = None
    date: Optional[str] = None
    total_laps: Optional[int] = None
    circuit_length_m: Optional[float] = None
    circuit_rotation: float = 0.0
    fps: int = 25
    total_frames: int = 0
    duration_s: float = 0.0
    drivers: List[DriverInfo] = Field(default_factory=list)
    status: Literal["ready", "unavailable", "loading", "error"] = "ready"
    data_source: Literal["fastf1", "cached", "fallback_demo"] = "fastf1"
    notice: Optional[str] = None


class SafetyCarState(BaseModel):
    x: float
    y: float
    phase: Literal["deploying", "on_track", "returning"] = "on_track"
    alpha: float = 1.0
    is_simulated: bool = True


class WeatherSnapshot(BaseModel):
    track_temp: Optional[float] = None
    air_temp: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[float] = None
    rain_state: str = "DRY"


class DriverFrameState(BaseModel):
    x: float
    y: float
    dist: float = 0.0
    rel_dist: float = 0.0
    fraction: float = 0.0
    lap: int = 1
    position: int = 1
    tyre: int = -1
    tyre_compound_name: str = "UNKNOWN"
    tyre_life: int = 0
    speed: float = 0.0
    gear: int = 0
    drs: int = 0
    throttle: float = 0.0
    brake: float = 0.0
    in_pit: bool = False
    is_out: bool = False
    gap_to_leader_s: Optional[float] = None
    interval_s: Optional[float] = None


class ReplayFrame(BaseModel):
    frame_index: int = 0
    t: float
    lap: int = 1
    track_status: str = "1"
    track_status_label: str = "GREEN"
    drivers: Dict[str, DriverFrameState] = Field(default_factory=dict)
    weather: Optional[WeatherSnapshot] = None
    safety_car: Optional[SafetyCarState] = None


class TrackStatusPeriod(BaseModel):
    status: str
    label: str = "GREEN"
    start_time: float
    end_time: Optional[float] = None
    start_lap: Optional[int] = None
    end_lap: Optional[int] = None


class RaceControlMessage(BaseModel):
    time: float
    category: str = ""
    message: str
    flag: str = ""
    scope: str = ""
    sector: str = ""
    racing_number: str = ""


class TimelineEventMarker(BaseModel):
    type: str
    frame: int
    end_frame: Optional[int] = None
    label: str = ""
    lap: Optional[int] = None


class LeaderboardEntry(BaseModel):
    position: int
    code: str
    full_name: Optional[str] = None
    team: Optional[str] = None
    color: str = "#FFFFFF"
    lap: int = 1
    tyre: int = -1
    tyre_compound: str = "UNKNOWN"
    tyre_life: int = 0
    in_pit: bool = False
    is_out: bool = False
    speed_kph: float = 0.0
    gear: int = 0
    drs_active: bool = False
    gap_to_leader_s: Optional[float] = None
    interval_s: Optional[float] = None
    last_lap_s: Optional[float] = None
    best_lap_s: Optional[float] = None


class LeaderboardSnapshot(BaseModel):
    frame_index: int = 0
    time_s: float = 0.0
    lap: int = 1
    total_laps: Optional[int] = None
    track_status: str = "1"
    track_status_label: str = "GREEN"
    entries: List[LeaderboardEntry] = Field(default_factory=list)


class LapSectorEntry(BaseModel):
    lap: int
    time_s: Optional[float] = None
    sector1_s: Optional[float] = None
    sector2_s: Optional[float] = None
    sector3_s: Optional[float] = None
    sector1_status: Literal["session_best", "personal_best", "none"] = "none"
    sector2_status: Literal["session_best", "personal_best", "none"] = "none"
    sector3_status: Literal["session_best", "personal_best", "none"] = "none"
    tyre: int = -1
    tyre_compound: str = "UNKNOWN"
    tyre_life: int = 0
    is_pit_entry: bool = False
    is_out_lap: bool = False
    is_pit_affected: bool = False
    is_outlier: bool = False
    end_time_s: Optional[float] = None
    official_gap_to_leader_s: Optional[float] = None
    moving_avg_3_s: Optional[float] = None
    source: str = "official"


class DriverLapSummary(BaseModel):
    code: str
    color: str = "#FFFFFF"
    best_lap_s: Optional[float] = None
    theoretical_best_s: Optional[float] = None
    best_sectors: Dict[str, Optional[float]] = Field(default_factory=dict)
    laps: List[LapSectorEntry] = Field(default_factory=list)


class TyreStint(BaseModel):
    stint_number: int
    compound: str
    compound_int: int
    start_lap: int
    end_lap: int
    lap_count: int
    max_tyre_life: int


class TyreDegradationHealth(BaseModel):
    driver_code: str
    compound: str = "UNKNOWN"
    laps_on_tyre: int = 0
    health_pct: float = 100.0
    expected_delta_s: float = 0.0
    degradation_rate_s_per_lap: float = 0.0
    overdriving: bool = False
    uncertainty_s: float = 0.0
    summary_text: str = "N/A"


class DriverStrategySummary(BaseModel):
    code: str
    position: Optional[int] = None
    color: str = "#FFFFFF"
    pit_stops: int = 0
    pit_windows_s: List[List[float]] = Field(default_factory=list)
    stints: List[TyreStint] = Field(default_factory=list)
    degradation: Optional[TyreDegradationHealth] = None


class TelemetrySample(BaseModel):
    t: float
    dist_m: float
    rel_dist: float = 0.0
    lap: int = 1
    speed_kph: float = 0.0
    throttle_pct: float = 0.0
    brake_pct: float = 0.0
    gear: int = 0
    drs: int = 0


class DriverTelemetrySeries(BaseModel):
    code: str
    color: str = "#FFFFFF"
    mode: Literal["lap", "time", "quali_segment", "best_lap"] = "lap"
    lap: Optional[int] = None
    segment: Optional[str] = None
    lap_time_s: Optional[float] = None
    sector1_s: Optional[float] = None
    sector2_s: Optional[float] = None
    sector3_s: Optional[float] = None
    compound: Optional[str] = None
    max_speed_kph: Optional[float] = None
    min_speed_kph: Optional[float] = None
    samples: List[TelemetrySample] = Field(default_factory=list)


class TelemetryComparisonResponse(BaseModel):
    year: int = 2025
    round_number: int
    session_type: str
    mode: str
    primary: DriverTelemetrySeries
    comparison: Optional[DriverTelemetrySeries] = None
    delta_summary: Optional[Dict[str, Any]] = None


class FrameChunkResponse(BaseModel):
    year: int = 2025
    round_number: int
    session_type: str
    start_frame: int
    end_frame: int
    step: int = 1
    total_frames: int
    frames: List[ReplayFrame] = Field(default_factory=list)


class ChatSource(BaseModel):
    title: str
    url: str
    source_org: str = "FIA / Formula 1"
    retrieval_date: str = "2025-03-01"
    category: str = "Regulations"


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    year: int = Field(default=2025)
    round_number: Optional[int] = None
    session_type: Optional[str] = "R"
    selected_drivers: List[str] = Field(default_factory=list)
    current_lap: Optional[int] = None
    current_time_s: Optional[float] = None
    session_context: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    source_details: List[ChatSource] = Field(default_factory=list)
    verified_session_facts: List[str] = Field(default_factory=list)
    calculated_metrics: List[str] = Field(default_factory=list)
    general_f1_knowledge: List[str] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    model: Optional[str] = None
    provider_mode: Literal["llm_api", "local_rag_synthesizer"] = "local_rag_synthesizer"
