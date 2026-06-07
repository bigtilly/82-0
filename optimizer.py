"""
Expected-value draft optimizer for Classic mode.

This version replaces the old "global oracle filler" approach with a market-based
decision model:

  - Score every player by their direct weighted contribution to team OVR
  - For a live spin, compare:
      1. taking the best available player/position now
      2. team-reroll EV (same era, different team)
      3. era-reroll EV (same team, different era)
  - Value remaining open slots by their expected best future contribution from a
    fresh random spin, rather than by assuming perfect future luck

The result is still a heuristic, but it is much closer to the reroll logic the
user described: Bucks 60s should be valued as "Wilt lottery in the 60s pool",
and GSW should be valued as "can era-reroll into 60s Wilt/Curry/etc. on this team".
"""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from engine import (
    POSITIONS,
    BENCH_PPG, BENCH_RPG, BENCH_APG, BENCH_SPG, BENCH_BPG,
    W_PPG, W_RPG, W_APG, W_SPG, W_BPG,
    calculate_team_result,
)
from simulator import (
    can_player_play_position, reroll_team, reroll_decade,
    random_spin, get_players_by_team_and_decade, player_slug,
)

REROLL_BUDGET_TEAM = 1
REROLL_BUDGET_DECADE = 1
MAX_CANDIDATE_PLAYERS_PER_SPIN = 18


def stat_contribution(player: dict) -> float:
    """
    Direct weighted contribution to Classic team OVR.

    This uses the exact benchmark weights from the JS scoring engine:
      ppg / 133.4 * 0.46
      rpg / 39.7  * 0.25
      apg / 29.3  * 0.18
      spg / 6.1   * 0.07
      bpg / 3.2   * 0.04
    """
    return (
        (player.get("ppg") or 0) / BENCH_PPG * W_PPG +
        (player.get("rpg") or 0) / BENCH_RPG * W_RPG +
        (player.get("apg") or 0) / BENCH_APG * W_APG +
        (player.get("spg") or 0) / BENCH_SPG * W_SPG +
        (player.get("bpg") or 0) / BENCH_BPG * W_BPG
    )


def _player_value(player: dict) -> float:
    return player.get("_stat_value", stat_contribution(player))


def build_top_players_by_pos(all_players: list, n: int = 50) -> dict[str, list]:
    """
    Kept as a lightweight utility for reporting/debugging.

    The live optimizer no longer relies on this table for decision-making.
    """
    by_pos: dict[str, list] = {}
    for pos in POSITIONS:
        candidates = [p for p in all_players if can_player_play_position(p, pos)]
        candidates.sort(key=_player_value, reverse=True)
        by_pos[pos] = candidates[:n]
    return by_pos


def build_market_context(teams: list, valid_combos: list) -> dict:
    """
    Precompute combo/player rankings and spin probabilities for EV evaluation.
    """
    combo_players: dict[tuple[str, str], list] = {}
    combo_pos_players: dict[tuple[str, str, str], tuple] = {}
    combo_best_pos_value: dict[tuple[str, str, str], float] = {}
    era_to_teams: dict[str, list[str]] = defaultdict(list)
    team_to_eras: dict[str, list[str]] = defaultdict(list)

    for team_abbr, decade in valid_combos:
        players = list(get_players_by_team_and_decade(teams, team_abbr, decade))
        for player in players:
            player["_stat_value"] = stat_contribution(player)
        players.sort(key=_player_value, reverse=True)
        combo_players[(team_abbr, decade)] = players
        for pos in POSITIONS:
            pos_players = tuple(p for p in players if can_player_play_position(p, pos))
            combo_pos_players[(team_abbr, decade, pos)] = pos_players
            combo_best_pos_value[(team_abbr, decade, pos)] = _player_value(pos_players[0]) if pos_players else 0.0
        era_to_teams[decade].append(team_abbr)
        team_to_eras[team_abbr].append(decade)

    base_spin_weights = []
    era_count = len(era_to_teams)
    for decade, era_teams in era_to_teams.items():
        if not era_teams:
            continue
        weight = 1.0 / era_count / len(era_teams)
        for team_abbr in era_teams:
            base_spin_weights.append((team_abbr, decade, weight))

    expected_pos_baseline = {}
    for pos in POSITIONS:
        total = 0.0
        for team_abbr, decade, weight in base_spin_weights:
            total += weight * combo_best_pos_value[(team_abbr, decade, pos)]
        expected_pos_baseline[pos] = total

    return {
        "combo_players": combo_players,
        "combo_pos_players": combo_pos_players,
        "combo_best_pos_value": combo_best_pos_value,
        "era_to_teams": {k: tuple(v) for k, v in era_to_teams.items()},
        "team_to_eras": {k: tuple(v) for k, v in team_to_eras.items()},
        "base_spin_weights": tuple(base_spin_weights),
        "best_pos_cache": {},
        "expected_pos_cache": {},
        "future_slots_cache": {},
        "best_pick_cache": {},
        "spin_value_cache": {},
        "expected_pos_baseline": expected_pos_baseline,
    }


def build_combo_strength_report(context: dict) -> dict:
    """
    Convenience report for analysis:
      - top teams within each era by their best weighted player
      - best era for each team by their best weighted player
    """
    combo_players = context["combo_players"]
    era_to_teams = context["era_to_teams"]
    team_to_eras = context["team_to_eras"]

    by_era = {}
    for decade, teams in era_to_teams.items():
        board = []
        for team_abbr in teams:
            players = combo_players.get((team_abbr, decade), [])
            if not players:
                continue
            best = players[0]
            board.append({
                "team": team_abbr,
                "player": best["player"],
                "value": round(_player_value(best), 4),
            })
        by_era[decade] = sorted(board, key=lambda row: row["value"], reverse=True)

    by_team = {}
    for team_abbr, eras in team_to_eras.items():
        board = []
        for decade in eras:
            players = combo_players.get((team_abbr, decade), [])
            if not players:
                continue
            best = players[0]
            board.append({
                "era": decade,
                "player": best["player"],
                "value": round(_player_value(best), 4),
            })
        by_team[team_abbr] = sorted(board, key=lambda row: row["value"], reverse=True)

    return {"top_teams_by_era": by_era, "top_eras_by_team": by_team}


def run_draft(
    teams: list,
    valid_combos: list,
    market_context: dict,
    team_rerolls: int = REROLL_BUDGET_TEAM,
    decade_rerolls: int = REROLL_BUDGET_DECADE,
    first_round_policy: Optional[dict] = None,
) -> Optional[dict]:
    """
    Run one draft using expected-value reroll logic.

    Returns None only if a spin becomes completely unplayable after all rerolls
    (for example, every player in every reachable combo is blocked or ineligible).
    """
    roster: dict[str, Optional[dict]] = {pos: None for pos in POSITIONS}
    used_slugs: set[str] = set()
    team_rerolls_left = team_rerolls
    decade_rerolls_left = decade_rerolls
    rounds_detail = []

    for round_num in range(1, 6):
        open_positions = _open_positions_tuple(roster)
        if not open_positions:
            break

        team_abbr, decade = random_spin(valid_combos)
        initial_team_abbr, initial_decade = team_abbr, decade
        initial_best_pick = _best_pick_for_combo(
            market_context,
            initial_team_abbr,
            initial_decade,
            open_positions,
            _blocked_key(used_slugs),
        )
        if _should_restart_for_first_round_initial_value(
            round_num=round_num,
            initial_best_pick=initial_best_pick,
            policy=first_round_policy,
        ):
            return None
        action_log = []

        while True:
            action = _best_action_for_spin(
                context=market_context,
                team_abbr=team_abbr,
                decade=decade,
                open_positions=open_positions,
                blocked_key=_blocked_key(used_slugs),
                team_rerolls_left=team_rerolls_left,
                decade_rerolls_left=decade_rerolls_left,
            )

            if action is None:
                return None

            if _should_restart_for_first_round_policy(
                round_num=round_num,
                team_abbr=team_abbr,
                decade=decade,
                action=action,
                policy=first_round_policy,
            ):
                return None

            if action["kind"] == "team_reroll":
                old = (team_abbr, decade)
                team_abbr, decade = reroll_team(valid_combos, decade, excluded_team=team_abbr)
                team_rerolls_left -= 1
                action_log.append(f"team-reroll {old} -> ({team_abbr},{decade})")
                continue

            if action["kind"] == "era_reroll":
                old = (team_abbr, decade)
                team_abbr, decade = reroll_decade(valid_combos, team_abbr, excluded_decade=decade)
                decade_rerolls_left -= 1
                action_log.append(f"era-reroll {old} -> ({team_abbr},{decade})")
                continue

            player = action["player"]
            position = action["position"]
            roster[position] = player
            used_slugs.add(player_slug(player))

            rounds_detail.append({
                "round": round_num,
                "spin": (team_abbr, decade),
                "initial_spin": (initial_team_abbr, initial_decade),
                "initial_best_player": initial_best_pick["player"].get("player") if initial_best_pick else None,
                "initial_best_player_value": round(initial_best_pick["immediate"], 4) if initial_best_pick else None,
                "initial_best_decision_value": round(initial_best_pick["value"], 4) if initial_best_pick else None,
                "picked": player.get("player"),
                "position": position,
                "player_value": round(_player_value(player), 4),
                "decision_value": round(action["value"], 4),
                "actions": action_log,
            })
            break

    filled = [p for p in roster.values() if p is not None]
    return {
        "roster": roster,
        "result": calculate_team_result(filled),
        "restarted": False,
        "team_rerolls_used": team_rerolls - team_rerolls_left,
        "decade_rerolls_used": decade_rerolls - decade_rerolls_left,
        "rounds_detail": rounds_detail,
    }


def _best_action_for_spin(
    context: dict,
    team_abbr: str,
    decade: str,
    open_positions: tuple[str, ...],
    blocked_key: tuple[str, ...],
    team_rerolls_left: int,
    decade_rerolls_left: int,
) -> Optional[dict]:
    """
    Choose between:
      - best immediate pick on this spin
      - team reroll EV
      - era reroll EV
    """
    best_pick = _best_pick_for_combo(context, team_abbr, decade, open_positions, blocked_key)
    pick_value = best_pick["value"] if best_pick else float("-inf")

    best_value = pick_value
    best_action = None if best_pick is None else {
        "kind": "pick",
        "player": best_pick["player"],
        "position": best_pick["position"],
        "value": best_pick["value"],
    }

    if team_rerolls_left > 0:
        teams = [t for t in context["era_to_teams"].get(decade, ()) if t != team_abbr]
        if teams:
            reroll_value = sum(
                _spin_value(context, t, decade, open_positions, blocked_key, team_rerolls_left - 1, decade_rerolls_left)
                for t in teams
            ) / len(teams)
            if reroll_value > best_value:
                best_value = reroll_value
                best_action = {"kind": "team_reroll", "value": reroll_value}

    if decade_rerolls_left > 0:
        eras = [e for e in context["team_to_eras"].get(team_abbr, ()) if e != decade]
        if eras:
            reroll_value = sum(
                _spin_value(context, team_abbr, e, open_positions, blocked_key, team_rerolls_left, decade_rerolls_left - 1)
                for e in eras
            ) / len(eras)
            if reroll_value > best_value:
                best_value = reroll_value
                best_action = {"kind": "era_reroll", "value": reroll_value}

    return best_action


def _spin_value(
    context: dict,
    team_abbr: str,
    decade: str,
    open_positions: tuple[str, ...],
    blocked_key: tuple[str, ...],
    team_rerolls_left: int,
    decade_rerolls_left: int,
) -> float:
    """
    Same-round value after landing on a specific (team, era) combo.

    This allows chained reroll reasoning inside a single round:
      current combo pick EV vs team-reroll EV vs era-reroll EV.
    """
    cache = context["spin_value_cache"]
    key = (team_abbr, decade, open_positions, blocked_key, team_rerolls_left, decade_rerolls_left)
    if key in cache:
        return cache[key]

    best_pick = _best_pick_for_combo(context, team_abbr, decade, open_positions, blocked_key)
    best_value = best_pick["value"] if best_pick else float("-inf")

    if team_rerolls_left > 0:
        teams = [t for t in context["era_to_teams"].get(decade, ()) if t != team_abbr]
        if teams:
            reroll_value = sum(
                _spin_value(context, t, decade, open_positions, blocked_key, team_rerolls_left - 1, decade_rerolls_left)
                for t in teams
            ) / len(teams)
            best_value = max(best_value, reroll_value)

    if decade_rerolls_left > 0:
        eras = [e for e in context["team_to_eras"].get(team_abbr, ()) if e != decade]
        if eras:
            reroll_value = sum(
                _spin_value(context, team_abbr, e, open_positions, blocked_key, team_rerolls_left, decade_rerolls_left - 1)
                for e in eras
            ) / len(eras)
            best_value = max(best_value, reroll_value)

    cache[key] = best_value
    return best_value


def _best_pick_for_combo(
    context: dict,
    team_abbr: str,
    decade: str,
    open_positions: tuple[str, ...],
    blocked_key: tuple[str, ...],
) -> Optional[dict]:
    """
    Best pick from one combo, valuing:
      immediate player contribution
      + expected future contribution from remaining open slots
    """
    cache = context["best_pick_cache"]
    key = (team_abbr, decade, open_positions, blocked_key)
    if key in cache:
        return cache[key]

    players = context["combo_players"].get((team_abbr, decade), [])
    blocked = set(blocked_key)

    best = None
    candidates_considered = 0

    for player in players:
        slug = player_slug(player)
        if slug in blocked:
            continue

        eligible_positions = [pos for pos in open_positions if can_player_play_position(player, pos)]
        if not eligible_positions:
            continue

        candidates_considered += 1
        immediate = _player_value(player)
        next_blocked = _add_blocked(blocked_key, slug)

        for pos in eligible_positions:
            remaining = tuple(p for p in open_positions if p != pos)
            value = immediate + _future_slots_value(context, remaining, next_blocked)
            if best is None or value > best["value"]:
                best = {
                    "player": player,
                    "position": pos,
                    "immediate": immediate,
                    "value": value,
                }

        if candidates_considered >= MAX_CANDIDATE_PLAYERS_PER_SPIN and best is not None:
            break

    cache[key] = best
    return best


def _future_slots_value(
    context: dict,
    open_positions: tuple[str, ...],
    blocked_key: tuple[str, ...],
) -> float:
    """
    Approximate future value by summing independent expected best-pick values for
    each remaining slot from a fresh random spin.
    """
    if not open_positions:
        return 0.0

    cache = context["future_slots_cache"]
    key = open_positions
    if key in cache:
        return cache[key]

    value = sum(_expected_position_value(context, pos, blocked_key) for pos in open_positions)
    cache[key] = value
    return value


def _expected_position_value(
    context: dict,
    position: str,
    blocked_key: tuple[str, ...],
) -> float:
    """
    Expected contribution of the best available player for one position from a
    fresh random spin.
    """
    cache = context["expected_pos_cache"]
    key = position
    if key in cache:
        return cache[key]

    total = context["expected_pos_baseline"][position]
    cache[key] = total
    return total


def _best_position_value_for_combo(
    context: dict,
    team_abbr: str,
    decade: str,
    position: str,
    blocked_key: tuple[str, ...],
) -> float:
    """
    Best weighted player contribution for a single position inside one combo.
    """
    cache = context["best_pos_cache"]
    key = (team_abbr, decade, position, blocked_key)
    if key in cache:
        return cache[key]

    blocked = set(blocked_key)
    best_value = 0.0

    for player in context["combo_pos_players"].get((team_abbr, decade, position), ()):
        if player_slug(player) in blocked:
            continue
        best_value = _player_value(player)
        break

    cache[key] = best_value
    return best_value


def _open_positions_tuple(roster: dict) -> tuple[str, ...]:
    return tuple(pos for pos in POSITIONS if roster.get(pos) is None)


def _blocked_key(used_slugs: set[str]) -> tuple[str, ...]:
    return tuple(sorted(used_slugs))


def _add_blocked(blocked_key: tuple[str, ...], slug: str) -> tuple[str, ...]:
    if slug in blocked_key:
        return blocked_key
    return tuple(sorted((*blocked_key, slug)))


def _should_restart_for_first_round_policy(
    round_num: int,
    team_abbr: str,
    decade: str,
    action: dict,
    policy: Optional[dict],
) -> bool:
    """
    Optional round-1 gate for meta strategies.

    If a reroll is the best opening action but it is not one of the allowed
    round-1 reroll patterns, restart the draft instead of counting it.
    """
    if not policy or round_num != 1:
        return False

    kind = action.get("kind")
    if kind == "pick":
        return False

    if kind == "team_reroll":
        allowed_eras = set(policy.get("team_reroll_eras", ()))
        return decade not in allowed_eras

    if kind == "era_reroll":
        allowed_teams = set(policy.get("era_reroll_teams", ()))
        return team_abbr not in allowed_teams

    return False


def _should_restart_for_first_round_initial_value(
    round_num: int,
    initial_best_pick: Optional[dict],
    policy: Optional[dict],
) -> bool:
    """
    Optional round-1 gate on the pre-reroll opening spin.
    """
    if not policy or round_num != 1:
        return False

    threshold = policy.get("initial_best_value_lt")
    if threshold is None or initial_best_pick is None:
        return False

    return initial_best_pick.get("immediate", float("inf")) < threshold
