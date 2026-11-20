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

    def fixture(self,app,large=False,*,link_sources=True):
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
                for order,c in enumerate(sources if link_sources else []):
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

    @staticmethod
    def seed_submitted_incorrect_attempt(db, uid, material_id, qids):
        attempt_id = str(uuid4())
        db.execute(
            "insert into app_private.quiz_attempts(attempt_id,user_id,material_id,origin,question_ids,total_questions,omitted_count) "
            "values(%s,%s,%s,'MANUAL',%s,%s,%s)",
            (attempt_id, uid, material_id, Jsonb(qids), len(qids), len(qids)),
        )
        for qid in qids:
            db.execute(
                "insert into app_private.quiz_responses(response_id,user_id,attempt_id,question_id,selected_option_id,validity,is_correct,graded_at) "
                "values(%s,%s,%s,%s,'B','VALID',false,'2026-11-18T00:00:00Z')",
                (str(uuid4()), uid, attempt_id, qid),
            )
        db.execute(
            "update app_private.quiz_attempts set status='SUBMITTED',valid_response_count=%s,incorrect_count=%s,"
            "omitted_count=0,score_percent=0,submitted_at='2026-11-18T00:00:00Z' where attempt_id=%s",
            (len(qids), len(qids), attempt_id),
        )
        return attempt_id

    @staticmethod
    def stored_choices_and_evidence(recommendation_id):
        with psycopg.connect(os.environ['F1_DB_TEST_DSN']) as db:
            return db.execute(
                'select suggested_minutes, priority::float8, evidence from app_private.revision_recommendations '
                'where recommendation_id = %s',
                (recommendation_id,),
            ).fetchone()

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
            tampered=self.decide(app,body,{**ref,'target_id':str(uuid4())})
            self.assertEqual(tampered.status_code,409,tampered.text)
            self.assertEqual(tampered.json()['error']['code'],'APPROVAL_REQUIRED')
            rec=created['result']['data']['revision_recommendation'];self.assertEqual(rec['evidence']['attempt_ids'],[attempt])
            self.assertEqual(rec['evidence']['error_count'],1);self.assertEqual(rec['confidence_limit']['level'],'LOW')
            replay=self.ok(self.f.post(app,'/v1/assessment/recommendations',body,key=key));self.assertEqual(replay['result']['data'],created['result']['data'])
            self.assertEqual(self.f.post(app,'/v1/assessment/recommendations',{**body,'priority':1},key=key).status_code,409)
            self.assertEqual(self.f.post(app,'/v1/assessment/recommendations',body,who='b').status_code,404)
            self.submit(app,body,qids,selected='A')
        with self.client() as app:
            replay = self.f.post(app, '/v1/assessment/recommendations', body, key=key)
            self.assertEqual(replay.headers.get('Idempotency-Replayed'), 'true')
            self.assertEqual(self.ok(replay)['result']['data'], created['result']['data'])
            review=self.ok(self.f.post(app,f"/v1/actions/{ref['action_id']}/review",dict(schema_version='1.1',conversation_id=body['conversation_id'],expected_action_version=ref['action_version'])))
            self.assertEqual(review['result']['data']['revision_recommendation']['evidence'],rec['evidence'])
            accepted=self.ok(self.decide(app,body,review['action_reference']));self.assertEqual(accepted['state'],'NEEDS_CLARIFICATION')
            pres=accepted['result']['data'];self.assertEqual(pres['revision_recommendation']['status'],'ACCEPTED');self.assertEqual(self.snapshot(body),before)
            blocked=self.f.post(app,'/v1/assessment/recommendations',body)
            self.assertEqual(blocked.status_code,409,blocked.text)
            self.assertEqual(blocked.json()['error']['code'],'ACTION_REVIEW_REQUIRED')
            candidate=pres['candidate'];action=pres['pending_action']
            self.assertEqual(candidate['slots']['estimated_minutes'], body['suggested_minutes'])
            self.assertEqual(candidate['slots']['priority'], body['priority'])
            partial=dict(schema_version='1.1',conversation_id=body['conversation_id'],expected_action_version=action['version'],expected_candidate_version=candidate['version'],candidate_patch={'start_at':'2027-03-01T01:00:00Z'})
            patched=self.ok(self.f.post(app,f"/v1/actions/{action['action_id']}/review",partial));self.assertEqual(patched['state'],'NEEDS_CLARIFICATION')
            self.assertIsNone(patched['result']['data']['candidate']['slots'].get('deadline_at'))
            pres=patched['result']['data'];patch={**partial,'expected_action_version':pres['pending_action']['version'],'expected_candidate_version':pres['candidate']['version'],'candidate_patch':{'deadline_at':'2027-03-02T01:00:00Z','estimated_minutes':20,'priority':1}}
            patchkey=f'it-{uuid4().hex}';ready=self.ok(self.f.post(app,f"/v1/actions/{action['action_id']}/review",patch,key=patchkey))
            self.assertEqual(ready['state'],'AWAITING_APPROVAL');self.assertEqual(self.snapshot(body),before)
            repeated=self.ok(self.f.post(app,f"/v1/actions/{action['action_id']}/review",patch,key=patchkey));self.assertEqual(repeated['action_reference'],ready['action_reference'])
            self.assertEqual(self.f.post(app,f"/v1/actions/{action['action_id']}/review",patch).status_code,409)
            final=self.ok(self.decide(app,body,ready['action_reference']));self.assertEqual(final['state'],'SUCCEEDED')
            after=self.snapshot(body);self.assertEqual(after,(before[0]+1,before[1],before[2]+1))
            replayed_create=self.f.post(app,'/v1/assessment/recommendations',body,key=key)
            self.assertEqual(replayed_create.status_code,200,replayed_create.text)
            self.assertEqual(replayed_create.headers['Idempotency-Replayed'],'true')
            replayed_json=replayed_create.json()
            self.assertEqual(replayed_json['result']['data'],created['result']['data'])
            self.assertEqual(replayed_json['action_reference'],ref)
            concluded_review=self.f.post(app,f"/v1/actions/{ref['action_id']}/review",dict(schema_version='1.1',conversation_id=body['conversation_id'],expected_action_version=ready['action_reference']['action_version']))
            self.assertEqual(concluded_review.status_code,409,concluded_review.text)
            self.assertEqual(self.decide(app,body,ref).status_code,409)
            self.assertEqual(self.decide(app,body,ready['action_reference']).status_code,409)
            self.assertEqual(self.f.post(app,f"/v1/actions/{action['action_id']}/review",patch).status_code,409)  # a patch cannot reopen a completed action
            self.assertEqual(self.snapshot(body),after)
            with psycopg.connect(os.environ['F1_DB_TEST_DSN']) as db:
                self.assertEqual(db.execute('select count(*) from app_private.task_candidates where conversation_id=%s',(body['conversation_id'],)).fetchone()[0],1)
                task = db.execute(
                    'select t.estimated_minutes, t.priority from app_private.academic_tasks t '
                    'join app_private.task_candidates c on c.confirmed_task_id = t.task_id '
                    'where c.candidate_id = %s',
                    (candidate['candidate_id'],),
                ).fetchone()
                self.assertEqual(task, (20, 1))
            self.assertEqual(
                self.stored_choices_and_evidence(rec['recommendation_id']),
                (body['suggested_minutes'], body['priority'], rec['evidence']),
            )

    def test_learner_choices_are_validated_and_independent_of_evidence(self):
        with self.client() as app:
            body, qids, _ = self.fixture(app)
            for selected in ('B', 'B', 'B', 'A'):
                self.submit(app, body, qids, selected)
            path = '/v1/assessment/recommendations'
            for field, value in (
                ('suggested_minutes', None), ('priority', None),
                ('suggested_minutes', 14), ('suggested_minutes', 241),
                ('suggested_minutes', 20.5), ('priority', 0.7),
            ):
                with self.subTest(field=field, value=value):
                    invalid = dict(body)
                    if value is None:
                        del invalid[field]
                    else:
                        invalid[field] = value
                    response = self.f.post(app, path, invalid)
                    self.assertEqual(response.status_code, 422, response.text)
                    self.assertEqual(response.json()['error']['code'], 'INVALID_PARAMETER')

            first_evidence = None
            for minutes, priority in ((15, 0.5), (20, 0.1), (60, 1), (240, 1)):
                with self.subTest(minutes=minutes, priority=priority):
                    created = self.ok(self.f.post(app, path, {**body, 'suggested_minutes': minutes, 'priority': priority}))
                    rec = created['result']['data']['revision_recommendation']
                    self.assertEqual((rec['suggested_minutes'], rec['priority']), (minutes, priority))
                    evidence = rec['evidence']
                    self.assertEqual((evidence['error_count'], evidence['valid_response_count']), (3, 4))
                    if first_evidence is None:
                        first_evidence = evidence
                    self.assertEqual(evidence, first_evidence)
                    self.assertEqual(self.stored_choices_and_evidence(rec['recommendation_id']), (minutes, priority, evidence))
                    self.ok(self.decide(app, body, created['action_reference'], 'REJECT'))

    def test_missing_evidence_does_not_create_pending_action(self):
        with self.client() as app:
            body,qids,_=self.fixture(app)
            path = '/v1/assessment/recommendations'
            self.assertEqual(self.f.post(app, path, body).status_code, 422)
            for selected in (None,'Z','A'):
                self.submit(app,body,qids,selected)
                response=self.f.post(app,path,body)
                self.assertEqual(response.status_code,422,response.text)
                self.assertEqual(response.json()['error']['code'], 'INVALID_PARAMETER')
            # A legacy fixture with source IDs but no relational link cannot supply B7 citations.
            unlinked, unlinked_qids, _ = self.fixture(app, link_sources=False)
            self.submit(app, unlinked, unlinked_qids)
            response = self.f.post(app, path, unlinked)
            self.assertEqual(response.status_code, 422, response.text)
            self.assertEqual(response.json()['error']['code'], 'INVALID_PARAMETER')
            for conversation_id in (body['conversation_id'], unlinked['conversation_id']):
                with psycopg.connect(os.environ['F1_DB_TEST_DSN']) as db:
                    self.assertFalse(db.execute(
                        'select 1 from app_private.revision_recommendations where conversation_id = %s',
                        (conversation_id,),
                    ).fetchone())
                    self.assertFalse(db.execute(
                        'select 1 from app_private.pending_actions where conversation_id = %s '
                        "and intent = 'ACCEPT_REVISION_RECOMMENDATION'",
                        (conversation_id,),
                    ).fetchone())
            self.assertEqual(self.f.post(app,'/v1/assessment/recommendations',{**body,'conversation_id':str(uuid4())}).status_code,404)

    def test_recent_fifty_ties_source_cap_and_no_join_multiplication(self):
        with self.client() as app:
            body,qids,chunks=self.fixture(app,large=True);uid=self.f.users['a'][1];ids=[]
            # Fixed timestamp deliberately tests attempt_id as the tie-breaker. Every DB trigger stays enabled.
            with psycopg.connect(os.environ['F1_DB_TEST_DSN'],autocommit=True) as db:
                for _ in range(51):
                    ids.append(self.seed_submitted_incorrect_attempt(db, uid, body['material_id'], qids))
            made=self.ok(self.f.post(app,'/v1/assessment/recommendations',body));rec=made['result']['data']['revision_recommendation'];e=rec['evidence']
            self.assertEqual(e['attempt_ids'],sorted(ids,reverse=True)[:50]);self.assertEqual((e['valid_response_count'],e['error_count'],e['error_rate']),(300,300,1))
            self.assertEqual(e['chunk_ids'],[c['chunk_id'] for c in sorted(chunks[:60],key=lambda c:(c['page'],c['chunk_index'],c['chunk_id']))[:50]])
            self.assertTrue(any('50 đoạn' in x for x in rec['confidence_limit']['limitations']));self.assertTrue(any('lặp' in x for x in rec['confidence_limit']['limitations']))
            stats=self.ok(app.get('/v1/assessment/topics/stats',params={'material_id':body['material_id']},headers=self.f.auth('a')))
            self.assertEqual(stats['data']['items'][0]['valid_response_count'],306)
            rejected=self.ok(self.decide(app,body,made['action_reference'],'REJECT'))
            self.assertEqual(made['result']['data']['revision_recommendation']['status'],'PROPOSED')
            self.assertEqual(rejected['state'],'SUCCEEDED')
            self.assertIsNone(rejected['result']['data']['candidate'])
            self.assertEqual(rejected['result']['data']['revision_recommendation']['status'],'REJECTED')
            with psycopg.connect(os.environ['F1_DB_TEST_DSN']) as db:
                self.assertEqual(db.execute('select status,candidate_id from app_private.revision_recommendations where recommendation_id=%s',(rec['recommendation_id'],)).fetchone(),('REJECTED',None))
                self.assertEqual(db.execute('select count(*) from app_private.task_candidates where conversation_id=%s',(body['conversation_id'],)).fetchone()[0],0)

    def test_decision_race_and_candidate_cancel_preserve_accepted_status(self):
        with self.client() as app:
            body,qids,_=self.fixture(app);self.submit(app,body,qids);made=self.ok(self.f.post(app,'/v1/assessment/recommendations',body));before=self.snapshot(body)
        def choose(decision):
            with self.client() as app:return self.decide(app,body,made['action_reference'],decision)
        with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(choose,['APPROVE','REJECT']))
        self.assertEqual(sorted(r.status_code for r in responses),[200,409],[r.text for r in responses]);self.assertEqual(self.snapshot(body),before)
        accepted=next((r.json() for r in responses if r.status_code==200 and r.json()['state']=='NEEDS_CLARIFICATION'),None)
        if accepted is None:
            with self.client() as app:
                retry=self.ok(self.f.post(app,'/v1/assessment/recommendations',body))
                accepted=self.ok(self.decide(app,body,retry['action_reference']))
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


    def test_fractional_error_rate_survives_review_wire_round_trip(self):
        with self.client() as app:
            body,qids,_=self.fixture(app)
            for choice in ('B','A','A'): self.submit(app,body,qids,choice)
            made=self.ok(self.f.post(app,'/v1/assessment/recommendations',body));ref=made['action_reference']
            rate=made['result']['data']['revision_recommendation']['evidence']['error_rate']
            self.assertAlmostEqual(rate,1/3)
            reviewed=self.ok(self.f.post(app,f"/v1/actions/{ref['action_id']}/review",dict(schema_version='1.1',conversation_id=body['conversation_id'],expected_action_version=ref['action_version'])))
            self.assertEqual(reviewed['result']['data']['revision_recommendation']['evidence']['error_rate'],rate)
            self.ok(self.decide(app,body,reviewed['action_reference'],'REJECT'))

    def test_candidate_patch_and_task_approval_race_has_one_winner(self):
        with self.client() as app:
            body,qids,_=self.fixture(app);self.submit(app,body,qids)
            made=self.ok(self.f.post(app,'/v1/assessment/recommendations',body))
            handed=self.ok(self.decide(app,body,made['action_reference']))['result']['data']
            a=handed['pending_action'];c=handed['candidate']
            form=dict(schema_version='1.1',conversation_id=body['conversation_id'],expected_action_version=a['version'],expected_candidate_version=c['version'],candidate_patch=dict(start_at='2027-03-01T01:00:00Z',deadline_at='2027-03-02T01:00:00Z'))
            ready=self.ok(self.f.post(app,f"/v1/actions/{a['action_id']}/review",form));before=self.snapshot(body)
            pres=ready['result']['data'];form.update(expected_action_version=pres['pending_action']['version'],expected_candidate_version=pres['candidate']['version'],candidate_patch={'priority':1})
        def act(kind):
            with self.client() as app:
                return self.f.post(app,f"/v1/actions/{a['action_id']}/review",form) if kind=='patch' else self.decide(app,body,ready['action_reference'])
        with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(act,['patch','approve']))
        self.assertEqual(sorted(r.status_code for r in responses),[200,409],[r.text for r in responses])
        after=self.snapshot(body)
        self.assertEqual(after[1],before[1]);self.assertIn(after[0]-before[0],(0,1));self.assertEqual(after[2]-before[2],after[0]-before[0])
