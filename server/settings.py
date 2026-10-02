"""Settings defaults plus load/save. Values are stored as JSON in the settings table."""
import json

CARD_KINDS = ["identify", "locate", "neighbors", "capital", "flag", "silhouette"]

DEFAULTS = {
    "desired_retention": 0.90,
    "new_countries_per_day": 8,
    "mc_graduation_days": 3,
    "unlock_days": 7,
    "fast_ms": 3000,
    "slow_ms": 15000,
    "day_starts_hour": 4,
    "enabled_kinds": list(CARD_KINDS),
    "window": None,  # last app window geometry: {width, height, x, y}; not shown on the Settings screen
}


def _number(lo, hi, integer=False):
    def check(value):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("must be a number")
        if integer and value != int(value):
            raise ValueError("must be a whole number")
        if not lo <= value <= hi:
            raise ValueError(f"must be between {lo} and {hi}")
        return int(value) if integer else float(value)
    return check


def _kinds(value):
    if not isinstance(value, list) or not value:
        raise ValueError("must be a non-empty list")
    unknown = [k for k in value if k not in CARD_KINDS]
    if unknown:
        raise ValueError(f"unknown kinds: {unknown}")
    return [k for k in CARD_KINDS if k in value]


def _window(value):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("must be an object or null")
    check = _number(-100000, 100000, integer=True)
    return {k: check(value[k]) for k in ("width", "height", "x", "y") if k in value}


VALIDATORS = {
    "desired_retention": _number(0.70, 0.99),
    "new_countries_per_day": _number(0, 100, integer=True),
    "mc_graduation_days": _number(0, 365),
    "unlock_days": _number(0, 365),
    "fast_ms": _number(0, 600000, integer=True),
    "slow_ms": _number(0, 600000, integer=True),
    "day_starts_hour": _number(0, 23, integer=True),
    "enabled_kinds": _kinds,
    "window": _window,
}


def load(conn):
    """All settings: stored values over defaults. Unknown or invalid stored values are ignored."""
    result = json.loads(json.dumps(DEFAULTS))  # deep copy
    for row in conn.execute("SELECT key, value FROM settings"):
        if row["key"] in VALIDATORS:
            try:
                result[row["key"]] = VALIDATORS[row["key"]](json.loads(row["value"]))
            except ValueError:
                pass
    return result


def save(conn, updates):
    """Validates and stores some settings; returns all settings. Raises ValueError on bad input."""
    if not isinstance(updates, dict):
        raise ValueError("settings must be a JSON object")
    clean = {}
    for key, value in updates.items():
        if key not in VALIDATORS:
            raise ValueError(f"unknown setting: {key}")
        try:
            clean[key] = VALIDATORS[key](value)
        except ValueError as error:
            raise ValueError(f"{key}: {error}") from None
    merged = {**load(conn), **clean}
    if merged["fast_ms"] > merged["slow_ms"]:
        raise ValueError("fast_ms must not be greater than slow_ms")
    with conn:
        conn.executemany(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            [(k, json.dumps(v)) for k, v in clean.items()],
        )
    return load(conn)
