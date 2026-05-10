import json
from pathlib import Path


def load_site_config(local_path="site_config.local.json", example_path="site_config.example.json"):
    config = {}
    for path in (example_path, local_path):
        config_path = Path(path)
        if config_path.exists():
            with config_path.open(encoding="utf-8") as file:
                config.update(json.load(file))
    return config


def merge_site_config(data, site_config=None):
    merged = dict(load_site_config() if site_config is None else site_config)
    merged.update(data)
    return merged
