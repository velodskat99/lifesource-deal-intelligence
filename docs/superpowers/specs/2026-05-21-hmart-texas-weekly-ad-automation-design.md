# H Mart Texas Weekly Ad Automation Design

## Goal

LifeSource should watch the H Mart Texas weekly ad for the Austin shopping context, notify the user when the ad refreshes, and also send a weekly planning summary even when the ad has not changed. The source of truth for H Mart deals is the regional weekly ad page:

`https://www.hmart.com/weekly-ads-texas#/`

The generic H Mart `/sale` catalog should not be treated as a reliable deal source unless it is later proven to represent current regional weekly promotions.

## Product Behavior

LifeSource will support two notification lanes:

1. Refresh alerts
   - Run a daily H Mart Texas source check.
   - Compare the current weekly ad fingerprint with the last stored fingerprint.
   - If the fingerprint changes, send a Telegram alert.
   - The alert should include the source link, detected ad dates if available, high-confidence highlights if parsed, and a short "worth planning around this?" summary.

2. Weekly planning digest
   - Run on a fixed weekly schedule.
   - Send a H Mart Texas planning summary even if the ad has not changed.
   - The digest should include current known highlights, likely meal-plan anchors, items to skip when confidence is low, and a suggested shopping-list section.

## Data Rules

Only sources with `source_type = weekly_ad` should contribute to H Mart Texas deal counts and meal-planning highlights.

The first implementation should prefer reliable refresh detection over aggressive item extraction. If the page exposes structured data, LifeSource can parse item names, sale prices, regular prices, categories, images, ad dates, and source URLs. If the page is image or PDF based, the system should first store the changed source snapshot and notify the user, then parse items with OCR or vision only from the weekly-ad assets.

Avoid importing product catalogs into `deals`. A product without evidence of being in the weekly ad should not appear as a deal.

## Data Model

Add a `source_snapshots` table:

- `id`
- `store`
- `region`
- `source_url`
- `source_type`
- `fingerprint`
- `raw_metadata`
- `first_seen_at`
- `last_seen_at`

The unique key should be scoped to `store`, `region`, `source_url`, and `source_type`.

For H Mart Texas deals, reuse the existing `deals` table where possible:

- `store = hmart`
- `source_url = https://www.hmart.com/weekly-ads-texas#/` or the specific weekly-ad asset URL
- `source_type = weekly_ad`
- `confidence` reflects parser confidence
- `image_url` stores the product or ad image when available

If regional source tracking becomes important across more stores, add a dedicated `region` column later. For the first H Mart implementation, region can live in `source_snapshots.raw_metadata` and source URL conventions.

## Components

### HmartWeeklyAdTexasSource

Fetches and fingerprints the weekly ad page. The fingerprint should be based on the strongest stable evidence available, in this order:

1. Structured weekly-ad payload, if discoverable.
2. Weekly-ad image or PDF asset URLs and date labels.
3. Rendered page text plus relevant asset URLs.
4. Raw HTML as a fallback.

The source checker should return a typed result with:

- `changed`
- `fingerprint`
- `source_url`
- `metadata`
- `assets`
- `warnings`

### HmartWeeklyAdParser

Converts weekly-ad assets into `Deal` objects. This can be incremental:

1. Structured parser for exposed JSON or API payloads.
2. HTML/image URL metadata parser.
3. OCR or vision parser for ad images or PDFs.

Low-confidence parsed items should be excluded from automatic meal planning and labeled in notifications as requiring review.

### Notification Jobs

Add two job entry points:

- `hmart-weekly-ad-monitor`: refresh detection plus immediate alert on change.
- `weekly-planning-digest`: scheduled planning summary, even when unchanged.

Both jobs should reuse shared formatting helpers so Telegram output and future UI summaries stay consistent.

## Meal Planning

Meal planning should start simple:

- Group deals into protein, produce, pantry, dairy, frozen, and other.
- Suggest meals only when there is at least one reliable anchor item, usually protein or produce.
- Prefer 2 to 4 practical meal ideas over broad recipe generation.
- Include a shopping-list draft that can be copied into the app list.

Later, this can become an AI-assisted planner using purchase history, pantry staples, preferences, and price history.

## Failure Modes

- Page fetch fails: keep the previous snapshot, do not delete existing deals, send no refresh alert unless the weekly digest is due.
- Fingerprint changes but parser extracts no deals: send a refresh alert with the source link and say item extraction needs review.
- Parser extracts unusually many items: treat as suspicious, suppress automatic deal replacement, and include a warning.
- OCR or vision confidence is low: store no automatic deals, or store only high-confidence rows.

## Testing

Add focused tests for:

- Snapshot insert and unchanged detection.
- Changed fingerprint detection.
- Refresh alert formatting.
- Weekly digest formatting when no changed source exists.
- H Mart weekly-ad parser behavior with fixture HTML or captured asset metadata.
- Guardrail: generic H Mart catalog rows do not count as weekly-ad deals.

## First Implementation Slice

The first implementation should include:

1. `source_snapshots` schema migration.
2. H Mart Texas source checker with fingerprinting.
3. Telegram refresh alert on changed fingerprint.
4. Weekly planning digest using current weekly-ad deals or a source-link fallback.
5. Tests for snapshot detection, alert formatting, and no-catalog guardrails.

OCR or vision extraction can follow after refresh detection is reliable.
