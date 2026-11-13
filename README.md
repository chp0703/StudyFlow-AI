# StudyFlow AI

StudyFlow AI is a student-controlled learning workspace for Vietnamese students. It brings three connected features together: an Intelligent Academic Planner, Learning Assessment & Adaptive Revision, and Daily AI Learning.

Students add tasks, set free and busy time, and ask an AI assistant to plan their week. Every write is shown for review first and only applied after the student confirms it.

> **Plan with AI. Stay in control.**

The repository currently contains the implemented Planner foundation: a React frontend, a FastAPI backend, a deterministic scheduler, a shared contract, Supabase migrations and automated acceptance tests. Assessment and Daily Learning are part of the product scope; their requirements are defined and their implementation is pending.

---

## Table of Contents

- [Demo](#demo)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Available Scripts](#available-scripts)
- [Project Structure](#project-structure)
- [Application Pages](#application-pages)
- [How Planning Works](#how-planning-works)
- [Backend Integration](#backend-integration)
- [Testing](#testing)
- [Development Guidelines](#development-guidelines)
- [Design Reference](#design-reference)
- [License](#license)

---

## Demo

Screens captured from the frontend running in demo mode (no login, in-memory data).

<table>
  <tr>
    <td align="center" width="33%">
      <strong>Homepage</strong><br />
      <img src="docs/screenshots/Homepage.png" alt="StudyFlow AI Homepage" />
    </td>
    <td align="center" width="33%">
      <strong>Planner</strong><br />
      <img src="docs/screenshots/Planner.png" alt="StudyFlow AI Planner" />
    </td>
    <td align="center" width="33%">
      <strong>Study</strong><br />
      <img src="docs/screenshots/Study.png" alt="StudyFlow AI Study workspace" />
    </td>
  </tr>
</table>

---

## Features

- **AI Assistant** — a Vietnamese chat home screen where students describe tasks and working time in natural language. Conversation history is stored in the browser (IndexedDB).
- **Intelligent Academic Planner** — tasks with an exact start time, duration, priority weight and color; working time configured independently for each day; busy intervals; a weekly calendar view.
- **Deterministic scheduling** — plans come from a pure scheduler, not from a model. Proposals expose conflicts, warnings and unscheduled work before approval.
- **Approval-first writes** — chat never approves. Every change becomes a server-issued pending action that the student reviews and confirms.
- **Study workspace** — a prototype page with multiple-choice practice, a materials list and a Q&A panel. Demo mode makes no claim of upload, extraction or live AI.
- **Demo and API modes** — run the UI with local data and no login, or connect it to Supabase Auth and the FastAPI backend.
- **Database as authority** — Postgres functions validate and write state, with immutable plan history and rejection of stale approvals.

---

## Tech Stack

| Layer           | Technology                                                                                                  |
| --------------- | ----------------------------------------------------------------------------------------------------------- |
| Frontend        | React 19, Vite 8, TypeScript, Tailwind CSS, GSAP, lucide-react                                              |
| Backend         | FastAPI, deterministic scheduler, chat/NLU layer                                                            |
| Auth & Database | Supabase Auth, Postgres                                                                                     |
| AI              | DeepSeek for language understanding; model output is treated as untrusted data and normalized on the server |
| Contracts       | OpenAPI and JSON Schema                                                                                     |
| Testing         | `node --test`, Python `unittest`, pgTAP                                                                     |
| CI              | GitHub Actions                                                                                              |

---

## Prerequisites

- **Node.js 22** and npm
- **Git LFS** — images and the logo are stored in Git LFS (`git lfs install` before cloning)
- **Python 3.11 or newer** — backend only
- **Supabase CLI 3.0.0** and **Docker Desktop** — API mode and database tests only

The frontend demo needs only Node.js and npm.

---

## Getting Started

Run the frontend in demo mode:

```bash
git clone https://github.com/chp0703/StudyFlow-AI.git
cd StudyFlow-AI/frontend
npm install
npm run dev
```

The app starts on the Vite dev server (by default `http://localhost:5173`). Without API variables it uses local fallback data, so no backend or login is required.

To run the full stack (API mode), start Supabase and the backend from the repository root:

```bash
supabase start
supabase db reset --yes
python -m pip install -r backend/requirements.txt
uvicorn backend.app.main:create_app --factory --port 8000
```

Register a local RPC signing key with `supabase/scripts/register_dev_key.sql`, then add the variables below to `frontend/.env.local` and run `npm run dev`. `POST /v1/messages` returns `503` until a `DEEPSEEK_API_KEY` is configured.

---

## Environment Variables

API mode needs all three frontend variables. Copy `frontend/.env.example` to `frontend/.env.local`:

```bash
VITE_API_BASE_URL=http://localhost:8000
VITE_SUPABASE_URL=http://127.0.0.1:54321
VITE_SUPABASE_PUBLISHABLE_KEY=
```

> Leave them unset to run the demo. Restart the dev server after changing them. Never commit real values.

The backend reads its settings (`SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `DEEPSEEK_API_KEY`, `RPC_SIGNING_KEY_ID`, `RPC_SIGNING_SECRET_BASE64`, `CORS_ORIGINS` and others) from the root `.env`. See [`.env.example`](.env.example). `.env*` files are gitignored.

---

## Available Scripts

Run frontend commands from `frontend/`:

| Command            | Description                          |
| ------------------ | ------------------------------------ |
| `npm run dev`      | Start the Vite dev server            |
| `npm run build`    | Build the production bundle          |
| `npm run preview`  | Preview the production build locally |
| `npm run format`   | Format the source with oxfmt         |
| `npx tsc --noEmit` | Type-check the project               |

---

## Project Structure

```text
backend/     # FastAPI API, workflow orchestration, RPC client, NLU and scheduler
contracts/   # Approved OpenAPI, JSON Schema, registries and validation fixtures
docs/        # Product, feature and architecture documentation
eval/        # Independent Vietnamese NLU acceptance dataset
frontend/    # React 19 + Vite application
  src/
    api/         # API client, mappers, auth and server data hooks
    components/  # Shared UI (Button, Card, Modal) and home summary
    features/    # assistant, planner and auth feature modules
    pages/       # Planner and Study pages
    styles/      # Brand tokens and page styles
supabase/    # Local configuration, immutable migrations and database tests
worklogs/    # Team implementation logs
```

---

## Application Pages

The app is a single page; navigation is driven by the left sidebar, which can be collapsed.

| Page    | Label        | Description                                                                                      |
| ------- | ------------ | ------------------------------------------------------------------------------------------------ |
| Home    | Trang chủ    | Assistant chat, new conversation and history, plus today's task, deadline and study-time summary |
| Planner | Lập kế hoạch | Weekly calendar, task list, working-time editor and proposal review                              |
| Study   | Học tập      | Multiple-choice practice, study materials and AI Q&A prototype                                   |
| Login   | —            | Supabase email login, shown only in API mode                                                     |

---

## How Planning Works

1. The student describes a task or schedule change in the assistant.
2. The backend extracts structured data with the language model and normalizes it. Model output is untrusted.
3. A server-issued pending action is returned and shown as a proposal with warnings and conflicts.
4. The student reviews the proposal and approves or rejects it.
5. Only `POST /v1/decisions` with the unmodified `action_reference` applies the change, and the database validates and writes it.

---

## Backend Integration

The API exposes the eight Planner endpoints declared in `contracts/openapi.yaml`. Authentication uses Supabase JWTs, and database access goes through signed RPC envelopes.

| Endpoint                                        | Purpose                              |
| ----------------------------------------------- | ------------------------------------ |
| `POST /v1/messages`                             | Send a chat message to the assistant |
| `/v1/actions`, `/v1/actions/{action_id}/review` | Prepare and review a pending action  |
| `POST /v1/decisions`                            | Approve or reject a pending action   |
| `/v1/tasks`                                     | List tasks                           |
| `/v1/time-windows`                              | List working-time windows            |
| `/v1/preferences`                               | Read planner preferences             |
| `/v1/plans`                                     | Read the confirmed plan              |

The frontend never talks to Postgres directly except for Supabase Auth; all data goes through the API. The technical `F1` identifiers remain for compatibility with the implemented Planner contract.

---

## Testing

Run commands from the repository root:

```bash
python -B contracts/check_contract.py
python -B -m unittest discover -s backend/tests/unit -t . -v
python -B -m unittest discover -s backend/tests/acceptance_sol -v
python -B -m unittest discover -s backend/tests/acceptance_api_sol -v
python -B backend/scripts/evaluate_planner.py
```

Frontend (from `frontend/`):

```bash
npx tsc --noEmit
npm run build
node --test src/api/*.test.ts src/features/assistant/*.test.ts src/features/planner/*.test.ts
```

Database, integration and concurrency suites need the local Supabase stack:

```bash
supabase test db
python -B -m unittest discover -s backend/tests/integration -t . -v
python -B -m unittest discover -s supabase/tests_concurrency -v
```

---

## Development Guidelines

- Read [`frontend/DESIGN.md`](frontend/DESIGN.md) before UI changes and [`docs/architecture/overview.md`](docs/architecture/overview.md) before backend or database changes.
- Keep application logic inside its own application and do not change public contracts without updating every consumer (schema, migration, backend, frontend mappers, tests).
- Supabase migrations are append-only. Add a new migration instead of editing an applied one.
- Reuse `components/ui` (Button, Card, Modal) and `lucide-react` icons.
- Commit messages are in English. Pull request titles use a conventional prefix such as `feat(frontend): ...`; descriptions are in Vietnamese.
- Add an entry to `worklogs/<github-username>.md` before every push (see `worklogs/sample.md`).
- Never commit secrets or `.env` files.

---

## Design Reference

Brand assets are documented in [`frontend/public/brand/README.md`](frontend/public/brand/README.md). The README screenshots use a [MacBook Pro 14 realistic mockup](https://www.figma.com/design/bgsV8lwhK0jsmzPYjWGvod/MacBook-Pro-14-%E2%80%94-Realistic-Mockup--Community-?node-id=7-245).

Further documentation: [docs index](docs/README.md), [product requirements](docs/product/requirements.md), [feature map](docs/features/README.md) and [contracts](contracts/README.md).

---

## License

StudyFlow AI is a team project. No open-source license has been declared yet.
