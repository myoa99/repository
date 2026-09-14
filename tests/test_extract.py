from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.extract import build_params, validate_payload


def test_build_params_joins_hourly():
    config = {"api": {"params": {"latitude": 1, "hourly": ["a", "b"]}}}
    p = build_params(config, "2026-09-15", "2026-09-16")
    assert p["hourly"] == "a,b"
    assert p["start_date"] == "2026-09-15"
    assert p["end_date"] == "2026-09-16"
    assert "forecast_days" not in p


def test_validate_payload_ok():
    payload = {"hourly": {"time": ["t1", "t2"], "temperature_2m": [1, 2], "relative_humidity_2m": [50, 60], "precipitation": [0, 1], "wind_speed_10m": [5, 6]}}
    validate_payload(payload, ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m"])


def test_validate_payload_rejects_missing():
    try:
        validate_payload({"hourly": {"time": ["t1"]}}, ["temperature_2m"])
    except ValueError:
        return
    assert False
