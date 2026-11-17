"""B7 orchestration checks; evidence aggregation is exercised against PostgreSQL separately."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import Mock

from backend.app.assessment.recommendations import RevisionRecommendationOperations
from backend.app.core import contract
from backend.app.orchestrator.actions import ActionProcessor
from backend.app.orchestrator.workflow_shared import _ok, Terminal
from backend.app.orchestrator.workflow_ports import WorkflowError

ROOT = Path(__file__).resolve().parents[3]

def presentation():
    rec = json.loads((ROOT/'contracts/examples/valid/RevisionRecommendation.json').read_text(encoding='utf-8'))
    chunk = json.loads((ROOT/'contracts/examples/valid/MaterialChunk.json').read_text(encoding='utf-8'))
    ctx = SimpleNamespace(user_id=rec['user_id'])
    pending = ActionProcessor.pending_shell(ctx, rec['pending_action_id'], rec['conversation_id'],
        'ACCEPT_REVISION_RECOMMENDATION', 'AWAITING_APPROVAL', candidate_id=None,
        draft={'recommendation_id':rec['recommendation_id']}, missing=[])
    return dict(kind='ACTION_PRESENTATION', pending_action=pending, candidate=None, proposal=None,
        normalized_command=None, effective_policy=None, schedule_confirmation=None,
        revision_recommendation=rec, revision_source_chunks=[chunk])

class RevisionRecommendationTests(TestCase):
    def setUp(self):
        self.pres=presentation();r=self.pres['revision_recommendation'];a=self.pres['pending_action']
        self.ctx=SimpleNamespace(user_id=r['user_id'],request_id='b7-unit')
        self.receipt=dict(action_id=a['action_id'],message_id='00000000-0000-4000-8000-000000000099',created_at=a['created_at'])
        self.body=dict(schema_version='1.1',conversation_id=r['conversation_id'],material_id=r['material_id'],
            topic=r['topic'],suggested_minutes=60,priority=1)
        self.rpc=Mock(side_effect=lambda ctx,op,args,**kw: _ok(ctx.request_id,'COMMITTED', self.pres if op=='create_revision_recommendation' else args['message']))
        self.ops=RevisionRecommendationOperations(self.rpc,lambda: datetime(2026,11,18,tzinfo=timezone.utc))

    def test_creation_returns_complete_reference_and_signed_domain_inputs(self):
        status,reply=self.ops.create(self.ctx,self.receipt,'b7-unit-key-00001',self.body)
        self.assertEqual(status,200);self.assertTrue(contract.is_valid('OrchestratorReply',reply))
        ref=reply['action_reference'];self.assertEqual(ref['action_id'],ref['target_id']);self.assertEqual(ref['action_version'],ref['target_version'])
        ctx,op,args=self.rpc.call_args.args
        self.assertTrue(contract.is_valid('CreateRevisionRecommendationArguments',args))
        self.assertEqual(op,'create_revision_recommendation');self.assertNotIn('evidence',args);self.assertNotIn('user_id',args)
        self.assertEqual(self.rpc.call_args.kwargs['conversation_id'],self.body['conversation_id'])
        self.assertEqual(self.rpc.call_args.kwargs['message_id'],self.receipt['message_id'])

    def test_retry_uses_same_domain_key_and_ids(self):
        self.ops.create(self.ctx,self.receipt,'b7-unit-key-00001',self.body);first=self.rpc.call_args
        self.ops.create(self.ctx,self.receipt,'b7-unit-key-00001',self.body)
        self.assertEqual(first,self.rpc.call_args)

    def test_business_errors_remain_terminal(self):
        error=dict(code='INVALID_PARAMETER',message='Chưa có dữ liệu.',field=None,details={},retryable=False)
        self.rpc.return_value=None;self.rpc.side_effect=lambda *a,**k:dict(schema_version='1.1',request_id='b7-unit',outcome='ERROR',data=None,error=error,warnings=[])
        with self.assertRaises(Terminal):self.ops.create(self.ctx,self.receipt,'b7-unit-key-00001',self.body)

    def test_transient_error_remains_retryable(self):
        self.rpc.side_effect=lambda *a,**k:dict(outcome='ERROR',error=dict(code='SERVICE_UNAVAILABLE',message='Retry',field=None))
        with self.assertRaises(WorkflowError) as raised:self.ops.create(self.ctx,self.receipt,'b7-unit-key-00001',self.body)
        self.assertTrue(raised.exception.retryable)

    def test_malformed_domain_result_is_rejected(self):
        self.rpc.side_effect=lambda ctx,op,args,**kw:_ok(ctx.request_id,'COMMITTED',{} if op=='create_revision_recommendation' else args['message'])
        with self.assertRaises(WorkflowError):self.ops.create(self.ctx,self.receipt,'b7-unit-key-00001',self.body)

    def test_patch_fields_require_version_as_a_pair(self):
        request=dict(schema_version='1.1',conversation_id=self.body['conversation_id'],expected_action_version=1)
        self.assertTrue(contract.is_valid('ReviewActionRequest',request))
        self.assertFalse(contract.is_valid('ReviewActionRequest',{**request,'candidate_patch':{'start_at':None}}))
        self.assertFalse(contract.is_valid('ReviewActionRequest',{**request,'expected_candidate_version':1}))
        self.assertTrue(contract.is_valid('ReviewActionRequest',{**request,'candidate_patch':{},'expected_candidate_version':1}))
