#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Dict, List, Optional

from dotenv import load_dotenv

try:
	from openai import OpenAI  # type: ignore
except Exception:
	OpenAI = None  # type: ignore

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
	sys.path.insert(0, str(PROJECT_ROOT))

from sleeper_client import (
	get_league_users,
	get_league_rosters,
	get_players_nfl,
	get_matchups,
	preferred_team_name,
)


SYSTEM_PROMPT = (
	"You are an elite but spicy fantasy football analyst. Given weekly matchups, team names, ranks, and rosters, "
	"predict winners with reasoning and pick one 'Spicy matchup of the week' that could deliver an upset. "
	"Be concise, realistic, and add lighthearted jabs.")

USER_TEMPLATE = (
	"SEASON {season} • WEEK {week}\n"
	"FORMAT strictly JSON as: {{\"predictions\":[{{\"home_roster_id\":...,\"away_roster_id\":...,\"predicted_winner_roster_id\":...,\"reasoning\":...}}],\"spicy_matchup\":{{\"home_roster_id\":...,\"away_roster_id\":...,\"why\":...}}}}\n\n"
	"RANKS (lower is better):\n{ranks}\n\n"
	"MATCHUPS:\n{matchups}\n\n"
	"ROSTERS (roster_id -> starters then notable bench):\n{rosters}\n\n"
	"Guidelines: Favor better rank but allow upsets; include a clear, punchy reasoning per matchup; choose one spicy matchup with an underdog case and explain why."
)


def build_avatar_map(users: List[dict]) -> Dict[int, str]:
	avatars: Dict[int, str] = {}
	for u in users:
		avatar = u.get("avatar") or ""
		owner_id = str(u.get("user_id") or "")
		if not avatar:
			continue
		# We'll map via owner id -> roster id later
		u["_avatar_url"] = f"https://sleepercdn.com/avatars/{avatar}"
	return avatars


def map_team_info(users: List[dict], rosters: List[dict], ranks_by_roster: Dict[int, int]) -> Dict[int, dict]:
	owner_to_roster = {str(r.get("owner_id") or ""): int(r.get("roster_id")) for r in rosters}
	info: Dict[int, dict] = {}
	for u in users:
		owner_id = str(u.get("user_id") or "")
		roster_id = owner_to_roster.get(owner_id)
		if roster_id is None:
			continue
		avatar = u.get("avatar") or ""
		avatar_url = f"https://sleepercdn.com/avatars/{avatar}" if avatar else ""
		info[roster_id] = {
			"team_name": preferred_team_name(u),
			"avatar_url": avatar_url,
			"rank": ranks_by_roster.get(roster_id),
		}
	return info


def summarize_rosters(rosters: List[dict], players: Dict[str, dict]) -> Dict[int, List[str]]:
	by_id: Dict[int, List[str]] = {}
	for r in rosters:
		rid = int(r.get("roster_id"))
		starters = r.get("starters") or []
		bench = [p for p in (r.get("players") or []) if p not in starters]
		entries: List[str] = []
		for pid in starters[:10]:
			p = players.get(str(pid)) or {}
			name = p.get("full_name") or p.get("first_name") or p.get("last_name") or str(pid)
			pos = p.get("position") or ""
			nfl = p.get("team") or ""
			entries.append(f"STARTER: {name} ({pos}-{nfl})")
		for pid in bench[:6]:
			p = players.get(str(pid)) or {}
			name = p.get("full_name") or p.get("first_name") or p.get("last_name") or str(pid)
			pos = p.get("position") or ""
			nfl = p.get("team") or ""
			entries.append(f"BENCH: {name} ({pos}-{nfl})")
		by_id[rid] = entries
	return by_id


def call_openai(model: str, api_key: str, system_prompt: str, user_prompt: str) -> dict:
	if OpenAI is None:
		raise RuntimeError("openai package not installed. Add to requirements.txt and set OPENAI_API_KEY.")
	client = OpenAI(api_key=api_key)
	resp = client.chat.completions.create(
		model=model,
		messages=[
			{"role": "system", "content": system_prompt},
			{"role": "user", "content": user_prompt},
		],
		response_format={"type": "json_object"},
		temperature=0.9,
	)
	content = resp.choices[0].message.content or "{}"
	return json.loads(content)


def main(argv: Optional[List[str]] = None) -> int:
	parser = argparse.ArgumentParser(description="Generate weekly matchup predictions via OpenAI (JSON)")
	parser.add_argument("--league-id", default="1248075580834856960")
	parser.add_argument("--season", type=int, default=2025)
	parser.add_argument("--week", type=int, default=1)
	parser.add_argument("--docs-dir", default=str(Path.cwd() / "docs"))
	parser.add_argument("--model", default="gpt-4o-mini")
	args = parser.parse_args(argv)

	load_dotenv()
	api_key = os.getenv("OPENAI_API_KEY")
	if not api_key:
		print("Missing OPENAI_API_KEY environment variable.")
		return 2

	league_id = str(args.league_id)
	season = int(args.season)
	week = int(args.week)
	data_dir = Path(args.docs_dir) / "data"

	users = get_league_users(league_id)
	rosters = get_league_rosters(league_id)
	players = get_players_nfl()
	matchups = get_matchups(league_id, week)

	# Load ranks from power rankings JSON if available
	pr_path = data_dir / f"{season}/week{week}/power_rankings.json"
	ranks_by_roster: Dict[int, int] = {}
	if pr_path.exists():
		pr = json.loads(pr_path.read_text(encoding="utf-8"))
		for entry in pr.get("rankings", []):
			rid = int(entry.get("roster_id"))
			ranks_by_roster[rid] = int(entry.get("rank"))

	team_info = map_team_info(users, rosters, ranks_by_roster)
	roster_summaries = summarize_rosters(rosters, players)

	# Build structured lines for prompt
	ranks_lines = []
	for rid, info in sorted(team_info.items(), key=lambda kv: (kv[1].get("rank") or 999)):
		ranks_lines.append(f"roster_id={rid}: rank={info.get('rank')} team={info.get('team_name')}")
	ranks_text = "\n".join(ranks_lines)

	match_lines = []
	if matchups:
		from collections import defaultdict
		by_mid = defaultdict(list)
		for m in matchups:
			by_mid[m.get("matchup_id")].append(m)
		for mid, entries in by_mid.items():
			ids = [int(e.get("roster_id")) for e in entries if e.get("roster_id") is not None]
			if len(ids) >= 2:
				A, B = ids[0], ids[1]
				ai = team_info.get(A, {"team_name": f"Team {A}"})
				bi = team_info.get(B, {"team_name": f"Team {B}"})
				match_lines.append(f"{A} ({ai.get('team_name')}) vs {B} ({bi.get('team_name')})")
	else:
		# fallback: pair by roster_id sequentially
		rids = sorted(team_info.keys())
		for i in range(0, len(rids), 2):
			if i + 1 < len(rids):
				A, B = rids[i], rids[i + 1]
				ai = team_info.get(A, {})
				bi = team_info.get(B, {})
				match_lines.append(f"{A} ({ai.get('team_name')}) vs {B} ({bi.get('team_name')})")
	match_text = "\n".join(match_lines)

	rosters_lines = []
	for rid, lines in roster_summaries.items():
		rosters_lines.append(f"roster_id={rid}: "+ ", ".join(lines))
	rosters_text = "\n".join(rosters_lines[:24])  # trim

	user_prompt = USER_TEMPLATE.format(
		season=season,
		week=week,
		ranks=ranks_text,
		matchups=match_text,
		rosters=rosters_text,
	)

	result = call_openai(args.model, api_key, SYSTEM_PROMPT, user_prompt)

	# Persist predictions JSON
	out_path = data_dir / f"{season}/week{week}/matchup_predictions.json"
	out_path.parent.mkdir(parents=True, exist_ok=True)
	with out_path.open("w", encoding="utf-8") as f:
		json.dump({"league_id": league_id, "season": season, "week": week, **result}, f, indent=2)
	print(f"Wrote: {out_path}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())


