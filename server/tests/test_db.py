from server import db

TABLES = {"cards", "reviews", "attempts", "mixups", "sweeps", "settings", "meta"}


def tables(conn):
    return {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}


def test_init_creates_schema(tmp_path):
    path = tmp_path / "sub" / "progress.db"  # folder is created too
    assert db.init_db(path) == len(db.MIGRATIONS)
    conn = db.connect(path)
    assert TABLES <= tables(conn)
    assert db.schema_version(conn) == 1
    assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    conn.close()


def test_init_is_idempotent(db_path):
    assert db.init_db(db_path) == 1
    assert db.init_db(db_path) == 1


def test_later_migrations_apply_in_order(conn):
    extra = db.MIGRATIONS + ["CREATE TABLE extra_a (x);", "CREATE TABLE extra_b (y);"]
    assert db.migrate(conn, extra) == 3
    assert {"extra_a", "extra_b"} <= tables(conn)
    assert db.migrate(conn, extra) == 3  # nothing re-applied


def test_failed_migration_rolls_back(conn):
    broken = db.MIGRATIONS + ["CREATE TABLE half_done (x); THIS IS NOT SQL;"]
    try:
        db.migrate(conn, broken)
    except Exception:
        conn.rollback()
    assert db.schema_version(conn) == 1
    assert "half_done" not in tables(conn)
