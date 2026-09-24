#!/bin/bash
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$DIR"

if [ ! -d "venv" ]; then
    echo "[ERROR] Python virtual environment (venv) not found. Please run ./start_server.sh first."
    exit 1
fi

source venv/bin/activate
python3 siem_admin.py "$@"
