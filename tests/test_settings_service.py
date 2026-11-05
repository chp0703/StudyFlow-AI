import copy
import json
import unittest
from pathlib import Path

from backend.app.orchestrator.dispatcher import Dispatcher, Principal, TrustedContext
from backend.app.services.settings import SettingsService, settings_handlers
from backend.app.services.tasks import TaskError
from tests.test_task_service import MemoryStore, USER, OTHER, CONV, MSG, ACTION, APPROVAL, NOW

ROOT = Path(__file__).resolve().parents[1]
COMMANDS = json.loads((ROOT / 'contracts/examples/command_cases.json').read_text(encoding='utf-8'))
WINDOW_ID = '00000000-0000-4000-8000-000000000010'


def arguments(op): return copy.deepcopy(next(x['command']['arguments'] for x in COMMANDS if x['name'] == op))


class SettingsStore(MemoryStore):
    def __init__(self):
        super().__init__()
        self.data['profile'] = {'user_id':USER,'schedule_revision':0,'scheduling_policy':{
            'min_block_minutes':25,'max_block_minutes':90,'allow_short_final_block':True,
            'max_daily_minutes':240,'break_minutes':10}}
        self.data['windows'] = {}
        self.data['current_plan'] = {'unchanged': True}
        self.fail_window = False
    def get_profile(self, owner): return copy.deepcopy(self.data['profile'])
    def get_window(self, window_id): return copy.deepcopy(self.data['windows'].get(window_id))
    def get_warning_context(self, owner): return {'current_plan':copy.deepcopy(self.data['current_plan'])}
    def save_window(self, window):
        self.data['windows'][window['window_id']] = copy.deepcopy(window)
        if self.fail_window: raise RuntimeError('injected failure')
    def save_policy(self, owner, policy): self.data['profile']['scheduling_policy'] = copy.deepcopy(policy)
    def increment_schedule_revision(self, owner): self.data['profile']['schedule_revision'] += 1


class SettingsServiceTests(unittest.TestCase):
    def setUp(self):
        self.store = SettingsStore()
        self.ctx = TrustedContext('req-settings', Principal(USER), approval_action_id=APPROVAL,
                                  idempotency_key='key', conversation_id=CONV, message_id=MSG)
        self.warnings = [{'code':'PLAN_AFFECTED','message':'Review','field':None,'details':{}}]
        self.service = SettingsService(self.store, validate_window=lambda w: [],
            warnings=lambda snapshot, change: copy.deepcopy(self.warnings), clock=lambda:NOW, id_factory=lambda:WINDOW_ID)

    def authorize(self, op, args, effective_policy=None):
        ref = {'action_id':ACTION,'action_version':1,'target_type':'PENDING_ACTION','target_id':ACTION,'target_version':1}
        decision = {'schema_version':'1.1','conversation_id':CONV,'action_reference':ref,'decision':'APPROVE'}
        self.store.data['pending'][ACTION] = {'action_id':ACTION,'user_id':USER,'conversation_id':CONV,
            'version':1,'state':'AWAITING_CONFIRMATION','requires_review':False,'intent':op.upper(),
            'draft_arguments':copy.deepcopy(args)}
        self.store.data['reviews'][(ACTION,1)] = {'user_id':USER,'conversation_id':CONV,'action_id':ACTION,
            'action_version':1,'target_id':ACTION,'target_version':1,
            'displayed_action':{'operation':op,'arguments':copy.deepcopy(args),'effective_policy':copy.deepcopy(effective_policy)}}
        self.store.data['decisions'][APPROVAL] = {'user_id':USER,'conversation_id':CONV,'source':'CHAT',
            'source_message_id':MSG,'decision':copy.deepcopy(decision)}
        self.store.data['decision_sources'][APPROVAL] = {'user_id':USER,'conversation_id':CONV,'source':'CHAT',
            'source_message_id':MSG,'decision':copy.deepcopy(decision)}

    def test_add_update_archive_and_no_plan_mutation(self):
        op='set_availability'; a=arguments(op); self.authorize(op,a)
        response = Dispatcher(settings_handlers(self.service)).dispatch({'schema_version':'1.1','operation':op,'arguments':a},self.ctx)
        self.assertEqual(response['outcome'],'COMMITTED',response)
        self.assertEqual(response['warnings'], self.warnings)
        self.assertEqual(response['data']['kind'],'AVAILABILITY')
        self.assertEqual(self.store.data['profile']['schedule_revision'],1)
        self.assertEqual(self.store.data['current_plan'],{'unchanged':True})
        for change, version in [('UPDATE',1),('ARCHIVE',2)]:
            a={'change_type':change,'window_id':WINDOW_ID,'expected_window_version':version,
               'window':arguments(op)['window'] if change=='UPDATE' else None}
            self.authorize(op,a)
            ctx=TrustedContext('r',Principal(USER),approval_action_id=APPROVAL,idempotency_key=change,conversation_id=CONV,message_id=MSG)
            data,_=self.service.change_window(op,a,ctx)
            self.assertEqual(data['version'],version+1)
        self.assertIsNotNone(self.store.data['windows'][WINDOW_ID]['archived_at'])
        self.assertEqual(self.store.data['profile']['schedule_revision'],3)

    def test_policy_merge_replay_and_conflict(self):
        op='set_scheduling_preferences'; a={'policy_patch':{'min_block_minutes':120,'max_block_minutes':120},'expected_schedule_revision':0}
        full={**self.store.data['profile']['scheduling_policy'],**a['policy_patch']}
        self.authorize(op,a,full)
        data,warnings=self.service.set_preferences(a,self.ctx)
        self.assertEqual(data['scheduling_policy'],full)
        self.assertEqual(data['schedule_revision'],1)
        self.assertEqual(self.service.set_preferences(a,self.ctx),(data,warnings))
        self.assertEqual(self.store.data['profile']['schedule_revision'],1)
        with self.assertRaises(TaskError) as caught:
            self.service.set_preferences({**a,'policy_patch':{'max_block_minutes':130}},self.ctx)
        self.assertEqual(caught.exception.code,'IDEMPOTENCY_CONFLICT')

    def test_wrong_source_review_version_and_owner_block(self):
        op='set_availability'; a=arguments(op)
        for record, field, value, code in [('pending','requires_review',True,'ACTION_REVIEW_REQUIRED'),
            ('pending','version',2,'ACTION_REVIEW_REQUIRED'),('decisions','user_id',OTHER,'FORBIDDEN'),
            ('reviews','displayed_action',{},'ACTION_REVIEW_REQUIRED'),('decision_sources','source_message_id',OTHER,'FORBIDDEN')]:
            with self.subTest(record=record,field=field):
                self.authorize(op,a)
                key=(ACTION,1) if record=='reviews' else ACTION if record=='pending' else APPROVAL
                self.store.data[record][key][field]=value
                with self.assertRaises(TaskError) as caught: self.service.change_window(op,a,self.ctx)
                self.assertEqual(caught.exception.code,code)
                self.assertEqual(self.store.data['windows'],{})

    def test_wrong_kind_stale_revision_and_rollback(self):
        op='set_busy_interval'; a=arguments('set_availability'); self.authorize(op,a)
        with self.assertRaises(TaskError): self.service.change_window(op,a,self.ctx)
        op='set_scheduling_preferences'; a={'policy_patch':{'break_minutes':2},'expected_schedule_revision':1}
        self.authorize(op,a,{**self.store.data['profile']['scheduling_policy'],**a['policy_patch']})
        with self.assertRaises(TaskError) as caught: self.service.set_preferences(a,self.ctx)
        self.assertEqual(caught.exception.code,'STALE_ENTITY_VERSION')
        op='set_availability'; a=arguments(op); self.authorize(op,a); before=copy.deepcopy(self.store.data)
        self.store.fail_window=True
        with self.assertRaises(RuntimeError): self.service.change_window(op,a,self.ctx)
        self.assertEqual(self.store.data,before)

    def test_busy_window_cross_owner_stale_and_validator(self):
        op='set_busy_interval'
        a=arguments('set_availability')
        a['window']['kind']='BUSY'
        self.authorize(op,a)
        data,_=self.service.change_window(op,a,self.ctx)
        self.assertEqual(data['kind'],'BUSY')
        update={'change_type':'UPDATE','window_id':WINDOW_ID,'expected_window_version':1,'window':a['window']}
        self.authorize(op,update)
        ctx=TrustedContext('r',Principal(USER),approval_action_id=APPROVAL,idempotency_key='new',conversation_id=CONV,message_id=MSG)
        self.store.data['windows'][WINDOW_ID]['user_id']=OTHER
        with self.assertRaises(TaskError) as caught: self.service.change_window(op,update,ctx)
        self.assertEqual(caught.exception.code,'FORBIDDEN')
        self.store.data['windows'][WINDOW_ID]['user_id']=USER
        self.store.data['windows'][WINDOW_ID]['version']=2
        with self.assertRaises(TaskError) as caught: self.service.change_window(op,update,ctx)
        self.assertEqual(caught.exception.code,'STALE_ENTITY_VERSION')
        self.store.data['windows'][WINDOW_ID]['version']=1
        self.service.validate_window=lambda window: [{'code':'invalid'}]
        with self.assertRaises(TaskError) as caught: self.service.change_window(op,update,ctx)
        self.assertEqual(caught.exception.code,'INVALID_PARAMETER')

    def test_draft_arguments_and_full_policy_must_match_review(self):
        op='set_scheduling_preferences'; a={'policy_patch':{'max_block_minutes':120},'expected_schedule_revision':0}
        full={**self.store.data['profile']['scheduling_policy'],**a['policy_patch']}
        self.authorize(op,a,full)
        self.store.data['reviews'][(ACTION,1)]['displayed_action']['effective_policy']['break_minutes']=0
        with self.assertRaises(TaskError) as caught: self.service.set_preferences(a,self.ctx)
        self.assertEqual(caught.exception.code,'ACTION_REVIEW_REQUIRED')
        self.authorize(op,a,full)
        self.store.data['pending'][ACTION]['draft_arguments']['policy_patch']['max_block_minutes']=130
        with self.assertRaises(TaskError) as caught: self.service.set_preferences(a,self.ctx)
        self.assertEqual(caught.exception.code,'ACTION_REVIEW_REQUIRED')

    def test_window_replay_after_commit_and_key_conflict(self):
        op='set_availability'; a=arguments(op); self.authorize(op,a)
        first=self.service.change_window(op,a,self.ctx)
        self.assertEqual(self.store.data['pending'][ACTION]['state'],'COMPLETED')
        self.assertEqual(self.service.change_window(op,a,self.ctx),first)
        self.assertEqual(self.store.data['profile']['schedule_revision'],1)
        changed=copy.deepcopy(a); changed['window']['label']='different'
        with self.assertRaises(TaskError) as caught: self.service.change_window(op,changed,self.ctx)
        self.assertEqual(caught.exception.code,'IDEMPOTENCY_CONFLICT')
        self.assertEqual(len(self.store.data['windows']),1)

    def test_window_replay_does_not_return_foreign_owner(self):
        op='set_availability'; a=arguments(op); self.authorize(op,a)
        self.service.change_window(op,a,self.ctx)
        record=self.store.data['idempotency'][(USER,op,'key')]
        record['result']['data']['user_id']=OTHER
        with self.assertRaises(TaskError) as caught: self.service.change_window(op,a,self.ctx)
        self.assertEqual(caught.exception.code,'INTERNAL_ERROR')

    def test_direct_service_missing_approval_and_bad_conversation(self):
        op='set_availability'; a=arguments(op); self.authorize(op,a)
        cases=[(TrustedContext('r',Principal(USER),idempotency_key='k',conversation_id=CONV,message_id=MSG),'APPROVAL_REQUIRED'),
               (TrustedContext('r',Principal(USER),approval_action_id=APPROVAL,idempotency_key='k',conversation_id=None,message_id=MSG),'FORBIDDEN'),
               (TrustedContext('r',None,approval_action_id=APPROVAL,idempotency_key='k',conversation_id=CONV,message_id=MSG),'FORBIDDEN')]
        for ctx, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(TaskError) as caught: self.service.change_window(op,a,ctx)
                self.assertEqual(caught.exception.code,code)
                self.assertEqual(self.store.data['windows'],{})

    def test_invalid_or_empty_policy_patch_cannot_write(self):
        for patch in ({}, {'min_block_minutes':100}, {'allow_short_final_block':1}):
            with self.subTest(patch=patch):
                a={'policy_patch':patch,'expected_schedule_revision':0}
                self.authorize('set_scheduling_preferences',a,self.store.data['profile']['scheduling_policy'])
                with self.assertRaises(TaskError) as caught: self.service.set_preferences(a,self.ctx)
                self.assertEqual(caught.exception.code,'INVALID_PARAMETER')
                self.assertEqual(self.store.data['profile']['schedule_revision'],0)


if __name__ == '__main__': unittest.main()
