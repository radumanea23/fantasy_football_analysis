#!/usr/bin/env python3
"""
Export Sleeper league teams and rosters to CSV.

Usage:
  python sleeper_export.py --league-id 1248075580834856960 --out-dir ./data

This script fetches:
- League users (teams)
- League rosters (players per team)
- Player metadata (name, position, NFL team)

And writes a CSV with one row per player on a roster.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import requests
from sleeper_client import (
    get_league_users,
    get_league_rosters,
    get_players_nfl,
    build_user_maps,
    preferred_team_name,
)


def write_rosters_csv(
    league_id: str,
    rosters: Iterable[dict],
    user_id_to_user: Dict[str, dict],
    players_by_id: Dict[str, dict],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "league_id",
        "roster_id",
        "owner_user_id",
        "owner_display_name",
        "team_name",
        "player_id",
        "player_name",
        "position",
        "nfl_team",
        "is_starter",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for roster in rosters:
            roster_id = roster.get("roster_id")
            owner_id = str(roster.get("owner_id") or "")
            starters = set(roster.get("starters") or [])
            user = user_id_to_user.get(owner_id) or {}
            display_name = str(user.get("display_name") or "")
            team_name = preferred_team_name(user)

            for player_id in roster.get("players") or []:
                player = players_by_id.get(str(player_id)) or {}
                player_name = player.get("full_name") or player.get("first_name") or player.get("last_name") or "Unknown Player"
                position = player.get("position") or ""
                nfl_team = player.get("team") or ""

                writer.writerow(
                    {
                        "league_id": league_id,
                        "roster_id": roster_id,
                        "owner_user_id": owner_id,
                        "owner_display_name": display_name,
                        "team_name": team_name,
                        "player_id": player_id,
                        "player_name": player_name,
                        "position": position,
                        "nfl_team": nfl_team,
                        "is_starter": str(player_id in starters),
                    }
                )


def write_teams_csv(
    league_id: str,
    users: Iterable[dict],
    rosters: Iterable[dict],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Map owner_id -> roster_id for quick lookup
    owner_to_roster: Dict[str, int] = {}
    for r in rosters:
        owner_id = str(r.get("owner_id") or "")
        roster_id = r.get("roster_id")
        if owner_id:
            owner_to_roster[owner_id] = roster_id

    fieldnames = [
        "league_id",
        "roster_id",
        "owner_user_id",
        "owner_display_name",
        "team_name",
    ]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for user in users:
            owner_id = str(user.get("user_id") or "")
            display_name = str(user.get("display_name") or "")
            team_name = preferred_team_name(user)
            roster_id = owner_to_roster.get(owner_id, "")

            writer.writerow(
                {
                    "league_id": league_id,
                    "roster_id": roster_id,
                    "owner_user_id": owner_id,
                    "owner_display_name": display_name,
                    "team_name": team_name,
                }
            )


def export_league_to_csv(league_id: str, out_dir: Path) -> Tuple[Path, Path]:
    users = get_league_users(league_id)
    rosters = get_league_rosters(league_id)
    players_by_id = get_players_nfl()

    user_id_to_user, _ = build_user_maps(users)

    rosters_csv = out_dir / f"{league_id}_rosters.csv"
    teams_csv = out_dir / f"{league_id}_teams.csv"

    write_rosters_csv(league_id, rosters, user_id_to_user, players_by_id, rosters_csv)
    write_teams_csv(league_id, users, rosters, teams_csv)

    return rosters_csv, teams_csv


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export Sleeper league data to CSV")
    parser.add_argument(
        "--league-id",
        default="1248075580834856960",
        help="Sleeper league ID (default: 1248075580834856960)",
    )
    parser.add_argument(
        "--out-dir",
        default=str(Path.cwd() / "data"),
        help="Directory to write CSV files to (default: ./data)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    league_id = str(args.league_id)
    out_dir = Path(args.out_dir)

    try:
        rosters_csv, teams_csv = export_league_to_csv(league_id, out_dir)
        print(f"Wrote rosters CSV: {rosters_csv}")
        print(f"Wrote teams CSV:   {teams_csv}")
    except requests.HTTPError as http_err:
        print(f"HTTP error: {http_err}", file=sys.stderr)
        return 2
    except Exception as ex:
        print(f"Error: {ex}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


