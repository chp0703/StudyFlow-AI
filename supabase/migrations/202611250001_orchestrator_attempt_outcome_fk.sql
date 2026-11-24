-- Orchestrator P1: a SESSION_HANDOFF quiz attempt must cite an existing session outcome owned by the same user.
-- NOT VALID: new and updated rows are checked; legacy rows are left untouched (validate after cleanup if any exist).
alter table app_private.session_outcome
    add constraint session_outcome_user_outcome_key unique (user_id, outcome_id);

alter table app_private.quiz_attempts
    add constraint quiz_attempts_session_outcome_fkey
    foreign key (user_id, session_outcome_id)
    references app_private.session_outcome (user_id, outcome_id) not valid;
