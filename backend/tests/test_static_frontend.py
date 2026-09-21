from fastapi.testclient import TestClient

from app.main import app, mount_frontend


def test_frontend_is_served_without_shadowing_the_api(tmp_path):
    # imagem Docker: STATIC_DIR aponta pro build do React
    (tmp_path / "index.html").write_text("<html>ApitaCerto</html>", encoding="utf-8")
    mount_frontend(app, tmp_path)
    try:
        client = TestClient(app)
        home = client.get("/")
        assert home.status_code == 200
        assert "ApitaCerto" in home.text
        assert client.get("/health").json() == {"status": "ok", "database": "ok"}
        assert client.get("/filters").status_code == 200
    finally:
        app.router.routes.pop()  # desfaz o mount pros outros testes
