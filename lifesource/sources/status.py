import json
from typing import Any
from urllib.parse import urlsplit

from lifesource.db import get_db
from lifesource.sources.hmart_weekly import (
    HMART_TEXAS_WEEKLY_AD_URL,
    HmartTexasWeeklyAdSource,
    WeeklyAdInspection,
)
from lifesource.sources.snapshots import SourceSnapshot, record_source_snapshot
from lifesource.sources.weekly_items import count_weekly_ad_items


def get_hmart_texas_status(db_path: str) -> dict[str, Any]:
    """Return current H Mart Texas weekly-ad source status."""
    with get_db(db_path) as conn:
        row = conn.execute(
            """SELECT * FROM source_snapshots
               WHERE store = 'hmart'
                 AND region = 'texas'
                 AND source_url = ?
                 AND source_type = 'weekly_ad'""",
            (HMART_TEXAS_WEEKLY_AD_URL,),
        ).fetchone()

    base = {
        "store": "hmart",
        "store_label": "H Mart",
        "region": "texas",
        "region_label": "Texas",
        "source_type": "weekly_ad",
        "source_url": HMART_TEXAS_WEEKLY_AD_URL,
        "has_snapshot": False,
        "fingerprint": None,
        "fingerprint_short": None,
        "asset_count": 0,
        "item_count": count_weekly_ad_items(db_path, store="hmart", region="texas"),
        "assets": [],
        "strategy": None,
        "first_seen_at": None,
        "last_seen_at": None,
        "warnings": [],
    }
    if row is None:
        return base

    metadata = _decode_metadata(row["raw_metadata"])
    assets = metadata.get("assets", [])
    warnings = metadata.get("warnings", [])
    fingerprint = row["fingerprint"]
    return {
        **base,
        "has_snapshot": True,
        "fingerprint": fingerprint,
        "fingerprint_short": fingerprint[:12],
        "asset_count": len(assets),
        "assets": assets,
        "strategy": metadata.get("strategy"),
        "first_seen_at": row["first_seen_at"],
        "last_seen_at": row["last_seen_at"],
        "warnings": warnings,
    }


def record_hmart_texas_inspection(
    db_path: str,
    inspection: WeeklyAdInspection,
) -> dict[str, Any]:
    """Persist a H Mart Texas inspection and return changed status plus snapshot."""
    manual_assets = _get_existing_manual_assets(db_path)
    assets = _dedupe([*inspection.assets, *manual_assets])
    fingerprint = (
        HmartTexasWeeklyAdSource().fingerprint([inspection.fingerprint, *assets])
        if manual_assets
        else inspection.fingerprint
    )
    result = record_source_snapshot(
        db_path,
        SourceSnapshot(
            store="hmart",
            region="texas",
            source_url=inspection.source_url,
            source_type="weekly_ad",
            fingerprint=fingerprint,
            raw_metadata={
                "assets": assets,
                "manual_assets": manual_assets,
                "warnings": inspection.warnings,
                **inspection.metadata,
            },
        ),
    )
    return {
        "changed": result.changed,
        "previous_fingerprint": result.previous_fingerprint,
        "current_fingerprint": result.current_fingerprint,
        "status": get_hmart_texas_status(db_path),
    }


def add_hmart_texas_manual_asset(db_path: str, asset_url: str) -> dict[str, Any]:
    """Trust a manually supplied H Mart weekly-ad asset URL for review extraction."""
    asset_url = asset_url.strip()
    source = HmartTexasWeeklyAdSource()
    if not _is_hmart_url(asset_url) or not source._looks_like_weekly_ad_asset(asset_url):
        raise ValueError("Asset URL does not look like a H Mart weekly-ad image or PDF.")

    current = get_hmart_texas_status(db_path)
    manual_assets = _dedupe([*_get_existing_manual_assets(db_path), asset_url])
    assets = _dedupe([*current.get("assets", []), *manual_assets])
    fingerprint = source.fingerprint(["manual_weekly_ad_assets", *assets])
    result = record_source_snapshot(
        db_path,
        SourceSnapshot(
            store="hmart",
            region="texas",
            source_url=HMART_TEXAS_WEEKLY_AD_URL,
            source_type="weekly_ad",
            fingerprint=fingerprint,
            raw_metadata={
                "assets": assets,
                "manual_assets": manual_assets,
                "warnings": [],
                "strategy": "manual_weekly_ad_assets",
                "date_labels": [],
            },
        ),
    )
    return {
        "changed": result.changed,
        "previous_fingerprint": result.previous_fingerprint,
        "current_fingerprint": result.current_fingerprint,
        "status": get_hmart_texas_status(db_path),
    }


def _get_existing_manual_assets(db_path: str) -> list[str]:
    with get_db(db_path) as conn:
        row = conn.execute(
            """SELECT raw_metadata FROM source_snapshots
               WHERE store = 'hmart'
                 AND region = 'texas'
                 AND source_url = ?
                 AND source_type = 'weekly_ad'""",
            (HMART_TEXAS_WEEKLY_AD_URL,),
        ).fetchone()
    if row is None:
        return []
    metadata = _decode_metadata(row["raw_metadata"])
    return [asset for asset in metadata.get("manual_assets", []) if isinstance(asset, str)]


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _is_hmart_url(asset_url: str) -> bool:
    host = urlsplit(asset_url).netloc.lower()
    return host == "hmart.com" or host.endswith(".hmart.com")


def _decode_metadata(raw_metadata: str | None) -> dict[str, Any]:
    if not raw_metadata:
        return {}
    try:
        data = json.loads(raw_metadata)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
