from app.services.scoring import calculate_points


def test_calculate_points_scores_groups_knockout_and_extras():
    prediction = {
        "grupos": {
            "g_A_1": "México",
            "g_A_2": "Corea del Sur",
            "g_A_3": "Sudáfrica",
        },
        "eliminatorias": {
            "octavos": ["México", "España"],
            "cuartos": ["España"],
            "semis": ["Argentina"],
            "final": ["España", "Argentina"],
            "campeon": "España",
            "subcampeon": "Argentina",
            "pichichi": "Mbappe",
        },
    }
    results = {
        "g_a_1": "México",
        "g_a_2": "Sudáfrica",
        "g_a_3": "Corea del Sur",
        "octavos": ["México", "España"],
        "cuartos": ["España"],
        "semis": ["Argentina"],
        "final": ["España", "Argentina"],
        "campeon": "España",
        "subcampeon": "Argentina",
        "pichichi": ["mbappe", "kylian mbappe"],
    }

    assert calculate_points(prediction, results) == 84


def test_calculate_points_ignores_missing_predictions():
    assert calculate_points({"grupos": {}, "eliminatorias": {}}, {}) == 0
