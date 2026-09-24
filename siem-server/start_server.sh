#!/bin/bash

# ==============================================================================
# SIEM Server Bootstrapper & Launcher
# ==============================================================================

echo "[INFO] Starting SIEM Server Initialization..."

# Navigate to the server directory
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR" || exit

if [ ! -f "main.py" ]; then
    echo "[ERROR] main.py not found in $DIR. Make sure this script is inside the siem-server folder."
    exit 1
fi

echo "[INFO] Setting up Python Virtual Environment..."
if ! command -v python3-venv &> /dev/null && ! python3 -m venv --help &> /dev/null; then
    echo "[WARNING] python3-venv might be missing. Attempting to install it..."
    if command -v apt-get &> /dev/null; then apt-get install -y python3-venv; fi
fi

if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

source venv/bin/activate

echo "[INFO] Installing Python dependencies..."
pip3 install -r requirements.txt --quiet

echo "[INFO] Launching SIEM Server..."
echo "----------------------------------------------------"
python3 main.py
