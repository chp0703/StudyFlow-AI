import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'contracts/schemas/validated_command.json').read_text(encoding='utf-8'))
CASES = json.loads((ROOT / 'contracts/examples/command_cases.json').read_text(encoding='utf-8'))


class CommandContractTest(unittest.TestCase):
    def test_schema_is_valid(self):
        Draft202012Validator.check_schema(SCHEMA)

    def test_examples(self):
        validator = Draft202012Validator(SCHEMA, format_checker=FormatChecker())
        for case in CASES:
            with self.subTest(case=case['name']):
                self.assertEqual(not list(validator.iter_errors(case['command'])), case['valid'])


if __name__ == '__main__':
    unittest.main()
