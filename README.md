# AI Civic Services

A simple Flask-based civic complaint management app with AI-assisted classification and priority prediction.

## Features
- Submit civic complaints
- AI-based category classification
- AI-inspired priority prediction
- Admin view to update status/priority
- SQLite persistence

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the app:
   ```bash
   python app.py
   ```
4. Open http://localhost:5000

## Production Features
- Multi-language and voice-friendly complaint intake design
- Duplicate detection and SLA scoring
- PDF report export for executives
- Docker support via Dockerfile and docker-compose.yml

## Deploy with Docker
```bash
docker compose up --build
```
