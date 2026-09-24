import os
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    def __init__(self, config_path: str = None):
        if not config_path:
            config_path = os.environ.get("SIEM_AGENT_CONFIG", "/etc/siem-agent/config.json")
            if os.name == 'nt' and not os.environ.get("SIEM_AGENT_CONFIG"):
                # Default for Windows if no env var
                config_path = "C:\\ProgramData\\siem-agent\\config.json"
                
        self.config_path = Path(config_path)
        self.config = self._default_config()
        self.load()

    def _default_config(self) -> dict:
        data_path = "/var/lib/siem-agent" if os.name != 'nt' else "C:\\ProgramData\\siem-agent\\data"
        cert_path = "/etc/siem-agent/certs" if os.name != 'nt' else "C:\\ProgramData\\siem-agent\\certs"
        
        # Override with test env vars if they exist
        data_path = os.environ.get("SIEM_AGENT_DATA", data_path)
        cert_path = os.environ.get("SIEM_AGENT_CERTS", cert_path)

        return {
            "server": {
                "host": "127.0.0.1",
                "port": 8443,
                "tls_enabled": True
            },
            "agent": {
                "id": None, # Will be set on registration
                "queue_db_path": os.path.join(data_path, "queue.db"),
                "log_level": "INFO",
                "heartbeat_interval_sec": 5  # Set to 5 for faster testing
            },
            "suricata": {
                "binary_path": None,
                "config_path": None,
                "eve_json_path": None,
                "mock_mode": False
            },
            "security": {
                "client_cert_path": os.path.join(cert_path, "client.crt"),
                "client_key_path": os.path.join(cert_path, "client.key"),
                "ca_cert_path": os.path.join(cert_path, "ca.crt")
            }
        }

    def load(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    self._merge_config(self.config, loaded)
                    logger.info(f"Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load config from {self.config_path}: {e}")
        else:
            logger.info(f"Config file not found at {self.config_path}, using defaults.")
            self.save()  # Auto-save defaults if not present

    def save(self):
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            # Ensure safe permissions on Linux (user-only read/write)
            if os.name != 'nt':
                os.chmod(self.config_path, 0o600)
            logger.info(f"Saved configuration to {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")

    def _merge_config(self, base: dict, override: dict):
        for k, v in override.items():
            if isinstance(v, dict) and k in base and isinstance(base[k], dict):
                self._merge_config(base[k], v)
            else:
                base[k] = v

    def get(self, section: str, key: str = None):
        if key:
            return self.config.get(section, {}).get(key)
        return self.config.get(section, {})
