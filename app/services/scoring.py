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
    points = 0
    group_predictions = prediction.get("grupos", {})
    knockout_predictions = prediction.get("eliminatorias", {})

    for letter in "ABCDEFGHIJKL":
        # Only count group points when that specific group has finished all its matches
        if not results.get(f"g_{letter.lower()}_complete"):
            continue

        actual_positions = [
            results.get(f"g_{letter.lower()}_1"),
            results.get(f"g_{letter.lower()}_2"),
            results.get(f"g_{letter.lower()}_3"),
        ]
        actual_qualified = {team for team in actual_positions if team}

        for position in ("1", "2", "3"):
            predicted = group_predictions.get(f"g_{letter}_{position}")
            actual = results.get(f"g_{letter.lower()}_{position}")

            if not predicted:
                continue
            if predicted in actual_qualified:
                points += GROUP_POINTS_ANY_POSITION
            if predicted == actual:
                points += GROUP_POINTS_EXACT_POSITION

    for round_name, round_points in KNOCKOUT_POINTS.items():
        # Only count knockout points when that round is fully complete
        if not results.get(f"{round_name}_complete"):
            continue
        actual_teams = set(results.get(round_name, []))
        for predicted in knockout_predictions.get(round_name, []):
            if predicted in actual_teams:
                points += round_points

    if results.get("final_complete"):
        champion = knockout_predictions.get("campeon")
        if champion and champion == results.get("campeon"):
            points += CHAMPION_POINTS

        runner_up = knockout_predictions.get("subcampeon")
        if runner_up and runner_up == results.get("subcampeon"):
            points += RUNNER_UP_POINTS

    top_scorer = knockout_predictions.get("pichichi", "").strip().lower()
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
