import unittest

from backend.app.clients.rpc import READ_OPERATIONS


class MaterialRpcTests(unittest.TestCase):
    def test_material_reads_do_not_carry_write_attestations(self):
        self.assertTrue({'get_assessment_material', 'search_material_chunks'} <= READ_OPERATIONS)
        self.assertNotIn('store_assessment_material', READ_OPERATIONS)
