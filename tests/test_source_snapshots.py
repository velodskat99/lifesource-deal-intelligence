from lifesource.db import init_db
from lifesource.sources.snapshots import SourceSnapshot, record_source_snapshot


def test_record_source_snapshot_marks_first_seen_as_changed(tmp_db):
    init_db(tmp_db)

    result = record_source_snapshot(
        tmp_db,
        SourceSnapshot(
            store="hmart",
            region="texas",
            source_url="https://www.hmart.com/weekly-ads-texas#/",
            source_type="weekly_ad",
            fingerprint="abc123",
            raw_metadata={"assets": ["ad-page-1.jpg"]},
        ),
    )

    assert result.changed is True
    assert result.previous_fingerprint is None
    assert result.current_fingerprint == "abc123"


def test_record_source_snapshot_marks_same_fingerprint_as_unchanged(tmp_db):
    init_db(tmp_db)
    snapshot = SourceSnapshot(
        store="hmart",
        region="texas",
        source_url="https://www.hmart.com/weekly-ads-texas#/",
        source_type="weekly_ad",
        fingerprint="abc123",
        raw_metadata={"assets": ["ad-page-1.jpg"]},
    )

    record_source_snapshot(tmp_db, snapshot)
    result = record_source_snapshot(tmp_db, snapshot)

    assert result.changed is False
    assert result.previous_fingerprint == "abc123"
    assert result.current_fingerprint == "abc123"


def test_record_source_snapshot_marks_new_fingerprint_as_changed(tmp_db):
    init_db(tmp_db)
    first = SourceSnapshot(
        store="hmart",
        region="texas",
        source_url="https://www.hmart.com/weekly-ads-texas#/",
        source_type="weekly_ad",
        fingerprint="abc123",
        raw_metadata={"assets": ["ad-page-1.jpg"]},
    )
    second = SourceSnapshot(
        store="hmart",
        region="texas",
        source_url="https://www.hmart.com/weekly-ads-texas#/",
        source_type="weekly_ad",
        fingerprint="def456",
        raw_metadata={"assets": ["ad-page-2.jpg"]},
    )

    record_source_snapshot(tmp_db, first)
    result = record_source_snapshot(tmp_db, second)

    assert result.changed is True
    assert result.previous_fingerprint == "abc123"
    assert result.current_fingerprint == "def456"
