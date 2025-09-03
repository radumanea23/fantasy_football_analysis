## Fantasy Football Site for the fellas

Static site hosted via GitHub Pages with weekly power rankings, matchup predictions, and an analytics chart. Data comes from the Sleeper API and optional GPT generation.

### GitHub Pages Site

This repo contains a static site in `docs/` that GitHub Pages can host.

- Pages:
  - `docs/power-rankings.html` – sleek, expandable cards with team avatar, rank, summary, analysis (key players, bench potential, make-or-break), source links, and mobile-first UX with light/dark theme toggle
  - `docs/matchups.html` – GPT matchup predictions with avatars, winner, reasoning, and a “🌶️ Spicy Matchup of the Week” highlight
  - `docs/analytics.html` – scatter chart showing rank-over-time (x=week, y=rank), reading from season history
- Data JSON in `docs/data/...` built by scripts (see below)

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

### Sleeper CSV Export (optional)

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

### Generate GPT-based Matchup Predictions (optional)

Writes to `docs/data/<season>/week<week>/matchup_predictions.json` with `predictions` and `spicy_matchup`:

```bash
source .venv/bin/activate
python scripts/generate_matchup_predictions.py --league-id 1248075580834856960 --season 2025 --week 1 --docs-dir ./docs --model gpt-4o-mini
```

Each prediction includes:
- `home_roster_id`, `away_roster_id`
- `predicted_winner_roster_id`
- `reasoning`
- Spicy highlight: `spicy_matchup` with `{ home_roster_id, away_roster_id, why }`

### Theming and Mobile UX

- Light/dark theme toggle (☀️/🌙) persisted in localStorage
- Mobile-friendly layouts with responsive typography, wrapped content, and smooth card expand/collapse animations
- Footer with links to Dom’s huddle highlights and this GitHub repo

### Repo Structure

```
docs/
  analytics.html            # Rank-over-time chart (reads history.json)
  matchups.html             # Matchup predictions UI (avatars, winner, reasoning, spicy)
  power-rankings.html       # Power rankings UI (expandable analysis, source links)
  styles.css                # Theme + responsive styles
  data/
    2025/
      history.json          # Season rank history (weeks → [{roster_id, team_name, rank}])
      week1/
        power_rankings.json # Per-team {rank, summary, analysis{...}, optional sources}
        matchup_predictions.json
        matchups.json       # Raw Sleeper pairings (fallback)

scripts/
  build_site_data.py        # Fetch users/rosters/matchups, write teams.json and baseline week files, update history
  generate_power_rankings.py# GPT power rankings + analysis (supports --enable-web)
  generate_matchup_predictions.py # GPT matchup predictions (spicy highlight)
  update_history.py         # Update history.json from a generated week file

sleeper_client.py           # Sleeper API helpers
sleeper_export.py           # CSV exporter for rosters/teams
```

### GitHub Pages Deployment

1. Push to GitHub
2. Settings → Pages → Deploy from a branch → `master` → `/docs`
3. Visit your site after deploy completes

### Automation (optional)

Use GitHub Actions to run weekly and push new JSON to `docs/data`. Configure a repo secret `OPENAI_API_KEY`.

Example workflow (pseudo):
```yaml
name: Weekly Data Refresh
on:
  schedule:
    - cron: '0 13 * * 2' # Tuesdays 13:00 UTC
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt
      - env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python scripts/generate_power_rankings.py --league-id 1248075580834856960 --season 2025 --week $WEEK --docs-dir ./docs --model gpt-4o-mini
          python scripts/update_history.py --season 2025 --week $WEEK --docs-dir ./docs
          python scripts/generate_matchup_predictions.py --league-id 1248075580834856960 --season 2025 --week $WEEK --docs-dir ./docs --model gpt-4o-mini
      - run: |
          git config user.name github-actions
          git config user.email actions@github.com
          git add docs/data
          git commit -m "Week $WEEK data refresh" || echo "No changes"
          git push
```

### Security Notes

- Keep secrets out of the repo. `.env` is gitignored; scripts load `OPENAI_API_KEY` from environment.
- The site is static; no backend is required for hosting on GitHub Pages.

