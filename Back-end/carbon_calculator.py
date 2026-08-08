"""
carbon_calculator.py
---------------------
Converts a logged activity into an estimated CO2e value (kilograms).

The emission factors below intentionally mirror the constants in
frontend/script.js (EMISSION_FACTORS) so that the client-side fallback
calculation and the authoritative server-side calculation agree. In a
production system these factors would instead be pulled from a live
"Carbon Emission Factor API" (see the architecture report) — here they
are static constants suitable for a course project.
"""

# kg CO2e per km
TRAVEL_FACTORS = {
    "car_petrol": 0.192,
    "car_diesel": 0.171,
    "bus": 0.105,
    "train": 0.041,
    "flight": 0.255,
    "bike": 0.0,
}

# kg CO2e per kWh (grid-average placeholder)
ELECTRICITY_FACTOR = 0.82

# kg CO2e per meal
FOOD_FACTORS = {
    "meat": 3.3,
    "dairy": 1.9,
    "veg": 1.1,
    "vegan": 0.9,
}

# kg CO2e per kg of waste
WASTE_FACTORS = {
    "landfill": 0.58,
    "recycled": 0.21,
    "composted": 0.05,
}

VALID_CATEGORIES = {"travel", "electricity", "food", "waste"}


class InvalidActivityError(ValueError):
    """Raised when an activity payload is missing fields or has bad values."""


def _to_float(value, field_name):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise InvalidActivityError(f"'{field_name}' must be a number")


def calculate_co2(category: str, fields: dict) -> float:
    """
    Calculate CO2e (kg) for a single activity.

    category: one of 'travel' | 'electricity' | 'food' | 'waste'
    fields:   dict with the category-specific inputs, e.g.
              travel      -> {"mode": "car_petrol", "distance": 12.5}
              electricity -> {"units": 8.2}
              food        -> {"mealType": "meat", "meals": 2}
              waste       -> {"wasteType": "landfill", "weight": 1.2}
    """
    if category not in VALID_CATEGORIES:
        raise InvalidActivityError(f"Unknown category '{category}'")

    if category == "travel":
        mode = fields.get("mode")
        if mode not in TRAVEL_FACTORS:
            raise InvalidActivityError(f"Unknown travel mode '{mode}'")
        distance = _to_float(fields.get("distance", 0), "distance")
        if distance < 0:
            raise InvalidActivityError("distance cannot be negative")
        co2 = TRAVEL_FACTORS[mode] * distance

    elif category == "electricity":
        units = _to_float(fields.get("units", 0), "units")
        if units < 0:
            raise InvalidActivityError("units cannot be negative")
        co2 = ELECTRICITY_FACTOR * units

    elif category == "food":
        meal_type = fields.get("mealType")
        if meal_type not in FOOD_FACTORS:
            raise InvalidActivityError(f"Unknown meal type '{meal_type}'")
        meals = _to_float(fields.get("meals", 0), "meals")
        if meals < 0:
            raise InvalidActivityError("meals cannot be negative")
        co2 = FOOD_FACTORS[meal_type] * meals

    else:  # waste
        waste_type = fields.get("wasteType")
        if waste_type not in WASTE_FACTORS:
            raise InvalidActivityError(f"Unknown waste type '{waste_type}'")
        weight = _to_float(fields.get("weight", 0), "weight")
        if weight < 0:
            raise InvalidActivityError("weight cannot be negative")
        co2 = WASTE_FACTORS[waste_type] * weight

    return round(co2, 2)


def category_totals(activities) -> dict:
    """
    activities: iterable of dict-like rows with 'category' and 'co2' keys.
    Returns {"travel": x, "electricity": x, "food": x, "waste": x}
    """
    totals = {"travel": 0.0, "electricity": 0.0, "food": 0.0, "waste": 0.0}
    for a in activities:
        cat = a["category"] if isinstance(a, dict) else a["category"]
        if cat in totals:
            totals[cat] += a["co2"] or 0.0
    return {k: round(v, 2) for k, v in totals.items()}
