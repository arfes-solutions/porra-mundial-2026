from app import create_app


def test_default_storage_backend_is_supabase():
    app = create_app({"TESTING": True})

    assert app.config["STORAGE_BACKEND"] == "supabase"


def test_test_fixture_uses_sqlite(app):
    assert app.config["STORAGE_BACKEND"] == "sqlite"
