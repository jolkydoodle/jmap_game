import sys
from pathlib import Path

from server import paths

ROOT = Path(__file__).resolve().parents[2]


def test_source_mode_paths():
    assert not paths.is_frozen()
    assert paths.web_dir() == ROOT / "web"
    assert (paths.web_dir() / "index.html").is_file()
    assert paths.db_path() == ROOT / "progress.db"


def test_db_override(tmp_path):
    assert paths.db_path(str(tmp_path / "x.db")) == (tmp_path / "x.db").resolve()


def test_frozen_mode_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    assert paths.web_dir() == tmp_path / "bundle" / "web"
    assert paths.db_path() == tmp_path / "roaming" / "MapGame" / "progress.db"


def test_frozen_mode_macos(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    assert paths.db_path() == tmp_path / "home" / "Library" / "Application Support" / "MapGame" / "progress.db"
