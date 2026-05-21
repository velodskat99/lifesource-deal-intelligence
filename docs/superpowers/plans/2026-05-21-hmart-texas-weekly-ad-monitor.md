# H Mart Texas Weekly Ad Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first reliable H Mart Texas weekly-ad automation slice: detect weekly-ad refreshes, store source fingerprints, format Telegram alerts, and produce a weekly planning summary fallback.

**Architecture:** Add a focused source snapshot repository around SQLite, a H Mart Texas weekly-ad source checker that fingerprints the page/assets, and notification formatting helpers that can be called by small job functions. Keep item extraction conservative: only weekly-ad source data is eligible for H Mart deal/planning notifications.

**Tech Stack:** Python 3.11, FastAPI app codebase, SQLite, httpx, BeautifulSoup, pytest.

---

### Task 1: Source Snapshot Storage

**Files:**
- Modify: `lifesource/db.py`
- Create: `lifesource/sources/__init__.py`
- Create: `lifesource/sources/snapshots.py`
- Test: `tests/test_source_snapshots.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_source_snapshots.py` with tests that initialize a temp DB, upsert a new snapshot, confirm first-seen changed detection, upsert the same fingerprint, and confirm unchanged detection.

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/python -m pytest tests/test_source_snapshots.py -v`

Expected: FAIL because `lifesource.sources.snapshots` does not exist.

- [ ] **Step 3: Implement minimal storage**

Add `source_snapshots` to the schema and implement `record_source_snapshot(db_path, snapshot)` returning a result object with `changed`, `previous_fingerprint`, and `current_fingerprint`.

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/python -m pytest tests/test_source_snapshots.py -v`

Expected: PASS.

### Task 2: H Mart Texas Weekly-Ad Source Checker

**Files:**
- Create: `lifesource/sources/hmart_weekly.py`
- Test: `tests/test_hmart_weekly_source.py`

- [ ] **Step 1: Write failing tests**

Create fixture-style tests for fingerprinting HTML with weekly-ad asset links and for falling back to raw HTML when no assets are found.

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/python -m pytest tests/test_hmart_weekly_source.py -v`

Expected: FAIL because `lifesource.sources.hmart_weekly` does not exist.

- [ ] **Step 3: Implement minimal source checker**

Implement `HmartTexasWeeklyAdSource` with `source_url`, `fetch_html()`, `inspect_html(html)`, `fingerprint(parts)`, and `check()` methods. Extract candidate weekly-ad asset URLs from anchor/image/script/source tags and JSON-ish text.

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/python -m pytest tests/test_hmart_weekly_source.py -v`

Expected: PASS.

### Task 3: H Mart Alert and Weekly Planning Formatting

**Files:**
- Create: `lifesource/notifications/hmart_weekly.py`
- Test: `tests/test_hmart_weekly_notifications.py`

- [ ] **Step 1: Write failing tests**

Test refresh alert text for changed source with highlights and weekly digest text when there are no parsed deals yet.

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/python -m pytest tests/test_hmart_weekly_notifications.py -v`

Expected: FAIL because the notification module does not exist.

- [ ] **Step 3: Implement minimal formatting**

Implement `format_hmart_refresh_alert()` and `format_hmart_weekly_planning_digest()`. Both must include the H Mart Texas source URL and never imply catalog rows are deals.

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/python -m pytest tests/test_hmart_weekly_notifications.py -v`

Expected: PASS.

### Task 4: Monitor Jobs

**Files:**
- Create: `lifesource/daily/hmart_weekly.py`
- Test: `tests/test_hmart_weekly_jobs.py`

- [ ] **Step 1: Write failing tests**

Test that the monitor sends an alert when the fingerprint changes, sends nothing when unchanged, and that the weekly digest sends even when unchanged.

- [ ] **Step 2: Run test to verify it fails**

Run: `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/python -m pytest tests/test_hmart_weekly_jobs.py -v`

Expected: FAIL because `lifesource.daily.hmart_weekly` does not exist.

- [ ] **Step 3: Implement minimal jobs**

Implement `run_hmart_weekly_ad_monitor()` and `run_hmart_weekly_planning_digest()` with dependency injection for source, sender, token, and chat ID so tests do not hit the network.

- [ ] **Step 4: Run test to verify it passes**

Run: `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/python -m pytest tests/test_hmart_weekly_jobs.py -v`

Expected: PASS.

### Task 5: Guardrail and Verification

**Files:**
- Modify: `lifesource/scrapers/hmart.py`
- Test: `tests/test_hmart_scraper.py`
- Test: existing suite

- [ ] **Step 1: Write failing guardrail test**

Add a test proving the existing generic H Mart scraper is marked as a catalog or generic sale source, not `weekly_ad`.

- [ ] **Step 2: Run test to verify behavior**

Run: `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/python -m pytest tests/test_hmart_scraper.py -v`

Expected: pass if current source type already avoids `weekly_ad`; otherwise fail and update implementation.

- [ ] **Step 3: Run full verification**

Run:
- `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/ruff check lifesource tests`
- `/Users/kcjq940909/Claude\ Daily\ Life\ Sourcing/.venv/bin/python -m pytest`

Expected: all checks pass.
