import os
import shutil
import subprocess
import logging
import yaml
import time
from pathlib import Path

logger = logging.getLogger(__name__)

class SuricataDetector:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.suricata_config = self.config_manager.get("suricata")
        
    def detect_all(self):
        """Attempts to find Suricata binary, config, and log paths."""
        logger.info("Starting Suricata detection process.")
        
        if self.suricata_config.get("mock_mode", False):
            logger.info("Mock mode enabled. Skipping actual detection.")
            return True
            
        binary_path = self._detect_binary()
        if not binary_path:
            logger.warning("Suricata binary not found on the system. Attempting to install...")
            if not self._install_suricata():
                logger.error("Failed to install Suricata.")
                return False
            binary_path = self._detect_binary()
            if not binary_path:
                logger.error("Suricata still not found after installation attempt.")
                return False

        version = self._detect_version(binary_path)
        
        config_path = self._detect_config(binary_path)
        if not config_path:
            logger.error("Suricata configuration file (suricata.yaml) not found.")
            return False
            
        # Ensure it is configured and running
        if not self._configure_and_start(config_path):
            logger.error("Failed to configure and start Suricata.")
            return False

        eve_path = self._detect_eve_log(config_path)
        if not eve_path:
            logger.error("Could not determine eve.json location from config.")
            return False

        self.suricata_config["binary_path"] = binary_path
        self.suricata_config["config_path"] = config_path
        self.suricata_config["eve_json_path"] = eve_path
        self.config_manager.save()
        
        logger.info(f"Suricata {version} detected successfully.")
        logger.info(f"Binary: {binary_path}")
        logger.info(f"Config: {config_path}")
        logger.info(f"Eve Log: {eve_path}")
        return True

    def _install_suricata(self):
        try:
            if shutil.which("apt-get"):
                logger.info("Installing Suricata via apt-get...")
                subprocess.check_call(["apt-get", "update"])
                subprocess.check_call(["apt-get", "install", "-y", "suricata"])
                return True
            elif shutil.which("yum"):
                logger.info("Installing Suricata via yum...")
                subprocess.check_call(["yum", "install", "-y", "epel-release"])
                subprocess.check_call(["yum", "install", "-y", "suricata"])
                return True
            elif shutil.which("dnf"):
                logger.info("Installing Suricata via dnf...")
                subprocess.check_call(["dnf", "install", "-y", "suricata"])
                return True
            else:
                logger.error("Unsupported OS for auto-installation of Suricata.")
                return False
        except Exception as e:
            logger.error(f"Error during Suricata installation: {e}")
            return False

    def _configure_and_start(self, config_path):
        """Ensures Suricata is configured to output eve.json and the service is running."""
        # Note: In a real system, we would parse suricata.yaml safely.
        # For prototype, we ensure the service starts.
        try:
            # Get default route interface
            res = subprocess.run("ip route show default | awk '/default/ {print $5}'", shell=True, capture_output=True, text=True)
            interface = res.stdout.strip()
            if interface and os.path.exists(config_path):
                # Basic sed to replace af-packet interface just in case (Debian/Ubuntu fix)
                subprocess.run(f"sed -i 's/interface: eth0/interface: {interface}/g' {config_path}", shell=True)
                
            if shutil.which("systemctl"):
                logger.info("Starting and enabling suricata.service...")
                subprocess.run(["systemctl", "unmask", "suricata.service"], capture_output=True)
                subprocess.run(["systemctl", "enable", "--now", "suricata.service"], check=True)
                time.sleep(2)  # Give it a moment to create eve.json
                
                # Check status
                status = subprocess.run(["systemctl", "is-active", "suricata"], capture_output=True, text=True)
                if status.stdout.strip() != "active":
                    logger.warning("Suricata service did not start cleanly via systemd. It might be running in init.d or requires manual config.")
            return True
        except Exception as e:
            logger.warning(f"Error starting Suricata service: {e}. Assuming it will be started manually.")
            return True # Don't block entirely, let the queue reading attempt

    def _detect_binary(self):
        if self.suricata_config.get("binary_path"):
            return self.suricata_config.get("binary_path")
        return shutil.which("suricata")

    def _detect_version(self, binary_path):
        try:
            result = subprocess.run([binary_path, "-V"], capture_output=True, text=True, check=True)
            output = result.stdout.strip()
            return output
        except Exception as e:
            logger.warning(f"Failed to detect Suricata version: {e}")
            return "unknown"

    def _detect_config(self, binary_path):
        if self.suricata_config.get("config_path"):
            return self.suricata_config.get("config_path")
            
        common_paths = [
            "/etc/suricata/suricata.yaml",
            "/usr/local/etc/suricata/suricata.yaml",
            "/opt/suricata/etc/suricata/suricata.yaml"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return path
        return None

    def _detect_eve_log(self, config_path):
        if self.suricata_config.get("eve_json_path"):
            return self.suricata_config.get("eve_json_path")
            
        default_log_dir = "/var/log/suricata"
        try:
            with open(config_path, "r") as f:
                data = yaml.safe_load(f)
                
            if data and isinstance(data, dict):
                default_log_dir = data.get("default-log-dir", "/var/log/suricata")
                
                outputs = data.get("outputs", [])
                for output in outputs:
                    if isinstance(output, dict) and "eve-log" in output and output["eve-log"].get("enabled", False):
                        filename = output["eve-log"].get("filename", "eve.json")
                        if os.path.isabs(filename):
                            return filename
                        else:
                            return os.path.join(default_log_dir, filename)
        except Exception as e:
            logger.warning(f"Failed to parse {config_path} for eve.json location: {e}")
            
        # Hard fallback - Do not check if exists, because Suricata might just be starting up
        return os.path.join(default_log_dir, "eve.json")
