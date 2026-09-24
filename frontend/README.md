# ThreatHunter SIEM - Frontend

The modern, high-performance web interface for the ThreatHunter SIEM. Built with React, Vite, Tailwind CSS, and Framer Motion.

## Prerequisites

- Node.js (v16 or newer)
- npm

## Installation

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```

## Development

Start the development server with Hot Module Replacement (HMR):

```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

## Building for Production

To create an optimized production build:

```bash
npm run build
```

This will generate a `dist` folder. You can copy the contents of this folder directly to your SIEM server (which is configured to serve these static files via FastAPI).

## Features

- **Real-Time Websocket Feed**: Alerts prepend to the grid instantly as they happen.
- **Enterprise UI**: Dark theme (slate colors), Lucide icons, and grid-dense layouts.
- **AI Agent Integration**: Conversational assistant embedded in alert detail panels.
- **Export to PDF**: Generate structured, signed incident reports with AI context.
