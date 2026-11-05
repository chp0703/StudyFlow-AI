from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class Operation:
    writes: bool
    requires_approval: bool = False


OPERATIONS = MappingProxyType({
    'create_task_candidate': Operation(True),
    'confirm_task': Operation(True, True),
    'search_tasks': Operation(False),
    'set_availability': Operation(True, True),
    'set_busy_interval': Operation(True, True),
    'set_scheduling_preferences': Operation(True, True),
    'generate_study_plan': Operation(True),
    'get_study_plan': Operation(False),
    'approve_study_plan': Operation(True, True),
    'reject_study_plan': Operation(True),
})
