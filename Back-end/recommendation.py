"""
recommendation.py
-------------------
Rule-based "AI Recommendation Engine" for CarbonSense.

This plays the role of the AI Recommendation microservice described in
the architecture report. For a course project it uses simple, explainable
rules over the user's logged activities rather than a trained ML model —
the interface (generate_tips) is written so a real model could be dropped
in later (e.g. train_model.py / model.pkl) without changing app.py.

Expects a list of activity dicts using the same snake_case field names
as the `activities` DB table: category, mode, distance, units,
meal_type, meals, waste_type, weight, co2.
"""

from carbon_calculator import category_totals

TRAVEL_THRESHOLD_KG = 30
ELECTRICITY_THRESHOLD_KG = 15
WASTE_THRESHOLD_KG = 5
CAR_KM_THRESHOLD = 20
MEAT_MEAL_THRESHOLD = 3

DEFAULT_TIP = (
    "Keep logging activities — personalised suggestions get sharper "
    "the more data CarbonSense has to work with."
)


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def generate_tips(activities: list) -> list:
    """Return up to 4 short, actionable sustainability tips."""
    if not activities:
        return [DEFAULT_TIP]

    totals = category_totals(activities)
    tips = []

    if totals["travel"] > TRAVEL_THRESHOLD_KG:
        tips.append(
            "Your travel emissions are your biggest contributor — swapping one "
            "petrol-car trip a week for a bus or train could save several kg of "
            "CO\u2082e a month."
        )

    car_km = sum(
        _num(a.get("distance"))
        for a in activities
        if a.get("category") == "travel" and a.get("mode") in ("car_petrol", "car_diesel")
    )
    if car_km >= CAR_KM_THRESHOLD:
        saving = round(car_km * 0.19 * 0.4, 1)
        tips.append(
            f"You've logged {car_km:.0f} km by car recently — carpooling twice "
            f"this week would cut roughly {saving} kg CO\u2082e."
        )

    if totals["electricity"] > ELECTRICITY_THRESHOLD_KG:
        tips.append(
            "Electricity use is trending high — switching a few devices to "
            "power-saving mode during peak hours can meaningfully lower this "
            "category."
        )

    meat_meals = sum(
        1 for a in activities
        if a.get("category") == "food" and a.get("meal_type") == "meat"
    )
    if meat_meals >= MEAT_MEAL_THRESHOLD:
        tips.append(
            "You've logged several meat-based meals — one extra plant-based "
            "meal a week is one of the highest-impact small changes you can "
            "make."
        )

    if totals["waste"] > WASTE_THRESHOLD_KG:
        tips.append(
            "A good share of your waste is going to landfill — sorting out "
            "recyclables and compostables could cut this category's "
            "footprint by half."
        )

    if not tips:
        tips.append(DEFAULT_TIP)

    return tips[:4]
