import json

import pytest

from server import settings


def test_defaults(conn):
    s = settings.load(conn)
    assert s["desired_retention"] == 0.90
    assert s["new_countries_per_day"] == 8
    assert s["mc_graduation_days"] == 3
    assert s["unlock_days"] == 7
    assert (s["fast_ms"], s["slow_ms"]) == (3000, 15000)
    assert s["day_starts_hour"] == 4
    assert s["enabled_kinds"] == settings.CARD_KINDS


def test_save_and_reload(conn, db_path):
    settings.save(conn, {"new_countries_per_day": 12, "enabled_kinds": ["locate", "identify"]})
    from server import db
    other = db.connect(db_path)
    s = settings.load(other)
    other.close()
    assert s["new_countries_per_day"] == 12
    assert s["enabled_kinds"] == ["identify", "locate"]  # canonical order
    assert s["unlock_days"] == 7  # untouched


@pytest.mark.parametrize("updates", [
    {"nope": 1},
    {"desired_retention": 1.5},
    {"desired_retention": "0.9"},
    {"new_countries_per_day": 2.5},
    {"new_countries_per_day": True},
    {"day_starts_hour": 24},
    {"enabled_kinds": []},
    {"enabled_kinds": ["identify", "dance"]},
    {"fast_ms": 20000},  # above slow_ms
    [1, 2],
])
def test_rejects_bad_input(conn, updates):
    with pytest.raises(ValueError):
        settings.save(conn, updates)
    assert settings.load(conn) == settings.DEFAULTS  # nothing partially saved


def test_ignores_corrupt_stored_values(conn):
    conn.execute("INSERT INTO settings VALUES ('unlock_days', ?)", (json.dumps(-5),))
    conn.execute("INSERT INTO settings VALUES ('old_key', '1')")
    conn.commit()
    assert settings.load(conn) == settings.DEFAULTS


def test_window_geometry(conn):
    s = settings.save(conn, {"window": {"width": 1000, "height": 700, "x": 10, "y": -5}})
    assert s["window"] == {"width": 1000, "height": 700, "x": 10, "y": -5}
