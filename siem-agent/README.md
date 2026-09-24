# ThreatHunter SIEM - Agent

The endpoint agent responsible for collecting telemetry, logs, and system events, and forwarding them securely to the ThreatHunter SIEM Server.

## Prerequisites

- Python 3.8+

## Installation

1. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configuration:
   Edit the configuration file (e.g. `config.yaml` or `.env` depending on setup) to point the agent to your SIEM server's address.
   ```
   SERVER_URL=http://<SIEM_SERVER_IP>:8443
   ```

## Running the Agent

Start the agent service:

```bash
python agent.py
```

The agent will register with the server and begin transmitting logs. Check the server dashboard to approve or monitor the new agent.
