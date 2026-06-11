import os
from pathlib import Path

from flask import Flask


def create_app(test_config=None):
    project_root = Path(__file__).resolve().parents[1]
    api_templates = project_root / "api" / "templates"
    api_static = project_root / "api" / "static"
    template_folder = api_templates if api_templates.exists() else project_root / "app" / "templates"
    static_folder = api_static if api_static.exists() else project_root / "app" / "static"

    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(template_folder),
        static_folder=str(static_folder),
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-change-me"),
        DATABASE="mundial.db",
        STORAGE_BACKEND=os.environ.get("STORAGE_BACKEND", "supabase"),
        SUPABASE_URL=os.environ.get("SUPABASE_URL"),
        SUPABASE_SERVICE_ROLE_KEY=os.environ.get("SUPABASE_SERVICE_ROLE_KEY"),
        ADMIN_PASSWORD=os.environ.get("ADMIN_PASSWORD", ""),
        FOOTBALL_DATA_API_KEY=os.environ.get("FOOTBALL_DATA_API_KEY", ""),
        SYNC_SECRET=os.environ.get("SYNC_SECRET", ""),
    )
    if test_config:
        app.config.update(test_config)

    if app.config["STORAGE_BACKEND"] == "sqlite":
        from app import db

        db.init_app(app)

    from app.routes.public import public_bp

    app.register_blueprint(public_bp)
    return app
