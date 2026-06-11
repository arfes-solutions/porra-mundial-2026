from flask import current_app


def get_storage():
    backend = current_app.config["STORAGE_BACKEND"]
    if backend == "sqlite":
        from app.storage import sqlite

        return sqlite
    if backend == "supabase":
        from app.storage import supabase

        return supabase
    raise RuntimeError(f"Unknown storage backend: {backend}")
