# F1 Race Replay Project Documentation

## 1. Project overview

F1 Race Replay is a desktop Python application that replays Formula 1 sessions using data pulled from FastF1 and renders the result in a locally hosted graphical interface. The codebase does not implement a web backend or a multi-user service; instead, it is organized as a single-process desktop app with a GUI shell, replay engine, telemetry-processing pipeline, and secondary insight windows.

The repository evidence points to the following confirmed purpose:

- Load an F1 session (race, qualifying, sprint qualifying, or practice) for a given year and round.
- Download and cache telemetry data via FastF1.
- Process per-driver telemetry into replay frames.
- Render the track, position markers, leaderboard, lap times, and race status overlays.
- Support live telemetry insight windows and a local telemetry stream for developer tooling.

The main entrypoint is `main.py`, which parses command-line arguments and either opens a CLI session selection flow or a GUI-driven selection flow. The core telemetry logic sits in `src/f1_data.py`, while the replay renderer is assembled through `src/run_session.py` and the Arcade-based interfaces under `src/interfaces/`.

## 2. Evidence-based technology stack

From the repository manifests and imports, the project is built on:

- Python 3.11+ (documented in `README.md`)
- FastF1 for session fetching and telemetry extraction
- Arcade for the replay rendering window and interactive scene
- PySide6 for the selection GUI and additional Qt-based windows
- pandas and numpy for telemetry processing and numerical work
- matplotlib for telemetry chart windows
- pytest for lightweight automated tests

This is confirmed by:

- `requirements.txt`
- `requirements-dev.txt`
- import statements in `main.py`, `src/f1_data.py`, `src/interfaces/*.py`, and `src/insights/*.py`
- `docs/Testing.md`

## 3. Architectural summary

The application follows a local desktop architecture with four main layers:

1. Startup and session bootstrap
   - `main.py`
   - `src/cli/race_selection.py`
   - `src/gui/race_selection.py`

2. Data acquisition and processing
   - `src/f1_data.py`
   - `src/lib/settings.py`
   - `src/lib/season.py`
   - `src/lib/tyres.py`
   - `src/lib/time.py`

3. Replay and visual rendering
   - `src/run_session.py`
   - `src/interfaces/race_replay.py`
   - `src/interfaces/qualifying.py`
   - `src/interfaces/practice.py`
   - `src/ui_components.py`

4. Secondary analysis and streaming tools
   - `src/services/stream.py`
   - `src/insights/*.py`
   - `src/gui/insights_menu.py`
   - `src/gui/pit_wall_window.py`

```mermaid
flowchart TD
    A[main.py entrypoint] --> B[Session selection CLI/GUI]
    B --> C[load_session() in src/f1_data.py]
    C --> D[FastF1 data download/cache]
    D --> E[Telemetry processing + frame generation]
    E --> F[Arcade replay window]
    F --> G[HUD + leaderboard + track overlays]
    F --> H[Telemetry stream server on localhost:9999]
    H --> I[Insight windows / telemetry viewer]
    F --> J[Live standings + safety car tracking]
```

## 4. Startup and execution flow

### 4.1 Entry point

`main.py` is the application entrypoint. It parses command-line arguments such as:

- `--cli` to launch the terminal-based session picker
- `--viewer` to launch the replay view
- `--year` and `--round` for direct targeting
- `--qualifying`, `--sprint-qualifying`, `--sprint`, `--fp1`, `--fp2`, `--fp3`
- `--no-hud` to hide the user HUD
- `--list-rounds` and `--list-sprints`
- `--playback-speed`
- `--refresh-data` support is mentioned in the README for forcing recomputation

The file then calls `load_session(year, round_number, session_type)` and routes into either:

- `run_qualifying_replay()`
- `run_practice_replay()`
- `run_arcade_replay()` for race/sprint sessions

### 4.2 GUI selection workflow

`src/gui/race_selection.py` provides the primary GUI selection flow. It lets the user choose a year, round, and session type. The CLI equivalent in `src/cli/race_selection.py` performs a similar pick-and-launch process using `questionary` and `rich`.

### 4.3 Session loading

The application uses a `load_session()` call from `src/f1_data.py` to fetch the session object from FastF1. The session object is then used to obtain:

- driver lineup
- event metadata
- track status information
- lap data
- qualifying/practice/race telemetry
- standings context

This is the central integration point with the upstream F1 data source.

## 5. Data pipeline and replay logic

The heart of the project is `src/f1_data.py`. This file does more than download data; it transforms raw FastF1 output into replay-ready structures.

### 5.1 Telemetry acquisition

The project has a set of session-specific loaders, including:

- `get_race_telemetry(session, session_type="R")`
- `get_quali_telemetry(session, session_type="Q")`
- `get_practice_telemetry(session, session_type="FP1")`
- helper functions such as `list_rounds(year)` and `list_sprints(year)`

The processing model is explicit: session laps are picked per driver, lap telemetry is extracted with `lap.get_telemetry()`, and arrays such as X/Y coordinates, speed, gear, throttle, brake, tyre compounds, DRS, and lap numbers are assembled into replay frames.

### 5.2 Multi-driver frame generation

The function `_process_single_driver(args)` processes one driver's laps and gathers arrays for:

- `SessionTime`
- `X`, `Y`
- `Distance`, `RelativeDistance`
- speed, gear, throttle, brake
- DRS, tyre compound, tyre life
- lap numbering

The data is concatenated into a single per-driver telemetry profile and then used to build the final session frames. The code comments explicitly call out performance-oriented processing and caching, including computed-data storage and reuse.

### 5.3 Track status and race-state overlays

The race replay includes track status data (`track_statuses`) and a `safety_car` object in each frame. The repository explicitly documents and implements a simulated safety car because the underlying F1 API does not provide actual GPS telemetry for the Safety Car. In `src/f1_data.py`, a simulated safety-car placement is used to position the car ahead of the leader based on track reference points.

The `README.md` confirms this behavior and its limitations, including:

- safety car deployment timing comes from `session.track_status`
- position is approximated by placing the SC roughly 500 meters ahead of the leader
- phases include deploying, on_track, and returning
- the object is rendered as a larger amber marker with an animation glow

### 5.4 Live standings

The app also computes standing snapshots in real time for the replay. `main.py` calls `_get_current_championship_standings(session)` and `get_live_standings(...)` before launching the replay.

This means the replay is not only a pure visualization: it also integrates with live championship state by building per-lap points progression using the session lap position data and Ergast standings data.

## 6. Rendering architecture

### 6.1 Replay window composition

`src/interfaces/race_replay.py` defines `F1RaceReplayWindow`, the main Arcade window for race sessions. It handles:

- world geometry for the track
- car markers and position overlays
- HUD and leaderboard placement
- safety car rendering
- lap/time indicators
- telemetry stream startup
- configurable title and HUD visibility

The replay uses a real-world circuit reference polyline and then converts world coordinates to screen coordinates for rendering. DRS zones and track geometry are derived from a representative lap and a circuit rotation is applied to fit the track cleanly.

### 6.2 Qualifying and practice views

The project includes dedicated interfaces:

- `src/interfaces/qualifying.py` for qualifying session replay and telemetry overlay display
- `src/interfaces/practice.py` for practice session replay and comparison-oriented analysis

These use similar patterns to the race replay but adapt the UI to the characteristics of practice and qualifying data, such as lap leaderboard views and comparison telemetry selection.

### 6.3 UI helper layer

`src/ui_components.py` contains reusable Arcade UI building blocks such as:

- leaderboard component
- race controls component
- DRS/legend helpers
- lap time and driver summary widgets

This is the visual composition layer that sits between the data pipeline and the on-screen replay scene.

## 7. Secondary analysis tools and telemetry stream

One of the more distinctive features of the project is the local telemetry stream. The repo documents a demo/insight capability to expose live telemetry to additional windows.

### 7.1 Stream server

`src/services/stream.py` defines `TelemetryStreamServer`, which:

- binds to `localhost:9999`
- listens for client connections
- broadcasts JSON-encoded telemetry data with newline separators
- keeps a list of active connected clients

`TelemetryStreamClient` is the opposite side, used by a secondary process to connect and receive the payload.

### 7.2 Insight windows

The project includes several insight windows under `src/insights/`:

- `driver_telemetry_window.py`
- `lap_time_chart_window.py`
- `race_control_feed_window.py`
- `sector_times_window.py`
- `track_position_window.py`
- `tyre_strategy_window.py`
- `telemetry_stream_viewer.py`
- `example_pit_wall_window.py`

The repository also includes a `PitWallWindow` base class in `src/gui/pit_wall_window.py` and a menu for launching these windows from `src/gui/insights_menu.py`.

This confirms the project was designed as an extensible pit-wall-style analysis environment rather than a single fixed window.

## 8. Configuration and persisted state

The project uses `src/lib/settings.py` to manage user settings. The settings manager stores JSON values in the OS user app-data directory and exposes defaults for:

- `cache_location` defaulting to `.fastf1-cache`
- `computed_data_location` defaulting to `computed_data`

The settings dialog in `src/gui/settings_dialog.py` lets the user change the FastF1 cache location and computed-data location. The repository implies that local caches are important for both downloaded telemetry and pre-processed event data.

Important implementation detail: `enable_cache()` in `src/f1_data.py` enables a FastF1 local cache using the configured path and creates the folder if it does not exist.

## 9. Directory structure and responsibilities

`main.py`
- CLI/GUI entrypoint and session dispatch.

`src/f1_data.py`
- session loading, telemetry processing, standings, safety car approximation, and replay data generation.

`src/run_session.py`
- launches the main Arcade replay window, telemetry viewer, and insights menu.

`src/interfaces/`
- replay windows for race, qualifying, and practice sessions.

`src/gui/`
- PySide6 windows for session selection, settings, and insight launchers.

`src/insights/`
- additional analysis windows consuming telemetry stream data.

`src/services/stream.py`
- TCP telemetry stream server/client for local data broadcasting.

`src/lib/`
- small helpers for season detection, time parsing, tyres, and settings management.

`docs/`
- project guidance, including testing notes and additional developer documentation.

`tests/`
- lightweight pytest suite focusing on non-live functionality.

## 10. Testing posture and validation evidence

The repository’s developer documentation states the test strategy is intentionally lightweight and avoids live-data or GUI-heavy cases.

From `docs/Testing.md`, the current suite includes:

- time formatting/parsing
- tyre compound mapping
- season detection
- settings persistence
- import smoke tests

This is an important architectural fact: the repo does not appear to include a broad end-to-end race validation suite in the checked-in tests. The project relies heavily on FastF1 data and runtime behavior during interactive sessions rather than a large automated acceptance suite.

## 11. Confirmed features vs. in-progress features

### Confirmed features

The following features are directly supported by code and documentation:

- race replay with driver positions and track render
- session selection by year/round and session type
- automatic FastF1 cache use and local precomputed data
- leaderboard and lap-time UI
- driver status overlays and retirements
- safety car visualization based on track status data
- telemetry insight windows
- local telemetry stream for external viewers

### Explicitly in-development or demo features

The repository itself labels some capabilities as early-stage:

- qualifying support is described as “in development” in `README.md`
- telemetry stream is described as a “usable state” or “early demo” in `telemetry.md`
- some UI and leaderboard elements are noted as approximations with known issues (for example, first-corner leaderboard inaccuracies and temporary pit-lane effects)

These are not hidden assumptions; they are explicitly documented in the repo.

## 12. Important non-features and constraints

The repository evidence does not show any of the following:

- database layer
- server-side API backend
- authentication system
- user accounts or multi-user session management
- deployment/service architecture

The app is a local desktop tool that interacts with external F1 data sources and renders results on the machine running it. This is a key architectural distinction and is important when evaluating the project’s intended runtime model.

## 13. Notable implementation nuances

The code also contains several practical design decisions that are worth documenting:

- The application uses `FastF1.Cache.enable_cache(...)` and stores session data in a project-configurable location.
- The telemetry processing is optimized for per-driver batch processing and concatenation.
- Safety car position is approximated rather than actual GPS-tracked SC telemetry.
- A fallback path for sprint qualifying sessions maps `S` to `SQ`-style flow in the session selection logic.
- Computed telemetry and race-state overlays are stored and re-used to speed up repeated launches.

## 14. Maintenance guidance

For future maintenance, the repo is organized in a way that maps directly to concerns:

- modify session-fetch logic in `src/f1_data.py`
- change the replay paint loop in `src/interfaces/race_replay.py`
- adjust selection UX in `src/gui/race_selection.py`
- extend visual insight tooling in `src/insights/`
- change telemetry broadcast behavior in `src/services/stream.py`
- adjust persistent paths and cache settings in `src/lib/settings.py`

The app’s modularity is strong enough for new telemetry windows or additional session types, but the underlying race logic still depends heavily on FastF1 data semantics and local approximations for non-ideal metadata.

## 15. Conclusion

The repository clearly defines F1 Race Replay as a local, desktop, Formula 1 telemetry replay and analysis application. Its architecture is centered on FastF1 session ingestion, custom telemetry processing, Arcade-based visual replay rendering, and extensible telemetry insight windows. The app supports live race replay, session selection, tracks, HUD overlays, safety-car simulation, and a telemetry stream for adjacent visualization tools.

The project is best understood as a desktop analysis tool with a graphical front end, not as a web application or data service. The repository evidence also makes clear that some features are still early-stage or demo-oriented, particularly the qualifying workflow and the telemetry-stream tooling, and that the project intentionally includes approximation-based behavior where official data is incomplete.

This document is intentionally grounded in the repository itself and does not assume a broader product scope beyond what the code and docs clearly support.
