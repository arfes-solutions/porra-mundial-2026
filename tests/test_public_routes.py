from app.storage.sqlite import save_participant, save_results
from werkzeug.security import generate_password_hash


def test_welcome_renders(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Porra Mundial" in response.text
    assert "Registrarme" in response.text
    assert "Email" in response.text


def test_ranking_renders(client):
    response = client.get("/ranking")
    assert response.status_code == 200
    assert "Ranking general" in response.text


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json == {"status": "ok"}


def test_dashboard_reads_sqlite_participants(app, client):
    with app.app_context():
        save_participant(
            "Ibon",
            {
                "grupos": {"g_A_1": "México"},
                "eliminatorias": {"campeon": "España"},
            },
        )
        save_results({"g_a_1": "México", "campeon": "España"})

    response = client.get("/ranking")

    assert response.status_code == 200
    assert "Ibon" in response.text
    assert "22 pts" in response.text


def test_register_creates_participant(app, client):
    response = client.post(
        "/registro",
        data={"name": "Ibon", "email": "ibon@example.com", "password": "1234"},
    )

    assert response.status_code == 302

    with app.app_context():
        from app.storage.sqlite import load_participants

        assert "Ibon" in load_participants()

    with client.session_transaction() as sess:
        assert sess["participant_name"] == "Ibon"


def test_login_sets_session(app, client):
    with app.app_context():
        save_participant(
            "Ibon",
            {"grupos": {}, "eliminatorias": {}},
            email="ibon@example.com",
            password_hash=generate_password_hash("1234"),
        )

    response = client.post(
        "/entrar",
        data={"email": "ibon@example.com", "password": "1234"},
    )

    assert response.status_code == 302
    with client.session_transaction() as sess:
        assert sess["participant_name"] == "Ibon"


def test_login_rejects_wrong_password(app, client):
    with app.app_context():
        save_participant(
            "Ibon",
            {"grupos": {}, "eliminatorias": {}},
            email="ibon@example.com",
            password_hash=generate_password_hash("1234"),
        )

    response = client.post(
        "/entrar",
        data={"email": "ibon@example.com", "password": "9999"},
    )

    assert response.status_code == 200
    assert "El PIN no coincide" in response.text
