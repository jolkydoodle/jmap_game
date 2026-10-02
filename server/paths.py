"""Resolves the web/ folder and the database location (source vs. packaged).

All file paths go through this module. Never build paths from the current
working directory.
"""
import os
import sys
from pathlib import Path

APP_NAME = "MapGame"
DB_NAME = "progress.db"


def is_frozen():
    """True when running from a PyInstaller bundle."""
    return bool(getattr(sys, "frozen", False))


def app_root():
    """Folder holding web/: the repository root, or the bundle's data folder."""
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def web_dir():
    return app_root() / "web"


def user_data_dir():
    """Per-user folder for the packaged app's data (SPEC 3.4)."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
        return Path(base) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"
    return Path(base) / APP_NAME


def db_path(override=None):
    """Database file: --db if given, else next to run.py (source) or in the user data folder (packaged)."""
    if override:
        return Path(override).expanduser().resolve()
    if is_frozen():
        return user_data_dir() / DB_NAME
    return app_root() / DB_NAME
