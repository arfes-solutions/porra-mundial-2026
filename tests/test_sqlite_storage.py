from app.storage.sqlite import (
    get_participant_by_email,
    get_setting,
    load_participants,
    load_results,
    save_participant,
    save_results,
    set_setting,
)


def test_save_and_load_participant(app):
    prediction = {
        "grupos": {"g_A_1": "México"},
        "eliminatorias": {"campeon": "España"},
    }

    with app.app_context():
        save_participant("Ibon", prediction)

        assert load_participants() == {"Ibon": prediction}


def test_get_participant_by_email(app):
    with app.app_context():
        save_participant(
            "Ibon",
            {"grupos": {}, "eliminatorias": {}},
            email="ibon@example.com",
            password_hash="hash",
        )

        participant = get_participant_by_email("IBON@example.com")

        assert participant["name"] == "Ibon"
        assert participant["password_hash"] == "hash"


def test_save_and_load_results(app):
    results = {"g_a_1": "México", "campeon": "España"}

    with app.app_context():
        save_results(results)

        assert load_results() == results


def test_settings(app):
    with app.app_context():
        assert get_setting("registrations_open") == "true"

        set_setting("registrations_open", "false")

        assert get_setting("registrations_open") == "false"
