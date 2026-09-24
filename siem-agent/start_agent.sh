#!/bin/bash

# ==============================================================================
# SIEM Agent Bootstrapper & Launcher
# ==============================================================================

echo "[INFO] Starting SIEM Agent Initialization..."

# 1. Check for Root Privileges
if [ "$EUID" -ne 0 ]; then
  echo "[ERROR] Please run this script as root (using sudo)."
  echo "        Root privileges are required to install Python, read Suricata logs, and run as a background service."
  exit 1
fi

# 2. Check and Install Python 3
if ! command -v python3 &> /dev/null; then
    echo "[INFO] Python 3 is not installed. Detecting package manager to install it..."
    
    if command -v apt-get &> /dev/null; then
        echo "[INFO] Detected Debian/Ubuntu (apt-get)."
        apt-get update
        apt-get install -y python3 python3-pip
    elif command -v dnf &> /dev/null; then
        echo "[INFO] Detected Fedora/RHEL 8+ (dnf)."
        dnf install -y python3 python3-pip
    elif command -v yum &> /dev/null; then
        echo "[INFO] Detected CentOS/RHEL 7 (yum)."
        yum install -y python3 python3-pip
    elif command -v zypper &> /dev/null; then
        echo "[INFO] Detected openSUSE (zypper)."
        zypper install -y python3 python3-pip
    elif command -v pacman &> /dev/null; then
        echo "[INFO] Detected Arch Linux (pacman)."
        pacman -Sy --noconfirm python python-pip
    else
        echo "[ERROR] Unsupported Linux distribution. Please install Python 3 and pip manually."
        exit 1
    fi
    echo "[INFO] Python 3 installation successful."
else
    echo "[INFO] Python 3 is already installed."
fi

# 3. Ensure pip is available
if ! command -v pip3 &> /dev/null && ! command -v pip &> /dev/null; then
    echo "[INFO] pip is missing. Attempting to install python3-pip..."
    if command -v apt-get &> /dev/null; then apt-get install -y python3-pip;
    elif command -v dnf &> /dev/null; then dnf install -y python3-pip;
    elif command -v yum &> /dev/null; then yum install -y python3-pip;
    elif command -v zypper &> /dev/null; then zypper install -y python3-pip;
    fi
fi

# 4. Navigate to the agent directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR" || exit

# 5. Background Service Installation
echo "[INFO] Checking if Agent should be installed as a background service..."
if command -v systemctl &> /dev/null; then
    python3 -c "from installer.service import install_systemd_service; install_systemd_service()"
    echo "[INFO] If the service was installed, it is enabled to start on boot."
    echo "[INFO] To start it now in the background, run: sudo systemctl start siem-agent"
fi

# 6. Run the Agent (Foreground for setup/testing if not started as service)
echo "[INFO] Launching SIEM Agent..."
echo "----------------------------------------------------"
python3 main.py
