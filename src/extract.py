from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import yaml

LOG = logging.getLogger("extract")
ROOT = Path(__file__).resolve().parents[1]
RETRYABLE_DEFAULT = {429, 500, 502, 503, 504}


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError("Конфигурация YAML должна быть объектом")
    return data


def parse_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Дата должна быть в формате YYYY-MM-DD") from exc
    return value


def build_params(config: dict[str, Any], start_date: str | None, end_date: str | None) -> dict[str, Any]:
    params = dict(config["api"]["params"])
    hourly = params.get("hourly", [])
    if not hourly:
        raise ValueError("В api.params.hourly должен быть хотя бы один показатель")
    params["hourly"] = ",".join(hourly) if isinstance(hourly, list) else str(hourly)
    if start_date:
        params["start_date"] = start_date
        params.pop("forecast_days", None)
    if end_date:
        params["end_date"] = end_date
    return params


def get_with_retries(url: str, params: dict[str, Any], timeout: int, retries: int, retry_codes: set[int], backoff: int) -> requests.Response:
    last_exc: Exception | None = None
    with requests.Session() as session:
        for attempt in range(1, retries + 1):
            try:
                response = session.get(url, params=params, timeout=timeout)
                LOG.info("HTTP %s | %s", response.status_code, response.url)
                if response.ok:
                    return response

                if response.status_code not in retry_codes:
                    detail = response.text[:500].replace("\n", " ")
                    raise RuntimeError(f"HTTP {response.status_code}: {detail}")

                if attempt < retries:
                    retry_after = response.headers.get("Retry-After")
                    delay = int(retry_after) if retry_after and retry_after.isdigit() else backoff * (2 ** (attempt - 1))
                    delay = min(delay, 30)
                    LOG.warning("HTTP %s; повтор через %s сек.", response.status_code, delay)
                    time.sleep(delay)
                else:
                    detail = response.text[:500].replace("\n", " ")
                    raise RuntimeError(f"HTTP {response.status_code} после {retries} попыток: {detail}")
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_exc = exc
                if attempt < retries:
                    delay = min(backoff * (2 ** (attempt - 1)), 30)
                    LOG.warning("%s; повтор через %s сек.", type(exc).__name__, delay)
                    time.sleep(delay)
                else:
                    raise RuntimeError(f"Сетевой запрос не выполнен после {retries} попыток: {exc}") from exc
    raise RuntimeError(str(last_exc) if last_exc else "Неизвестная ошибка HTTP")


def validate_payload(payload: dict[str, Any], expected: list[str]) -> None:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict) or not isinstance(hourly.get("time"), list):
        raise ValueError("В ответе API отсутствует hourly.time")
    n = len(hourly["time"])
    for name in expected:
        values = hourly.get(name)
        if not isinstance(values, list):
            raise ValueError(f"В ответе отсутствует hourly.{name}")
        if len(values) != n:
            raise ValueError(f"Длины hourly.time и hourly.{name} различаются")


def save_raw(payload: dict[str, Any], output_dir: Path, city_id: str) -> Path:
    now = datetime.now().astimezone()
    folder = output_dir / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{city_id}_forecast_{now.strftime('%H%M%S')}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def run(config_path: Path, output_dir: Path, start_date: str | None, end_date: str | None, timeout_override: int | None, retries_override: int | None) -> Path:
    config = load_config(config_path)
    api = config["api"]
    entity = config["entity"]
    if str(api.get("method", "GET")).upper() != "GET":
        raise ValueError("Этот Extract поддерживает только GET")

    req = api.get("request", {})
    timeout = timeout_override or int(req.get("timeout_seconds", 30))
    retries = retries_override or int(req.get("retries", 3))
    retry_codes = {int(x) for x in req.get("retry_status_codes", sorted(RETRYABLE_DEFAULT))}
    backoff = int(req.get("backoff_seconds", 2))
    params = build_params(config, start_date, end_date)
    expected = api["params"]["hourly"]

    response = get_with_retries(api["base_url"], params, timeout, retries, retry_codes, backoff)
    try:
        payload = response.json()
    except ValueError as exc:
        raise ValueError("API вернул невалидный JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("JSON-ответ API должен быть объектом")
    validate_payload(payload, expected)

    path = save_raw(payload, output_dir, entity["city_id"])
    LOG.info("RAW сохранён: %s", path)
    return path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "configs" / "variant_02.yml")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--start-date", type=parse_date)
    parser.add_argument("--end-date", type=parse_date)
    parser.add_argument("--timeout", type=int)
    parser.add_argument("--retries", type=int)
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    args = parser.parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(asctime)s %(levelname)s %(message)s")

    if args.start_date and args.end_date and args.start_date > args.end_date:
        parser.error("--start-date не может быть позже --end-date")
    if args.timeout is not None and args.timeout <= 0:
        parser.error("--timeout должен быть > 0")
    if args.retries is not None and args.retries <= 0:
        parser.error("--retries должен быть > 0")

    try:
        run(args.config, args.output_dir, args.start_date, args.end_date, args.timeout, args.retries)
        return 0
    except (OSError, KeyError, ValueError, RuntimeError) as exc:
        LOG.error("Extract завершён с ошибкой: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
