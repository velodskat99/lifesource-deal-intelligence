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
HOST=127.0.0.1
PORT=8000
LIFESOURCE_ACCESS_PIN=
```

## Run

```bash
python -m lifesource
```

Open `http://localhost:8000`.

## Phone App Mode

LifeSource can run like a local phone app as a Progressive Web App (PWA).
Your Mac hosts the app, and your phone opens it over the same Wi-Fi network.

1. Set a local access PIN and allow LAN connections:

```bash
HOST=0.0.0.0
LIFESOURCE_ACCESS_PIN=choose-a-private-pin
```

2. Start LifeSource on your Mac:

```bash
python -m lifesource
```

3. Find your Mac's local IP address:

```bash
ipconfig getifaddr en0
```

4. On your phone, open `http://<your-mac-ip>:8000`, enter the PIN, then use
   **Add to Home Screen** from the browser share menu.

Keep `HOST=127.0.0.1` when you only want access from the Mac itself.

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
