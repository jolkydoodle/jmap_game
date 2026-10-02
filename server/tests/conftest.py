import json
import urllib.error
import urllib.request

import pytest

from server import app, db

_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "progress.db"
    db.init_db(path)
    return path


@pytest.fixture
def conn(db_path):
    connection = db.connect(db_path)
    yield connection
    connection.close()


class Client:
    def __init__(self, base):
        self.base = base

    def request(self, method, path, body=None, raw=None, headers=None):
        data = raw if raw is not None else (None if body is None else json.dumps(body).encode())
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers or {})
        try:
            with _opener.open(req, timeout=5) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers, error.read()

    def json(self, method, path, body=None, **kwargs):
        status, _, content = self.request(method, path, body, **kwargs)
        return status, json.loads(content)


@pytest.fixture
def server(db_path):
    srv = app.make_server(db_path, port=18765, tries=50, quiet=True)
    app.start_in_thread(srv)
    yield srv
    srv.shutdown()
    srv.server_close()


@pytest.fixture
def client(server):
    return Client(app.url_of(server).rstrip("/"))
