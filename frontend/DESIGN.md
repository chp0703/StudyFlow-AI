# DESIGN.md — StudyFlow AI

Guide for teammates. Read before changing UI code.

## 1. What this is

A deterministic React prototype of a student study workspace: AI homepage (chat + progress summary), Planner and Study. Academic data (tasks, files) lives in memory only and starts empty. Conversation history alone is stored in this browser's IndexedDB, as explicitly approved for the history feature. There is no backend, auth, account sync, file parsing, source retrieval or live AI.

Hard rules:
- Keep the demo/source disclaimers. Never present illustrative data as verified learning evidence.
- Do not claim mastery, upload completion, document extraction or live AI.
- No analytics, external services or storage beyond the approved conversation-only IndexedDB history without explicit approval.
- Keep dates, courses, quiz answers and messages clearly illustrative.

## 2. Stack and commands

React 19 · Vite 8 · TypeScript (strict) · Tailwind CSS v4 (`@tailwindcss/vite`) · `lucide-react` icons · oxfmt formatter. Node 22, npm.

| Command | Purpose |
|---|---|
| `npm install` | install |
| `npm run dev` | dev server (`$PORT`, default 5173) |
| `npm run build` | production build to `dist/` |
| `npm run preview` | serve the build |
| `npm run format` | format with oxfmt |

Before opening a PR: `npm run format && npm run build`, and `npx tsc --noEmit`.

## 3. Layout

```text
index.html          document shell, favicons, noindex meta
public/brand/       logo + favicons (served at /brand/...)
src/main.tsx        mounts <App/>, imports styles/index.css
src/App.tsx         shell: navigation, shared state, modals
src/pages/          Planner, Study
src/components/      HomeSummary; ui/ Button, Card, Modal
src/features/assistant/  Assistant UI, assistantService (reply stub), conversationHistory (IndexedDB)
src/features/planner/ rule-based planner agent (chat -> calendar)
src/types/          shared types (Task, assistant contract)
src/utils/          date helpers
src/styles/brand.css       design tokens (--sf-*)
src/styles/index.css       Tailwind import, @theme, global + component CSS, responsive rules
vite.config.ts      react + tailwind plugins only
```

Generated: `dist/`, `node_modules/` — never edit or commit.

## 4. Architecture

- `App.tsx` owns navigation and non-chat demo state. The Assistant is separate because conversation history and persistence require isolated state.
- Navigation is **state-based** (`page`: Assistant · Planner · Study). No router dependency.
- Assistant conversations have stable UUIDs, independent composer drafts and clarification drafts. Restored pending proposals require review before demo acknowledgement. Transcript data never authorizes a backend write.
- IndexedDB uses one record per conversation and a separate active-conversation key. If storage fails, the UI stays usable in memory and announces that reload persistence is unavailable. There is no account synchronization.
- Reuse the local primitives `Button`, `Card`, `Modal` before writing new wrappers.
- File selection stores only names and status labels; nothing is uploaded or parsed.
- Icons: `lucide-react` only.

## 5. Styling

- Styles live in `src/styles/index.css`; tokens in `src/styles/brand.css`. Match existing class naming (`.button`, `.primary`, `.secondary`, `.card`, `.tabs`, `.info-banner`, `.warning-banner`).
- Use `--sf-*` tokens / semantic vars (`--color-primary`, `--color-ink`, `--color-line`…) before adding raw colours.
- Global element defaults go in `@layer base` so Tailwind utilities can override them. Keep `@import`s at the top.
- Palette: primary `#596CF0`, indigo `#5064E9`, purple `#8B5CF6`, pink `#FF6B81`, orange `#FF9F43`, yellow `#FFE066`, teal `#22B8A7`, text-primary `#17203B`, text-secondary `#667085`, background `#F7F8FF`, border `#E5E8F4`.
- Ambient Background: radial glow highlights (yellow `#FFE066` top-right, teal `#22B8A7` bottom-left) over 135deg gradient (`#FBFBFF` -> `#F5F7FF` -> `#FFF8FC`). Card surfaces: `rgba(255,255,255,0.94)` with subtle blur. Brand gradient: `linear-gradient(115deg, #596cf0, #8b5cf6 58%, #d657c7)`.
- Floating Chrome: `.topbar` and `.sidebar` are styled as floating rounded cards with `border-radius: var(--radius-card)`, `border: 1px solid var(--color-line)`, `backdrop-filter: blur(16px)` and floating insets to allow the ambient glowing background to shine around all chrome elements.
- Light logo (`/brand/logo-horizontal-light-transparent.png`) on the light header.

## 6. Accessibility (non-negotiable)

- Semantic HTML first; everything keyboard reachable.
- Keep visible `:focus-visible`, the skip link, modal focus restore + Escape handling, and `aria-label` / `aria-current` / `aria-pressed`.
- Never rely on colour alone for status, deadlines, completion or errors (add icon/text).
- Minimum 44px interactive targets.
- Respect `prefers-reduced-motion` and `forced-colors`; keep responsive breakpoints (1250 / 800 / 480px).
- On page change, move focus to the page heading.

## 7. Change workflow

1. Read the component and its CSS first; grep all callers when touching a shared class, state value or primitive.
2. Smallest change that does the job — no new abstractions, routes, deps or persistence without a concrete need.
3. `npm run format`, `npm run build`, then check the UI in the browser for layout/interaction changes.
4. Report build failures honestly. Never commit secrets, `.env`, or `dist/`.
