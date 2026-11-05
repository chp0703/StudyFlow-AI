# Gemini development through Antigravity CLI

Verified locally on 2026-11-05: official Antigravity CLI `agy` 1.5.1 uses the existing Google sign-in. A real headless request pinned to `gemini-4-argon-high` with `--effort high` returned `SUCCESS` and `AGY_ARGON_READY`. No API key was supplied. This proves that request succeeded, not unlimited quota or future availability.

The separate legacy Gemini CLI 0.67.0 was also tried. Its real OAuth request failed with `UNSUPPORTED_CLIENT`; do not use its earlier login instructions for this workflow. No credentials or private client protocols were extracted.

## Run locally

The repository-local executable is ignored by Git and does not change PATH:

```powershell
Set-Location E:\TDTT\StudyFlow-AI
.\.tools\antigravity-cli\agy.exe --version
.\.tools\antigravity-cli\agy.exe models
.\.tools\antigravity-cli\agy.exe -p 'Reply READY without using tools.' --model gemini-4-argon-high --effort high --mode plan --output-format json
```

If `agy` is already installed on PATH, use `agy` in place of the full executable path. Authentication belongs to the user: if the session expires, launch the official CLI interactively and sign in with the subscribed Google account. Do not paste OAuth codes, tokens or credential files into chat.

## Sol–Gemini loop

- Only one implementer edits the shared workspace. The original GUI WP1 turn finished before CLI implementation resumed.
- Pin `gemini-4-argon-high` and `--effort high`; switch to `gemini-3.8-flash-high` only after a real Argon quota failure. A full context requires a new session with a handoff.
- Pass scoped per-session permissions through `--settings`; allow implementation paths, deny acceptance-test/contract/secret edits and command execution. Sol runs tests and Git separately. Do not use `--dangerously-skip-permissions`.
- Inspect JSON status, response, stderr and the actual diff. Exit zero alone cannot prove edits occurred: tools needing interactive approval may be denied in headless mode.
- Sol owns independent acceptance tests and reviews results before committing. Gemini must report limitations and may not weaken tests.

The product backend continues to use DeepSeek; this CLI is a development tool only.

Official references: [installation](https://antigravity.google/docs/getting-started?tab=cli), [authentication](https://antigravity.google/docs/install?tab=cli), [headless models and results](https://antigravity.google/docs/cli/headless/), [CLI flags](https://antigravity.google/docs/cli/reference/).
