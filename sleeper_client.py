from __future__ import annotations

import requests

SLEEPER_API_BASE = "https://api.sleeper.app/v1"


def http_get_json(url: str) -> object:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def get_league_users(league_id: str):
    url = f"{SLEEPER_API_BASE}/league/{league_id}/users"
    data = http_get_json(url)
    if not isinstance(data, list):
        raise RuntimeError("Unexpected users response from Sleeper API")
    return data


def get_league_rosters(league_id: str):
    url = f"{SLEEPER_API_BASE}/league/{league_id}/rosters"
    data = http_get_json(url)
    if not isinstance(data, list):
        raise RuntimeError("Unexpected rosters response from Sleeper API")
    return data


def get_players_nfl():
    url = f"{SLEEPER_API_BASE}/players/nfl"
    data = http_get_json(url)
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected players response from Sleeper API")
    return data  # type: ignore[return-value]


def get_matchups(league_id: str, week: int):
    url = f"{SLEEPER_API_BASE}/league/{league_id}/matchups/{week}"
    data = http_get_json(url)
    if not isinstance(data, list):
        # If the season hasn't started, Sleeper may return [] or an empty object
        return []
    return data


def get_projections_nfl(season: int, week: int, position: str | None = None, season_type: str = "regular"):
    """Fetch Sleeper projections for a given season/week.

    Sleeper groups by position; we'll optionally pass position (e.g., QB, RB, WR, TE, K, DEF).
    """
    query = []
    if position:
        query.append(f"position={position}")
    if season_type:
        query.append(f"season_type={season_type}")
    qs = ("?" + "&".join(query)) if query else ""
    url = f"{SLEEPER_API_BASE}/projections/nfl/{season}/{week}{qs}"
    data = http_get_json(url)
    if not isinstance(data, list):
        return []
    return data


def build_player_headshot_url(player_id: str) -> str:
    # Sleeper CDN headshots; if missing the image tag will hide via onerror
    return f"https://sleepercdn.com/content/nfl/players/thumb/{player_id}.jpg"


def get_state_nfl() -> dict:
    url = f"{SLEEPER_API_BASE}/state/nfl"
    data = http_get_json(url)
    if not isinstance(data, dict):
        return {}
    return data


def build_user_maps(users):
    user_id_to_user = {}
    display_name_to_user = {}
    for u in users:
        user_id = str(u.get("user_id", ""))
        if user_id:
            user_id_to_user[user_id] = u
        display_name = str(u.get("display_name") or "")
        if display_name:
            display_name_to_user[display_name] = u
    return user_id_to_user, display_name_to_user


def preferred_team_name(user: dict) -> str:
    metadata = user.get("metadata") or {}
    team_name = metadata.get("team_name") if isinstance(metadata, dict) else None
    display_name = user.get("display_name")
    return str(team_name or display_name or user.get("username") or "Unknown Team")


