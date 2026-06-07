"""
Exact Python port of the JS scoring engine (chunk 89050 in Engine.js).
All constants and formulas mirror the JS precisely.
"""
import math

POSITIONS = ["PG", "SG", "SF", "PF", "C"]
DECADES   = ["1960s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s"]

ERA_CEILINGS = {
    "1960s": {"ppg": 30,   "rpg": 18, "apg": 8,  "spg": 1.8, "bpg": 1.8},
    "1970s": {"ppg": 28,   "rpg": 13, "apg": 9,  "spg": 2.0, "bpg": 2.0},
    "1980s": {"ppg": 28,   "rpg": 11, "apg": 11, "spg": 2.2, "bpg": 2.0},
    "1990s": {"ppg": 27,   "rpg": 11, "apg": 9,  "spg": 2.0, "bpg": 2.0},
    "2000s": {"ppg": 27,   "rpg": 11, "apg": 9,  "spg": 2.0, "bpg": 2.0},
    "2010s": {"ppg": 28,   "rpg": 11, "apg": 9,  "spg": 1.8, "bpg": 1.8},
    "2020s": {"ppg": 28,   "rpg": 11, "apg": 9,  "spg": 1.8, "bpg": 1.8},
}

POSITION_WEIGHTS = {
    "PG": {"ppg": 0.40, "rpg": 0.10, "apg": 0.35, "spg": 0.10, "bpg": 0.05},
    "SG": {"ppg": 0.45, "rpg": 0.10, "apg": 0.20, "spg": 0.20, "bpg": 0.05},
    "SF": {"ppg": 0.45, "rpg": 0.15, "apg": 0.20, "spg": 0.15, "bpg": 0.05},
    "PF": {"ppg": 0.40, "rpg": 0.30, "apg": 0.10, "spg": 0.10, "bpg": 0.10},
    "C":  {"ppg": 0.40, "rpg": 0.35, "apg": 0.10, "spg": 0.05, "bpg": 0.10},
}

# Team OVR benchmark denominators and weights
BENCH_PPG, W_PPG = 133.4, 0.46
BENCH_RPG, W_RPG = 39.7,  0.25
BENCH_APG, W_APG = 29.3,  0.18
BENCH_SPG, W_SPG = 6.1,   0.07
BENCH_BPG, W_BPG = 3.2,   0.04

LEGENDS = {
    "larry bird", "tim duncan", "kevin durant", "magic johnson", "shaquille o'neal",
    "hakeem olajuwon", "bill russell", "kobe bryant", "oscar robertson", "karl malone",
    "kevin garnett", "isiah thomas", "tony parker", "manu ginobili", "draymond green",
    "scottie pippen", "dennis rodman", "stephen curry", "nikola jokic", "dirk nowitzki",
}

TEAM_GRADES = [
    {"minWins": 80, "grade": "S",  "label": "PERFECT",   "color": "#a855f7"},
    {"minWins": 72, "grade": "A+", "label": "HISTORIC",  "color": "#22c55e"},
    {"minWins": 62, "grade": "A",  "label": "DYNASTY",   "color": "#22c55e"},
    {"minWins": 57, "grade": "B",  "label": "CONTENDER", "color": "#3b82f6"},
    {"minWins": 50, "grade": "C",  "label": "PLAYOFF",   "color": "#f59e0b"},
    {"minWins": 40, "grade": "D",  "label": "LOTTERY",   "color": "#64748b"},
    {"minWins":  0, "grade": "F",  "label": "TANKING",   "color": "#ef4444"},
]


def _js_gt_zero(val) -> bool:
    """Mirrors JS `val > 0` where null/None coerces to 0 (so None returns False)."""
    return val is not None and val > 0


def calculate_player_rating(player: dict, test_mode: bool = False) -> float:
    """
    Port of JS function f(player, test=false).

    test_mode=False  → display mode: simple stat/ceiling sums, 2pt multi-pos bonus
    test_mode=True   → scoring mode: position-weighted, era-exponent 1.25 when above ceiling,
                       3pt multi-pos bonus, 2.5pt legend bonus
    """
    era   = player.get("decade") or player.get("era") or "2020s"
    ceil  = ERA_CEILINGS.get(era, ERA_CEILINGS["2020s"])
    n     = 0.0

    if test_mode:
        pos_key = (player.get("positions") or [None])[0] or player.get("pos") or "SF"
        weights = dict(POSITION_WEIGHTS.get(pos_key, POSITION_WEIGHTS["SF"]))

        # Redistribute weight from missing spg/bpg to the present stats
        missing = [s for s in ("spg", "bpg") if player.get(s) is None or _safe_isnan(player.get(s))]
        if missing:
            present_sum = sum(
                weights[s] for s in ("ppg", "rpg", "apg", "spg", "bpg") if s not in missing
            )
            scale = (1.0 / present_sum) if present_sum > 0 else 1.0
            for s in ("ppg", "rpg", "apg"):
                weights[s] *= scale
            for s in missing:
                weights[s] = 0.0

        for stat in ("ppg", "rpg", "apg", "spg", "bpg"):
            val = player.get(stat)
            if val is not None and not _safe_isnan(val):
                ratio = val / ceil[stat]
                if ratio > 1:
                    ratio = ratio ** 1.25
                n += weights[stat] * ratio
    else:
        for stat in ("ppg", "rpg", "apg", "spg", "bpg"):
            val = player.get(stat)
            if val is not None and not _safe_isnan(val):
                n += val / ceil[stat]

    base        = 60.0 + 40.0 * n
    positions   = player.get("positions") or []
    multi_bonus = (len(positions) - 1) * (3 if test_mode else 2)
    leg_bonus   = 2.5 if test_mode and (player.get("player") or "").lower() in LEGENDS else 0.0

    return min(100.0, round((base + multi_bonus + leg_bonus) * 10) / 10)


def adjust_spg_bpg(players: list) -> dict:
    """
    Port of JS function A(players).
    Scales SPG and BPG by (5 / count_with_valid_stat) to compensate for missing entries.
    Players with spg/bpg == 0 or None are excluded from the count (mirrors JS `val > 0`).
    """
    spg_vals = [p["spg"] for p in players if _js_gt_zero(p.get("spg"))]
    bpg_vals = [p["bpg"] for p in players if _js_gt_zero(p.get("bpg"))]
    n_spg, n_bpg = len(spg_vals), len(bpg_vals)
    return {
        "adjustedSpg": sum(spg_vals) * (5.0 / n_spg if n_spg > 0 else 1.0),
        "adjustedBpg": sum(bpg_vals) * (5.0 / n_bpg if n_bpg > 0 else 1.0),
    }


def calculate_team_result(roster: list, test_mode: bool = False) -> dict:
    """
    Port of JS function C(roster, test=false).
    Expects a list of player dicts (non-None entries only).
    """
    if not roster:
        return {"teamOvr": 0, "wins": 0, "losses": 82, "grade": "F", "label": "TANKING", "color": "#ef4444"}

    if test_mode:
        ratings = [calculate_player_rating(p, True) for p in roster]
        geo_mean = math.prod(ratings) ** (1.0 / len(ratings))
        team_ovr = round(1.1 * geo_mean * 10) / 10
        wins = round(82 * min(team_ovr / 110, 1) ** 2.2)
    else:
        adj      = adjust_spg_bpg(roster)
        sum_ppg  = sum(p.get("ppg") or 0 for p in roster)
        sum_rpg  = sum(p.get("rpg") or 0 for p in roster)
        sum_apg  = sum(p.get("apg") or 0 for p in roster)
        team_ovr = round(100 * (
            sum_ppg / BENCH_PPG * W_PPG +
            sum_rpg / BENCH_RPG * W_RPG +
            sum_apg / BENCH_APG * W_APG +
            adj["adjustedSpg"] / BENCH_SPG * W_SPG +
            adj["adjustedBpg"] / BENCH_BPG * W_BPG
        ) * 10) / 10
        wins = projected_wins(team_ovr)

    grade = next((g for g in TEAM_GRADES if wins >= g["minWins"]), TEAM_GRADES[-1])
    return {
        "teamOvr":  team_ovr,
        "wins":     wins,
        "losses":   82 - wins,
        "grade":    grade["grade"],
        "label":    grade["label"],
        "color":    grade["color"],
    }


def projected_wins(team_ovr: float) -> int:
    """Port of JS function E(ovr). Used in non-test scoring."""
    return round(82 * min(team_ovr / 110, 1) ** 1.15)


def calculate_team_ovr(roster: list, test_mode: bool = False) -> float:
    """Convenience: returns teamOvr only."""
    return calculate_team_result(roster, test_mode)["teamOvr"]


# ── internal helpers ──────────────────────────────────────────────────────────

def _safe_isnan(val) -> bool:
    """True only for actual NaN floats; None/null returns False (mirrors JS isNaN(null)==false)."""
    if val is None:
        return False
    try:
        return math.isnan(float(val))
    except (TypeError, ValueError):
        return True
