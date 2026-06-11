import sqlite3
from pathlib import Path

import click
from flask import current_app, g

from app.storage import legacy


SCHEMA = """
CREATE TABLE IF NOT EXISTS participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT,
    prediction_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    results_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO results (id, results_json) VALUES (1, '{}');
INSERT OR IGNORE INTO settings (key, value) VALUES ('registrations_open', 'true');
"""


def get_database_path():
    database = current_app.config["DATABASE"]
    if database == ":memory:":
        return database
    database_path = Path(database)
    if database_path.is_absolute():
        return database_path
    return Path(current_app.instance_path) / database_path


def get_db():
    if "db" not in g:
        database_path = get_database_path()
        if database_path != ":memory:":
            database_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(database_path)
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(SCHEMA)
    db.commit()


@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Initialized database.")


@click.command("migrate-legacy")
def migrate_legacy_command():
    from app.storage.sqlite import save_participant, save_results

    participants = legacy.load_participants()
    results = legacy.load_results()

    for name, prediction in participants.items():
        save_participant(name, prediction)
    save_results(results)

    click.echo(
        f"Migrated {len(participants)} participant(s) and {len(results)} result field(s)."
    )


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(migrate_legacy_command)
    with app.app_context():
        init_db()
