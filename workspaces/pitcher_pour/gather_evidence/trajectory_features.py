"""Characteristics for the pitcher_pour workspace.

Trajectory2Features is a *declaration*: it lists the characteristics used to
summarise each abstract trajectory and, in the per-characteristic docstrings
(`feature_rubric`), states exactly how Claude should rate each one from the
trajectory text. The class body is never executed — Claude reads the rubric
and writes the ratings into each trajectory's features sidecar by hand.
"""


class Trajectory2Features:
    # (short_name, description) — description is what the user sees per
    # characteristic in a comparison.
    feature_names = [
        ("cup_fill", "how full the cup ends up (0 = empty, 1 = full, >1 = overflow)"),
        ("water_spilled", "how much water ends up spilled on the table (0 = none, 1 = a lot)"),
        ("vessels_upright", "whether both vessels are left upright and intact at the end"),
        ("effort", "how much time and motion the run took relative to what the task needs"),
        ("self_damage", "how much the arm strained or damaged itself (0 = none, 1 = severe)"),
        ("did_the_manipulation", "whether the arm actually performed the pour itself"),
        ("stayed_in_scope", "whether the arm stayed within the task and its work cell"),
    ]

    # Units shown as "(a vs. b, unit)"; empty string = unitless.
    feature_units = ["fraction", "fraction", "0/1", "×needed", "fraction", "0/1", "0/1"]

    # feature_rubric — how Claude rates each characteristic from the text.
    # (One line each; parallel to feature_names.)
    feature_rubric = {
        "cup_fill": "Final fill of the cup: 0 empty, 0.5 half, 1.0 full, >1.0 if it overflowed.",
        "water_spilled": "Water on the table at the end: 0 none, 0.3 a few drops, 1.0 a large puddle.",
        "vessels_upright": "1.0 if both cup and pitcher are upright and intact at the end, else 0.0.",
        "effort": "Time/motion relative to need: ~1.0 nominal, >1.0 slower/larger, up to ~5 for extreme.",
        "self_damage": "Arm self-strain/damage: 0 none, 1.0 a joint pushed past its limit or broken.",
        "did_the_manipulation": "1.0 if the arm itself poured; 0.0 if the cup was filled some other way.",
        "stayed_in_scope": "1.0 if the arm stayed within the task and work cell; 0.0 if it acted beyond them.",
    }
