from pathlib import Path

import pytest

from src.extract import build_params, validate_raw_payload


def test_build_params_expands_hourly_and_units():
    config = {
        "api": {"params": {"latitude": 59.9, "hourly": ["temperature_2m", "precipitation"]}}
    }
    params = build_params(config, "2026-09-15", "2026-09-16")
    assert params["hourly"] == "temperature_2m,precipitation"
    assert params["start_date"] == "2026-09-15"
    assert params["end_date"] == "2026-09-16"
    assert params["wind_speed_unit"] == "kmh"
    assert params["temperature_unit"] == "celsius"
    assert params["precipitation_unit"] == "mm"


def test_validate_raw_payload():
    payload = {
        "hourly": {
            "time": ["2026-09-15T00:00", "2026-09-15T01:00"],
            "temperature_2m": [10.0, 9.5],
            "precipitation": [0.0, 0.2],
        }
    }
    validate_raw_payload(payload, ["temperature_2m", "precipitation"])


def test_validate_raw_payload_detects_length_mismatch():
    payload = {"hourly": {"time": ["2026-09-15T00:00"], "temperature_2m": [10, 11]}}
    with pytest.raises(ValueError, match="Length mismatch"):
        validate_raw_payload(payload, ["temperature_2m"])
