"""Serving the built frontend (DEPRO_WEB_DIST) from the API app."""

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def spa_app(tmp_path, monkeypatch):
    """A reloaded app.main with DEPRO_WEB_DIST pointing at a fake dist dir."""
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>depro</html>")
    (dist / "favicon.svg").write_text("<svg></svg>")
    (dist / "assets" / "main.js").write_text("console.log(1)")
    monkeypatch.setenv("DEPRO_WEB_DIST", str(dist))
    import app.main as main

    importlib.reload(main)
    yield main
    monkeypatch.delenv("DEPRO_WEB_DIST")
    importlib.reload(main)


def test_spa_fallback_and_static_files(spa_app):
    with TestClient(spa_app.app) as client:
        # Root and deep links serve the SPA shell (client-side routing).
        assert client.get("/").text == "<html>depro</html>"
        assert client.get("/tasks").text == "<html>depro</html>"
        # Real files from dist are served as-is.
        assert client.get("/favicon.svg").text == "<svg></svg>"
        asset = client.get("/assets/main.js")
        assert asset.status_code == 200
        assert asset.text == "console.log(1)"
        # API routes are untouched; unknown API paths stay 404.
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/nope").status_code == 404
