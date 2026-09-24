# ThreatHunter SIEM - Server

The backend component of the ThreatHunter SIEM platform, powered by FastAPI.

## Prerequisites

- Python 3.10+
- pip

## Installation

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```
2. Activate the virtual environment:
   - Windows: `.venv\Scripts\activate`
   - Linux/Mac: `source .venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Database Setup:
   The application uses Alembic for migrations and SQLite by default. Run migrations to initialize the database schema:
   ```bash
   alembic upgrade head
   ```

## Running the Server

Start the FastAPI server using Uvicorn:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8443 --reload
```

The server will be available at `http://localhost:8443`.
The interactive API documentation (Swagger) will be available at `http://localhost:8443/docs`.

## Environment Variables

Check `.env` (or create one) to configure settings like `SECRET_KEY`, `DATABASE_URL`, and AI API keys.
