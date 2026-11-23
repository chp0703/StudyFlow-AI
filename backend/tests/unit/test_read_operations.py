"""Danh sách thao tác đọc trong contract phải khớp app_private.rpc_is_read của migration mới nhất."""

import re
import unittest
from pathlib import Path

from backend.app.clients.rpc import READ_OPERATIONS

MIGRATIONS = Path(__file__).resolve().parents[3] / "supabase/migrations"


class ReadOperationsTests(unittest.TestCase):
    def test_sql_rpc_is_read_matches_contract(self):
        latest = [
            path for path in sorted(MIGRATIONS.glob("*.sql"))
            if "function app_private.rpc_is_read" in path.read_text(encoding="utf-8")
        ][-1]
        body = re.search(
            r"function app_private\.rpc_is_read.*?p_routine in \((.*?)\)", latest.read_text(encoding="utf-8"), re.S
        ).group(1)
        self.assertEqual(set(re.findall(r"'(\w+)'", body)), set(READ_OPERATIONS), latest.name)


if __name__ == "__main__":
    unittest.main()
