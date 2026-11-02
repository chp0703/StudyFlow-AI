# DESIGN.md — StudyFlow AI

Guide for teammates. Read before changing UI code.

## 1. What this is

A deterministic React prototype of a student study workspace: Dashboard, Planner, Study, Review, Materials, plus an illustrative copilot. **Everything is demo data** held in memory (resets on reload). No backend, auth, persistence, file parsing, source retrieval or live AI.

Hard rules:
- Keep the demo/source disclaimers. Never present illustrative data as verified learning evidence.
- Do not claim mastery, upload completion, document extraction or live AI.
- No analytics, external services or storage without explicit approval.
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
src/main.tsx        mounts <App/>, imports index.css
src/App.tsx         whole prototype: state, data, primitives, pages
src/brand.css       design tokens (--sf-*)
src/index.css       Tailwind import, @theme, global + component CSS, responsive rules
vite.config.ts      react + tailwind plugins only
```

Generated: `dist/`, `node_modules/` — never edit or commit.

## 4. Architecture

- `App.tsx` is intentionally a single file. It owns navigation, demo state, modals, task editing, planner, timer, quiz, file-name list and copilot messages. Do not split it or add services unless a task requires it.
- Navigation is **state-based** (`page`: Dashboard · Planner · Study · Review · Materials). No router dependency.
- Reuse the local primitives `Button`, `Card`, `Modal` before writing new wrappers.
- File selection stores only names and status labels; nothing is uploaded or parsed.
- Icons: `lucide-react` only.

## 5. Styling

- Styles live in `src/index.css`; tokens in `src/brand.css`. Match existing class naming (`.button`, `.primary`, `.secondary`, `.card`, `.tabs`, `.info-banner`, `.warning-banner`).
- Use `--sf-*` tokens / semantic vars (`--color-primary`, `--color-ink`, `--color-line`…) before adding raw colours.
- Global element defaults go in `@layer base` so Tailwind utilities can override them. Keep `@import`s at the top.
- Palette: primary `#2563EB`, navy `#0F172A`, slate `#64748B`, background `#F8FAFC`, border `#E2E8F0`, success `#10B981`, warning `#F59E0B`, danger `#EF4444`, purple `#8B5CF6`.
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
