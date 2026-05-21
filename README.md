# LifeSource

LifeSource is a local-first deal intelligence app for grocery discounts, gas prices,
purchase tracking, and morning digest notifications. It runs a FastAPI server with
Jinja templates, stores data in SQLite, and can send outbound Telegram summaries.

## Public Safety

This repository is intended to be safe to publish. Real runtime data and secrets
belong only in local ignored files:

- `.env`
- `*.db`
- `backups/`
- `logs/`
- `.venv/`
- scraper caches and test caches

Use `.env.example` as the template for local credentials.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Fill in `.env`:

```bash
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
ANTHROPIC_API_KEY=
```

## Run

```bash
python -m lifesource.server
```

Open `http://localhost:8000`.

Run the daily scrape/digest job:

```bash
python -m lifesource.daily
```

## macOS launchd

The tracked plist files are templates and intentionally use `__PROJECT_DIR__`
instead of a personal machine path. Install local LaunchAgents with:

```bash
bash scripts/install-launchd.sh
```

The installer renders the templates into `~/Library/LaunchAgents` using the
absolute path of your checkout.

## Tests

```bash
python3 -m pytest
```
