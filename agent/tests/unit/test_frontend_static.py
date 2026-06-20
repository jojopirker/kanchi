import anyio
from fastapi.routing import APIRoute
from starlette.requests import Request

from app import create_app


async def request_app(app, path: str, accept: str = "text/html", root_path: str = ""):
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


def test_frontend_static_mount_uses_generated_ui_directory(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "ui"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html>Kanchi UI</html>", encoding="utf-8")
    (frontend_dir / "200.html").write_text("<html>Nuxt shell</html>", encoding="utf-8")

    monkeypatch.setenv("FRONTEND_DIST_DIR", str(frontend_dir))

    app = create_app()

    root_route = next(
        route for route in app.routes if isinstance(route, APIRoute) and route.path == "/"
    )
    assert root_route.include_in_schema is False

    status, _, body = anyio.run(request_app, app, "/ui/")

    assert status == 200
    assert b"Kanchi UI" in body


def test_frontend_static_mount_prefixes_generated_ui_assets(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "ui"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text(
        "\n".join(
            [
                "<!DOCTYPE html>",
                '<html><head><link rel="modulepreload" href="/ui/_nuxt/app.js"></head>',
                "<body>",
                '<div id="__nuxt"></div><script type="module" src="/ui/_nuxt/entry.js"></script>',
                "</body></html>",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("FRONTEND_DIST_DIR", str(frontend_dir))
    monkeypatch.setenv("NUXT_PUBLIC_URL_PREFIX", "/kanchi")

    app = create_app()
    status, _, body = anyio.run(request_app, app, "/ui/")

    assert status == 200
    assert b'"/kanchi/ui/_nuxt/app.js"' in body
    assert b'"/kanchi/ui/_nuxt/entry.js"' in body
    assert b"__KANCHI_UI_ENV__" not in body


def test_frontend_static_mount_leaves_assets_unprefixed_without_url_prefix(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "ui"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text(
        '<html><head><script src="/ui/_nuxt/app.js"></script></head><body>Kanchi</body></html>',
        encoding="utf-8",
    )

    monkeypatch.setenv("FRONTEND_DIST_DIR", str(frontend_dir))

    app = create_app()
    status, _, body = anyio.run(request_app, app, "/ui/")

    assert status == 200
    assert b'"/ui/_nuxt/app.js"' in body


def test_frontend_static_mount_uses_asgi_root_path_for_asset_prefix(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "ui"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text(
        '<html><head><script src="/ui/_nuxt/app.js"></script></head><body>Kanchi</body></html>',
        encoding="utf-8",
    )

    monkeypatch.setenv("FRONTEND_DIST_DIR", str(frontend_dir))
    monkeypatch.delenv("NUXT_PUBLIC_URL_PREFIX", raising=False)

    app = create_app()
    status, _, body = anyio.run(request_app, app, "/ui/", "text/html", "/kanchi")

    assert status == 200
    assert b'"/kanchi/ui/_nuxt/app.js"' in body


def test_frontend_static_mount_falls_back_for_dynamic_routes(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "ui"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html>Nuxt shell</html>", encoding="utf-8")
    (frontend_dir / "404.html").write_text("<html>Not found</html>", encoding="utf-8")

    monkeypatch.setenv("FRONTEND_DIST_DIR", str(frontend_dir))

    app = create_app()

    status, _, body = anyio.run(request_app, app, "/ui/tasks/example-task")
    assert status == 200
    assert b"Nuxt shell" in body


def test_frontend_static_mount_falls_back_for_dynamic_routes_without_404(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "ui"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html>Nuxt shell</html>", encoding="utf-8")

    monkeypatch.setenv("FRONTEND_DIST_DIR", str(frontend_dir))

    app = create_app()

    status, _, body = anyio.run(request_app, app, "/ui/tasks/example-task")
    assert status == 200
    assert b"Nuxt shell" in body

    status, _, _ = anyio.run(request_app, app, "/ui/tasks/_payload.json")
    assert status == 404


def test_frontend_root_redirect_uses_url_prefix(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "ui"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html>Kanchi UI</html>", encoding="utf-8")

    monkeypatch.setenv("FRONTEND_DIST_DIR", str(frontend_dir))
    monkeypatch.setenv("NUXT_PUBLIC_URL_PREFIX", "/kanchi")

    app = create_app()
    root_route = next(
        route for route in app.routes if isinstance(route, APIRoute) and route.path == "/"
    )
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})
    response = anyio.run(root_route.endpoint, request)

    assert response.headers["location"] == "/kanchi/ui/"


def test_frontend_root_redirect_uses_asgi_root_path(monkeypatch, tmp_path):
    frontend_dir = tmp_path / "ui"
    frontend_dir.mkdir()
    (frontend_dir / "index.html").write_text("<html>Kanchi UI</html>", encoding="utf-8")

    monkeypatch.setenv("FRONTEND_DIST_DIR", str(frontend_dir))
    monkeypatch.delenv("NUXT_PUBLIC_URL_PREFIX", raising=False)

    app = create_app()
    root_route = next(
        route for route in app.routes if isinstance(route, APIRoute) and route.path == "/"
    )
    request = Request(
        {"type": "http", "method": "GET", "path": "/", "root_path": "/kanchi", "headers": []}
    )
    response = anyio.run(root_route.endpoint, request)

    assert response.headers["location"] == "/kanchi/ui/"
