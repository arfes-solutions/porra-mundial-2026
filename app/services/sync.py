"""
Sync real World Cup 2026 data from football-data.org API.
Fetches: match fixtures (all rounds), live scores, group standings, knockout results.
Docs: https://docs.football-data.org/general/v4/index.html
"""
import datetime
import requests as _req

_BASE = "https://api.football-data.org/v4"
_COMPETITION = "WC"

# API team names → our Spanish names
_NAME_MAP = {
    "Mexico": "México",
    "South Africa": "Sudáfrica",
    "Korea Republic": "Corea del Sur",
    "South Korea": "Corea del Sur",
    "Czech Republic": "Chequia", "Czechia": "Chequia",
    "Canada": "Canadá",
    "Bosnia and Herzegovina": "Bosnia y Herzegovina",
    "Bosnia-Herzegovina": "Bosnia y Herzegovina",
    "Bosnia & Herzegovina": "Bosnia y Herzegovina",
    "Qatar": "Qatar",
    "Switzerland": "Suiza",
    "Brazil": "Brasil",
    "Morocco": "Marruecos",
    "Haiti": "Haití",
    "Scotland": "Escocia",
    "United States": "Estados Unidos", "USA": "Estados Unidos",
    "Paraguay": "Paraguay",
    "Australia": "Australia",
    "Türkiye": "Turquía", "Turkey": "Turquía",
    "Germany": "Alemania",
    "Curaçao": "Curazao",
    "Ivory Coast": "Costa de Marfil", "Côte d'Ivoire": "Costa de Marfil",
    "Ecuador": "Ecuador",
    "Netherlands": "Países Bajos",
    "Japan": "Japón",
    "Sweden": "Suecia",
    "Tunisia": "Túnez",
    "Belgium": "Bélgica",
    "Egypt": "Egipto",
    "Iran": "Irán",
    "New Zealand": "Nueva Zelanda",
    "Spain": "España",
    "Cape Verde Islands": "Cape Verde",
    "Saudi Arabia": "Arabia Saudita",
    "Uruguay": "Uruguay",
    "France": "Francia",
    "Senegal": "Senegal",
    "Norway": "Noruega",
    "Argentina": "Argentina",
    "Algeria": "Argelia",
    "Austria": "Austria",
    "Jordan": "Jordania",
    "Portugal": "Portugal",
    "DR Congo": "RD Congo", "Congo DR": "RD Congo",
    "Uzbekistan": "Uzbekistán",
    "Colombia": "Colombia",
    "England": "Inglaterra",
    "Croatia": "Croacia",
    "Ghana": "Ghana",
    "Panama": "Panamá",
}

# ISO flag codes for each Spanish team name
_FLAG_MAP = {
    "México": "mx", "Sudáfrica": "za", "Corea del Sur": "kr", "Chequia": "cz",
    "Canadá": "ca", "Bosnia y Herzegovina": "ba", "Qatar": "qa", "Suiza": "ch",
    "Brasil": "br", "Marruecos": "ma", "Haití": "ht", "Escocia": "gb-sct",
    "Estados Unidos": "us", "Paraguay": "py", "Australia": "au", "Turquía": "tr",
    "Alemania": "de", "Curazao": "cw", "Costa de Marfil": "ci", "Ecuador": "ec",
    "Países Bajos": "nl", "Japón": "jp", "Suecia": "se", "Túnez": "tn",
    "Bélgica": "be", "Egipto": "eg", "Irán": "ir", "Nueva Zelanda": "nz",
    "España": "es", "Cape Verde": "cv", "Arabia Saudita": "sa", "Uruguay": "uy",
    "Francia": "fr", "Senegal": "sn", "Iraq": "iq", "Noruega": "no",
    "Argentina": "ar", "Argelia": "dz", "Austria": "at", "Jordania": "jo",
    "Portugal": "pt", "RD Congo": "cd", "Uzbekistán": "uz", "Colombia": "co",
    "Inglaterra": "gb-eng", "Croacia": "hr", "Ghana": "gh", "Panamá": "pa",
}

# API stage → Spanish label + our round key
_STAGE_LABELS = {
    "GROUP_STAGE":    ("Fase de Grupos", None),
    "ROUND_OF_32":    ("Dieciseisavos de Final", "octavos"),
    "LAST_32":        ("Dieciseisavos de Final", "octavos"),
    "ROUND_OF_16":    ("Octavos de Final", "cuartos"),
    "LAST_16":        ("Octavos de Final", "cuartos"),
    "QUARTER_FINALS": ("Cuartos de Final", "semis"),
    "SEMI_FINALS":    ("Semifinales", "final"),
    "FINAL":          ("Final", None),
    "THIRD_PLACE":    ("Tercer y Cuarto Puesto", None),
}

_MONTH_ES = {
    1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun",
    7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic",
}

_STATUS_FINISHED = {"FINISHED", "AWARDED"}
_STATUS_LIVE     = {"IN_PLAY", "PAUSED", "HALF_TIME", "EXTRA_TIME", "PENALTY_SHOOTOUT"}


def _norm(name) -> str:
    if not name:
        return "?"
    return _NAME_MAP.get(name, name)

def _flag(name: str) -> str:
    return _FLAG_MAP.get(name, "")

def _headers(api_key: str) -> dict:
    return {"X-Auth-Token": api_key}

def _utc_to_peninsular(utc_str: str):
    """Convert '2026-06-11T19:00:00Z' → (date_str '11 Jun', time_str '21:00') CEST=UTC+2."""
    try:
        dt = datetime.datetime.strptime(utc_str, "%Y-%m-%dT%H:%M:%SZ")
        dt_pen = dt + datetime.timedelta(hours=2)  # CEST (summer)
        fecha = f"{dt_pen.day} {_MONTH_ES[dt_pen.month]}"
        hora  = dt_pen.strftime("%H:%M")
        return fecha, hora
    except Exception:
        return "?", "?"

def _check(response):
    if response.status_code >= 400:
        raise RuntimeError(f"API error {response.status_code}: {response.text[:200]}")
    return response


def fetch_all(api_key: str) -> dict:
    """
    Fetch everything from the API and return a combined dict:
    {
      'results': { ...standings/winners... },
      'fixtures': [ ...all matches... ]
    }
    """
    results  = {}
    fixtures = []

    # ── 1. ALL MATCHES (fixtures + results) ──────────────────────────────
    try:
        r = _check(_req.get(
            f"{_BASE}/competitions/{_COMPETITION}/matches",
            headers=_headers(api_key),
            timeout=15,
        ))
        matches = r.json().get("matches", [])

        advanced = {"octavos": set(), "cuartos": set(), "semis": set(), "final": set()}
        champion = runner_up = None
        # Track jornada 1 completion per group (2 matches per group in matchday 1)
        j1_total    = {}  # letter -> total jornada-1 matches
        j1_finished = {}  # letter -> finished jornada-1 matches
        # Teams that actually qualified to the round of 32 (top 2 of each group + 8 best thirds)
        qualified_r32 = set()
        # Track completion per knockout round (for display only — a round's predictions
        # shouldn't be marked "failed" until every match in that round has been played)
        round_total    = {}  # round_key -> total matches
        round_finished = {}  # round_key -> finished matches
        final_total = final_finished = 0

        for m in matches:
            stage      = m.get("stage", "")
            group_raw  = m.get("group") or ""             # e.g. "GROUP_A"
            matchday   = m.get("matchday") or 1
            utc_date   = m.get("utcDate", "")
            status     = m.get("status", "")
            home_name  = _norm(m.get("homeTeam", {}).get("name", "?"))
            away_name  = _norm(m.get("awayTeam", {}).get("name", "?"))
            score      = m.get("score", {})
            ft         = score.get("fullTime") or {}
            home_score = ft.get("home")
            away_score = ft.get("away")
            winner_key = score.get("winner")           # HOME_TEAM / AWAY_TEAM / DRAW

            # If the bulk endpoint returned null for a finished match, fetch it individually
            if status in _STATUS_FINISHED and (home_score is None or away_score is None):
                try:
                    match_id = m.get("id")
                    if match_id:
                        r2 = _req.get(f"{_BASE}/matches/{match_id}", headers=_headers(api_key), timeout=10)
                        if r2.status_code == 200:
                            ft2 = (r2.json().get("score") or {}).get("fullTime") or {}
                            if ft2.get("home") is not None:
                                home_score = ft2["home"]
                                away_score = ft2.get("away")
                                winner_key = (r2.json().get("score") or {}).get("winner", winner_key)
                except Exception:
                    pass

            # The API's "winner" field is sometimes missing/null even for finished
            # matches with a clear scoreline — fall back to comparing the score.
            if status in _STATUS_FINISHED and not winner_key and home_score is not None and away_score is not None:
                if home_score > away_score:
                    winner_key = "HOME_TEAM"
                elif away_score > home_score:
                    winner_key = "AWAY_TEAM"
                else:
                    winner_key = "DRAW"

            fecha, hora = _utc_to_peninsular(utc_date)
            label, round_key = _STAGE_LABELS.get(stage, (stage, None))
            group_letter = group_raw.replace("GROUP_", "") if group_raw.startswith("GROUP_") else ""

            is_finished = status in _STATUS_FINISHED
            is_live     = status in _STATUS_LIVE

            # Track jornada 1 completion (matchday 1 of group stage)
            if stage == "GROUP_STAGE" and group_letter and matchday == 1:
                j1_total[group_letter]    = j1_total.get(group_letter, 0) + 1
                j1_finished[group_letter] = j1_finished.get(group_letter, 0) + (1 if is_finished else 0)

            # Round of 32 fixtures reveal exactly which teams qualified from groups
            # (top 2 of each group + the 8 best third-placed teams)
            if stage in ("ROUND_OF_32", "LAST_32"):
                if home_name and home_name != "?":
                    qualified_r32.add(home_name)
                if away_name and away_name != "?":
                    qualified_r32.add(away_name)

            # Track knockout round completion
            if stage == "FINAL":
                final_total += 1
                final_finished += 1 if is_finished else 0
            elif round_key:
                round_total[round_key]    = round_total.get(round_key, 0) + 1
                round_finished[round_key] = round_finished.get(round_key, 0) + (1 if is_finished else 0)

            # Build fixture entry
            fixture = {
                "stage":       stage,
                "stage_label": label,
                "group":       group_letter,
                "jornada":     f"Jornada {matchday}" if stage == "GROUP_STAGE" else "",
                "fecha":       fecha,
                "hora":        hora,
                "utc_date":    utc_date,
                "home":        {"name": home_name, "flag": _flag(home_name)},
                "away":        {"name": away_name, "flag": _flag(away_name)},
                "home_score":  home_score,
                "away_score":  away_score,
                "status":      status,
                "is_finished": is_finished,
                "is_live":     is_live,
            }
            fixtures.append(fixture)

            # ── Collect knockout results ──────────────────────────────────
            if is_finished:
                if stage == "FINAL":
                    if winner_key == "HOME_TEAM":
                        champion, runner_up = home_name, away_name
                    elif winner_key == "AWAY_TEAM":
                        champion, runner_up = away_name, home_name
                elif round_key:
                    winner = home_name if winner_key == "HOME_TEAM" else away_name if winner_key == "AWAY_TEAM" else None
                    if winner:
                        advanced[round_key].add(winner)

        for ronda, teams in advanced.items():
            if teams:
                results[ronda] = sorted(teams)
        if champion:
            results["campeon"] = champion
        if runner_up:
            results["subcampeon"] = runner_up

        # jornada_1_complete = all 12 groups have finished ALL their matchday-1 matches
        # (2 matches per group = all 4 teams in each group have played once)
        all_groups = set("ABCDEFGHIJKL")
        groups_with_j1 = {
            letter for letter, total in j1_total.items()
            if total > 0 and j1_finished.get(letter, 0) >= total
        }
        if all_groups == groups_with_j1:
            results["jornada_1_complete"] = True

        if qualified_r32:
            results["qualified_r32"] = sorted(qualified_r32)

        # Knockout round completion flags (display only)
        for ronda, total in round_total.items():
            if total > 0 and round_finished.get(ronda, 0) >= total:
                results[f"{ronda}_complete"] = True
        if final_total > 0 and final_finished >= final_total:
            results["final_complete"] = True

    except Exception as exc:
        raise RuntimeError(f"Error fetching matches: {exc}")

    # ── 2. GROUP STANDINGS ───────────────────────────────────────────────
    try:
        r = _check(_req.get(
            f"{_BASE}/competitions/{_COMPETITION}/standings",
            headers=_headers(api_key),
            timeout=15,
        ))
        for standing in r.json().get("standings", []):
            if standing.get("type") != "TOTAL":
                continue
            raw_group = standing.get("group", "")
            letter = raw_group.replace("GROUP_", "").replace("Group ", "").strip()
            if not letter or len(letter) != 1:
                continue
            group_standings = []
            for idx, row in enumerate(standing.get("table", []), start=1):
                name = _norm(row.get("team", {}).get("name", ""))
                if not name:
                    continue
                if idx <= 3:
                    results[f"g_{letter.lower()}_{idx}"] = name
                group_standings.append({
                    "pos":    idx,
                    "name":   name,
                    "flag":   _flag(name),
                    "played": row.get("playedGames", 0),
                    "won":    row.get("won", 0),
                    "draw":   row.get("draw", 0),
                    "lost":   row.get("lost", 0),
                    "gf":     row.get("goalsFor", 0),
                    "ga":     row.get("goalsAgainst", 0),
                    "gd":     row.get("goalDifference", 0),
                    "pts":    row.get("points", 0),
                })
            if group_standings:
                results[f"g_{letter.lower()}_standings"] = group_standings
    except Exception:
        pass   # standings failure is non-fatal

    # ── 3. TOP SCORERS ──────────────────────────────────────────────────
    try:
        r = _check(_req.get(
            f"{_BASE}/competitions/{_COMPETITION}/scorers?limit=9",
            headers=_headers(api_key),
            timeout=15,
        ))
        scorers = []
        for s in r.json().get("scorers", []):
            player = s.get("player", {})
            team   = s.get("team", {})
            scorers.append({
                "name":   player.get("name", "?"),
                "team":   _norm(team.get("name", "?")),
                "flag":   _flag(_norm(team.get("name", "?"))),
                "goals":  s.get("goals") or 0,
                "assists": s.get("assists") or 0,
            })
        if scorers:
            results["top_scorers"] = scorers
    except Exception:
        pass   # scorers failure is non-fatal

    return {"results": results, "fixtures": fixtures}


# Keep old name for backward compatibility
def fetch_results(api_key: str) -> dict:
    return fetch_all(api_key)["results"]
