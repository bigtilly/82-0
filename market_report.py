"""
Quick market report for the EV draft model.

Examples:
    python market_report.py --era 1960s
    python market_report.py --team GSW
    python market_report.py --all-teams
    python market_report.py --era 2020s --team MIL --limit 10
"""
from __future__ import annotations

import argparse

from simulator import load_players
from optimizer import build_market_context, build_combo_strength_report


def _safe_text(text: str) -> str:
    return text.encode("cp1252", errors="replace").decode("cp1252")


def _print_team_board(team: str, board: list[dict], limit: int) -> None:
    print(f"Top eras for {team}")
    for i, row in enumerate(board[:limit], 1):
        print(f"{i:2d}. {row['era']:6s}  {_safe_text(row['player']):30s}  {row['value']:.4f}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--era", help="Show top teams in this era, e.g. 1960s")
    parser.add_argument("--team", help="Show top eras for this team, e.g. GSW")
    parser.add_argument("--all-teams", action="store_true", help="Show top eras for every team")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    teams, valid_combos, _ = load_players()
    context = build_market_context(teams, valid_combos)
    report = build_combo_strength_report(context)

    if args.era:
        board = report["top_teams_by_era"].get(args.era, [])
        print(f"Top teams in {args.era}")
        for i, row in enumerate(board[:args.limit], 1):
            print(f"{i:2d}. {row['team']:4s}  {_safe_text(row['player']):30s}  {row['value']:.4f}")
        print()

    if args.team:
        board = report["top_eras_by_team"].get(args.team, [])
        _print_team_board(args.team, board, args.limit)

    if args.all_teams:
        for team in sorted(report["top_eras_by_team"]):
            board = report["top_eras_by_team"][team]
            _print_team_board(team, board, args.limit)

    if not args.era and not args.team and not args.all_teams:
        for era in sorted(report["top_teams_by_era"]):
            board = report["top_teams_by_era"][era][: min(args.limit, 5)]
            print(f"Top teams in {era}")
            for i, row in enumerate(board, 1):
                print(f"{i:2d}. {row['team']:4s}  {_safe_text(row['player']):30s}  {row['value']:.4f}")
            print()


if __name__ == "__main__":
    main()
