from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import requests
import yaml


LOG = logging.getLogger("extract")
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def load_config(config_path: Path) -> dict[str, Any]:
    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError("Config must contain a YAML mapping at the top level")
    return config


def build_params(config: dict[str, Any], start_date: str | None, end_date: str | None) -> dict[str, Any]:
    params = dict(config["api"].get("params", {}))
    hourly = params.get("hourly", [])
    if isinstance(hourly, list):
        params["hourly"] = ",".join(hourly)

 
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    params.setdefault("temperature_unit", "celsius")
    params.setdefault("wind_speed_unit", "kmh")
    params.setdefault("precipitation_unit", "mm")
    return params


def validate_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}', expected YYYY-MM-DD") from exc
    return value


def request_json(url: str, params: dict[str, Any], timeout: int, retries: int, retryable_status_codes: set[int]) -> requests.Response:
    last_error: Exception | None = None
    with requests.Session() as session:
        for attempt in range(1, retries + 1):
            try:
                LOG.info("GET %s (attempt %d/%d)", url, attempt, retries)
                response = session.get(url, params=params, timeout=timeout)
                LOG.info("HTTP %s, %.3fs", response.status_code, response.elapsed.total_seconds())

                if response.ok:
                    return response

                if response.status_code not in retryable_status_codes:
                    response.raise_for_status()

                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = min(int(retry_after), 30)
                else:
                    delay = min(2 ** (attempt - 1), 10)
                if attempt < retries:
                    LOG.warning("Transient HTTP %s; retrying in %ss", response.status_code, delay)
                    import time

                    time.sleep(delay)
                else:
                    response.raise_for_status()
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt < retries:
                    delay = min(2 ** (attempt - 1), 10)
                    LOG.warning("Request failed (%s); retrying in %ss", exc.__class__.__name__, delay)
                    import time

                    time.sleep(delay)
                else:
                    raise RuntimeError(f"HTTP request failed after {retries} attempts: {exc}") from exc
            except requests.HTTPError:
                raise

    raise RuntimeError(f"HTTP request failed: {last_error}")


def validate_raw_payload(payload: dict[str, Any], requested_hourly: list[str]) -> None:
    if "hourly" not in payload:
        raise ValueError("API response does not contain 'hourly'")

    hourly = payload["hourly"]
    times = hourly.get("time")
    if not isinstance(times, list):
        raise ValueError("API response hourly.time must be a list")

    for variable in requested_hourly:
        if variable not in hourly:
            raise ValueError(f"API response missing requested hourly variable: {variable}")
        if not isinstance(hourly[variable], list) or len(hourly[variable]) != len(times):
            raise ValueError(f"Length mismatch for hourly variable '{variable}'")


def choose_output_path(base_dir: Path, city_id: str, run_dt: datetime) -> Path:
    folder = base_dir / run_dt.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{city_id}_forecast_{run_dt.strftime('%H%M%S')}.json"


def run(config_path: Path, output_dir: Path, start_date: str | None, end_date: str | None,
        timeout: int, retries: int) -> Path:
    config = load_config(config_path)
    api = config["api"]
    entity = config["entity"]
    url = api["base_url"]
    requested_hourly = api["params"].get("hourly", [])
    params = build_params(config, start_date, end_date)

    request_cfg = api.get("request", {})
    configured_codes = request_cfg.get("retry_status_codes", sorted(RETRYABLE_STATUS_CODES))
    retryable_status_codes = {int(code) for code in configured_codes}
    timeout = int(request_cfg.get("timeout_seconds", timeout)) if timeout == DEFAULT_TIMEOUT else timeout
    retries = int(request_cfg.get("retries", retries)) if retries == DEFAULT_RETRIES else retries

    response = request_json(url, params, timeout, retries, retryable_status_codes)
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("API returned a non-JSON response") from exc

    if not isinstance(payload, dict):
        raise ValueError("API response JSON must be an object")
    validate_raw_payload(payload, requested_hourly)

    run_dt = datetime.now().astimezone()
    output_path = choose_output_path(output_dir, entity["city_id"], run_dt)

    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOG.info("Saved raw response: %s", output_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract raw weather data from Open-Meteo")
    parser.add_argument("--config", type=Path, default=Path("configs/variant_02.yml"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--start-date", type=validate_date)
    parser.add_argument("--end-date", type=validate_date)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    if args.timeout <= 0 or args.retries <= 0:
        parser.error("--timeout and --retries must be positive")
    if args.start_date and args.end_date:
        start = datetime.strptime(args.start_date, "%Y-%m-%d")
        end = datetime.strptime(args.end_date, "%Y-%m-%d")
        if start > end:
            parser.error("--start-date must not be after --end-date")

    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s")

    try:
        run(args.config, args.output_dir, args.start_date, args.end_date, args.timeout, args.retries)
        return 0
    except (OSError, KeyError, ValueError, requests.HTTPError, RuntimeError) as exc:
        LOG.error("Extract failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
