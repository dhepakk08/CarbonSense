"""
app.py
------
CarbonSense backend — a small Flask API that the frontend (frontend/script.js)
talks to. Implements the endpoints the client already calls:

    POST /api/login            -> create/fetch a user
    POST /api/activity         -> calculate + store one activity
    POST /api/recommendations  -> rule-based sustainability tips

...plus a few supporting endpoints useful for testing the API directly
(with curl/Postman) and for the Docker/health-check section of the
assignment report:

    GET  /api/health
    GET  /api/activities/<user_id>
    GET  /api/dashboard/<user_id>
    POST /api/goal
    GET  /api/goal/<user_id>

Run directly:      python app.py
Run in Docker:      see backend/Dockerfile
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

import database
from carbon_calculator import calculate_co2, category_totals, InvalidActivityError
from recommendation import generate_tips

app = Flask(__name__)
CORS(app)  # frontend is served from a different container/port in Docker

DEMO_USER_ID = 1


def ensure_demo_user():
    """Guarantee a fallback user exists so activities can always be linked
    to a user_id even before the frontend passes a real session id."""
    conn = database.get_db()
    try:
        row = conn.execute("SELECT id FROM users WHERE id = ?", (DEMO_USER_ID,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO users (id, name, email) VALUES (?, ?, ?)",
                (DEMO_USER_ID, "Demo User", "demo@carbonsense.local"),
            )
            conn.commit()
    finally:
        conn.close()


database.init_db()
ensure_demo_user()


# ----------------------------------------------------------------------
# Health
# ----------------------------------------------------------------------
@app.get("/")
def index():
    return jsonify({"service": "CarbonSense API", "status": "running"})


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


# ----------------------------------------------------------------------
# Auth (demo-simple: name + email, no password)
# ----------------------------------------------------------------------
@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()

    if not name or not email:
        return jsonify({"error": "name and email are required"}), 400

    conn = database.get_db()
    try:
        row = conn.execute("SELECT id, name, email FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:
            cur = conn.execute(
                "INSERT INTO users (name, email) VALUES (?, ?)", (name, email)
            )
            conn.commit()
            user = {"id": cur.lastrowid, "name": name, "email": email}
        else:
            user = {"id": row["id"], "name": row["name"], "email": row["email"]}
        return jsonify(user)
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Activities
# ----------------------------------------------------------------------
@app.post("/api/activity")
def add_activity():
    data = request.get_json(silent=True) or {}
    category = data.get("category")
    user_id = data.get("user_id", DEMO_USER_ID)
    date = data.get("date")

    try:
        co2 = calculate_co2(category, data)
    except InvalidActivityError as e:
        return jsonify({"error": str(e)}), 400

    conn = database.get_db()
    try:
        cur = conn.execute(
            """
            INSERT INTO activities
                (user_id, category, mode, distance, units, meal_type, meals,
                 waste_type, weight, co2, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                category,
                data.get("mode"),
                data.get("distance"),
                data.get("units"),
                data.get("mealType"),
                data.get("meals"),
                data.get("wasteType"),
                data.get("weight"),
                co2,
                date,
            ),
        )
        conn.commit()
        activity_id = cur.lastrowid
    finally:
        conn.close()

    response = dict(data)
    response.update({"id": activity_id, "co2": co2, "user_id": user_id})
    return jsonify(response), 201


@app.get("/api/activities/<int:user_id>")
def list_activities(user_id):
    conn = database.get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM activities WHERE user_id = ? ORDER BY date DESC, id DESC",
            (user_id,),
        ).fetchall()
        return jsonify([dict(r) for r in rows])
    finally:
        conn.close()


# ----------------------------------------------------------------------
# Dashboard summary (category totals + running total)
# ----------------------------------------------------------------------
@app.get("/api/dashboard/<int:user_id>")
def dashboard(user_id):
    conn = database.get_db()
    try:
        rows = conn.execute(
            "SELECT * FROM activities WHERE user_id = ?", (user_id,)
        ).fetchall()
        activities = [dict(r) for r in rows]
    finally:
        conn.close()

    totals = category_totals(activities)
    total_all = round(sum(totals.values()), 2)
    return jsonify({
        "user_id": user_id,
        "totals": totals,
        "total_co2": total_all,
        "activity_count": len(activities),
    })


# ----------------------------------------------------------------------
# Recommendations
# ----------------------------------------------------------------------
@app.post("/api/recommendations")
def recommendations():
    data = request.get_json(silent=True) or {}
    raw_activities = data.get("activities", [])

    # Normalise camelCase (as sent by the browser) to the snake_case
    # keys recommendation.py expects (same shape as the DB rows).
    normalised = []
    for a in raw_activities:
        normalised.append({
            "category": a.get("category"),
            "mode": a.get("mode"),
            "distance": a.get("distance"),
            "units": a.get("units"),
            "meal_type": a.get("mealType"),
            "meals": a.get("meals"),
            "waste_type": a.get("wasteType"),
            "weight": a.get("weight"),
            "co2": a.get("co2"),
        })

    tips = generate_tips(normalised)
    return jsonify(tips)


# ----------------------------------------------------------------------
# Goals
# ----------------------------------------------------------------------
@app.post("/api/goal")
def set_goal():
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", DEMO_USER_ID)
    target = data.get("target")

    try:
        target = float(target)
        if target <= 0:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"error": "target must be a positive number"}), 400

    conn = database.get_db()
    try:
        conn.execute(
            """
            INSERT INTO goals (user_id, target_kg) VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET target_kg = excluded.target_kg,
                                                updated_at = datetime('now')
            """,
            (user_id, target),
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({"user_id": user_id, "target": target})


@app.get("/api/goal/<int:user_id>")
def get_goal(user_id):
    conn = database.get_db()
    try:
        row = conn.execute(
            "SELECT target_kg FROM goals WHERE user_id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        return jsonify({"user_id": user_id, "target": None})
    return jsonify({"user_id": user_id, "target": row["target_kg"]})


# ----------------------------------------------------------------------
if __name__ == "__main__":
    # host 0.0.0.0 so the app is reachable from outside the Docker container
    app.run(host="0.0.0.0", port=5000, debug=True)
