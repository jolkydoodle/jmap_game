"""Map Game entry point: starts the local server, then opens the app window (or a browser)."""
import argparse
import json
import sys
import time
import urllib.request
import webbrowser

from server import app, db, paths


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Map Game: learn the countries of the world.")
    parser.add_argument("--browser", action="store_true",
                        help="open in the default web browser instead of the app window (development)")
    parser.add_argument("--debug", action="store_true", help="enable the web inspector in the app window")
    parser.add_argument("--db", metavar="PATH", help="use this progress database file")
    return parser.parse_args(argv)


def wait_for_health(url, timeout=10.0):
    """Polls /api/health until it answers, so the user never sees a connection error page."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # never route localhost via a proxy
    deadline = time.monotonic() + timeout
    while True:
        try:
            with opener.open(url + "api/health", timeout=1) as response:
                if json.load(response).get("ok"):
                    return
        except OSError:
            pass
        if time.monotonic() > deadline:
            raise RuntimeError(f"server at {url} did not respond within {timeout:.0f} s")
        time.sleep(0.05)


def main(argv=None):
    args = parse_args(argv)
    db_path = paths.db_path(args.db)
    db.init_db(db_path)

    server = app.make_server(db_path, quiet=not (args.browser or args.debug))
    app.start_in_thread(server)
    url = app.url_of(server)
    wait_for_health(url)
    print(f"Map Game running at {url}  (progress: {db_path})", flush=True)

    if args.browser:
        webbrowser.open(url)
        print("Press Ctrl+C to stop.", flush=True)
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("Stopping.")
    else:
        from server import desktop  # imported here so --browser works without pywebview installed
        desktop.open_window(url, db_path, debug=args.debug)

    server.shutdown()
    server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
