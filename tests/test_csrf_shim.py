from flask import Flask

from src.app.csrf import CSRFProtect


def create_basic_app():
    app = Flask(__name__)
    app.secret_key = "testing-secret"
    csrf = CSRFProtect(app)

    @app.route("/token")
    def token():
        return csrf.generate_csrf()

    @app.route("/submit", methods=["POST"])
    def submit():
        return "ok"

    return app


def test_csrf_skipped_when_app_testing():
    app = create_basic_app()
    app.testing = True

    client = app.test_client()
    response = client.post("/submit")

    assert response.status_code == 200


def test_csrf_enforced_when_not_testing():
    app = create_basic_app()
    client = app.test_client()

    response = client.post("/submit")
    assert response.status_code == 400

    with client:
        token = client.get("/token").data.decode()
        response = client.post("/submit", data={"csrf_token": token})

    assert response.status_code == 200


def test_csrf_disabled_via_config():
    app = create_basic_app()
    app.config["WTF_CSRF_ENABLED"] = False
    client = app.test_client()

    response = client.post("/submit")

    assert response.status_code == 200
