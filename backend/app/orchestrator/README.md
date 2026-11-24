# Workflow orchestration

This package contains the active durable workflow steps used by `backend.app.api.v1.workflow.ActionProcessor`:

- `receipts.py` creates, loads and completes idempotent request receipts.
- `actions.py` prepares and reviews typed pending actions.
- `chat.py` persists chat turns and coordinates untrusted NLU extraction.
- `workflow_ports.py` and `workflow_shared.py` define shared workflow boundaries.

Cross-feature chat intents extend `chat.py`'s durable queue; they must not add a second orchestration path:

- `CREATE_QUIZ` generates question drafts for one READY learning material and waits on a `VERIFY_QUESTION_DRAFTS` action.
- `PROPOSE_REVISION` creates a revision recommendation and waits on `ACCEPT_REVISION_RECOMMENDATION`. Approving it creates a draft task, so the same step waits again on that task; a `GENERATE_STUDY_PLAN` step is appended automatically, so confirming the task yields a plan proposal for approval.
- Decisions for these actions (`ActionProcessor.resume_cross_feature`) resume the queue only when the action belongs to it; REST-created actions keep their old behavior.
- `SUMMARIZE_LEARNING` is recognized but answered as unsupported in chat: chat does not create learning sessions with turns yet.

Authentication and HTTP validation stay in `api/v1/`. Database access stays behind the RPC client. Planning uses `app/f1/scheduler/`; workflow code must not create a second scheduling implementation.
