import yaml
import os
from pathlib import Path

class ConfigLoader:
    """Loads analytics configuration from a YAML file.

    The configuration file is expected at ``analytics/analytics.yaml`` relative to the
    project root. All configurable values are defined there; the loader provides
    defaults for missing keys.
    """

    DEFAULTS = {
        "database_path": "data/analytics/metrics.sqlite",
        "queue_maxsize": 1000,
        "retention_days": 30,
        "system_monitor_interval_seconds": 10,
        "alert_thresholds": {
            "retrieval_latency_sec": 2.0,
            "llm_latency_sec": 5.0,
            "memory_mb": 500,
            "disk_usage_percent": 80,
            "hallucination_rate": 0.1,
        },
    }

    def __init__(self, config_path: str = None):
        # Resolve config path – if not supplied, look for standard location.
        self.config_path = Path(config_path or Path(__file__).parent / "analytics.yaml").expanduser()
        self.config = self.DEFAULTS.copy()
        self._load()

    def _load(self) -> None:
        if self.config_path.is_file():
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                # shallow merge – user‑provided keys override defaults
                self.config.update(data)
        else:
            # Ensure directory exists for future writes
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            # Write default config for user convenience
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(self.DEFAULTS, f)

    def get(self, key: str, default=None):
        return self.config.get(key, default)

    def __getitem__(self, key: str):
        return self.get(key)

    def __repr__(self) -> str:
        return f"ConfigLoader({self.config_path})"
