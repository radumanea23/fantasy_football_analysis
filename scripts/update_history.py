#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional, Dict, List

# Ensure project root on path
import sys
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sleeper_client import get_league_rosters, get_players_nfl


def ensure_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Update season history.json from an existing week power_rankings.json, and write standings/rosters snapshots")
    parser.add_argument("--docs-dir", default=str(Path.cwd() / "docs"))
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    args = parser.parse_args(argv)

    data_dir = Path(args.docs_dir) / "data"
    week_path = data_dir / f"{args.season}/week{args.week}/power_rankings.json"
    history_path = data_dir / f"{args.season}/history.json"
    standings_path = data_dir / f"{args.season}/standings.json"
    rosters_min_path = data_dir / f"{args.season}/rosters_min.json"

    if not week_path.exists():
        print(f"Week file not found: {week_path}")
        return 1

    with week_path.open("r", encoding="utf-8") as f:
        week_data = json.load(f)
    league_id = str(week_data.get("league_id"))

    rankings = week_data.get("rankings", [])
    history = {"season": args.season, "weeks": {}}
    if history_path.exists():
        try:
            with history_path.open("r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass

    history.setdefault("weeks", {})[str(args.week)] = [
        {"roster_id": r.get("roster_id"), "team_name": r.get("team_name"), "rank": r.get("rank")}
        for r in rankings
    ]

    ensure_dir(history_path)
    with history_path.open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
    print(f"Updated: {history_path}")

    # Build standings from Sleeper rosters
    try:
        rosters = get_league_rosters(league_id)
    except Exception:
        rosters = []
    standings: List[dict] = []
    for r in rosters:
        rid = r.get("roster_id")
        s = r.get("settings") or {}
        wins = int(s.get("wins") or 0)
        losses = int(s.get("losses") or 0)
        ties = int(s.get("ties") or 0)
        pf = float(s.get("fpts") or 0)
        pa = float(s.get("fpts_against") or 0)
        standings.append({
            "roster_id": rid,
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "pf": pf,
            "pa": pa,
        })
    if standings:
        ensure_dir(standings_path)
        with standings_path.open("w", encoding="utf-8") as f:
            json.dump({"season": args.season, "standings": standings}, f, indent=2)
        print(f"Wrote: {standings_path}")

    # Build minimal rosters (starters + bench top few) for UI enrichment
    try:
        players = get_players_nfl()
    except Exception:
        players = {}
    rosters_min: List[dict] = []
    for r in rosters:
        rid = r.get("roster_id")
        starters = r.get("starters") or []
        starter_objs = []
        for pid in starters:
            p = players.get(str(pid)) or {}
            starter_objs.append({
                "player_id": str(pid),
                "name": p.get("full_name") or p.get("first_name") or p.get("last_name") or str(pid),
                "position": p.get("position") or "",
                "nfl_team": p.get("team") or "",
            })
        rosters_min.append({"roster_id": rid, "starters": starter_objs})
    if rosters_min:
        ensure_dir(rosters_min_path)
        with rosters_min_path.open("w", encoding="utf-8") as f:
            json.dump({"season": args.season, "rosters": rosters_min}, f, indent=2)
        print(f"Wrote: {rosters_min_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


