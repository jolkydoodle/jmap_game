"""SQLite schema, migrations and queries."""
import sqlite3

# One entry per schema version. Never edit a released migration; append a new one.
MIGRATIONS = [
    # 1: initial schema (SPEC 8.1)
    """
    CREATE TABLE cards (
      id            INTEGER PRIMARY KEY,
      country       TEXT NOT NULL,
      kind          TEXT NOT NULL,
      fsrs          TEXT NOT NULL,
      due           TEXT NOT NULL,
      stability     REAL,
      state         INTEGER,
      introduced_at TEXT NOT NULL,
      UNIQUE(country, kind)
    );
    CREATE INDEX idx_cards_due ON cards(due);

    CREATE TABLE reviews (
      id          INTEGER PRIMARY KEY,
      card_id     INTEGER NOT NULL REFERENCES cards(id),
      ts          TEXT NOT NULL,
      rating      INTEGER NOT NULL,
      outcome     TEXT NOT NULL,
      review_log  TEXT NOT NULL
    );

    CREATE TABLE attempts (
      id       INTEGER PRIMARY KEY,
      ts       TEXT NOT NULL,
      mode     TEXT NOT NULL,
      country  TEXT NOT NULL,
      correct  INTEGER NOT NULL,
      detail   TEXT
    );

    CREATE TABLE mixups (
      target   TEXT NOT NULL,
      given    TEXT NOT NULL,
      count    INTEGER NOT NULL DEFAULT 1,
      last_ts  TEXT NOT NULL,
      PRIMARY KEY (target, given)
    );

    CREATE TABLE sweeps (
      id        INTEGER PRIMARY KEY,
      ts        TEXT NOT NULL,
      region    TEXT NOT NULL,
      seconds   REAL NOT NULL,
      mistakes  INTEGER NOT NULL
    );

    CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    """,
]


def connect(path):
    """Opens a connection. Use one per request and close it afterwards."""
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def schema_version(conn):
    row = conn.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()
    return int(row["value"]) if row else 0


def migrate(conn, migrations=MIGRATIONS):
    """Applies every migration newer than the stored schema_version, each in its own transaction."""
    conn.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.commit()
    current = schema_version(conn)
    for version, sql in enumerate(migrations, start=1):
        if version <= current:
            continue
        conn.executescript(
            "BEGIN;\n" + sql + "\n"
            f"INSERT OR REPLACE INTO meta (key, value) VALUES ('schema_version', '{version}');\n"
            "COMMIT;"
        )
    return schema_version(conn)


def init_db(path):
    """Creates the database file and its folder if needed, and brings the schema up to date."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(path)
    try:
        return migrate(conn)
    finally:
        conn.close()
