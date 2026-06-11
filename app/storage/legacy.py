import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
PARTICIPANTS_PATH = BASE_DIR / "participantes.json"
RESULTS_PATH = BASE_DIR / "resultados.txt"


def load_participants():
    if not PARTICIPANTS_PATH.exists() or PARTICIPANTS_PATH.stat().st_size == 0:
        return {}

    try:
        return json.loads(PARTICIPANTS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def load_results():
    results = {}
    if not RESULTS_PATH.exists():
        return results

    for line in RESULTS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue

        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()

        if key == "pichichi":
            results[key] = [item.strip().lower() for item in value.split(",") if item.strip()]
        elif key in {"octavos", "cuartos", "semis", "final"}:
            results[key] = [item.strip() for item in value.split(",") if item.strip()]
        else:
            results[key] = value

    return results
