import json

from app.db import get_db


def load_participants():
    rows = get_db().execute(
        "SELECT name, prediction_json FROM participants ORDER BY created_at ASC"
    ).fetchall()

    participants = {}
    for row in rows:
        participants[row["name"]] = json.loads(row["prediction_json"])
    return participants


def get_participant_by_email(email):
    row = get_db().execute(
        """
        SELECT id, name, email, password_hash, prediction_json
        FROM participants
        WHERE lower(email) = lower(?)
        """,
        (email.strip(),),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "password_hash": row["password_hash"],
        "prediction": json.loads(row["prediction_json"]),
    }


def save_participant(name, prediction, email=None, password_hash=None):
    payload = json.dumps(prediction, ensure_ascii=False)
    get_db().execute(
        """
        INSERT INTO participants (name, email, password_hash, prediction_json)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            email = COALESCE(excluded.email, participants.email),
            password_hash = COALESCE(excluded.password_hash, participants.password_hash),
            prediction_json = excluded.prediction_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (name.strip(), email.strip().lower() if email else None, password_hash, payload),
    )
    get_db().commit()


def create_participant(name, email, password_hash):
    payload = json.dumps({"grupos": {}, "eliminatorias": {}}, ensure_ascii=False)
    get_db().execute(
        """
        INSERT INTO participants (name, email, password_hash, prediction_json)
        VALUES (?, ?, ?, ?)
        """,
        (name.strip(), email.strip().lower(), password_hash, payload),
    )
    get_db().commit()


def load_results():
    row = get_db().execute(
        "SELECT results_json FROM results WHERE id = 1"
    ).fetchone()
    if row is None:
        return {}
    return json.loads(row["results_json"])


def save_results(results):
    payload = json.dumps(results, ensure_ascii=False)
    get_db().execute(
        """
        INSERT INTO results (id, results_json)
        VALUES (1, ?)
        ON CONFLICT(id) DO UPDATE SET
            results_json = excluded.results_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (payload,),
    )
    get_db().commit()


def get_setting(key, default=None):
    row = get_db().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return row["value"]


def set_setting(key, value):
    get_db().execute(
        """
        INSERT INTO settings (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )
    get_db().commit()
