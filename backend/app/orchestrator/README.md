# Workflow orchestration

This package contains the active durable workflow steps used by `backend.app.api.v1.workflow.ActionProcessor`:

- `receipts.py` creates, loads and completes idempotent request receipts.
- `actions.py` prepares and reviews typed pending actions.
- `chat.py` persists chat turns and coordinates untrusted NLU extraction.
- `workflow_ports.py` and `workflow_shared.py` define shared workflow boundaries.

Cross-feature chat intents (learning, quiz, revision) and handoffs extend `chat.py`'s durable queue; they must not add a second orchestration path.

Authentication and HTTP validation stay in `api/v1/`. Database access stays behind the RPC client. Planning uses `app/f1/scheduler/`; workflow code must not create a second scheduling implementation.
