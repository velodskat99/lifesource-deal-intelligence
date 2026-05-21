import logging
import shutil
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


def backup_database(db_path: str, backup_dir: str, retention_days: int = 30) -> str:
    """Copy the SQLite database to a dated backup file. Returns backup path."""
    backup_path = Path(backup_dir)
    backup_path.mkdir(parents=True, exist_ok=True)

    today = date.today().isoformat()
    dest = backup_path / f"lifesource-{today}.db"
    shutil.copy2(db_path, dest)
    logger.info(f"Database backed up to {dest}")

    # Clean old backups
    cutoff = date.today() - timedelta(days=retention_days)
    for old_file in backup_path.glob("lifesource-*.db"):
        try:
            file_date = date.fromisoformat(old_file.stem.replace("lifesource-", ""))
            if file_date < cutoff:
                old_file.unlink()
                logger.info(f"Deleted old backup: {old_file}")
        except ValueError:
            continue

    return str(dest)
