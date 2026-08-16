"""
test_carbonsense.py
-------------------
Automated test suite for the CarbonSense backend, covering:
  1. Unit tests for carbon_calculator.py (emission math + validation)
  2. Unit tests for recommendation.py (rule-based tip generation)
  3. Integration tests for app.py (Flask API endpoints, via test client)

Run with: pytest test_carbonsense.py -v
"""

import pytest

import carbon_calculator as cc
import recommendation as rec


# 1. carbon_calculator.py — unit tests
class TestCarbonCalculator:

    def test_travel_car_petrol(self):
        assert cc.calculate_co2(
            "travel",
            {"mode": "car_petrol", "distance": 25}
        ) == 4.8

    def test_travel_bike_is_zero(self):
        assert cc.calculate_co2(
            "travel",
            {"mode": "bike", "distance": 100}
        ) == 0.0

    def test_electricity(self):
        assert cc.calculate_co2(
            "electricity",
            {"units": 20}
        ) == 16.4

    def test_food_meat(self):
        assert cc.calculate_co2(
            "food",
            {"mealType": "meat", "meals": 3}
        ) == 9.9

    def test_waste_composted(self):
        assert cc.calculate_co2(
            "waste",
            {"wasteType": "composted", "weight": 2}
        ) == 0.1

    def test_invalid_category_raises(self):
        with pytest.raises(cc.InvalidActivityError):
            cc.calculate_co2("spaceflight", {"distance": 10})

    def test_invalid_travel_mode_raises(self):
        with pytest.raises(cc.InvalidActivityError):
            cc.calculate_co2(
                "travel",
                {"mode": "teleporter", "distance": 10}
            )

    def test_negative_distance_raises(self):
        with pytest.raises(cc.InvalidActivityError):
            cc.calculate_co2(
                "travel",
                {"mode": "car_petrol", "distance": -5}
            )

    def test_non_numeric_distance_raises(self):
        with pytest.raises(cc.InvalidActivityError):
            cc.calculate_co2(
                "travel",
                {"mode": "car_petrol", "distance": "abc"}
            )

    def test_category_totals(self):
        activities = [
            {"category": "travel", "co2": 4.8},
            {"category": "travel", "co2": 1.0},
            {"category": "food", "co2": 9.9},
        ]

        totals = cc.category_totals(activities)

        assert totals["travel"] == 5.8
        assert totals["food"] == 9.9
        assert totals["electricity"] == 0.0


# 2. recommendation.py — unit tests
class TestRecommendation:

    def test_empty_activities_returns_default_tip(self):
        tips = rec.generate_tips([])

        assert len(tips) == 1
        assert "Keep logging" in tips[0]

    def test_high_car_km_triggers_carpool_tip(self):
        activities = [
            {
                "category": "travel",
                "mode": "car_petrol",
                "distance": 30,
                "co2": 5.76,
            }
        ]

        tips = rec.generate_tips(activities)

        assert any("carpooling" in tip for tip in tips)

    def test_meat_heavy_diet_triggers_plant_based_tip(self):
        activities = [
            {
                "category": "food",
                "meal_type": "meat",
                "co2": 3.3,
            },
            {
                "category": "food",
                "meal_type": "meat",
                "co2": 3.3,
            },
            {
                "category": "food",
                "meal_type": "meat",
                "co2": 3.3,
            },
        ]

        tips = rec.generate_tips(activities)

        assert any("plant-based" in tip for tip in tips)

    def test_low_activity_does_not_overtrigger(self):
        activities = [
            {
                "category": "travel",
                "mode": "bike",
                "distance": 2,
                "co2": 0.0,
            }
        ]

        tips = rec.generate_tips(activities)

        assert len(tips) >= 1

    def test_returns_at_most_four_tips(self):
        activities = [
            {
                "category": "travel",
                "mode": "car_petrol",
                "distance": 50,
                "co2": 9.6,
            },
            {
                "category": "electricity",
                "co2": 20,
            },
            {
                "category": "food",
                "meal_type": "meat",
                "co2": 3.3,
            },
            {
                "category": "food",
                "meal_type": "meat",
                "co2": 3.3,
            },
            {
                "category": "food",
                "meal_type": "meat",
                "co2": 3.3,
            },
            {
                "category": "waste",
                "waste_type": "landfill",
                "co2": 6,
            },
        ]

        tips = rec.generate_tips(activities)

        assert len(tips) <= 4


# 3. app.py — integration tests via Flask test client
@pytest.fixture
def client(tmp_path, monkeypatch):
    """Run the Flask app against a temporary disposable SQLite database."""
    import database

    test_db_dir = tmp_path / "database"
    test_db_dir.mkdir()

    monkeypatch.setattr(database, "DB_DIR", str(test_db_dir))
    monkeypatch.setattr(
        database,
        "DB_PATH",
        str(test_db_dir / "database.db"),
    )

    import app as flask_app_module

    flask_app_module.database = database
    flask_app_module.database.init_db()
    flask_app_module.ensure_demo_user()

    flask_app_module.app.config["TESTING"] = True

    with flask_app_module.app.test_client() as test_client:
        yield test_client


class TestAPI:

    def test_health(self, client):
        response = client.get("/api/health")

        assert response.status_code == 200
        assert response.get_json()["status"] == "ok"

    def test_login_creates_user(self, client):
        response = client.post(
            "/api/login",
            json={
                "name": "Aditi Rao",
                "email": "aditi@example.com",
            },
        )

        assert response.status_code == 200

        body = response.get_json()

        assert body["name"] == "Aditi Rao"
        assert "id" in body

    def test_login_is_idempotent_by_email(self, client):
        response_one = client.post(
            "/api/login",
            json={
                "name": "Aditi Rao",
                "email": "aditi@example.com",
            },
        )

        response_two = client.post(
            "/api/login",
            json={
                "name": "Aditi Rao",
                "email": "aditi@example.com",
            },
        )

        assert response_one.get_json()["id"] == response_two.get_json()["id"]

    def test_login_missing_fields_returns_400(self, client):
        response = client.post(
            "/api/login",
            json={"name": ""},
        )

        assert response.status_code == 400

    def test_add_activity_valid(self, client):
        response = client.post(
            "/api/activity",
            json={
                "user_id": 1,
                "category": "travel",
                "mode": "car_petrol",
                "distance": 25,
                "date": "2026-08-01",
            },
        )

        assert response.status_code == 201
        assert response.get_json()["co2"] == 4.8

    def test_add_activity_invalid_returns_400(self, client):
        response = client.post(
            "/api/activity",
            json={
                "user_id": 1,
                "category": "travel",
                "mode": "teleporter",
                "distance": 10,
            },
        )

        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_dashboard_totals(self, client):
        client.post(
            "/api/activity",
            json={
                "user_id": 1,
                "category": "electricity",
                "units": 20,
                "date": "2026-08-01",
            },
        )

        client.post(
            "/api/activity",
            json={
                "user_id": 1,
                "category": "food",
                "mealType": "meat",
                "meals": 3,
                "date": "2026-08-02",
            },
        )

        response = client.get("/api/dashboard/1")
        data = response.get_json()

        assert data["totals"]["electricity"] == 16.4
        assert data["totals"]["food"] == 9.9
        assert data["total_co2"] == pytest.approx(26.3, 0.01)

    def test_goal_set_and_get(self, client):
        client.post(
            "/api/goal",
            json={
                "user_id": 1,
                "target": 100,
            },
        )

        response = client.get("/api/goal/1")

        assert response.get_json()["target"] == 100.0

    def test_goal_rejects_non_positive(self, client):
        response = client.post(
            "/api/goal",
            json={
                "user_id": 1,
                "target": -5,
            },
        )

        assert response.status_code == 400

    def test_recommendations_endpoint(self, client):
        response = client.post(
            "/api/recommendations",
            json={
                "activities": [
                    {
                        "category": "travel",
                        "mode": "car_petrol",
                        "distance": 30,
                        "co2": 5.76,
                    }
                ]
            },
        )

        assert response.status_code == 200

        tips = response.get_json()

        assert isinstance(tips, list)
        assert len(tips) >= 1