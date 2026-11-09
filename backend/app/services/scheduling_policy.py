"""Hợp nhất policy nội bộ cho các service; không lưu dữ liệu hay áp dụng mặc định."""

import json
from pathlib import Path

from jsonschema import Draft202012Validator

_ROOT = Path(__file__).resolve().parents[3]
_DEFS = json.loads((_ROOT / 'contracts/schemas/tool_result.json').read_text(encoding='utf-8'))['$defs']
_POLICY = Draft202012Validator({'$ref': '#/$defs/policy', '$defs': _DEFS})
_PATCH = Draft202012Validator({'$ref': '#/$defs/policy_patch', '$defs': _DEFS})


def merge_scheduling_policy(policy, patch):
    if not _POLICY.is_valid(policy) or not _PATCH.is_valid(patch):
        raise ValueError('Invalid scheduling policy or patch')
    if policy['max_block_minutes'] < policy['min_block_minutes']:
        raise ValueError('Invalid stored scheduling policy')
    merged = {**policy, **patch}
    if merged['max_block_minutes'] < merged['min_block_minutes']:
        raise ValueError('max_block_minutes must be at least min_block_minutes')
    return merged
