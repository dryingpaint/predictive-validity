"""Create the database schema and apply numbered migrations after it.

    python db/migrate.py init     # empty database -> db/schema.sql, recorded as migration SCHEMA_THROUGH
    python db/migrate.py status   # each migration's state; ledger rows the schema squashes
    python db/migrate.py apply    # pending migrations numbered above SCHEMA_THROUGH, in order

db/schema.sql is the schema as of migration SCHEMA_THROUGH: every earlier migration is
squashed into it, and their ledger rows (preclin.schema_migration, append-only) stay as
history. Later migrations are SQL or Python files named NN_name.sql / NN_name.py; an
applied file's SHA-256 is recorded, and changing it afterwards is a hard drift error.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import Json


ROOT = Path(__file__).resolve().parents[1]
DB_DIR = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
SCHEMA = DB_DIR / "schema.sql"
SCHEMA_THROUGH = 92  # the last migration db/schema.sql includes
MIGRATION_RE = re.compile(r"^(?P<number>[0-9]{2,})_(?P<name>.+)[.](?P<kind>sql|py)$")
ADVISORY_LOCK_NAME = "predictive-validity:preclin.schema_migration"


@dataclass(frozen=True)
class Migration:
    number: int
    name: str
    kind: str
    path: Path
    sha256: str

    @property
    def filename(self) -> str:
        return self.path.name


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def discover_migrations(db_dir: Path = DB_DIR) -> list[Migration]:
    """Migration files numbered above SCHEMA_THROUGH; a lower-numbered file is an error, since the
    schema already contains it."""
    migrations = []
    for path in sorted(db_dir.iterdir()):
        match = MIGRATION_RE.fullmatch(path.name)
        if match is None:
            continue
        number = int(match.group("number"))
        if number <= SCHEMA_THROUGH:
            raise RuntimeError(f"{path.name} is numbered within db/schema.sql (<= {SCHEMA_THROUGH})")
        migrations.append(Migration(number=number, name=match.group("name"),
                                    kind="python" if match.group("kind") == "py" else "sql",
                                    path=path, sha256=file_sha256(path)))
    numbers = [m.number for m in migrations]
    duplicates = sorted({n for n in numbers if numbers.count(n) > 1})
    if duplicates:
        raise RuntimeError(f"Duplicate migration numbers: {duplicates}")
    return sorted(migrations, key=lambda migration: migration.number)


def direct_database_url(url: str) -> str:
    """Use the direct Neon endpoint without ever logging the credential."""
    from urllib.parse import urlsplit, urlunsplit

    parsed = urlsplit(url)
    if "-pooler." not in (parsed.hostname or ""):
        return url
    return urlunsplit((parsed.scheme, parsed.netloc.replace("-pooler.", ".", 1), parsed.path, parsed.query,
                       parsed.fragment))


def git_commit() -> str | None:
    result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False)
    value = result.stdout.strip()
    return value if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def ledger_exists(conn) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT to_regclass('preclin.schema_migration') IS NOT NULL")
        return bool(cur.fetchone()[0])


def load_ledger(conn) -> dict[int, dict]:
    if not ledger_exists(conn):
        return {}
    with conn.cursor() as cur:
        cur.execute("""SELECT migration_number, migration_name, filename, file_sha256, migration_kind,
                              execution_mode, applied_at, applied_by, git_commit, details
                       FROM preclin.schema_migration ORDER BY migration_number""")
        fields = [description.name for description in cur.description]
        return {row[0]: dict(zip(fields, row)) for row in cur.fetchall()}


def migration_state(migration: Migration, ledger_row: dict | None) -> str:
    if ledger_row is None:
        return "pending"
    if (ledger_row["filename"] != migration.filename or ledger_row["migration_name"] != migration.name
            or ledger_row["migration_kind"] != migration.kind or ledger_row["file_sha256"] != migration.sha256):
        return "drift"
    return ledger_row["execution_mode"]


def record(conn, number: int, name: str, filename: str, sha256: str, kind: str, mode: str, details: dict) -> None:
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO preclin.schema_migration
                         (migration_number, migration_name, filename, file_sha256, migration_kind, execution_mode,
                          git_commit, details)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (number, name, filename, sha256, kind, mode, git_commit(), Json(details)))
    conn.commit()


def init_schema(conn) -> None:
    """Create db/schema.sql in an empty database and record it as migration SCHEMA_THROUGH."""
    if ledger_exists(conn):
        raise RuntimeError("preclin.schema_migration exists: this database already has a schema")
    with conn.cursor() as cur:
        cur.execute(SCHEMA.read_text())
    conn.commit()
    record(conn, SCHEMA_THROUGH, "schema", SCHEMA.name, file_sha256(SCHEMA), "sql", "applied",
           {"runner": "db/migrate.py", "schema_through": SCHEMA_THROUGH})
    print(f"created {SCHEMA.name} (schema through migration {SCHEMA_THROUGH})")


def print_status(conn, migrations: list[Migration]) -> int:
    if not ledger_exists(conn):
        print("ledger: absent (run `db/migrate.py init`)")
        return 0
    rows = load_ledger(conn)
    squashed = [n for n in rows if n <= SCHEMA_THROUGH]
    if SCHEMA_THROUGH not in rows:
        print(f"schema: migration {SCHEMA_THROUGH} not recorded; this database predates db/schema.sql")
        return 2
    print(f"schema: {SCHEMA.name} through migration {SCHEMA_THROUGH} ({len(squashed)} ledger rows)")
    drift = False
    for migration in migrations:
        state = migration_state(migration, rows.get(migration.number))
        drift |= state == "drift"
        print(f"{migration.number:02d} {state:8s} {migration.sha256[:12]} {migration.filename}")
    for number in sorted(set(rows) - set(squashed) - {m.number for m in migrations}):
        drift = True
        print(f"{number:02d} drift    {'-' * 12} ledger row has no local file")
    return 2 if drift else 0


def execute_python(migration: Migration) -> None:
    result = subprocess.run([sys.executable, str(migration.path)], cwd=ROOT, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Python migration {migration.filename} failed with exit code {result.returncode}")


def apply_pending(conn, migrations: list[Migration], through: int | None) -> None:
    rows = load_ledger(conn)
    if SCHEMA_THROUGH not in rows:
        raise RuntimeError("no schema recorded: run `db/migrate.py init` on an empty database first")
    for migration in migrations:
        if through is not None and migration.number > through:
            continue
        state = migration_state(migration, rows.get(migration.number))
        if state == "drift":
            raise RuntimeError(f"Checksum drift for {migration.filename}")
        if state != "pending":
            continue
        print(f"applying {migration.filename}", flush=True)
        if migration.kind == "sql":
            with conn.cursor() as cur:
                cur.execute(migration.path.read_text())
            conn.commit()
        else:
            execute_python(migration)
        record(conn, migration.number, migration.name, migration.filename, migration.sha256, migration.kind,
               "applied", {"runner": "db/migrate.py"})
        rows = load_ledger(conn)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status")
    subparsers.add_parser("init")
    apply_parser = subparsers.add_parser("apply")
    apply_parser.add_argument("--through", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    migrations = discover_migrations()
    conn = psycopg2.connect(direct_database_url(os.environ["DATABASE_URL"]))
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(hashtext(%s))", (ADVISORY_LOCK_NAME,))
        if args.command == "status":
            raise SystemExit(print_status(conn, migrations))
        if args.command == "init":
            init_schema(conn)
            return
        if args.command == "apply":
            apply_pending(conn, migrations, args.through)
            return
        raise AssertionError(args.command)
    finally:
        try:
            conn.rollback()
            with conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_unlock(hashtext(%s))", (ADVISORY_LOCK_NAME,))
            conn.commit()
        finally:
            conn.close()


if __name__ == "__main__":
    main()
