#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from typing import Dict, List, Optional

import requests
from dotenv import load_dotenv

# Optional: use OPENAI SDK if available
try:
	from openai import OpenAI  # type: ignore
except Exception:
	OpenAI = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sleeper_client import (
	get_league_users,
	get_league_rosters,
	get_players_nfl,
	preferred_team_name,
)

SYSTEM_PROMPT = (
	"You are an expert fantasy football analyst. Given Sleeper rosters and standings, "
	"produce JSON ranking output for the week with: rankings: [ { team_name, roster_id, rank, summary, analysis: { key_players: [ {name, note}... ], bench_potential, make_or_break } }... ]. "
	"Use web search to get the current NFL context (injuries, depth charts, trending players- this is super important). Also make sure you are looking at rookie rankings so that you don't hype up bad rookies. Keep summaries somewhat concise. Add in comedic roasts throughout analysis such as lmao why would you pick this player type of things. Do not include links to sources."
)

USER_TEMPLATE = (
	"League Context: This league is a dynasty league so rookies, age matters. It is also a full PPR league with a super flex spot so QB depth also matters- but you can only start 2 QBS.\n"
	"Season: {season} Week: {week}\n"
	"Teams (owner display/team name):\n{teams}\n\n"
	"ROSTERS (roster_id -> players list with position/team):\n{rosters}\n\n"
	"STANDINGS: All teams are 0-0 to start.\n\n"
	"Write only JSON with this shape: {{\"rankings\":[{{\"team_name\":...,\"roster_id\":...,\"rank\":1,\"summary\":...,\"analysis\":{{\"key_players\":[{{\"name\":...,\"note\":...}}],\"bench_potential\":...,\"make_or_break\":...}}}}...]}}"
)


def build_team_lists(users: List[dict], rosters: List[dict], players: Dict[str, dict]) -> Dict[str, List[str]]:
	# Map roster_id -> ["Name (POS - NFL)"...]
	roster_players: Dict[str, List[str]] = {}
	for r in rosters:
		roster_id = str(r.get("roster_id"))
		player_ids = r.get("players") or []
		entries: List[str] = []
		for pid in player_ids:
			p = players.get(str(pid)) or {}
			name = p.get("full_name") or p.get("first_name") or p.get("last_name") or str(pid)
			pos = p.get("position") or ""
			nfl = p.get("team") or ""
			entries.append(f"{name} ({pos} - {nfl})")
		roster_players[roster_id] = entries
	return roster_players


def format_users(users: List[dict], rosters: List[dict]) -> str:
	owner_to_roster = {str(r.get("owner_id") or ""): r.get("roster_id") for r in rosters}
	lines = []
	for u in users:
		owner_id = str(u.get("user_id") or "")
		roster_id = owner_to_roster.get(owner_id)
		if roster_id is None:
			continue
		display = u.get("display_name") or ""
		team = preferred_team_name(u)
		lines.append(f"- roster_id={roster_id}: {display} / {team}")
	return "\n".join(lines)


def call_openai(model: str, api_key: str, system_prompt: str, user_prompt: str, enable_web: bool = False) -> dict:
	if OpenAI is None:
		raise RuntimeError("openai package not installed. Add to requirements.txt and set OPENAI_API_KEY.")
	client = OpenAI(api_key=api_key)
	if enable_web:
		# Use Responses API. Embed system guidance into the input and instruct strict JSON output.
		resp = client.responses.create(
			model=model,
			tools=[{"type": "web_search"}],
			input=(
				f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\n"
				f"USER INPUT:\n{user_prompt}\n\n"
				"Return only valid JSON with the described schema, no extra text."
			),
		)
		content = getattr(resp, "output_text", None) or "{}"
	else:
		resp = client.chat.completions.create(
			model=model,
			messages=[
				{"role": "system", "content": system_prompt},
				{"role": "user", "content": user_prompt},
			],
			response_format={"type": "json_object"},
			temperature=0.7,
		)
		content = resp.choices[0].message.content or "{}"
	return json.loads(content)


def main(argv: Optional[List[str]] = None) -> int:
	parser = argparse.ArgumentParser(description="Generate weekly power rankings and analysis via OpenAI")
	parser.add_argument("--league-id", default="1248075580834856960")
	parser.add_argument("--season", type=int, default=2025)
	parser.add_argument("--week", type=int, default=1)
	parser.add_argument("--docs-dir", default=str(Path.cwd() / "docs"))
	parser.add_argument("--model", default="gpt-4o-mini")
	parser.add_argument("--enable-web", action="store_true", help="Enable web search tool if model supports it")
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

	teams_str = format_users(users, rosters)
	rosters_map = build_team_lists(users, rosters, players)
	rosters_str = "\n".join([f"- roster_id={rid}: {', '.join(players)}" for rid, players in rosters_map.items()])

	user_prompt = USER_TEMPLATE.format(season=season, week=week, teams=teams_str, rosters=rosters_str)
	try:
		result = call_openai(args.model, api_key, SYSTEM_PROMPT, user_prompt, enable_web=args.enable_web)
	except Exception as e:
		print(f"Warning: primary model/tool failed ({e}). Falling back to non-web gpt-4o-mini.")
		result = call_openai("gpt-4o-mini", api_key, SYSTEM_PROMPT, user_prompt, enable_web=False)

	# Expect result["rankings"] structure
	out_path = data_dir / f"{season}/week{week}/power_rankings.json"
	out_path.parent.mkdir(parents=True, exist_ok=True)
	with out_path.open("w", encoding="utf-8") as f:
		json.dump({"league_id": league_id, "season": season, "week": week, "rankings": result.get("rankings", [])}, f, indent=2)
	print(f"Wrote: {out_path}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
