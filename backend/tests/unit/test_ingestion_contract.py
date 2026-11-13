import copy
import unittest

from backend.app.core import contract


SOURCE = '00100000-0000-4000-8000-000000000001'
CONVERSATION = '00100000-0000-4000-8000-000000000002'


class IngestionContractTests(unittest.TestCase):
    def test_upload_contract_is_closed_and_owner_is_never_client_input(self):
        self.assertTrue('SourceUploadRequest' in contract.SCHEMA['$defs'])
        body = {'schema_version': '1.1', 'conversation_id': CONVERSATION,
                'filename': 'tasks.txt', 'mime_type': 'text/plain', 'content_base64': 'aGk='}
        self.assertTrue(contract.is_valid('SourceUploadRequest', body))
        self.assertFalse(contract.is_valid('SourceUploadRequest', {**body, 'user_id': SOURCE}))

    def test_message_source_ids_are_optional_unique_and_bounded(self):
        body = {'schema_version': '1.1', 'conversation_id': CONVERSATION, 'text': 'Nhập tệp này'}
        self.assertTrue(contract.is_valid('UserMessage', body))
        self.assertTrue(contract.is_valid('UserMessage', {**body, 'source_ids': [SOURCE]}))
        self.assertFalse(contract.is_valid('UserMessage', {**body, 'source_ids': [SOURCE, SOURCE]}))
        self.assertFalse(contract.is_valid('UserMessage', {**body, 'source_ids': ['https://private-file']}))

    def test_source_intents_cannot_authorize_plan_or_unknown_fields(self):
        self.assertTrue('SourceExtraction' in contract.SCHEMA['$defs'])
        extraction = {'parser': 'document-v1', 'model': 'deepseek-flash', 'prompt_version': 'be04-1',
                      'extracted_at': '2026-11-13T09:00:00Z', 'usage': {'input_tokens': 3, 'output_tokens': 4},
                      'intents': [{'intent': 'CREATE_TASK', 'slots': {'title': 'Homework'}, 'raw_expressions': {}, 'ambiguities': []}]}
        self.assertTrue(contract.is_valid('SourceExtraction', extraction))
        self.assertTrue(contract.is_valid('SourceExtraction', {**extraction, 'intents': []}))
        bad = copy.deepcopy(extraction)
        bad['intents'][0]['intent'] = 'GENERATE_STUDY_PLAN'
        self.assertFalse(contract.is_valid('SourceExtraction', bad))
        bad = copy.deepcopy(extraction)
        bad['intents'][0]['slots']['user_id'] = SOURCE
        self.assertFalse(contract.is_valid('SourceExtraction', bad))


if __name__ == '__main__':
    unittest.main()
