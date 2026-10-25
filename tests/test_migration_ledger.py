"""Migration discovery and ledger states after db/schema.sql squashes migrations through SCHEMA_THROUGH."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "db" / "migrate.py"
SPEC = importlib.util.spec_from_file_location("migration_runner", MODULE_PATH)
migrate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = migrate
SPEC.loader.exec_module(migrate)
AFTER = migrate.SCHEMA_THROUGH + 1


class MigrationLedgerTests(unittest.TestCase):
    def test_discovers_migrations_after_the_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / f"{AFTER}_one.py").write_text("print('one')\n")
            (root / f"{AFTER + 1}_two.sql").write_text("SELECT 2;\n")
            (root / "schema.sql").write_text("SELECT 1;\n")
            (root / "helper.py").write_text("pass\n")
            migrations = migrate.discover_migrations(root)
        self.assertEqual([m.number for m in migrations], [AFTER, AFTER + 1])
        self.assertEqual([m.kind for m in migrations], ["python", "sql"])

    def test_migration_inside_the_schema_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / f"{migrate.SCHEMA_THROUGH}_old.sql").write_text("SELECT 1;\n")
            with self.assertRaisesRegex(RuntimeError, "within db/schema.sql"):
                migrate.discover_migrations(root)

    def test_duplicate_migration_numbers_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / f"{AFTER}_one.sql").write_text("SELECT 1;\n")
            (root / f"{AFTER}_duplicate.py").write_text("pass\n")
            with self.assertRaisesRegex(RuntimeError, "Duplicate migration numbers"):
                migrate.discover_migrations(root)

    def test_changed_hash_is_drift(self):
        migration = migrate.Migration(number=AFTER, name="example", kind="sql",
                                      path=Path(f"{AFTER}_example.sql"), sha256="a" * 64)
        row = {"filename": migration.filename, "migration_name": migration.name, "migration_kind": "sql",
               "file_sha256": "b" * 64, "execution_mode": "applied"}
        self.assertEqual(migrate.migration_state(migration, row), "drift")
        self.assertEqual(migrate.migration_state(migration, {**row, "file_sha256": "a" * 64}), "applied")


if __name__ == "__main__":
    unittest.main()
