import os
import subprocess
import logging
import sys

logger = logging.getLogger(__name__)

SERVICE_TEMPLATE = """[Unit]
Description=SIEM Endpoint Agent
After=network.target suricata.service

[Service]
Type=simple
User=root
WorkingDirectory={working_dir}
ExecStart={python_exec} {main_script}
Restart=on-failure
RestartSec=10
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
"""

def install_systemd_service():
    """Installs the SIEM Agent as a systemd background service."""
    if os.geteuid() != 0:
        logger.error("Root privileges required to install systemd service.")
        return False
        
    if not os.path.exists("/bin/systemctl"):
        logger.warning("Systemd not found (not a systemd linux). Skipping service installation.")
        return False
        
    service_path = "/etc/systemd/system/siem-agent.service"
    
    # Check if already installed
    if os.path.exists(service_path):
        logger.info("SIEM Agent service is already installed.")
        return True
        
    working_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    main_script = os.path.join(working_dir, "main.py")
    python_exec = sys.executable
    
    service_content = SERVICE_TEMPLATE.format(
        working_dir=working_dir,
        python_exec=python_exec,
        main_script=main_script
    )
    
    try:
        with open(service_path, "w") as f:
            f.write(service_content)
            
        subprocess.check_call(["systemctl", "daemon-reload"])
        subprocess.check_call(["systemctl", "enable", "siem-agent.service"])
        logger.info("Successfully installed and enabled siem-agent.service")
        
        # We don't start it immediately here, we let the bootstrapper finish its first run
        # or we tell the user to use systemctl start siem-agent
        return True
    except Exception as e:
        logger.error(f"Failed to install systemd service: {e}")
        return False
