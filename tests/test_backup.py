import os
import tempfile
from datetime import date


def test_backup_creates_file(tmp_db):
    from lifesource.daily.backup import backup_database

    with tempfile.TemporaryDirectory() as backup_dir:
        result = backup_database(tmp_db, backup_dir)
        assert os.path.exists(result)
        assert f"lifesource-{date.today().isoformat()}" in result


def test_backup_creates_directory_if_missing(tmp_db):
    from lifesource.daily.backup import backup_database

    with tempfile.TemporaryDirectory() as parent:
        backup_dir = os.path.join(parent, "nested", "backups")
        result = backup_database(tmp_db, backup_dir)
        assert os.path.exists(result)
