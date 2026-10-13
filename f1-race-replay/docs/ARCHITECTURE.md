# Formula 1 2025 Web Platform — Architecture & Design

This document details the architecture, component boundaries, data flow, WebSocket streaming protocol, Bayesian tyre model integration, and Grounded AI Chatbot for the Formula 1 2025 Race Replay and Telemetry Analytics web platform.

---

## 1. High-Level Layered Architecture

The application strictly decouples the browser frontend from the underlying data processing and replay engine without removing or breaking the existing desktop code (`main.py`, `src/`).

```mermaid
flowchart TD
    subgraph Browser ["Layer 1: Browser Frontend (React + TypeScript + Vite + Tailwind)"]
        UI_Nav["Session Selector (2025 Locked)"]
        UI_Canvas["Circuit Canvas (HTML5 Canvas / SVG)"]
        UI_Controls["Playback Transport & Timeline Scrubber"]
        UI_Leaderboard["Live Timing Tower & Weather HUD"]
        UI_Telemetry["Telemetry Comparison Traces"]
        UI_Sectors["F1 Purple/Green Sector Timing"]
        UI_Strategy["Tyre Stints & Bayesian Health Cards"]
        UI_RC["FIA Race Control Stream"]
        UI_Chat["F1 Pit-Wall AI Strategist"]
    end

    subgraph API ["Layer 2: Web API & Streaming Adapter (FastAPI + Pydantic)"]
        HTTP_Endpoints["REST Endpoints (/api/events, /api/sessions/2025/...)"]
        WS_Endpoint["WebSocket Engine (/api/ws/replay/2025/{round})"]
        Chat_Endpoint["Chatbot Endpoint (/api/chat)"]
        Season_Guard["Season Guard: require_2025_year()"]
    end

    subgraph Processing ["Layer 3: Pure Race Replay & Telemetry Engine (Arcade-Free)"]
        Replay_Service["backend/app/services/replay.py"]
        Telemetry_Service["backend/app/services/telemetry.py"]
        RaceData_Service["backend/app/services/race_data.py"]
        Bayesian_Integrator["src/tyre_degradation_integration.py & src/bayesian_tyre_model.py"]
        Sector_Analyzer["src/lib/sectors.py & src/lib/time.py"]
    end

    subgraph Storage ["Layer 4: Storage & Versioned Cache Layer"]
        FastF1_Cache[".fastf1-cache/ (Raw HTTP Cache)"]
        Computed_Dir["computed_data/ (Desktop Pickles)"]
        Processed_Cache["data/processed/ (Versioned .json.gz Payloads)"]
        Memory_Cache["In-Memory Payload Cache (_MEMORY_CACHE)"]
    end

    subgraph AI ["Layer 5: F1 Grounded RAG & Knowledge Layer"]
        FIA_Corpus["FIA 2025 Sporting/Tech Regulations & Pirelli Tyre Reference"]
        BM25_Retriever["Local Keyword-Boosted BM25 Retriever"]
        Context_Evidence["Session Evidence Extractor (Facts vs Metrics vs Uncertainties)"]
        Grounded_Synthesizer["Deterministic Grounded Synthesizer / Optional External LLM"]
    end

    Browser <-->|HTTP REST & JSON| API
    Browser <-->|WebSocket Commands & Frames| WS_Endpoint
    API --> Season_Guard
    Season_Guard --> Processing
    Processing --> Storage
    Processing --> AI
    Chat_Endpoint --> AI
```

---

## 2. Replay Streaming Protocol (WebSocket & HTTP Fallback)

The client communicates with the server over WebSocket for zero-latency bidirectional replay streaming, with automatic fallback to local interpolation or chunked HTTP polling.

```mermaid
sequenceDiagram
    autonumber
    actor Client as React Client (CircuitCanvas)
    participant WS as FastAPI WebSocket (/api/ws/replay/2025/{round})
    participant Engine as Race Replay Engine (backend/app/services/race_data.py)

    Client->>WS: Connect WebSocket (Round N, Session R)
    WS->>Engine: load_replay_payload(2025, N, "R")
    Engine-->>WS: Replay Payload (Track Geometry, Drivers, Frames)
    WS-->>Client: session_init (Track Geometry, Total Frames, Initial Frame 0, Leaderboard)

    Client->>WS: {"action": "play"}
    loop Continuous Frame Stream (Adaptive Timing)
        WS-->>Client: {"type": "frame", "frame_index": i, "frame": {...}, "leaderboard": {...}}
    end

    Client->>WS: {"action": "seek", "frame_index": 125}
    WS-->>Client: {"type": "frame", "frame_index": 125, "frame": {...}, "leaderboard": {...}}

    Client->>WS: {"action": "set_speed", "speed": 4.0}
    WS-->>Client: {"type": "frame", "playback_speed": 4.0, ...}

    Client->>WS: {"action": "pause"}
    WS-->>Client: {"type": "frame", "is_paused": true, ...}
```

---

## 3. Grounded F1 Knowledge Chatbot Architecture

To prevent LLM hallucination and adhere strictly to verified session facts, the chatbot employs a 4-tier evidence categorization pipeline:

```mermaid
flowchart LR
    UserQuery["User Prompt ('Who is leading and how does DRS work?')"] --> Parser["Driver & Regulation Entity Detector"]
    Parser --> Tool_Session["Session Context Tool (backend/app/services/chatbot.py)"]
    Parser --> Tool_RAG["FIA Regulations Retriever (backend/app/services/retrieval.py)"]

    Tool_Session --> Facts["1. Verified Session Facts (Session, Laps, Leader, Stints)"]
    Tool_Session --> Metrics["2. Calculated Metrics (Pace Delta, Degradation Rate)"]
    Tool_Session --> Uncertainties["4. Scope Limitations (Non-2025 season refusal, unrecorded telemetry)"]

    Tool_RAG --> Knowledge["3. General F1 Knowledge (FIA Sporting Regs, DRS Rules, Flag Rules)"]
    Tool_RAG --> Citations["Trusted Sources (FIA 2025 Sporting Regulations, Pirelli)"]

    Facts --> Synthesizer["Grounded Synthesizer / Optional LLM Provider"]
    Metrics --> Synthesizer
    Knowledge --> Synthesizer
    Uncertainties --> Synthesizer
    Citations --> Synthesizer

    Synthesizer --> StructuredResponse["ChatResponse (Answer + Structured Evidence Accordions)"]
```

---

## 4. Centralized 2025 Season Restriction

All entry points enforce the 2025 season lock:
1. **API Router**: Validates `year == 2025` using `require_2025_year()`. Returns HTTP 400 with a descriptive error message if any other year is requested.
2. **WebSocket Route**: Rejects non-2025 seasons immediately with error code 1008 and close event.
3. **Data Loader & Cache Paths**: Keys include the season (`v1_2025_R01_R.json.gz`).
4. **Chatbot Service**: Rejects queries requesting telemetry for other seasons (e.g. 2021, 2024), adding an explicit Season Restriction notice to the response uncertainties.
