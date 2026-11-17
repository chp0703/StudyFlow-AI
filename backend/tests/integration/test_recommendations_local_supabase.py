"""B7 HTTP -> signed RPC -> local PostgreSQL checks. Admin SQL only prepares immutable quiz fixtures."""
import base64
import copy
import json
import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import httpx
import psycopg
from psycopg.types.json import Jsonb
from fastapi.testclient import TestClient
from backend.app.core import contract
from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.tests.integration import test_http_local_supabase as local

class RevisionLocalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if any(not os.environ.get(x) for x in local.REQUIRED):
            raise unittest.SkipTest('Local Supabase not configured')
        cls.f=local.LocalSupabaseHttp();cls.f.setUpClass()

    def client(self,transport=None):
        f=self.f
        settings=Settings(supabase_url=f.url,supabase_publishable_key=f.publishable,
            rpc_signing_key_id=f.key_id,rpc_signing_secret_base64=base64.b64encode(f.secret).decode())
        return TestClient(create_app(settings,rpc_transport=transport))

    def ok(self,response):
        self.assertEqual(response.status_code,200,response.text)
        return response.json()

    def fixture(self,app,large=False):
        conv=str(uuid4());text=('TCP UDP source. '*9000) if large else 'TCP connection. UDP datagrams.'
        uploaded=self.ok(self.f.post(app,'/v1/assessment/materials',dict(schema_version='1.1',conversation_id=conv,
            filename='b7.md',mime_type='text/markdown',content_base64=base64.b64encode(text.encode()).decode(),topics=['TCP'])))['data']
        material=uploaded['material']['material_id'];chunks=uploaded['chunks'];uid=self.f.users['a'][1]
        count=6 if large else 1;qids=[]
        if large:self.assertGreaterEqual(len(chunks),60)
        with psycopg.connect(os.environ['F1_DB_TEST_DSN'],autocommit=True) as db:
            for i in range(count):
                qid=str(uuid4());qids.append(qid);sources=chunks[i*10:(i+1)*10] if large else chunks[:1]
                db.execute("insert into app_private.question_drafts(question_id,user_id,conversation_id,material_id,topic,question_type,stem,options,answer_key,source_chunk_ids,prompt_version) values(%s,%s,%s,%s,'TCP','MCQ','TCP?',%s,'A',%s,'b7-test')",
                    (qid,uid,conv,material,Jsonb([dict(option_id='A',text='TCP'),dict(option_id='B',text='UDP')]),Jsonb([c['chunk_id'] for c in sources])))
                for order,c in enumerate(sources):
                    db.execute('insert into app_private.question_draft_sources(question_id,chunk_id,user_id,material_id,source_order) values(%s,%s,%s,%s,%s)',(qid,c['chunk_id'],uid,material,order))
                db.execute("update app_private.question_drafts set status='VERIFIED',version=2,verified_at=clock_timestamp() where question_id=%s",(qid,))
        body=dict(schema_version='1.1',conversation_id=conv,material_id=material,topic='TCP',suggested_minutes=45,priority=0.5)
        return body,qids,chunks

    def submit(self,app,body,qids,selected='B'):
        attempt=self.ok(self.f.post(app,'/v1/assessment/attempts',dict(schema_version='1.1',material_id=body['material_id'],question_ids=qids,origin='MANUAL',session_outcome_id=None)))['data']['attempt_id']
        if selected is not None:
            for qid in qids:
                self.ok(app.put(f'/v1/assessment/attempts/{attempt}/responses/{qid}',json=dict(schema_version='1.1',selected_option_id=selected),headers=self.f.auth('a',**{'Idempotency-Key':f'it-{uuid4().hex}'})))
        self.ok(self.f.post(app,f'/v1/assessment/attempts/{attempt}/submit',dict(schema_version='1.1')))
        return attempt

    def decide(self,app,body,ref,decision='APPROVE',key=None,who='a'):
        return self.f.post(app,'/v1/decisions',dict(schema_version='1.1',conversation_id=body['conversation_id'],action_reference=ref,decision=decision),key=key,who=who)

    def snapshot(self,body):
        with psycopg.connect(os.environ['F1_DB_TEST_DSN']) as db:
            uid=self.f.users['a'][1]
            return tuple(db.execute('select (select count(*) from app_private.academic_tasks where user_id=%s),(select count(*) from app_private.study_plans where user_id=%s),(select schedule_revision from app_private.user_profiles where user_id=%s)',(uid,uid,uid)).fetchone())

    def test_handoff_patch_confirm_and_snapshot_after_restart(self):
        with self.client() as app:
            body,qids,chunks=self.fixture(app);attempt=self.submit(app,body,qids);before=self.snapshot(body)
            key=f'it-{uuid4().hex}';created=self.ok(self.f.post(app,'/v1/assessment/recommendations',body,key=key));ref=created['action_reference']
            rec=created['result']['data']['revision_recommendation'];self.assertEqual(rec['evidence']['attempt_ids'],[attempt])
            self.assertEqual(rec['evidence']['error_count'],1);self.assertEqual(rec['confidence_limit']['level'],'LOW')
            replay=self.ok(self.f.post(app,'/v1/assessment/recommendations',body,key=key));self.assertEqual(replay['result']['data'],created['result']['data'])
            self.assertEqual(self.f.post(app,'/v1/assessment/recommendations',{**body,'priority':1},key=key).status_code,409)
            self.assertEqual(self.f.post(app,'/v1/assessment/recommendations',body,who='b').status_code,404)
            self.submit(app,body,qids,selected='A')
        with self.client() as app:
            review=self.ok(self.f.post(app,f"/v1/actions/{ref['action_id']}/review",dict(schema_version='1.1',conversation_id=body['conversation_id'],expected_action_version=ref['action_version'])))
            self.assertEqual(review['result']['data']['revision_recommendation']['evidence'],rec['evidence'])
            accepted=self.ok(self.decide(app,body,review['action_reference']));self.assertEqual(accepted['state'],'NEEDS_CLARIFICATION')
            pres=accepted['result']['data'];self.assertEqual(pres['revision_recommendation']['status'],'ACCEPTED');self.assertEqual(self.snapshot(body),before)
            candidate=pres['candidate'];action=pres['pending_action']
            partial=dict(schema_version='1.1',conversation_id=body['conversation_id'],expected_action_version=action['version'],expected_candidate_version=candidate['version'],candidate_patch={'start_at':'2027-03-01T01:00:00Z'})
            patched=self.ok(self.f.post(app,f"/v1/actions/{action['action_id']}/review",partial));self.assertEqual(patched['state'],'NEEDS_CLARIFICATION')
            self.assertIsNone(patched['result']['data']['candidate']['slots'].get('deadline_at'))
            pres=patched['result']['data'];patch={**partial,'expected_action_version':pres['pending_action']['version'],'expected_candidate_version':pres['candidate']['version'],'candidate_patch':{'deadline_at':'2027-03-02T01:00:00Z'}}
            patchkey=f'it-{uuid4().hex}';ready=self.ok(self.f.post(app,f"/v1/actions/{action['action_id']}/review",patch,key=patchkey))
            self.assertEqual(ready['state'],'AWAITING_APPROVAL');self.assertEqual(self.snapshot(body),before)
            repeated=self.ok(self.f.post(app,f"/v1/actions/{action['action_id']}/review",patch,key=patchkey));self.assertEqual(repeated['action_reference'],ready['action_reference'])
            self.assertEqual(self.f.post(app,f"/v1/actions/{action['action_id']}/review",patch).status_code,409)
            final=self.ok(self.decide(app,body,ready['action_reference']));self.assertEqual(final['state'],'SUCCEEDED')
            after=self.snapshot(body);self.assertEqual(after,(before[0]+1,before[1],before[2]+1))

    def test_no_data_omitted_invalid_correct_and_foreign_material(self):
        with self.client() as app:
            body,qids,_=self.fixture(app)
            for selected in (None,'Z','A'):
                self.submit(app,body,qids,selected)
                response=self.f.post(app,'/v1/assessment/recommendations',body)
                self.assertEqual(response.status_code,422,response.text)
            other,_,_=self.fixture(app);self.assertEqual(self.f.post(app,'/v1/assessment/recommendations',other).status_code,422)
            self.assertEqual(self.f.post(app,'/v1/assessment/recommendations',{**body,'conversation_id':str(uuid4())}).status_code,404)

    def test_recent_fifty_ties_source_cap_and_no_join_multiplication(self):
        with self.client() as app:
            body,qids,chunks=self.fixture(app,large=True);uid=self.f.users['a'][1];ids=[]
            # Fixed timestamp deliberately tests attempt_id as the tie-breaker. Every DB trigger stays enabled.
            with psycopg.connect(os.environ['F1_DB_TEST_DSN'],autocommit=True) as db:
                for _ in range(51):
                    aid=str(uuid4());ids.append(aid)
                    db.execute("insert into app_private.quiz_attempts(attempt_id,user_id,material_id,origin,question_ids,total_questions) values(%s,%s,%s,'MANUAL',%s,%s)",(aid,uid,body['material_id'],Jsonb(qids),len(qids)))
                    for qid in qids:
                        db.execute("insert into app_private.quiz_responses(response_id,user_id,attempt_id,question_id,selected_option_id,validity,is_correct,graded_at) values(%s,%s,%s,%s,'B','VALID',false,'2026-11-18T00:00:00Z')",(str(uuid4()),uid,aid,qid))
                    db.execute("update app_private.quiz_attempts set status='SUBMITTED',valid_response_count=%s,incorrect_count=%s,score_percent=0,submitted_at='2026-11-18T00:00:00Z' where attempt_id=%s",(len(qids),len(qids),aid))
            made=self.ok(self.f.post(app,'/v1/assessment/recommendations',body));rec=made['result']['data']['revision_recommendation'];e=rec['evidence']
            self.assertEqual(e['attempt_ids'],sorted(ids,reverse=True)[:50]);self.assertEqual((e['valid_response_count'],e['error_count'],e['error_rate']),(300,300,1))
            self.assertEqual(e['chunk_ids'],[c['chunk_id'] for c in sorted(chunks[:60],key=lambda c:(c['page'],c['chunk_index'],c['chunk_id']))[:50]])
            self.assertTrue(any('50 đoạn' in x for x in rec['confidence_limit']['limitations']));self.assertTrue(any('lặp' in x for x in rec['confidence_limit']['limitations']))
            stats=self.ok(app.get('/v1/assessment/topics/stats',params={'material_id':body['material_id']},headers=self.f.auth('a')))
            self.assertEqual(stats['data']['items'][0]['valid_response_count'],306)
            self.ok(self.decide(app,body,made['action_reference'],'REJECT'));self.assertEqual(made['result']['data']['revision_recommendation']['status'],'PROPOSED')

    def test_decision_race_and_candidate_cancel_preserve_accepted_status(self):
        with self.client() as app:
            body,qids,_=self.fixture(app);self.submit(app,body,qids);made=self.ok(self.f.post(app,'/v1/assessment/recommendations',body));before=self.snapshot(body)
        def choose(decision):
            with self.client() as app:return self.decide(app,body,made['action_reference'],decision)
        with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(choose,['APPROVE','REJECT']))
        self.assertEqual(sorted(r.status_code for r in responses),[200,409],[r.text for r in responses]);self.assertEqual(self.snapshot(body),before)
        accepted=next((r.json() for r in responses if r.status_code==200 and r.json()['state']=='NEEDS_CLARIFICATION'),None)
        if accepted:
            pres=accepted['result']['data'];a=pres['pending_action'];c=pres['candidate']
            ref=dict(action_id=a['action_id'],action_version=a['version'],target_type='TASK_CANDIDATE',target_id=c['candidate_id'],target_version=c['version'])
            with self.client() as app:self.ok(self.decide(app,body,ref,'REJECT'))
            with psycopg.connect(os.environ['F1_DB_TEST_DSN']) as db:
                self.assertEqual(db.execute('select status from app_private.revision_recommendations where recommendation_id=%s',(pres['revision_recommendation']['recommendation_id'],)).fetchone()[0],'ACCEPTED')
                self.assertEqual(db.execute('select status from app_private.task_candidates where candidate_id=%s',(c['candidate_id'],)).fetchone()[0],'CANCELLED')

    def test_lost_rpc_response_retries_from_durable_domain_result(self):
        with self.client() as app:
            body,qids,_=self.fixture(app);self.submit(app,body,qids)
        lost=[False]
        def forward(request):
            with httpx.Client() as upstream:response=upstream.send(request)
            if request.url.path.endswith('/create_revision_recommendation') and response.status_code==200 and response.json().get('outcome')=='COMMITTED' and not lost[0]:
                lost[0]=True;raise httpx.ReadError('simulated response loss',request=request)
            return response
        key=f'it-{uuid4().hex}'
        with self.client(httpx.MockTransport(forward)) as app:self.assertEqual(self.f.post(app,'/v1/assessment/recommendations',body,key=key).status_code,503)
        with self.client() as app:
            restored=self.ok(self.f.post(app,'/v1/assessment/recommendations',body,key=key));self.assertEqual(restored['state'],'AWAITING_APPROVAL')
        with psycopg.connect(os.environ['F1_DB_TEST_DSN']) as db:self.assertEqual(db.execute('select count(*) from app_private.revision_recommendations where material_id=%s',(body['material_id'],)).fetchone()[0],1)
