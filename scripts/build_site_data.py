#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple

# Ensure project root is on sys.path when running from scripts/
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sleeper_client import (
    get_league_users,
    get_league_rosters,
    get_players_nfl,
    get_matchups,
    build_user_maps,
    preferred_team_name,
)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def build_teams_json(league_id: str, users: List[dict], rosters: List[dict]) -> dict:
    owner_to_roster: Dict[str, int] = {}
    for r in rosters:
        owner_id = str(r.get("owner_id") or "")
        roster_id = r.get("roster_id")
        if owner_id:
            owner_to_roster[owner_id] = roster_id

    teams: List[dict] = []
    for user in users:
        owner_id = str(user.get("user_id") or "")
        display_name = str(user.get("display_name") or "")
        team_name = preferred_team_name(user)
        avatar = user.get("avatar") or ""
        avatar_url = f"https://sleepercdn.com/avatars/{avatar}" if avatar else ""
        roster_id = owner_to_roster.get(owner_id, None)
        # Filter out co-owners without a roster_id
        if roster_id is None:
            continue
        teams.append(
            {
                "roster_id": roster_id,
                "owner_user_id": owner_id,
                "owner_display_name": display_name,
                "team_name": team_name,
                "avatar_url": avatar_url,
            }
        )
    return {"league_id": league_id, "teams": teams}


def build_power_rankings_week1(league_id: str, season: int, users: List[dict], rosters: List[dict]) -> dict:
    # Placeholder: alphabetical by team_name
    teams_info = []
    owner_to_roster: Dict[str, int] = {str(r.get("owner_id") or ""): r.get("roster_id") for r in rosters}
    for u in users:
        team_name = preferred_team_name(u)
        owner_id = str(u.get("user_id") or "")
        roster_id = owner_to_roster.get(owner_id)
        if roster_id is None:
            continue
        teams_info.append((team_name, roster_id))
    teams_info.sort(key=lambda t: (t[0] or ""))

    rankings = []
    for idx, (team_name, roster_id) in enumerate(teams_info, start=1):
        rankings.append({"roster_id": roster_id, "team_name": team_name, "rank": idx})

    return {"league_id": league_id, "season": season, "week": 1, "rankings": rankings}


def build_matchups_week1(league_id: str, season: int, users: List[dict], rosters: List[dict]) -> dict:
    # Try to fetch from Sleeper; if empty, pair sequentially by roster_id
    owner_to_team_name: Dict[str, str] = {str(u.get("user_id") or ""): preferred_team_name(u) for u in users}
    roster_id_to_team_name: Dict[int, str] = {}
    for r in rosters:
        owner_id = str(r.get("owner_id") or "")
        roster_id = r.get("roster_id")
        roster_id_to_team_name[roster_id] = owner_to_team_name.get(owner_id, f"Team {roster_id}")

    matchups = get_matchups(league_id, 1)
    pairs: List[Tuple[int, int]] = []
    if matchups:
        # Sleeper returns list of matchup entries; group by matchup_id
        by_mid: Dict[int, List[dict]] = {}
        for m in matchups:
            mid = m.get("matchup_id")
            if mid is None:
                continue
            by_mid.setdefault(mid, []).append(m)
        for mid, entries in by_mid.items():
            teams = [e.get("roster_id") for e in entries if e.get("roster_id") is not None]
            if len(teams) >= 2:
                pairs.append((teams[0], teams[1]))
    if not pairs:
        # Fallback: sequential pairing by sorted roster_id
        roster_ids = sorted([int(r.get("roster_id")) for r in rosters if r.get("roster_id") is not None])
        for i in range(0, len(roster_ids), 2):
            if i + 1 < len(roster_ids):
                pairs.append((roster_ids[i], roster_ids[i + 1]))

    matchups_out: List[dict] = []
    for home_id, away_id in pairs:
        matchups_out.append(
            {
                "home_roster_id": home_id,
                "away_roster_id": away_id,
                "home_team_name": roster_id_to_team_name.get(home_id, f"Team {home_id}"),
                "away_team_name": roster_id_to_team_name.get(away_id, f"Team {away_id}"),
                "prediction": None,
            }
        )

    return {"league_id": league_id, "season": season, "week": 1, "matchups": matchups_out}


def write_json(path: Path, obj: dict) -> None:
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build site data JSON under docs/data")
    parser.add_argument("--league-id", default="1248075580834856960")
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--docs-dir", default=str(Path.cwd() / "docs"))
    args = parser.parse_args(argv)

    league_id = str(args.league_id)
    season = int(args.season)
    docs_dir = Path(args.docs_dir)
    data_dir = docs_dir / "data"

    users = get_league_users(league_id)
    rosters = get_league_rosters(league_id)
    _players = get_players_nfl()  # reserved for future use

    teams = build_teams_json(league_id, users, rosters)
    power_rankings_w1 = build_power_rankings_week1(league_id, season, users, rosters)
    matchups_w1 = build_matchups_week1(league_id, season, users, rosters)

    write_json(data_dir / "teams.json", teams)
    write_json(data_dir / f"{season}/week1/power_rankings.json", power_rankings_w1)
    write_json(data_dir / f"{season}/week1/matchups.json", matchups_w1)

    print(f"Wrote: {data_dir / 'teams.json'}")
    print(f"Wrote: {data_dir / f'{season}/week1/power_rankings.json'}")
    print(f"Wrote: {data_dir / f'{season}/week1/matchups.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


