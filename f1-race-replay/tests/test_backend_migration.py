from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app.services.race_data import (
    SessionUnavailableError,
    get_processed_cache_path,
    invalidate_processed_cache,
    load_replay_payload,
)
from src.lib.season import require_2025_year


client = TestClient(app)


class TestSeasonRestriction:
    """1. 2025 season restriction enforcement across service layer, HTTP API, WebSocket, and Chatbot."""

    def test_require_2025_year_accepts_2025_and_rejects_others(self):
        assert require_2025_year(2025) == 2025
        for invalid_year in (2021, 2023, 2024, 2026):
            with pytest.raises(ValueError, match="2025"):
                require_2025_year(invalid_year)

    def test_seasons_endpoint_returns_only_2025(self):
        resp = client.get("/api/seasons")
        assert resp.status_code == 200
        body = resp.json()
        assert body["supported_years"] == [2025]
        assert body["default_year"] == 2025

    def test_events_endpoint_rejects_non_2025_year(self):
        resp = client.get("/api/events?year=2024")
        assert resp.status_code == 400
        assert "2025" in resp.json()["detail"]

    def test_session_endpoints_reject_non_2025_year(self):
        for path in (
            "/api/sessions/2024/1",
            "/api/sessions/2023/1/replay",
            "/api/sessions/2024/1/frames",
            "/api/sessions/2024/1/leaderboard",
            "/api/sessions/2024/1/telemetry?driver=NOR",
            "/api/sessions/2024/1/strategy",
            "/api/sessions/2024/1/laps",
            "/api/sessions/2024/1/race-control",
        ):
            resp = client.get(path)
            assert resp.status_code == 400
            assert "2025" in resp.json()["detail"]


class TestEventAndSessionSelection:
    """2. Event and session selection for 2025 calendar."""

    def test_list_2025_events_returns_full_calendar(self):
        resp = client.get("/api/events?year=2025")
        assert resp.status_code == 200
        body = resp.json()
        assert body["year"] == 2025
        events = body["events"]
        assert isinstance(events, list)
        assert len(events) >= 20
        first = events[0]
        assert first["year"] == 2025
        assert first["round_number"] == 1
        assert "Australian" in first["event_name"]

    def test_sprint_weekend_includes_sq_and_s_sessions(self):
        resp = client.get("/api/events/2/sessions?year=2025")
        assert resp.status_code == 200
        body = resp.json()
        codes = [s["session_type"] for s in body["sessions"]]
        assert "SQ" in codes
        assert "S" in codes
        assert "Q" in codes
        assert "R" in codes

    def test_invalid_round_returns_404(self):
        resp = client.get("/api/events/99/sessions?year=2025")
        assert resp.status_code == 404


class TestReplaySerializationAndOrdering:
    """3 & 4. Serialization of processed session data, frame ordering, and timestamp handling."""

    def test_replay_payload_serializes_cleanly_with_monotonic_timestamps(self):
        resp = client.get("/api/sessions/2025/1/replay?session_type=R&include_frames=true")
        assert resp.status_code == 200
        data = resp.json()

        session_meta = data["session"]
        assert session_meta["year"] == 2025
        assert session_meta["round_number"] == 1
        assert session_meta["session_type"] == "R"
        assert session_meta["total_frames"] > 10
        assert len(session_meta["drivers"]) >= 10

        # Verify track geometry coordinates and inner/outer boundaries
        track = data["track_geometry"]
        assert len(track["x_ref"]) > 50
        assert len(track["x_ref"]) == len(track["y_ref"])
        assert len(track["x_inner"]) == len(track["y_inner"])
        assert len(track["x_outer"]) == len(track["y_outer"])
        assert track["x_max"] > track["x_min"]
        assert track["y_max"] > track["y_min"]

        # Verify frames have monotonically increasing timestamps and indices
        frames = data["frames"]
        assert len(frames) == session_meta["total_frames"]
        prev_time = -1.0
        for idx, frame in enumerate(frames):
            assert frame["t"] > prev_time
            prev_time = frame["t"]
            assert isinstance(frame["drivers"], dict)
            assert len(frame["drivers"]) > 0
            # Check safety car state explicitly marked as simulated
            if frame.get("safety_car"):
                assert frame["safety_car"]["is_simulated"] is True


class TestSeekingLeaderboardAndAnalytics:
    """5 & 6. Seeking, playback state transitions, leaderboard intervals, telemetry, strategy, and missing fields."""

    def test_frame_chunk_pagination_and_seeking(self):
        resp = client.get("/api/sessions/2025/1/frames?session_type=R&start_frame=5&end_frame=25&step=2")
        assert resp.status_code == 200
        chunk = resp.json()
        assert chunk["start_frame"] == 5
        assert chunk["step"] == 2
        assert len(chunk["frames"]) >= 5
        assert chunk["frames"][0]["frame_index"] == 5
        assert chunk["frames"][1]["frame_index"] == 7

    def test_leaderboard_snapshot_by_frame_and_lap(self):
        resp = client.get("/api/sessions/2025/1/leaderboard?session_type=R&frame_index=25")
        assert resp.status_code == 200
        lb = resp.json()
        assert lb["frame_index"] == 25
        assert len(lb["entries"]) >= 10
        assert lb["entries"][0]["position"] == 1
        assert lb["entries"][0]["gap_to_leader_s"] == 0.0

        resp_lap = client.get("/api/sessions/2025/1/leaderboard?session_type=R&lap=5")
        assert resp_lap.status_code == 200
        lb_lap = resp_lap.json()
        assert lb_lap["lap"] >= 5

    def test_telemetry_comparison_and_missing_driver_error(self):
        resp = client.get(
            "/api/sessions/2025/1/telemetry?session_type=R&driver=NOR&compare_with=VER&mode=lap&lap=5"
        )
        assert resp.status_code == 200
        telemetry = resp.json()
        assert telemetry["mode"] == "lap"
        assert telemetry["primary"]["code"] == "NOR"
        assert telemetry["comparison"]["code"] == "VER"
        assert len(telemetry["primary"]["samples"]) > 5
        sample = telemetry["primary"]["samples"][0]
        assert "speed_kph" in sample
        assert "throttle_pct" in sample
        assert "brake_pct" in sample
        assert "gear" in sample
        assert "drs" in sample
        assert telemetry["delta_summary"] is not None

        # Unknown driver returns 200 with empty samples (no fabricated telemetry)
        bad_resp = client.get("/api/sessions/2025/1/telemetry?session_type=R&driver=ZZZ")
        assert bad_resp.status_code == 200
        assert bad_resp.json()["primary"]["samples"] == []

    def test_strategy_laps_and_race_control_endpoints(self):
        strat_resp = client.get("/api/sessions/2025/1/strategy?session_type=R")
        assert strat_resp.status_code == 200
        strat = strat_resp.json()
        assert len(strat["strategies"]) >= 10
        first_strat = strat["strategies"][0]
        assert len(first_strat["stints"]) >= 1
        assert first_strat["degradation"] is not None
        assert 0.0 <= first_strat["degradation"]["health_pct"] <= 100.0

        laps_resp = client.get("/api/sessions/2025/1/laps?session_type=R")
        assert laps_resp.status_code == 200
        laps_data = laps_resp.json()
        assert len(laps_data["drivers"]) >= 10
        assert "sector1_s" in laps_data["session_best_sectors"]

        rc_resp = client.get("/api/sessions/2025/1/race-control?session_type=R")
        assert rc_resp.status_code == 200
        rc_data = rc_resp.json()
        assert isinstance(rc_data["race_control_messages"], list)
        assert "simulated" in rc_data["safety_car_note"].lower()


class TestCacheReuseAndInvalidation:
    """7 & 8. Processed data cache reuse, invalidation, and API error handling."""

    def test_cache_file_created_reused_and_invalidated(self):
        payload = load_replay_payload(2025, 3, "R")
        assert payload["session"]["round_number"] == 3
        cache_path = get_processed_cache_path(2025, 3, "R")
        assert cache_path.exists()

        # Reload from processed cache
        cached_payload = load_replay_payload(2025, 3, "R")
        assert cached_payload["session"]["total_frames"] == payload["session"]["total_frames"]

        # Invalidate via HTTP endpoint
        del_resp = client.delete("/api/sessions/2025/3/cache?session_type=R")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "cleared"
        assert not cache_path.exists()

    def test_invalid_session_type_returns_400(self):
        resp = client.get("/api/sessions/2025/1?session_type=INVALID")
        assert resp.status_code == 400

    def test_unavailable_session_error_returns_404(self, monkeypatch):
        import backend.app.api.routes as routes_mod

        monkeypatch.setattr(
            routes_mod,
            "load_session_details",
            lambda *a, **kw: (_ for _ in ()).throw(
                SessionUnavailableError("Telemetry not published yet for this session")
            ),
        )
        resp = client.get("/api/sessions/2025/24?session_type=FP3")
        assert resp.status_code == 404
        assert "not published yet" in resp.json()["detail"]


class TestWebSocketStreaming:
    """9. WebSocket connection, initial summary, seek, play, pause, speed, reset, ping, and disconnect."""

    def test_websocket_rejects_non_2025_season(self):
        with client.websocket_connect("/api/ws/replay/2024/1?session_type=R") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "2025" in msg["detail"]

    def test_websocket_session_init_seek_speed_play_pause_reset_ping(self):
        with client.websocket_connect("/api/ws/replay/2025/1?session_type=R") as ws:
            init_msg = ws.receive_json()
            assert init_msg["type"] == "session_init"
            assert init_msg["season"] == 2025
            assert init_msg["initial_frame"]["frame_index"] == 0
            assert "leaderboard" in init_msg["initial_frame"]

            # Seek by frame_index
            ws.send_json({"action": "seek", "frame_index": 15})
            seek_msg = ws.receive_json()
            assert seek_msg["type"] == "frame"
            assert seek_msg["frame_index"] == 15

            # Change speed
            ws.send_json({"action": "set_speed", "speed": 4.0})
            speed_msg = ws.receive_json()
            assert speed_msg["type"] == "frame"
            assert speed_msg["playback_speed"] == 4.0

            # Play and Pause
            ws.send_json({"action": "play"})
            play_msg = ws.receive_json()
            assert play_msg["is_paused"] is False

            ws.send_json({"action": "pause"})
            pause_msg = ws.receive_json()
            assert pause_msg["is_paused"] is True

            # Reset
            ws.send_json({"action": "reset"})
            reset_msg = ws.receive_json()
            assert reset_msg["frame_index"] == 0

            # Ping / Pong
            ws.send_json({"action": "ping"})
            pong_msg = ws.receive_json()
            assert pong_msg["type"] == "pong"


class TestFormula1Chatbot:
    """10 & 11. Chatbot context retrieval, FIA grounding, and refusal to fabricate facts or load other seasons."""

    def test_chatbot_retrieves_2025_session_facts_and_fia_regulations(self):
        resp = client.post(
            "/api/chat",
            json={
                "message": "Who is leading the race right now, what are their tyre stints, and how does DRS work?",
                "year": 2025,
                "round_number": 1,
                "session_type": "R",
                "current_frame_index": 30,
                "selected_driver": "NOR",
                "compare_driver": "VER",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["provider_mode"] in ("local_rag_synthesizer", "llm_api")
        assert len(body["verified_session_facts"]) > 0
        assert len(body["calculated_metrics"]) > 0
        assert len(body["general_f1_knowledge"]) > 0
        assert len(body["sources"]) > 0
        assert "NOR" in body["answer"] or "DRS" in body["answer"]

    def test_chatbot_refuses_non_2025_season_and_unrecorded_telemetry(self):
        # Request with year != 2025 in payload returns 422/400 validation error
        bad_year_resp = client.post(
            "/api/chat",
            json={
                "message": "Show me telemetry from 2024",
                "year": 2024,
            },
        )
        assert bad_year_resp.status_code in (400, 422)

        # Request asking about 2021 season and unrecorded tyre core temperatures / team radio
        resp = client.post(
            "/api/chat",
            json={
                "message": "What was the internal tyre core temperature and team radio transcript in 2021 Abu Dhabi?",
                "year": 2025,
                "round_number": 1,
                "session_type": "R",
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        uncertainties_text = " ".join(body["uncertainties"]).lower()
        assert "2021" in uncertainties_text and "2025" in uncertainties_text
        assert "cannot be verified" in uncertainties_text or "cannot be loaded" in uncertainties_text
