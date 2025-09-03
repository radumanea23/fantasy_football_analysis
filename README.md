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

### Weekly Data Build and History

Build or update a specific week (stores history at `docs/data/2025/history.json`):

```bash
source .venv/bin/activate
python scripts/build_site_data.py --league-id 1248075580834856960 --season 2025 --week 1 --docs-dir ./docs
```

### Generate GPT-based Power Rankings & Analysis (optional)

Set your OpenAI key and run the generator. This writes to `docs/data/<season>/week<week>/power_rankings.json` with `summary` and `analysis` fields per team.

```bash
echo 'OPENAI_API_KEY=sk-...' > .env  # recommended; .env is gitignored
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_power_rankings.py --league-id 1248075580834856960 --season 2025 --week 1 --docs-dir ./docs --model gpt-4o-mini
```

If you want web-enriched analysis (latest injuries/usage), pass `--enable-web` with a model that supports the web_search tool (e.g., vendor/model permitting). The script will attempt to use the Responses API with the tool.

