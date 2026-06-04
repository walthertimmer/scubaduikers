#!/usr/bin/env python3
"""
Restore local DB from Litestream backup on S3.
Usage: python restore_prod_db.py [--db-path scubaduikers.db] [--confirm]
"""
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# Configuration - set these via environment variables or edit here
S3_BUCKET = os.getenv("S3_BUCKET")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
DB_PATH = os.getenv("DATABASE_PATH", "scubaduikers.db")

def restore_database(db_path: str = DB_PATH, confirm: bool = False):
    """Restore database from Litestream S3 backup."""

    if not S3_ACCESS_KEY or not S3_SECRET_KEY:
        print("ERROR: S3 credentials not configured.")
        print("Set S3_ACCESS_KEY and S3_SECRET_KEY environment variables.")
        sys.exit(1)

    if not S3_BUCKET:
        print("ERROR: S3 bucket not configured. Set S3_BUCKET.")
        sys.exit(1)

    if Path(db_path).exists():
        if not confirm:
            print(f"WARNING: Database file '{db_path}' already exists.")
            print("This will be OVERWRITTEN. Use --confirm to proceed.")
            sys.exit(1)
        Path(db_path).unlink()
        Path(f"{db_path}-shm").unlink(missing_ok=True)
        Path(f"{db_path}-wal").unlink(missing_ok=True)

    print(f"→ Restoring s3://{S3_BUCKET}/scubaduikers to {db_path}")

    try:
        env = os.environ.copy()
        env.update({
            "AWS_ACCESS_KEY_ID": S3_ACCESS_KEY,
            "AWS_SECRET_ACCESS_KEY": S3_SECRET_KEY,
            "AWS_ENDPOINT_URL": f"https://{S3_ENDPOINT}",
        })
        subprocess.run([
            "litestream", "restore",
            "-o", db_path,
            f"s3://{S3_BUCKET}/scubaduikers",
        ], check=True, env=env)
        print(f"✓ Restored to {db_path}")
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"ERROR: {error_msg}")
        sys.exit(1)

if __name__ == "__main__":
    confirm = "--confirm" in sys.argv
    db_path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else DB_PATH

    restore_database(db_path, confirm)
