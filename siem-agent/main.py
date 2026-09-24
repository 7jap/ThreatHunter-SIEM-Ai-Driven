import time
import logging
import uuid
import sys
import subprocess
import importlib.util
import os

# Configure basic logging for bootstrap
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("siem_agent")

def ensure_dependencies():
    """Check and auto-install required third-party packages."""
    required = {
        "requests": "requests",
        "yaml": "pyyaml"
    }
    for mod_name, pkg_name in required.items():
        if importlib.util.find_spec(mod_name) is None:
            logger.info(f"Missing dependency '{pkg_name}'. Auto-installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])
                logger.info(f"Successfully installed {pkg_name}")
            except Exception as e:
                logger.critical(f"Failed to install {pkg_name}: {e}")
                sys.exit(1)

# Run dependency check BEFORE importing our modules
ensure_dependencies()

from config.manager import ConfigManager
from collector.suricata_detector import SuricataDetector
from collector.eve_reader import EveReader
from storage.sqlite_queue import SQLiteQueue
from transport.client import TransportClient

import argparse

def main():
    parser = argparse.ArgumentParser(description="SIEM Agent")
    parser.add_argument("--server-ip", type=str, help="IP address or Hostname of the SIEM Server")
    args = parser.parse_args()

    logger.info("Starting SIEM Agent Bootstrap Process...")
    
    # 1. Load Configuration
    config = ConfigManager()
    
    # Apply server IP from arguments if provided
    if args.server_ip:
        config.config["server"]["host"] = args.server_ip
        config.save()
        logger.info(f"SIEM Server updated from command line to: {args.server_ip}")
    else:
        # Check if we need to ask for the SIEM IP interactively
        current_host = config.get("server", "host")
        if current_host == "127.0.0.1" and sys.stdin.isatty():
            print("\n" + "="*50)
            print(" SIEM Agent First-Run Setup ")
            print("="*50)
            siem_ip = input("Please enter the SIEM Server IP address or Hostname: ").strip()
            if siem_ip:
                config.config["server"]["host"] = siem_ip
                config.save()
                logger.info(f"SIEM Server set to: {siem_ip}")
            
    # Check if agent ID exists, if not generate one (Registration phase placeholder)
    if not config.get("agent", "id"):
        new_id = f"agent-{uuid.uuid4().hex[:8]}"
        config.config["agent"]["id"] = new_id
        config.save()
        logger.info(f"Assigned new Agent ID: {new_id}")
    
    agent_id = config.get("agent", "id")

    # 2. Detect Suricata
    detector = SuricataDetector(config)
    if not detector.detect_all():
        logger.error("Suricata detection failed. Ensure Suricata is installed. Exiting.")
        sys.exit(1)
        
    eve_log_path = config.get("suricata", "eve_json_path")

    # 3. Initialize Local Queue
    queue_path = config.get("agent", "queue_db_path")
    queue = SQLiteQueue(db_path=queue_path)
    logger.info(f"Local queue initialized at {queue_path}. Current size: {queue.get_size()}")

    # 4. Initialize Components
    reader = EveReader(log_path=eve_log_path, queue=queue, agent_id=agent_id)
    client = TransportClient(config_manager=config, queue=queue)

    # 4.5 Ensure Registration
    import socket
    hostname = socket.gethostname()
    is_registered = False
    
    def attempt_registration():
        try:
            session = client._get_session()
            reg_url = f"{client.base_url}/agent/register"
            logger.info(f"Attempting to register agent {agent_id} (Hostname: {hostname}) with SIEM Server at {reg_url}...")
            # Disable mTLS specifically for registration (optional depending on strictness, but we use standard session)
            resp = session.post(reg_url, json={"agent_id": agent_id, "hostname": hostname}, timeout=10)
            resp.raise_for_status()
            logger.info(f"Agent registration successful. Server responded: {resp.json()}")
            return True
        except Exception as e:
            logger.error(f"Registration failed: {e}. Will retry later.")
            return False

    is_registered = attempt_registration()

    heartbeat_interval = config.get("agent", "heartbeat_interval_sec")
    last_heartbeat = 0

    logger.info("Initialization complete. Entering main monitoring loop.")
    
    # 5. Main Loop
    try:
        while True:
            current_time = time.time()
            
            if not is_registered:
                # Retry registration every heartbeat interval
                if current_time - last_heartbeat > heartbeat_interval:
                    is_registered = attempt_registration()
                    last_heartbeat = current_time
                time.sleep(2)
                continue
                
            # Read new events from Suricata
            reader.read_new_events()
            
            # Sync queued events to Server
            if queue.get_size() > 0:
                client.sync_events()
                
            # Send periodic heartbeat
            if current_time - last_heartbeat > heartbeat_interval:
                status = {
                    "suricata": "running",
                    "queue_size": queue.get_size(),
                    "agent_version": "1.0.0"
                }
                success = client.send_heartbeat(status)
                if not success:
                    # If heartbeat fails, it might be due to server wipe or network. 
                    # We will force a re-registration attempt just in case the server forgot us (404/403).
                    is_registered = attempt_registration()
                    
                last_heartbeat = current_time
                
            time.sleep(2) # Small sleep to prevent CPU spinning
            
    except KeyboardInterrupt:
        logger.info("Agent shutting down gracefully.")
    except Exception as e:
        logger.critical(f"Agent encountered a fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
