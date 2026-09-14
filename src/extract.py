import json
import logging
from datetime import datetime
from pathlib import Path
import requests
import yaml

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s"
)

def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"Конфигурационный файл не найден: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def fetch_weather_data(base_url: str, params: dict, timeout: int = 10) -> dict:
    try:
        logging.info(f"Запрос к Open-Meteo API: {base_url}")
        response = requests.get(base_url, params=params, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        logging.error("Превышен таймаут ожидания ответа от Open-Meteo")
        raise
    except requests.exceptions.HTTPError as err:
        logging.error(f"HTTP ошибка от API: {err.response.status_code} - {err.response.text}")
        raise
    except requests.exceptions.RequestException as err:
        logging.error(f"Сетевая ошибка при запросе к API: {err}")
        raise

def save_raw_artifact(data: dict, output_dir: Path, city_id: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = output_dir / f"raw_weather_{city_id}_{timestamp}.json"
    
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        
    logging.info(f"Сырые данные погоды успешно сохранены в: {file_path}")
    return file_path

def main():
    config_path = Path("configs/variant_02.yml")
    config = load_config(config_path)
    
    api_cfg = config.get("api", {})
    entity_cfg = config.get("entity", {})
    
    base_url = api_cfg.get("base_url")
    params = api_cfg.get("params", {})
    city_id = entity_cfg.get("city_id", "RU_LED")
    
    # Запрос данных
    raw_data = fetch_weather_data(base_url=base_url, params=params, timeout=10)
    
    # Сохранение артефакта
    raw_dir = Path("data/raw")
    save_raw_artifact(data=raw_data, output_dir=raw_dir, city_id=city_id)

if __name__ == "__main__":
    main()
