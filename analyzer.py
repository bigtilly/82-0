"""
Monte Carlo simulation for 82-0 probability estimation.

Usage:
    python analyzer.py
    python analyzer.py --n 100000
    python analyzer.py --n 10000 --rerolls-team 0 --rerolls-decade 0

This simulator now evaluates the expected-value draft policy from optimizer.py.
It still accepts `None` returns from the draft runner, but under the current
policy that should be rare.
"""
from __future__ import annotations

import argparse
import time
from collections import Counter
from pathlib import Path

from simulator import load_players
from optimizer import (
    build_market_context, run_draft,
    REROLL_BUDGET_TEAM, REROLL_BUDGET_DECADE,
)

ANALYZER_VERSION = "meta-filter-v2"
FIRST_PICK_BUCKET_EDGES = [0.15, 0.17, 0.19, 0.21, 0.23, 0.25, 0.27, 0.29, 0.31]
FIRST_ROUND_REROLL_STATES = ["none", "team_only", "era_only", "both"]
FIRST_ROUND_META_FILTER = {
    "initial_best_value_lt": 0.20,
}


def _safe_text(text: str) -> str:
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _first_pick_bucket_label(value: float) -> str:
    if value < FIRST_PICK_BUCKET_EDGES[0]:
        return f"<{FIRST_PICK_BUCKET_EDGES[0]:.2f}"

    for lo, hi in zip(FIRST_PICK_BUCKET_EDGES, FIRST_PICK_BUCKET_EDGES[1:]):
        if lo <= value < hi:
            return f"{lo:.2f}-{hi:.2f}"

    return f">={FIRST_PICK_BUCKET_EDGES[-1]:.2f}"


def _ordered_first_pick_bucket_labels() -> list[str]:
    labels = [f"<{FIRST_PICK_BUCKET_EDGES[0]:.2f}"]
    labels.extend(
        f"{lo:.2f}-{hi:.2f}"
        for lo, hi in zip(FIRST_PICK_BUCKET_EDGES, FIRST_PICK_BUCKET_EDGES[1:])
    )
    labels.append(f">={FIRST_PICK_BUCKET_EDGES[-1]:.2f}")
    return labels


def _first_round_reroll_state(actions: list[str]) -> str:
    used_team = any(action.startswith("team-reroll") for action in actions)
    used_era = any(action.startswith("era-reroll") for action in actions)
    if used_team and used_era:
        return "both"
    if used_team:
        return "team_only"
    if used_era:
        return "era_only"
    return "none"


def _empty_state_bucket_map() -> dict[str, Counter]:
    return {state: Counter() for state in FIRST_ROUND_REROLL_STATES}


def _format_state_label(state: str) -> str:
    return {
        "none": "No reroll",
        "team_only": "Team reroll only",
        "era_only": "Era reroll only",
        "both": "Both rerolls",
    }[state]


def run_simulation(
    n: int = 10_000,
    team_rerolls: int = REROLL_BUDGET_TEAM,
    decade_rerolls: int = REROLL_BUDGET_DECADE,
    data_path: Path = Path(__file__).parent / "data" / "player_flat.json",
    first_round_meta_filter: bool = False,
    verbose: bool = True,
) -> dict:
    mode_id = "FIRST_ROUND_LT_020" if first_round_meta_filter else "BASELINE"
    if verbose:
        print("Loading player data...")
    teams, valid_combos, all_players = load_players(data_path)
    market_context = build_market_context(teams, valid_combos)

    if verbose:
        print(f"  {len(all_players):,} players  |  {len(valid_combos)} valid combos")
        print(f"  mode id: {mode_id}")
        print(f"  rerolls: team={team_rerolls}  era={decade_rerolls}")
        if first_round_meta_filter:
            print("  FILTER ACTIVE: restart if round-1 opening best value < 0.20 before rerolls")
            print("  FILTER ID: FIRST_ROUND_LT_020")
        else:
            print("  FILTER OFF")
        print(f"Running until {n:,} completed drafts...")

    wins_list: list[int] = []
    restarts_total = 0
    player_appearances: Counter = Counter()
    player_82_appearances: Counter = Counter()
    combo_82_appearances: Counter = Counter()
    rerolls_team_used: Counter = Counter()
    rerolls_decade_used: Counter = Counter()
    first_pick_value_82_buckets: Counter = Counter()
    first_pick_value_all_buckets: Counter = Counter()
    first_opening_best_value_buckets: Counter = Counter()
    first_pick_value_by_r1_state_all = _empty_state_bucket_map()
    first_pick_value_by_r1_state_82 = _empty_state_bucket_map()
    first_pick_count_by_r1_state_all: Counter = Counter()
    first_pick_count_by_r1_state_82: Counter = Counter()
    reroll_team_rounds_82: Counter = Counter()
    reroll_decade_rounds_82: Counter = Counter()

    completed = 0
    interval = max(1, n // 20)
    t0 = time.time()

    while completed < n:
        if verbose and completed % interval == 0 and completed > 0:
            elapsed = time.time() - t0
            rate = completed / elapsed if elapsed > 0 else 0
            eta = (n - completed) / rate if rate > 0 else 0
            print(f"  {completed:6,}/{n:,}  restarts={restarts_total:,}  eta={eta:.0f}s", end="\r")

        if first_round_meta_filter:
            draft = run_draft(
                teams,
                valid_combos,
                market_context,
                team_rerolls,
                decade_rerolls,
                first_round_policy=FIRST_ROUND_META_FILTER,
            )
        else:
            draft = run_draft(teams, valid_combos, market_context, team_rerolls, decade_rerolls)
        if draft is None:
            restarts_total += 1
            continue

        completed += 1
        wins = draft["result"]["wins"]
        wins_list.append(wins)
        rerolls_team_used[draft["team_rerolls_used"]] += 1
        rerolls_decade_used[draft["decade_rerolls_used"]] += 1

        if draft["rounds_detail"]:
            first_round_state = _first_round_reroll_state(draft["rounds_detail"][0].get("actions", []))
            first_pick_value_all = draft["rounds_detail"][0].get("player_value")
            if first_pick_value_all is not None:
                bucket = _first_pick_bucket_label(first_pick_value_all)
                first_pick_value_all_buckets[bucket] += 1
                first_pick_value_by_r1_state_all[first_round_state][bucket] += 1
                first_pick_count_by_r1_state_all[first_round_state] += 1

            opening_best_value = draft["rounds_detail"][0].get("initial_best_player_value")
            if opening_best_value is not None:
                first_opening_best_value_buckets[_first_pick_bucket_label(opening_best_value)] += 1

        for player in draft["roster"].values():
            if player is None:
                continue
            key = f"{player['player']} ({player['team']}, {player['decade']})"
            player_appearances[key] += 1

        if wins >= 82:
            if draft["rounds_detail"]:
                first_round_state = _first_round_reroll_state(draft["rounds_detail"][0].get("actions", []))
                first_pick_value = draft["rounds_detail"][0].get("player_value")
                if first_pick_value is not None:
                    bucket = _first_pick_bucket_label(first_pick_value)
                    first_pick_value_82_buckets[bucket] += 1
                    first_pick_value_by_r1_state_82[first_round_state][bucket] += 1
                    first_pick_count_by_r1_state_82[first_round_state] += 1

            for round_detail in draft["rounds_detail"]:
                round_num = round_detail.get("round")
                for action in round_detail.get("actions", []):
                    if action.startswith("team-reroll"):
                        reroll_team_rounds_82[round_num] += 1
                    elif action.startswith("era-reroll"):
                        reroll_decade_rounds_82[round_num] += 1

            for player in draft["roster"].values():
                if player is None:
                    continue
                key = f"{player['player']} ({player['team']}, {player['decade']})"
                player_82_appearances[key] += 1
                combo_82_appearances[f"{player['team']} {player['decade']}"] += 1

    if verbose:
        print(f"  {n:,}/{n:,}  done in {time.time() - t0:.1f}s{' ' * 20}")

    return _summarise(
        wins_list, restarts_total, n, mode_id, team_rerolls, decade_rerolls,
        player_appearances, player_82_appearances, combo_82_appearances,
        rerolls_team_used, rerolls_decade_used,
        first_pick_value_all_buckets, first_opening_best_value_buckets,
        first_pick_value_82_buckets,
        first_pick_value_by_r1_state_all, first_pick_count_by_r1_state_all,
        first_pick_value_by_r1_state_82, first_pick_count_by_r1_state_82,
        reroll_team_rounds_82, reroll_decade_rounds_82,
    )


def _summarise(
    wins_list,
    restarts,
    n,
    mode_id,
    tr,
    dr,
    player_all,
    player_82,
    combos_82,
    rt_used,
    rd_used,
    first_pick_all_buckets,
    first_opening_best_buckets,
    first_pick_buckets_82,
    first_pick_by_r1_state_all,
    first_pick_count_by_r1_state_all,
    first_pick_by_r1_state_82,
    first_pick_count_by_r1_state_82,
    team_reroll_rounds_82,
    decade_reroll_rounds_82,
) -> dict:
    total_82 = sum(1 for w in wins_list if w >= 82)
    avg_wins = sum(wins_list) / n
    attempts = n + restarts

    buckets = [(82, 82), (72, 81), (62, 71), (57, 61), (50, 56), (40, 49), (0, 39)]
    win_dist = {}
    for lo, hi in buckets:
        label = "82-0" if lo == 82 else f"{lo}-{hi}"
        win_dist[label] = sum(1 for w in wins_list if lo <= w <= hi)

    return {
        "n": n,
        "mode_id": mode_id,
        "team_rerolls": tr,
        "decade_rerolls": dr,
        "avg_wins": round(avg_wins, 2),
        "rate_82_0_pct": round(total_82 / n * 100, 4),
        "count_82_0": total_82,
        "total_attempts": attempts,
        "restart_rate_pct": round(restarts / attempts * 100, 2),
        "attempts_per_complete": round(attempts / n, 2),
        "win_distribution": win_dist,
        "top_players_82_0": player_82.most_common(30),
        "top_combos_82_0": combos_82.most_common(20),
        "top_players_overall": player_all.most_common(20),
        "rerolls_team_used": dict(rt_used),
        "rerolls_decade_used": dict(rd_used),
        "first_pick_value_buckets_all": {
            label: first_pick_all_buckets.get(label, 0)
            for label in _ordered_first_pick_bucket_labels()
        },
        "most_common_first_pick_bucket_all": (
            first_pick_all_buckets.most_common(1)[0] if first_pick_all_buckets else None
        ),
        "first_opening_best_value_buckets": {
            label: first_opening_best_buckets.get(label, 0)
            for label in _ordered_first_pick_bucket_labels()
        },
        "most_common_first_opening_best_bucket": (
            first_opening_best_buckets.most_common(1)[0] if first_opening_best_buckets else None
        ),
        "first_pick_value_buckets_82_0": {
            label: first_pick_buckets_82.get(label, 0)
            for label in _ordered_first_pick_bucket_labels()
        },
        "most_common_first_pick_bucket_82_0": (
            first_pick_buckets_82.most_common(1)[0] if first_pick_buckets_82 else None
        ),
        "first_pick_value_by_r1_state_all": {
            state: {
                label: first_pick_by_r1_state_all[state].get(label, 0)
                for label in _ordered_first_pick_bucket_labels()
            }
            for state in FIRST_ROUND_REROLL_STATES
        },
        "first_pick_count_by_r1_state_all": {
            state: first_pick_count_by_r1_state_all.get(state, 0)
            for state in FIRST_ROUND_REROLL_STATES
        },
        "first_pick_value_by_r1_state_82_0": {
            state: {
                label: first_pick_by_r1_state_82[state].get(label, 0)
                for label in _ordered_first_pick_bucket_labels()
            }
            for state in FIRST_ROUND_REROLL_STATES
        },
        "first_pick_count_by_r1_state_82_0": {
            state: first_pick_count_by_r1_state_82.get(state, 0)
            for state in FIRST_ROUND_REROLL_STATES
        },
        "team_reroll_rounds_82_0": {round_num: team_reroll_rounds_82.get(round_num, 0) for round_num in range(1, 6)},
        "decade_reroll_rounds_82_0": {round_num: decade_reroll_rounds_82.get(round_num, 0) for round_num in range(1, 6)},
    }


def print_report(r: dict) -> None:
    sep = "-" * 62
    print(f"\n{'=' * 62}")
    print(f"  82-0 SIMULATOR [{ANALYZER_VERSION}]  |  mode={r['mode_id']}  |  accepted drafts={r['n']:,}  |  rerolls T={r['team_rerolls']} E={r['decade_rerolls']}")
    print(f"{'=' * 62}")
    print(f"  Avg wins          : {r['avg_wins']}")
    print(f"  82-0 rate         : {r['rate_82_0_pct']:.4f}%  ({r['count_82_0']:,} / {r['n']:,} accepted drafts)")
    print(f"  Rejected starts   : {r['restart_rate_pct']:.1f}%  ({r['total_attempts'] - r['n']:,} rejected, {r['total_attempts']:,} total starts)")
    print(f"  Starts per accept : {r['attempts_per_complete']:.1f}")

    print(f"\n{sep}")
    print("  WIN DISTRIBUTION")
    print(sep)
    for label, count in r["win_distribution"].items():
        bar = "#" * (count * 40 // r["n"])
        pct = count / r["n"] * 100
        print(f"  {label:>8}  {bar:<40} {count:6,}  ({pct:.1f}%)")

    if r["top_players_82_0"]:
        print(f"\n{sep}")
        print("  TOP PLAYERS IN 82-0 ROSTERS")
        print(sep)
        for i, (name, cnt) in enumerate(r["top_players_82_0"][:20], 1):
            pct = cnt / max(r["count_82_0"], 1) * 100
            print(f"  {i:2d}. {_safe_text(name):52s} {cnt:4,}  ({pct:.0f}% of 82-0 runs)")

    if r["most_common_first_pick_bucket_all"]:
        label, count = r["most_common_first_pick_bucket_all"]
        pct = count / max(r["n"], 1) * 100
        print(f"\n{sep}")
        print("  FIRST PICK VALUE BUCKETS FOR ALL RESULTS")
        print(sep)
        print(f"  Most common bucket : {label}  ({count:,} runs, {pct:.1f}%)")
        for bucket_label, bucket_count in r["first_pick_value_buckets_all"].items():
            if bucket_count == 0:
                continue
            bucket_pct = bucket_count / max(r["n"], 1) * 100
            print(f"  {bucket_label:>10}  {bucket_count:6,}  ({bucket_pct:.1f}%)")

    if r["most_common_first_opening_best_bucket"]:
        label, count = r["most_common_first_opening_best_bucket"]
        pct = count / max(r["n"], 1) * 100
        print(f"\n{sep}")
        print("  FIRST OPENING BEST PICK VALUE BUCKETS")
        print(sep)
        print(f"  Most common bucket : {label}  ({count:,} runs, {pct:.1f}%)")
        for bucket_label, bucket_count in r["first_opening_best_value_buckets"].items():
            if bucket_count == 0:
                continue
            bucket_pct = bucket_count / max(r["n"], 1) * 100
            print(f"  {bucket_label:>10}  {bucket_count:6,}  ({bucket_pct:.1f}%)")

    if r["most_common_first_pick_bucket_82_0"]:
        label, count = r["most_common_first_pick_bucket_82_0"]
        pct = count / max(r["count_82_0"], 1) * 100
        print(f"\n{sep}")
        print("  FIRST PICK VALUE BUCKETS IN 82-0 ROSTERS")
        print(sep)
        print(f"  Most common bucket : {label}  ({count:,} runs, {pct:.1f}%)")
        for bucket_label, bucket_count in r["first_pick_value_buckets_82_0"].items():
            if bucket_count == 0:
                continue
            bucket_pct = bucket_count / max(r["count_82_0"], 1) * 100
            print(f"  {bucket_label:>10}  {bucket_count:6,}  ({bucket_pct:.1f}%)")

    print(f"\n{sep}")
    print("  FIRST PICK VALUE BY ROUND 1 REROLL STATE (ALL RESULTS)")
    print(sep)
    for state in FIRST_ROUND_REROLL_STATES:
        total = r["first_pick_count_by_r1_state_all"][state]
        if total == 0:
            continue
        overall_pct = total / max(r["n"], 1) * 100
        print(f"  {_format_state_label(state)}  ({total:,} runs, {overall_pct:.1f}%)")
        for bucket_label, bucket_count in r["first_pick_value_by_r1_state_all"][state].items():
            if bucket_count == 0:
                continue
            bucket_pct = bucket_count / total * 100
            print(f"    {bucket_label:>10}  {bucket_pct:5.1f}%  ({bucket_count:,})")

    if r["count_82_0"] > 0:
        print(f"\n{sep}")
        print("  FIRST PICK VALUE BY ROUND 1 REROLL STATE (82-0 ONLY)")
        print(sep)
        for state in FIRST_ROUND_REROLL_STATES:
            total = r["first_pick_count_by_r1_state_82_0"][state]
            if total == 0:
                continue
            overall_pct = total / max(r["count_82_0"], 1) * 100
            print(f"  {_format_state_label(state)}  ({total:,} runs, {overall_pct:.1f}%)")
            for bucket_label, bucket_count in r["first_pick_value_by_r1_state_82_0"][state].items():
                if bucket_count == 0:
                    continue
                bucket_pct = bucket_count / total * 100
                print(f"    {bucket_label:>10}  {bucket_pct:5.1f}%  ({bucket_count:,})")

    if r["count_82_0"] > 0:
        print(f"\n{sep}")
        print("  REROLL ROUNDS IN 82-0 ROSTERS")
        print(sep)
        print("  Team reroll by round:")
        for round_num, count in r["team_reroll_rounds_82_0"].items():
            pct = count / max(r["count_82_0"], 1) * 100
            print(f"    Round {round_num}: {count:,}  ({pct:.1f}%)")
        print("  Era reroll by round:")
        for round_num, count in r["decade_reroll_rounds_82_0"].items():
            pct = count / max(r["count_82_0"], 1) * 100
            print(f"    Round {round_num}: {count:,}  ({pct:.1f}%)")

    if r["top_combos_82_0"]:
        print(f"\n{sep}")
        print("  TOP (TEAM, ERA) COMBOS IN 82-0 ROSTERS")
        print(sep)
        for i, (combo, cnt) in enumerate(r["top_combos_82_0"][:15], 1):
            print(f"  {i:2d}. {_safe_text(combo):30s} {cnt:,}")

    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=10_000)
    parser.add_argument("--rerolls-team", type=int, default=REROLL_BUDGET_TEAM)
    parser.add_argument("--rerolls-decade", type=int, default=REROLL_BUDGET_DECADE)
    parser.add_argument("--data", default=str(Path(__file__).parent / "data" / "player_flat.json"))
    parser.add_argument("--first-round-meta-filter", action="store_true")
    args = parser.parse_args()

    results = run_simulation(
        n=args.n,
        team_rerolls=args.rerolls_team,
        decade_rerolls=args.rerolls_decade,
        data_path=Path(args.data),
        first_round_meta_filter=args.first_round_meta_filter,
    )
    print_report(results)


if __name__ == "__main__":
    main()
