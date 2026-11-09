"""Gói schema contract trong SQL phải khớp chính xác contracts/schemas/f1.schema.json."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "backend" / "scripts" / "generate_contract_schema_migration.py"


def _load():
    spec = importlib.util.spec_from_file_location("gen_contract_schema", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ContractSchemaMigrationTest(unittest.TestCase):
    def test_generated_migration_is_current_and_deterministic(self):
        gen = _load()
        self.assertEqual(gen.render(), gen.render())
        committed = gen.TARGET.read_bytes().decode("utf-8").replace("\r\n", "\n")
        self.assertEqual(committed, gen.render(), "run backend/scripts/generate_contract_schema_migration.py")


if __name__ == "__main__":
    unittest.main()
