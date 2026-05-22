import json
from typing import Any

from lifesource.db import get_db
from lifesource.sources.hmart_weekly import HMART_TEXAS_WEEKLY_AD_URL, WeeklyAdInspection
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
    result = record_source_snapshot(
        db_path,
        SourceSnapshot(
            store="hmart",
            region="texas",
            source_url=inspection.source_url,
            source_type="weekly_ad",
            fingerprint=inspection.fingerprint,
            raw_metadata={
                "assets": inspection.assets,
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


def _decode_metadata(raw_metadata: str | None) -> dict[str, Any]:
    if not raw_metadata:
        return {}
    try:
        data = json.loads(raw_metadata)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
