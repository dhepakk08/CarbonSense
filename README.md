# CarbonSense

**AI-Based Personal Carbon Footprint Tracking and Sustainability Advisor**

CarbonSense helps individuals log daily activities (travel, electricity, food, waste), automatically calculates the resulting carbon footprint, and returns personalised, rule-based sustainability tips.

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML, CSS, vanilla JavaScript |
| Backend | Python, Flask, gunicorn |
| Database | SQLite |
| Containerization | Docker, Docker Compose, nginx |

## Project Structure

```
CarbonSense/
├── frontend/          # Static site: index.html, style.css, script.js
├── backend/           # Flask API: app.py, carbon_calculator.py, recommendation.py, database.py
├── database/          # SQLite database file (database.db)
├── docker-compose.yml # Orchestrates both containers
└── README.md
```

## Running with Docker (recommended)

```bash
git clone https://github.com/dhepakk08/CarbonSense.git
cd CarbonSense
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend API: http://localhost:5000/api/health

## Running locally without Docker

**Backend:**
```bash
cd backend
pip install -r requirements.txt
python app.py
```
The API will be available at `http://localhost:5000`.

**Frontend:**
Open `frontend/index.html` directly in a browser, or serve it with any static file server:
```bash
cd frontend
python -m http.server 8080
```

## Running Tests

```bash
cd backend
pip install pytest pytest-cov
pytest test_carbonsense.py -v
```

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/login` | Create or fetch a user by email |
| POST | `/api/activity` | Log an activity and calculate its CO₂e |
| GET | `/api/activities/<user_id>` | List a user's logged activities |
| GET | `/api/dashboard/<user_id>` | Category totals and running total |
| POST | `/api/goal` | Set a monthly CO₂e target |
| GET | `/api/goal/<user_id>` | Fetch the current goal |
| POST | `/api/recommendations` | Get rule-based sustainability tips |

## License

This project was built for academic purposes as part of CSA1012 — Software Engineering.
