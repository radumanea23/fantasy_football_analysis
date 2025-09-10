#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sleeper_client import get_projections_nfl, get_state_nfl


def normalize_projection(entry: dict) -> dict:
    player_id = str(entry.get("player_id") or entry.get("player"))
    stats = entry.get("stats") or {}
    # Sleeper sometimes places fantasy point totals at root-level fields
    points = (
        stats.get("pts_ppr")
        or entry.get("pts_ppr")
        or stats.get("pts_half_ppr")
        or entry.get("pts_half_ppr")
        or stats.get("pts_std")
        or entry.get("pts_std")
        or entry.get("fantasy_points")
        or 0
    )
    position = entry.get("position") or (entry.get("player") and entry.get("player").get("position")) or ""
    return {
        "player_id": player_id,
        "position": position,
        "points": float(points or 0),
    }


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch Sleeper projections and write projections.json")
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--week", type=int, default=1)
    parser.add_argument("--docs-dir", default=str(Path.cwd() / "docs"))
    parser.add_argument("--season-type", default="")
    args = parser.parse_args(argv)

    season = int(args.season)
    week = int(args.week)
    season_type = str(args.season_type)
    if not season_type:
        state = get_state_nfl() or {}
        season_type = state.get("season_type") or "regular"
    docs_dir = Path(args.docs_dir)
    out_path = docs_dir / f"data/{season}/week{week}/projections.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    projections: List[dict] = []
    for pos in ["QB", "RB", "WR", "TE", "K", "DEF"]:
        try:
            data = get_projections_nfl(season, week, pos, season_type=season_type)
        except Exception:
            data = []
        for e in data:
            proj = normalize_projection(e)
            if proj.get("player_id"):
                projections.append(proj)

    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"season": season, "week": week, "projections": projections}, f, indent=2)
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


