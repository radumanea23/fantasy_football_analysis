## Fantasy Football Sleeper Exporter

Export your Sleeper league teams and rosters to CSV.

### GitHub Pages Site

This repo contains a static site in `docs/` that GitHub Pages can host.

- Pages: `docs/power-rankings.html`, `docs/matchups.html`, `docs/analytics.html`
- Data JSON: `docs/data/...` built by `scripts/build_site_data.py`

#### Build site data

```bash
source .venv/bin/activate
python scripts/build_site_data.py --league-id 1248075580834856960 --season 2025 --docs-dir ./docs
```

#### Enable GitHub Pages

1. Push this repo to GitHub.
2. In repo Settings → Pages: Source = “Deploy from a branch”, Branch = `main` (or `master`), Folder = `/docs`.
3. Visit the provided URL once deployed.

### Setup

1. Create a virtual environment (optional but recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

### Usage

Default league ID is set to `1248075580834856960`.

```bash
python sleeper_export.py --out-dir ./data
```

Or specify a different league ID:

```bash
python sleeper_export.py --league-id YOUR_LEAGUE_ID --out-dir ./data
```

This will write two files:

- `./data/<LEAGUE_ID>_rosters.csv` – one row per player on a roster
- `./data/<LEAGUE_ID>_teams.csv` – one row per team/owner

### Notes

- The script fetches `players/nfl` once per run to map player IDs to names/positions.
- `is_starter` marks whether the player is currently in a starting slot according to Sleeper.

