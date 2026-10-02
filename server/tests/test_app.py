import socket

from server import __version__, app


def test_health(client):
    assert client.json("GET", "/api/health") == (200, {"ok": True, "version": __version__})


def test_binds_localhost_only(server):
    assert server.server_address[0] == "127.0.0.1"


def test_static_files(client):
    status, headers, body = client.request("GET", "/")
    assert status == 200 and b"<svg id=\"map\"" in body
    status, headers, _ = client.request("GET", "/js/main.js")
    assert status == 200 and headers["Content-Type"].startswith("text/javascript")
    status, headers, _ = client.request("GET", "/flags/de.svg")
    assert status == 200 and headers["Content-Type"] == "image/svg+xml"


def test_no_directory_listing_or_escape(client):
    assert client.request("GET", "/flags/")[0] == 404
    assert client.request("GET", "/../run.py")[0] == 404
    assert client.request("GET", "/%2e%2e/run.py")[0] == 404


def test_settings_api(client):
    status, s = client.json("GET", "/api/settings")
    assert status == 200 and s["unlock_days"] == 7
    status, s = client.json("POST", "/api/settings", {"unlock_days": 10})
    assert status == 200 and s["unlock_days"] == 10
    assert client.json("GET", "/api/settings")[1]["unlock_days"] == 10


def test_api_errors(client):
    status, body = client.json("POST", "/api/settings", {"unlock_days": "lots"})
    assert status == 400 and "unlock_days" in body["error"]
    status, body = client.json("POST", "/api/settings", raw=b"{not json")
    assert status == 400 and "JSON" in body["error"]
    assert client.json("GET", "/api/nope")[0] == 404
    assert client.json("POST", "/api/health")[0] == 405


def test_rejects_foreign_host_header(client):
    status, _ = client.json("GET", "/api/health", headers={"Host": "evil.example:80"})
    assert status == 403


def test_next_port_when_busy(db_path):
    blocker = socket.socket()
    blocker.bind(("127.0.0.1", 0))
    blocker.listen()
    busy = blocker.getsockname()[1]
    try:
        srv = app.make_server(db_path, port=busy, tries=5, quiet=True)
        assert srv.server_address[1] != busy
        srv.server_close()
    finally:
        blocker.close()


def test_second_instance_gets_its_own_port(server, db_path):
    second = app.make_server(db_path, port=server.server_address[1], tries=5, quiet=True)
    try:
        assert second.server_address[1] != server.server_address[1]
    finally:
        second.server_close()
