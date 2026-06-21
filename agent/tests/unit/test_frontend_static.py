import anyio

import app as app_module
from app import create_app


async def request_app(app, path: str, root_path: str = "", accept: str = "text/html"):
    messages = []
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": root_path,
        "headers": [(b"host", b"testserver"), (b"accept", accept.encode())],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)

    start = next(message for message in messages if message["type"] == "http.response.start")
    body = b"".join(
        message.get("body", b"")
        for message in messages
        if message["type"] == "http.response.body"
    )
    headers = {
        key.decode().lower(): value.decode()
        for key, value in start.get("headers", [])
    }
    return start["status"], headers, body


async def websocket_app(app, path: str, root_path: str = ""):
    messages = []
    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": root_path,
        "headers": [(b"host", b"testserver")],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "subprotocols": [],
    }

    async def receive():
        return {"type": "websocket.connect"}

    async def send(message):
        messages.append(message)

    await app(scope, receive, send)
    return messages


def create_frontend_app(
    monkeypatch,
    tmp_path,
    index_html: str,
    url_prefix: str = "",
    root_path: str = "",
):
    frontend_dir = tmp_path / "ui"
    frontend_dir.mkdir(exist_ok=True)
    (frontend_dir / "index.html").write_text(index_html, encoding="utf-8")

    monkeypatch.setenv("FRONTEND_DIST_DIR", str(frontend_dir))
    if url_prefix:
        monkeypatch.setenv("NUXT_PUBLIC_URL_PREFIX", url_prefix)
    else:
        monkeypatch.delenv("NUXT_PUBLIC_URL_PREFIX", raising=False)
    if root_path:
        monkeypatch.setenv("KANCHI_ROOT_PATH", root_path)
    else:
        monkeypatch.delenv("KANCHI_ROOT_PATH", raising=False)
    monkeypatch.delenv("ASGI_ROOT_PATH", raising=False)

    return create_app()


def test_frontend_serves_generated_ui_and_spa_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("NUXT_PUBLIC_API_URL", "https://kanchi.example.com")
    monkeypatch.setenv("NUXT_PUBLIC_WS_URL", "wss://kanchi.example.com/ws")
    monkeypatch.setenv("NUXT_PUBLIC_FRONTEND_URL", "https://kanchi.example.com/ui")
    app = create_frontend_app(monkeypatch, tmp_path, "<html>Nuxt shell</html>")

    status, _, body = anyio.run(request_app, app, "/ui/")
    assert status == 200
    assert b"Nuxt shell" in body
    assert (
        b'window.__KANCHI_BACKEND_URLS__={"apiUrl":"https://kanchi.example.com",'
        b'"wsUrl":"wss://kanchi.example.com/ws",'
        b'"frontendUrl":"https://kanchi.example.com/ui","urlPrefix":""}'
    ) in body

    status, _, body = anyio.run(request_app, app, "/ui/tasks/example-task")
    assert status == 200
    assert b"Nuxt shell" in body

    status, _, _ = anyio.run(request_app, app, "/ui/tasks/_payload.json")
    assert status == 404


def test_frontend_prefixes_ui_assets_from_configured_prefix(monkeypatch, tmp_path):
    app = create_frontend_app(
        monkeypatch,
        tmp_path,
        '<html><head><script src="/ui/_nuxt/app.js"></script></head></html>',
        url_prefix="/kanchi",
    )

    status, _, body = anyio.run(request_app, app, "/ui/")

    assert status == 200
    assert b'"/kanchi/ui/_nuxt/app.js"' in body


def test_frontend_prefixes_ui_assets_from_asgi_root_path(monkeypatch, tmp_path):
    app = create_frontend_app(
        monkeypatch,
        tmp_path,
        '<html><head><script src="/ui/_nuxt/app.js"></script></head></html>',
    )

    status, _, body = anyio.run(request_app, app, "/kanchi/ui/", "/kanchi")

    assert status == 200
    assert b'"/kanchi/ui/_nuxt/app.js"' in body


def test_frontend_root_redirect_uses_public_prefix(monkeypatch, tmp_path):
    app = create_frontend_app(monkeypatch, tmp_path, "<html>Kanchi UI</html>")
    _, headers, _ = anyio.run(request_app, app, "/", "/kanchi")
    assert headers["location"] == "/kanchi/ui/"

    app = create_frontend_app(
        monkeypatch,
        tmp_path,
        "<html>Kanchi UI</html>",
        url_prefix="/configured",
    )
    _, headers, _ = anyio.run(request_app, app, "/", "/proxy")
    assert headers["location"] == "/configured/ui/"


def test_configured_root_path_serves_prefixed_ui_api_and_websocket(monkeypatch, tmp_path):
    app = create_frontend_app(
        monkeypatch,
        tmp_path,
        '<html><head><script src="/ui/_nuxt/app.js"></script></head></html>',
        root_path="/kanchi",
    )

    assert app.root_path == "/kanchi"

    status, _, body = anyio.run(request_app, app, "/kanchi/ui/")
    assert status == 200
    assert b'"/kanchi/ui/_nuxt/app.js"' in body

    status, _, body = anyio.run(
        request_app,
        app,
        "/kanchi/api/health",
        "",
        "application/json",
    )
    assert status == 200
    assert b'"status":"healthy"' in body

    messages = anyio.run(websocket_app, app, "/kanchi/ws")
    assert {
        "type": "websocket.close",
        "code": 1011,
        "reason": "Server not initialized",
    } in messages


def test_url_prefix_configures_root_path_for_backwards_compatibility(monkeypatch, tmp_path):
    app = create_frontend_app(
        monkeypatch,
        tmp_path,
        "<html>Kanchi UI</html>",
        url_prefix="/kanchi",
    )

    assert app.root_path == "/kanchi"

    status, headers, _ = anyio.run(request_app, app, "/kanchi/")
    assert status == 307
    assert headers["location"] == "/kanchi/ui/"


def test_start_server_passes_normalized_root_path(monkeypatch):
    captured = {}

    monkeypatch.setenv("KANCHI_ROOT_PATH", "kanchi")
    monkeypatch.setattr(
        app_module.uvicorn,
        "run",
        lambda *args, **kwargs: captured.update(kwargs),
    )

    app_module.start_server()

    assert captured["root_path"] == "/kanchi"
