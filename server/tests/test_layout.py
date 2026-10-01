"""Milestone 0: the project layout is in place and the backend stubs import."""
import importlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_backend_modules_import():
    for name in ("app", "db", "scheduling", "settings", "paths", "desktop"):
        importlib.import_module(f"server.{name}")


def test_web_files_present():
    web = ROOT / "web"
    for rel in ("index.html", "css/style.css", "js/main.js", "data/countries.js",
                "data/world.js", "vendor/d3.min.js", "vendor/topojson-client.min.js"):
        assert (web / rel).is_file(), rel
    assert len(list((web / "flags").glob("*.svg"))) == 196


def test_no_remote_urls_in_page():
    # The app must make zero network requests at runtime.
    for rel in ("index.html", "css/style.css"):
        text = (ROOT / "web" / rel).read_text(encoding="utf-8")
        assert "http://" not in text and "https://" not in text, rel
