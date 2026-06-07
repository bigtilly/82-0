"""
Data loading, spin mechanics, and random draft.
Mirrors the JS data pipeline (chunk 23902) and game spin/selection logic.
"""
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Optional

from engine import (
    POSITIONS, DECADES, calculate_team_result, _safe_isnan
)

DEFAULT_DATA_PATH = Path(__file__).parent / "data" / "player_flat.json"

# Decade alias map from JS (alternate string formats → canonical key)
_DECADE_ALIAS = {
    "60's": "1960s", "70's": "1970s", "80's": "1980s", "90's": "1990s",
    "00's": "2000s", "10's": "2010s", "20's": "2020s",
}


def load_players(path=DEFAULT_DATA_PATH):
    """
    Parse the flat player JSON, build the team/decade index exactly as the JS does.

    Returns:
        teams       – list of team dicts  {id, abbreviation, name, decades}
        valid_combos – list of (team_abbr, decade) tuples for every non-empty combo
        all_players  – flat list of all processed player dicts (each has `decade` key set)

    Only decades 1960s-2020s are included (matches JS forEach over DECADES list).
    Players whose ppg/rpg/apg/spg/bpg contain an actual NaN are filtered out
    (JS filter: !isNaN(val ?? 0)  →  null/None passes, NaN fails).
    """
    raw = json.loads(Path(path).read_text(encoding="utf-8"))

    # Build team → decade → [players] dict (preserving insertion order)
    team_map: dict[str, dict[str, list]] = {}
    for entry in raw:
        team = entry.get("team")
        era  = entry.get("era")
        if not team or not era:
            continue
        canonical = _DECADE_ALIAS.get(era, era)
        if canonical not in DECADES:
            continue
        team_map.setdefault(team, {}).setdefault(canonical, []).append(entry)

    teams: list[dict] = []
    all_players: list[dict] = []

    for team_idx, (abbr, decade_map) in enumerate(team_map.items()):
        processed_decades: dict[str, list] = {}

        for decade in DECADES:
            raw_players = decade_map.get(decade)
            if not raw_players:
                continue

            bucket = []
            for p in raw_players:
                # JS NaN filter: skip only if a stat is actual NaN (null passes)
                if any(_safe_isnan(p.get(s)) for s in ("ppg", "rpg", "apg", "spg", "bpg")):
                    continue

                player = {
                    **p,
                    "team":   abbr,
                    "decade": decade,      # canonical decade key used in scoring
                    "teamId": team_idx,
                    "positions": _clean_positions(p),
                }
                bucket.append(player)

            if bucket:
                processed_decades[decade] = bucket
                all_players.extend(bucket)

        if processed_decades:
            teams.append({
                "id":           team_idx,
                "abbreviation": abbr,
                "name":         abbr,
                "decades":      processed_decades,
            })

    valid_combos = [
        (t["abbreviation"], decade)
        for t in teams
        for decade in t["decades"]
    ]

    return teams, valid_combos, all_players


def get_players_by_team_and_decade(teams: list, team_abbr: str, decade: str) -> list:
    """Port of JS getPlayersByTeamAndDecade (by abbreviation instead of ID)."""
    decade = _DECADE_ALIAS.get(decade, decade)
    team   = next((t for t in teams if t["abbreviation"] == team_abbr), None)
    return team["decades"].get(decade, []) if team else []


def can_player_play_position(player: dict, position: str) -> bool:
    """Port of JS canPlayerPlayPosition (function m)."""
    return position in player.get("positions", [])


def can_swap_positions(roster: dict, pos_a: str, pos_b: str) -> bool:
    """
    Port of JS canSwapPositions (function b).
    roster is {pos: player_or_None}.
    Returns True if swapping the players at pos_a and pos_b is valid.
    """
    if pos_a == pos_b:
        return False
    player_a = roster.get(pos_a)
    player_b = roster.get(pos_b)
    a_can_move = (player_a is None) or can_player_play_position(player_a, pos_b)
    b_can_move = (player_b is None) or can_player_play_position(player_b, pos_a)
    return a_can_move and b_can_move


def random_spin(
    valid_combos: list,
    excluded_team: Optional[str] = None,
    excluded_decade: Optional[str] = None,
) -> tuple[str, str]:
    """
    Era-first spin: pick one of 7 eras uniformly, then pick a team within that era uniformly.
    Mirrors the actual game mechanic (1/7 per era, not uniform across all 180 combos).

    excluded_team:   if set, that team_abbr is excluded (used to avoid repeat after reroll).
    excluded_decade: if set, that decade is excluded (used to avoid repeat after reroll).
    """
    era_to_teams: dict[str, list] = defaultdict(list)
    for (team, era) in valid_combos:
        if excluded_team is not None and team == excluded_team:
            continue
        if excluded_decade is not None and era == excluded_decade:
            continue
        era_to_teams[era].append(team)

    if not era_to_teams:
        # Fallback: drop exclusions if they leave nothing
        for (team, era) in valid_combos:
            era_to_teams[era].append(team)

    era  = random.choice(list(era_to_teams.keys()))
    team = random.choice(era_to_teams[era])
    return (team, era)


def reroll_team(
    valid_combos: list,
    current_decade: str,
    excluded_team: str,
) -> tuple[str, str]:
    """Keep current era, pick a new team within that era (uniform, excluding current team)."""
    pool = [t for (t, e) in valid_combos if e == current_decade and t != excluded_team]
    if not pool:
        pool = [t for (t, e) in valid_combos if e == current_decade]
    return (random.choice(pool), current_decade) if pool else random_spin(valid_combos, excluded_team=excluded_team)


def reroll_decade(
    valid_combos: list,
    current_team: str,
    excluded_decade: str,
) -> tuple[str, str]:
    """Keep current team, pick a new era (uniform across eras available for this team)."""
    pool = [e for (t, e) in valid_combos if t == current_team and e != excluded_decade]
    if not pool:
        pool = [e for (t, e) in valid_combos if t == current_team]
    return (current_team, random.choice(pool)) if pool else random_spin(valid_combos, excluded_decade=excluded_decade)


def run_random_draft(teams: list, valid_combos: list) -> dict:
    """
    Five rounds of pure random spin + random player/position pick.
    Returns {roster, result} where roster is {pos: player} and result is the team scoring dict.
    Same player (by baseSlug) cannot appear twice.
    """
    roster: dict[str, Optional[dict]] = {pos: None for pos in POSITIONS}
    used_slugs: set[str] = set()

    for _ in range(5):
        open_positions = [pos for pos in POSITIONS if roster[pos] is None]
        if not open_positions:
            break

        team_abbr, decade = random_spin(valid_combos)
        spin_players = get_players_by_team_and_decade(teams, team_abbr, decade)

        eligible = _eligible_pairs(spin_players, open_positions, used_slugs)

        if not eligible:
            attempts = 0
            while not eligible and attempts < 50:
                team_abbr, decade = random_spin(valid_combos)
                spin_players = get_players_by_team_and_decade(teams, team_abbr, decade)
                eligible = _eligible_pairs(spin_players, open_positions, used_slugs)
                attempts += 1
            if not eligible:
                continue

        player, position = random.choice(eligible)
        roster[position] = player
        used_slugs.add(player_slug(player))

    filled = [p for p in roster.values() if p is not None]
    return {"roster": roster, "result": calculate_team_result(filled)}


# ── public helpers ────────────────────────────────────────────────────────────

def player_slug(player: dict) -> str:
    """Unique player identity key. Same player across different team/decade entries share this."""
    return player.get("baseSlug") or player.get("player", "unknown")


# ── internal helpers ──────────────────────────────────────────────────────────

def _eligible_pairs(spin_players: list, open_positions: list, used_slugs: set) -> list:
    """Return (player, pos) pairs that are pickable: not used, has an open slot."""
    return [
        (p, pos)
        for p in spin_players
        if player_slug(p) not in used_slugs
        for pos in open_positions
        if can_player_play_position(p, pos)
    ]


def _clean_positions(raw_player: dict) -> list[str]:
    """
    Port of JS positions cleanup logic:
    Use positions array if it exists, else use [pos].
    Filter out 'nan' strings and None.
    """
    positions = raw_player.get("positions")
    if isinstance(positions, list):
        return [p for p in positions if p and p != "nan"]
    pos = raw_player.get("pos")
    return [pos] if pos and pos != "nan" else []
