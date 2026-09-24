# ThreatHunter SIEM

A modern, fast, and lightweight Security Information and Event Management (SIEM) system built with React, FastAPI, and Python.

## Project Structure

This repository is split into three main components:

1. **[siem-server](./siem-server)**: The backend API, database, and WebSocket server (FastAPI, SQLite/PostgreSQL).
2. **[frontend](./frontend)**: The modern UI/Dashboard for monitoring alerts and managing the system (React, Vite, Tailwind CSS).
3. **[siem-agent](./siem-agent)**: The endpoint agent that collects logs/telemetry and ships them to the server (Python).

## Getting Started

Please see the README files inside each specific folder for setup and installation instructions:

- [Server Setup Guide](./siem-server/README.md)
- [Frontend Setup Guide](./frontend/README.md)
- [Agent Setup Guide](./siem-agent/README.md)

## Features

- **Real-Time Telemetry**: WebSockets stream live alerts instantly to the dashboard.
- **AI-Powered Threat Analysis**: Built-in AI module acts as a Tier-3 SOC analyst to evaluate and explain alerts.
- **PDF Incident Reports**: Instantly export professional incident reports for compliance and sharing.
- **Enterprise UI**: Dark mode, data-dense grids, and seamless navigation.
- **Agent Management**: Monitor and manage connected sensor agents across your network.

## License

This project is licensed under the MIT License.
