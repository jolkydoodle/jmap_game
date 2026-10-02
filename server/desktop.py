"""pywebview app window. Native file dialogs (js_api) arrive in Milestone 8."""
import webview

from . import db, settings

TITLE = "Map Game"
DEFAULT_SIZE = (1280, 800)
MIN_SIZE = (900, 600)


def _saved_geometry(db_path):
    conn = db.connect(db_path)
    try:
        return settings.load(conn)["window"] or {}
    finally:
        conn.close()


def _save_geometry(db_path, window):
    try:
        geometry = {"width": window.width, "height": window.height, "x": window.x, "y": window.y}
        if min(geometry["x"], geometry["y"]) <= -10000:
            return  # minimized (Windows parks it at -32000); keep the last real position
        conn = db.connect(db_path)
        try:
            settings.save(conn, {"window": geometry})
        finally:
            conn.close()
    except Exception:
        pass  # remembering the window is a nicety; never block closing


def open_window(url, db_path, debug=False):
    """Opens the app window and blocks until it is closed."""
    geometry = _saved_geometry(db_path)
    width = max(geometry.get("width", DEFAULT_SIZE[0]), MIN_SIZE[0])
    height = max(geometry.get("height", DEFAULT_SIZE[1]), MIN_SIZE[1])
    window = webview.create_window(
        TITLE, url,
        width=width, height=height,
        x=geometry.get("x"), y=geometry.get("y"),
        min_size=MIN_SIZE, resizable=True,
    )
    window.events.closing += lambda: _save_geometry(db_path, window)
    webview.start(debug=debug)
