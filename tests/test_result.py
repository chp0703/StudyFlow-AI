import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'contracts/schemas/tool_result.json').read_text(encoding='utf-8'))
CASES = json.loads((ROOT / 'contracts/examples/result_cases.json').read_text(encoding='utf-8'))


class ResultContractTest(unittest.TestCase):
    def test_schema_is_valid(self):
        Draft202012Validator.check_schema(SCHEMA)

    def test_examples_by_operation(self):
        for case in CASES:
            with self.subTest(case=case['name']):
                selected = {'$ref': '#/$defs/result_' + case['operation'], '$defs': SCHEMA['$defs']}
                validator = Draft202012Validator(selected, format_checker=FormatChecker())
                self.assertEqual(not list(validator.iter_errors(case['result'])), case['valid'])


if __name__ == '__main__':
    unittest.main()
