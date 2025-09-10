#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import re
from pathlib import Path
import sys
from typing import Dict, List, Tuple

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sleeper_client import get_players_nfl


FP_BASE = "https://www.fantasypros.com/nfl/projections"


def fetch_fp_csv(position: str, week: int, scoring: str = "PPR") -> List[Dict[str, str]]:
    pos_map = {
        "QB": "qb",
        "RB": "rb",
        "WR": "wr",
        "TE": "te",
        "K": "k",
        "DST": "dst",
        "DEF": "dst",
    }
    key = pos_map.get(position.upper(), position.lower())
    url = f"{FP_BASE}/{key}.php?week={week}&scoring={scoring}&csv=1"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    content = resp.content.decode("utf-8", errors="ignore")
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def normalize_name(name: str) -> str:
    n = name.lower()
    n = re.sub(r"[^a-z0-9\s]", "", n)
    n = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def build_player_index(players: Dict[str, dict]) -> Dict[Tuple[str, str], str]:
    index: Dict[Tuple[str, str], str] = {}
    for pid, p in players.items():
        fullname = p.get("full_name") or ""
        team = (p.get("team") or "").upper()
        key = (normalize_name(fullname), team)
        if fullname:
            index[key] = pid
        # Some players may have last_name, first_name only
        if not fullname and p.get("first_name") and p.get("last_name"):
            alt = f"{p.get('first_name')} {p.get('last_name')}"
            index[(normalize_name(alt), team)] = pid
    return index


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fetch FantasyPros projections and write projections.json")
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--week", type=int, default=1)
    parser.add_argument("--docs-dir", default=str(Path.cwd() / "docs"))
    parser.add_argument("--scoring", default="PPR")
    args = parser.parse_args(argv)

    week = int(args.week)
    docs_dir = Path(args.docs_dir)
    out_path = docs_dir / f"data/{args.season}/week{week}/projections.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    players = get_players_nfl()
    idx = build_player_index(players)

    projections: List[dict] = []
    for pos in ["QB", "RB", "WR", "TE", "K", "DST"]:
        try:
            rows = fetch_fp_csv(pos, week, args.scoring)
        except Exception:
            rows = []
        for r in rows:
            name = (r.get("Player") or r.get("PLAYER") or "").strip()
            team = (r.get("Team") or r.get("TEAM") or "").upper().strip()
            pts = r.get("FPTS") or r.get("FPTS.") or r.get("Points") or "0"
            try:
                points = float(pts)
            except Exception:
                points = 0.0
            pid = idx.get((normalize_name(name), team))
            if not pid and team == "":
                # Try any team match for ambiguous entries
                for (nkey, tkey), cand in idx.items():
                    if nkey == normalize_name(name):
                        pid = cand
                        break
            if pid:
                projections.append({
                    "player_id": str(pid),
                    "position": pos,
                    "points": round(points, 2),
                })

    with out_path.open("w", encoding="utf-8") as f:
        json.dump({"season": int(args.season), "week": week, "projections": projections}, f, indent=2)
    print(f"Wrote: {out_path} ({len(projections)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



