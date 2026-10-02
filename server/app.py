"""HTTP handler: static files from web/ plus the /api routes."""
import json
import socket
import sys
import threading
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from . import __version__, db, paths, settings

HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PORT_TRIES = 10
MAX_BODY = 10 * 1024 * 1024


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


class Handler(SimpleHTTPRequestHandler):
    # Explicit types: on Windows the registry can map .js to text/plain, which breaks ES modules.
    extensions_map = {
        "": "application/octet-stream",
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".mjs": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".ico": "image/x-icon",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(paths.web_dir()), **kwargs)

    # Routing

    def do_GET(self):
        if self._is_api():
            self._api("GET")
        elif self._host_ok():
            super().do_GET()

    def do_HEAD(self):
        if self._is_api():
            self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"})
        elif self._host_ok():
            super().do_HEAD()

    def do_POST(self):
        if self._is_api():
            self._api("POST")
        else:
            self._send_json(HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method not allowed"})

    def _is_api(self):
        path = urlsplit(self.path).path
        return path == "/api" or path.startswith("/api/")

    def _api(self, method):
        if not self._host_ok():
            return
        path = urlsplit(self.path).path
        route = ROUTES.get((method, path))
        try:
            if route is None:
                known = any(p == path for _, p in ROUTES)
                if known:
                    raise ApiError(HTTPStatus.METHOD_NOT_ALLOWED, "method not allowed")
                raise ApiError(HTTPStatus.NOT_FOUND, f"no such endpoint: {path}")
            conn = db.connect(self.server.db_path)
            try:
                result = route(self, conn)
            finally:
                conn.close()
            self._send_json(HTTPStatus.OK, result)
        except ApiError as error:
            self._send_json(error.status, {"error": error.message})
        except Exception as error:  # keep the server alive; report the problem
            self.log_error("API error on %s %s: %r", method, path, error)
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal error"})

    # Helpers

    def _host_ok(self):
        """Rejects requests whose Host isn't this server (guards against DNS rebinding)."""
        host = (self.headers.get("Host") or "").lower()
        port = self.server.server_address[1]
        if host in (f"127.0.0.1:{port}", f"localhost:{port}"):
            return True
        self._send_json(HTTPStatus.FORBIDDEN, {"error": "bad host"})
        return False

    def read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise ApiError(HTTPStatus.BAD_REQUEST, "bad Content-Length") from None
        if length > MAX_BODY:
            raise ApiError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "request body too large")
        try:
            return json.loads(self.rfile.read(length) or b"null")
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ApiError(HTTPStatus.BAD_REQUEST, "body must be valid JSON") from None

    def _send_json(self, status, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        # Always serve fresh files, so edits show up without clearing the web view's cache.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(HTTPStatus.NOT_FOUND)
        return None

    def log_message(self, format, *args):
        if not self.server.quiet:
            super().log_message(format, *args)


# API routes: (method, path) -> function(handler, conn) returning JSON-able data.

def get_health(handler, conn):
    return {"ok": True, "version": __version__}


def get_settings(handler, conn):
    return settings.load(conn)


def post_settings(handler, conn):
    try:
        return settings.save(conn, handler.read_json())
    except ValueError as error:
        raise ApiError(HTTPStatus.BAD_REQUEST, str(error)) from None


ROUTES = {
    ("GET", "/api/health"): get_health,
    ("GET", "/api/settings"): get_settings,
    ("POST", "/api/settings"): post_settings,
}


class Server(ThreadingHTTPServer):
    daemon_threads = True
    # On Windows SO_REUSEADDR lets a second server bind a port already in use,
    # which would defeat the "try the next port" fallback. Claim it exclusively instead.
    allow_reuse_address = sys.platform != "win32"

    def __init__(self, address, db_path, quiet=False):
        self.db_path = db_path
        self.quiet = quiet
        super().__init__(address, Handler)

    def server_bind(self):
        if sys.platform == "win32":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def make_server(db_path, port=DEFAULT_PORT, tries=PORT_TRIES, quiet=False):
    """Binds to 127.0.0.1 on `port`, or the next free port among the following `tries - 1`."""
    last_error = None
    for candidate in range(port, port + tries):
        try:
            return Server((HOST, candidate), db_path, quiet=quiet)
        except OSError as error:
            last_error = error
    raise OSError(f"no free port in {port}-{port + tries - 1}: {last_error}")


def start_in_thread(server):
    """Serves in a daemon thread, so the process ends when the app window closes."""
    thread = threading.Thread(target=server.serve_forever, name="map-game-server", daemon=True)
    thread.start()
    return thread


def url_of(server):
    host, port = server.server_address[:2]
    return f"http://{host}:{port}/"
