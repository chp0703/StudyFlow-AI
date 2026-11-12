"""Kiểm tra artifact contract và bất biến thuần; đây không phải test backend/database."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
FORMATS = FormatChecker()


@FORMATS.checks('iana-timezone')
def valid_timezone(value):
    if not isinstance(value, str):
        return True
    try:
        ZoneInfo(value)
        return True
    except (ValueError, ZoneInfoNotFoundError):
        return False


def read(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def instant(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def semantic_errors(value, path='$'):
    """Chỉ kiểm tra bất biến từ một payload, không cần trạng thái đáng tin cậy."""
    errors = []
    if isinstance(value, list):
        for i, item in enumerate(value):
            errors += semantic_errors(item, f'{path}[{i}]')
        return errors
    if not isinstance(value, dict):
        return errors

    def fail(message):
        errors.append(f'{path}: {message}')

    for k, v in value.items():
        if k in {'start_at', 'end_at', 'available_from_at', 'deadline_at'} and isinstance(v, str):
            dt = instant(v)
            if dt.second or dt.microsecond:
                fail(f'{k} must be aligned to whole minutes')
    if value.get('start_at') is not None and value.get('end_at') is not None:
        if instant(value['end_at']) <= instant(value['start_at']):
            fail('end_at must be after start_at')
    if value.get('recurrence') == 'WEEKLY':
        if value['end_time'] <= value['start_time']:
            fail('WEEKLY end_time must exceed start_time; split overnight intervals')
        if value['valid_until'] and value['valid_until'] <= value['valid_from']:
            fail('valid_until must be after valid_from')
    if 'min_block_minutes' in value and 'max_block_minutes' in value:
        if value['max_block_minutes'] < value['min_block_minutes']:
            fail('max_block_minutes must be >= min_block_minutes after merge')
    if 'estimated_minutes' in value and 'remaining_minutes' in value:
        if value['remaining_minutes'] > value['estimated_minutes']:
            fail('remaining_minutes cannot exceed estimated_minutes')
    if value.get('available_from_at') and value.get('deadline_at'):
        if instant(value['available_from_at']) > instant(value['deadline_at']):
            fail('available_from_at cannot exceed deadline_at')
    if value.get('deadline_precision') == 'DATE' and value.get('deadline_at'):
        from datetime import date, time, timedelta
        expected = datetime.combine(date.fromisoformat(value['deadline_date']) + timedelta(days=1), time(), ZoneInfo(value['deadline_timezone']))
        if instant(value['deadline_at']) != expected:
            fail('DATE cutoff must be local midnight after deadline_date')
    if 'retained_future_minutes' in value:
        total = sum(value[k] for k in ('retained_future_minutes', 'newly_scheduled_minutes', 'unallocated_minutes'))
        if total != value['remaining_minutes']:
            fail('task summary must conserve remaining minutes')
    if set(value) == {'added', 'moved', 'removed', 'unchanged'}:
        flattened = [item for ids in value.values() for item in ids]
        if len(flattened) != len(set(flattened)):
            fail('plan_diff categories must be disjoint')
    if 'coverage' in value and 'task_summaries' in value:
        summaries = value['task_summaries']
        covered = sum(s['retained_future_minutes'] + s['newly_scheduled_minutes'] for s in summaries)
        missing = sum(s['unallocated_minutes'] for s in summaries)
        if value['coverage'] in {'FULL', 'NO_CHANGE'} and missing:
            fail('FULL/NO_CHANGE cannot hide unallocated work')
        if value['coverage'] == 'PARTIAL' and (not covered or not missing):
            fail('PARTIAL requires covered and unallocated work')
        if value['coverage'] == 'NONE' and (covered or not missing):
            fail('NONE requires unallocated demand and no covered work')
        if value['coverage'] == 'NO_CHANGE' and 'plan_diff' in value:
            if any(value['plan_diff'][k] for k in ('added', 'moved', 'removed')):
                fail('NO_CHANGE cannot contain changes')
    if 'proposal_id' in value and 'payload' in value:
        payload = value['payload']
        if payload['coverage'] not in {'FULL', 'PARTIAL'}:
            fail('persisted proposal must have FULL/PARTIAL coverage')
        if not any(payload['plan_diff'][k] for k in ('added', 'moved', 'removed')):
            fail('persisted proposal must change the snapshot')
        if any(b['user_id'] != value['user_id'] for b in payload['study_blocks']):
            fail('proposal blocks must have the same owner')
    blocks = value.get('study_blocks', [])
    if blocks:
        ids = [b['block_id'] for b in blocks]
        if len(ids) != len(set(ids)):
            fail('block IDs must be unique within one snapshot')
        ordered = sorted(blocks, key=lambda b: instant(b['start_at']))
        if any(instant(a['end_at']) > instant(b['start_at']) for a, b in zip(ordered, ordered[1:])):
            fail('blocks overlap within one snapshot')
    if value.get('kind') == 'PLAN_VIEW' and value['plan']:
        plan = value['plan']
        if any(b['plan_id'] != plan['plan_id'] or b['user_id'] != plan['user_id'] for b in blocks):
            fail('PlanView blocks must belong to its plan and owner')
    if value.get('kind') == 'ACTION_PRESENTATION':
        action = value['pending_action']
        for key, id_key in [('candidate', 'candidate_id'), ('proposal', 'proposal_id')]:
            target = value[key]
            if target and (target['user_id'] != action['user_id'] or target[id_key] != action[id_key]):
                fail('presentation target must match pending action and owner')
        command = value['normalized_command']
        if command and command['operation'] == 'set_scheduling_preferences' and value['effective_policy'] is None:
            fail('policy confirmation must present the full effective policy')
    if value.get('state') == 'AWAITING_APPROVAL' and 'result' in value:
        result = value['result']
        if result['outcome'] not in {'DRAFTED', 'PROPOSED'}:
            fail('approval prompt must present a draft or proposal')
        reference = value['action_reference']
        data = result['data']
        if data.get('kind') == 'ACTION_PRESENTATION':
            action = data['pending_action']
            if reference['action_id'] != action['action_id'] or reference['action_version'] != action['version']:
                fail('ActionReference must bind the displayed action/version')
            if reference['target_type'] == 'PENDING_ACTION':
                target = action
                id_key = 'action_id'
            else:
                key = 'candidate' if reference['target_type'] == 'TASK_CANDIDATE' else 'proposal'
                target = data[key]
                id_key = 'candidate_id' if key == 'candidate' else 'proposal_id'
        else:
            target = data
            id_key = 'proposal_id' if reference['target_type'] == 'PLAN_PROPOSAL' else 'candidate_id'
        if not target or target.get(id_key) != reference['target_id'] or target.get('version') != reference['target_version']:
            fail('ActionReference must bind the displayed target/version')
    if 'http_operation' in value and value.get('state') == 'COMPLETED':
        if value.get('response') is None or value.get('http_status') is None:
            fail('completed API receipt requires a response and status')
    if 'extraction' in value and 'depends_on' in value:
        intents = value['extraction'].get('intents', []) if isinstance(value['extraction'], dict) else []
        depends_on = value['depends_on']
        if isinstance(depends_on, list):
            if len(depends_on) != len(intents):
                fail('depends_on must have exactly one dependency list per extracted intent')
            for idx, deps in enumerate(depends_on):
                if isinstance(deps, list):
                    if len(deps) != len(set(deps)):
                        fail(f'depends_on[{idx}] cannot contain duplicate intent indices')
                    if any((not isinstance(d, int) or isinstance(d, bool) or d < 0 or d >= idx) for d in deps):
                        fail(f'depends_on[{idx}] must only reference earlier intent indices 0..{idx - 1}')
    if 'extraction' in value and 'cursor' in value and 'completed_steps' in value:
        intents = value['extraction'].get('intents', []) if isinstance(value['extraction'], dict) else []
        cursor = value['cursor']
        steps = value['completed_steps']
        if isinstance(cursor, int) and not isinstance(cursor, bool):
            if cursor > len(intents):
                fail('continuation cursor cannot exceed extracted intent count')
            if isinstance(steps, list):
                if len(steps) != cursor:
                    fail('completed_steps length must equal continuation cursor')
                for idx, step in enumerate(steps):
                    if isinstance(step, dict) and step.get('intent_index') != idx:
                        fail('completed_steps must have contiguous intent_index values 0..cursor-1')
            if cursor == len(intents) and value.get('awaiting_reference') is not None:
                fail('completed continuation queue cannot have an awaiting_reference')
    if 'extraction' in value and isinstance(value.get('receipt_binding'), dict):
        if value['receipt_binding'].get('http_operation') not in {'send_message', 'prepare_action'}:
            fail('only send_message or prepare_action may initialize a workflow continuation')
    if value.get('transition') == 'ADVANCE' and isinstance(value.get('outcome'), dict):
        if value['outcome'].get('intent_index') != value.get('expected_cursor'):
            fail('ADVANCE outcome intent_index must equal expected_cursor')
    if {'intent_index', 'step_key', 'disposition', 'operation', 'result', 'error'} <= set(value):
        disp = value['disposition']
        if disp == 'FAILED' and value.get('error') is None:
            fail('FAILED step outcome requires error')
        if disp == 'SUCCEEDED':
            if value.get('operation') is None or value.get('result') is None or value.get('error') is not None:
                fail('SUCCEEDED step outcome requires operation, result, and error=null')
            elif isinstance(value.get('result'), dict) and value['result'].get('outcome') not in {'READ', 'COMMITTED', 'PROPOSED'}:
                fail('SUCCEEDED step outcome result must be a terminal/non-draft ToolResult')
        if disp == 'DEPENDENCY_CANCELLED' and (value.get('operation') is not None or value.get('result') is not None):
            fail('DEPENDENCY_CANCELLED step outcome cannot carry a domain operation or result')
        if disp == 'REJECTED':
            if value.get('error') is not None:
                fail('REJECTED step outcome requires error=null')
            if value.get('operation') is not None and value.get('operation') != 'reject_study_plan':
                fail('REJECTED step outcome with domain operation must use reject_study_plan')
    if {'pending_action', 'candidate', 'proposal', 'last_presentation', 'presentation_source_message'} <= set(value):
        action = value['pending_action']
        if isinstance(action, dict):
            for key, id_key in [('candidate', 'candidate_id'), ('proposal', 'proposal_id')]:
                target = value.get(key)
                if isinstance(target, dict) and (target.get('user_id') != action.get('user_id') or target.get(id_key) != action.get(id_key)):
                    fail('workflow action target must match pending_action owner and target id')
            pres = value.get('last_presentation')
            src = value.get('presentation_source_message')
            if isinstance(pres, dict):
                if pres.get('user_id') != action.get('user_id') or pres.get('action_id') != action.get('action_id'):
                    fail('last_presentation must match pending_action owner and action_id')
                if (pres.get('source_message_id') is None) != (src is None):
                    fail('presentation_source_message must be present iff last_presentation.source_message_id is non-null')
                if isinstance(src, dict) and (src.get('message_id') != pres.get('source_message_id') or src.get('user_id') != action.get('user_id') or src.get('conversation_id') != action.get('conversation_id')):
                    fail('presentation_source_message must match last_presentation and pending_action')
            elif src is not None:
                fail('presentation_source_message requires last_presentation')
    if {'conversation_id', 'active_action', 'selected_action', 'source_message', 'read_at'} <= set(value):
        conv_id = value.get('conversation_id')
        for act_key in ('active_action', 'selected_action'):
            act_ctx = value.get(act_key)
            if isinstance(act_ctx, dict) and isinstance(act_ctx.get('pending_action'), dict):
                if act_ctx['pending_action'].get('conversation_id') != conv_id:
                    fail(f'{act_key} must belong to the requested conversation_id')
        if isinstance(value.get('active_action'), dict) and isinstance(value['active_action'].get('pending_action'), dict):
            if value['active_action']['pending_action'].get('state') not in {'AWAITING_CLARIFICATION', 'AWAITING_CONFIRMATION', 'AWAITING_APPROVAL'}:
                fail('active_action must be in an awaiting state')
        if isinstance(value.get('source_message'), dict) and value['source_message'].get('conversation_id') != conv_id:
            fail('source_message must belong to the requested conversation_id')
    for k, v in value.items():
        errors += semantic_errors(v, f'{path}.{k}')
    return errors


def validate_instance(definitions, name, value, semantic=True):
    schema = {'$schema': 'https://json-schema.org/draft/2020-12/schema', '$defs': definitions, '$ref': '#/$defs/' + name}
    errors = [f'{list(e.absolute_path)}: {e.message}' for e in Draft202012Validator(schema, format_checker=FORMATS).iter_errors(value)]
    return errors or (semantic_errors(value) if semantic else [])


def main():
    bundle = read('schemas/f1.schema.json')
    definitions = bundle['$defs']
    Draft202012Validator.check_schema(bundle)
    for definition in definitions.values():
        Draft202012Validator.check_schema(definition)
    service = read('service-contract.json')
    data = read('data-contract.json')
    api = read('openapi.yaml')
    assert service['contract_version'] == '1.0.1'
    assert data['contract_version'] == '1.0.1'
    assert api['info']['version'] == '1.0.1'
    assert bundle['$id'] == 'urn:studyflow:f1:1.1:integration:1.0.1'
    operations = {o['operation'] for o in service['operations']}
    assert len(operations) == 10
    assert operations == set(definitions['Operation']['enum'])
    assert len(api['paths']) == 8
    for op in service['operations']:
        assert op['arguments_schema'] in definitions and op['result_schema'] in definitions
        assert op['idempotency_required'] == (not op['read_only'])
    assert len(service['internal_interfaces']) == 18
    for op in service['internal_interfaces']:
        assert op['arguments_schema'] in definitions and op['data_schema'] in definitions and op['result_schema'] in definitions
        assert op['llm_callable'] is False
    assert len(data['entities']) == 10
    assert len(data['infrastructure_records']) == 5
    for entity in data['entities'] + data['infrastructure_records']:
        props = definitions[entity['schema']]['properties']
        assert set(props) == {c['name'] for c in entity['columns']}, entity['schema']
        assert set(entity['primary_key']) <= set(props)
        for col in entity['columns']:
            assert col['nullable'] == ('anyOf' in props[col['name']])
    source = (ROOT.parent / 'docs/features/planner/schema.md').read_text(encoding='utf-8')
    for entity in data['entities']:
        name = entity['entity']
        match = re.search(r'^### (?:3\.\d+\. )?' + name + r'[^\n]*\n[\s\S]*?```text\n([\s\S]*?)```', source, re.M)
        assert match, f'No authoritative source block for {name}'
        fields = set(re.findall(r'^([a-z_]+):', match[1], re.M))
        fields.add('created_at')
        if name in {'User', 'TaskCandidate', 'AcademicTask', 'TimeWindow', 'PlanProposal'}:
            fields.add('updated_at')
        assert fields == set(definitions[name]['properties']), f'Logical fields drifted: {name}'
    catalog = source.split('### Danh mục operation chính thức')[1].split('### Kiểu arguments')[0]
    assert set(re.findall(r'^\| `([a-z_]+)`', catalog, re.M)) == operations

    # Mọi con trỏ JSON cục bộ/bên ngoài đều phải phân giải được mà không dùng mạng.
    def check_refs(node, document):
        if isinstance(node, list):
            for item in node:
                check_refs(item, document)
        if isinstance(node, dict):
            if '$ref' in node:
                file, pointer = node['$ref'].split('#', 1)
                target = read(file) if file else document
                for part in pointer.lstrip('/').split('/'):
                    target = target[part.replace('~1', '/').replace('~0', '~')]
            for item in node.values():
                check_refs(item, document)
    check_refs(bundle, bundle)
    check_refs(api, api)
    try:
        from openapi_spec_validator import validate
    except ImportError as exc:
        raise SystemExit('Install contracts/requirements-check.txt to validate OpenAPI too.') from exc
    validate(api, base_uri=(ROOT / 'openapi.yaml').as_uri())
    manifest = read('examples/manifest.json')
    for case in manifest['cases']:
        payload = read(case['file'])
        errors = validate_instance(definitions, case['schema'], payload)
        if case['valid'] and errors:
            raise AssertionError(f"{case['file']}: {errors[:3]}")
        if not case['valid'] and not errors:
            raise AssertionError(f"Invalid example accepted: {case['file']}")
        if case.get('expected_error') and not any(case['expected_error'] in e for e in errors):
            raise AssertionError(f"Wrong rejection for {case['file']}: {errors[:3]}")
    print(f"PASS: {len(definitions)} definitions; 8 API paths; 10 tools; 10 entities; {len(manifest['cases'])} positive/negative fixtures; OpenAPI 3.1; source/mapping/reference checks.")
    print('Scope: static contracts and pure payload invariants only. DB/auth/transaction/UI runtime cases remain unrun.')


if __name__ == '__main__':
    main()
