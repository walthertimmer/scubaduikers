"""
Minimal migration runner.

- SQL migration files live in migrations/ and are named NNN_description.sql
  (e.g. 001_add_dive_columns.sql).  They run in alphabetical order.
- A schema_migration table records every applied migration by filename.
- Each file is run exactly once; already-applied files are skipped.
"""

from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import Connection, text
from sqlalchemy.exc import OperationalError

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

log = logging.getLogger(__name__)


def _ensure_tracking_table(conn: Connection) -> None:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS schema_migration (
            name       TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """))


def _applied(conn: Connection) -> set[str]:
    rows = conn.execute(text("SELECT name FROM schema_migration")).fetchall()
    return {row[0] for row in rows}


def run(engine) -> None:
    """Apply every unapplied migration in order."""
    migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))

    with engine.begin() as conn:          # single transaction for the whole run
        _ensure_tracking_table(conn)
        done = _applied(conn)

        for path in migration_files:
            if path.name in done:
                log.debug("skip  %s", path.name)
                continue

            log.info("apply %s", path.name)
            sql = path.read_text(encoding="utf-8")

            # Execute each statement separately (SQLite doesn't support multi-statement exec)
            for statement in _split(sql):
                try:
                    conn.execute(text(statement))
                except OperationalError as e:
                    if "duplicate column" in str(e).lower():
                        log.debug("skipping: %s", statement[:50])
                        continue
                    raise

            conn.execute(
                text("INSERT INTO schema_migration (name) VALUES (:name)"),
                {"name": path.name},
            )

        log.info("migrations up to date (%d file(s) found)", len(migration_files))


def _split(sql: str) -> list[str]:
    """Split a SQL file on semicolons, dropping empty statements."""
    return [s.strip() for s in sql.split(";") if s.strip()]
