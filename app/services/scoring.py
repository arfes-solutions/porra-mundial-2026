import unicodedata


def _normalize_name(name) -> str:
    """Lowercase + strip accents, so 'Mbappé', 'mbappe', 'MBAPPÉ' all match."""
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return no_accents.strip().lower()


GROUP_POINTS_ANY_POSITION = 1
GROUP_POINTS_EXACT_POSITION = 1
KNOCKOUT_POINTS = {
    "octavos": 3,
    "cuartos": 5,
    "semis": 8,
    "final": 12,
}
CHAMPION_POINTS = 20
RUNNER_UP_POINTS = 10
TOP_SCORER_POINTS = 7


def calculate_points(prediction, results):
    # No points until all teams have played their first match
    if not results.get("jornada_1_complete"):
        return 0

    points = 0
    group_predictions = prediction.get("grupos", {})
    knockout_predictions = prediction.get("eliminatorias", {})
    # Teams that actually qualified to the round of 32 (only known once those
    # fixtures are published by the API). A 3rd-place finish does NOT guarantee
    # qualification (only the 8 best thirds advance), so we require explicit
    # confirmation before crediting a "best third" prediction.
    qualified_r32 = set(results.get("qualified_r32", []))

    for letter in "ABCDEFGHIJKL":
        g1 = results.get(f"g_{letter.lower()}_1")
        g2 = results.get(f"g_{letter.lower()}_2")
        g3 = results.get(f"g_{letter.lower()}_3")
        # Only 1st and 2nd place are guaranteed to qualify
        guaranteed_qualified = {team for team in (g1, g2) if team}

        for position, actual in (("1", g1), ("2", g2)):
            predicted = group_predictions.get(f"g_{letter}_{position}")
            if not predicted:
                continue
            if predicted in guaranteed_qualified:
                points += GROUP_POINTS_ANY_POSITION
            if predicted == actual:
                points += GROUP_POINTS_EXACT_POSITION

        # "Best third" prediction: only counts once we know it actually
        # qualified for the knockout stage
        predicted_3 = group_predictions.get(f"g_{letter}_3")
        if predicted_3 and predicted_3 == g3 and predicted_3 in qualified_r32:
            points += GROUP_POINTS_ANY_POSITION + GROUP_POINTS_EXACT_POSITION

    for round_name, round_points in KNOCKOUT_POINTS.items():
        actual_teams = set(results.get(round_name, []))
        for predicted in knockout_predictions.get(round_name, []):
            if predicted in actual_teams:
                points += round_points

    champion = knockout_predictions.get("campeon")
    if champion and champion == results.get("campeon"):
        points += CHAMPION_POINTS

    runner_up = knockout_predictions.get("subcampeon")
    if runner_up and runner_up == results.get("subcampeon"):
        points += RUNNER_UP_POINTS

    top_scorer = _normalize_name(knockout_predictions.get("pichichi"))
    if top_scorer and top_scorer in results.get("pichichi", []):
        points += TOP_SCORER_POINTS

    return points


def build_standings(participants, results):
    standings = []
    for name, prediction in participants.items():
        standings.append(
            {
                "name": name,
                "points": calculate_points(prediction, results),
                "champion": prediction.get("eliminatorias", {}).get("campeon", ""),
            }
        )

    return sorted(standings, key=lambda row: row["points"], reverse=True)
