import json
from dataclasses import dataclass, field
from typing import Any

from lifesource.db import get_db


@dataclass(frozen=True)
class SourceSnapshot:
    store: str
    region: str
    source_url: str
    source_type: str
    fingerprint: str
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SourceSnapshotResult:
    changed: bool
    previous_fingerprint: str | None
    current_fingerprint: str


def record_source_snapshot(
    db_path: str,
    snapshot: SourceSnapshot,
) -> SourceSnapshotResult:
    """Insert or update a source snapshot and report whether it changed."""
    with get_db(db_path) as conn:
        row = conn.execute(
            """SELECT fingerprint FROM source_snapshots
               WHERE store = ? AND region = ? AND source_url = ? AND source_type = ?""",
            (
                snapshot.store,
                snapshot.region,
                snapshot.source_url,
                snapshot.source_type,
            ),
        ).fetchone()
        previous = row["fingerprint"] if row else None
        metadata = json.dumps(snapshot.raw_metadata, sort_keys=True)

        if row is None:
            conn.execute(
                """INSERT INTO source_snapshots
                   (store, region, source_url, source_type, fingerprint, raw_metadata)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    snapshot.store,
                    snapshot.region,
                    snapshot.source_url,
                    snapshot.source_type,
                    snapshot.fingerprint,
                    metadata,
                ),
            )
        else:
            conn.execute(
                """UPDATE source_snapshots
                   SET fingerprint = ?, raw_metadata = ?, last_seen_at = CURRENT_TIMESTAMP
                   WHERE store = ? AND region = ? AND source_url = ? AND source_type = ?""",
                (
                    snapshot.fingerprint,
                    metadata,
                    snapshot.store,
                    snapshot.region,
                    snapshot.source_url,
                    snapshot.source_type,
                ),
            )
        conn.commit()

    return SourceSnapshotResult(
        changed=previous != snapshot.fingerprint,
        previous_fingerprint=previous,
        current_fingerprint=snapshot.fingerprint,
    )
