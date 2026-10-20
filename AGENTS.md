# Repository documentation

- Inspect branch, working tree, and recent commits before repository work.
- On `main`, read and update `docs/STATUS.md` for current work and actual validation;
  use `docs/DECISIONS.md` for accepted shared choices and rationale.
- On long-lived variant branches (such as `ics410_l01`), read the shared documents
  and `docs/<branch>/STATUS.md` / `docs/<branch>/DECISIONS.md`. Store variant-only
  work, validation, and decisions in those branch files. Create them if absent.
  Keep shared README, STATUS, and DECISIONS aligned with main unless the user
  explicitly requests shared edits. Use links instead of copying shared history.
- Keep STATUS concise: current state, evidence, gaps, blockers, and next steps.
  Replace stale entries; use Git for detailed history. DECISIONS records accepted
  choices, rationale, superseded alternatives, and unresolved proposals distinctly.
- Treat `README.md` as approval-only: suggest changes, but never edit it without
  explicit user approval for the README change. General implementation or
  documentation requests do not authorize README edits. Its scope is marketing
  and user help; development decisions and implementation details belong elsewhere.
- Keep build/customization details in `DEVELOPMENT.md` and implementation
  contracts in code docstrings. Follow `RELEASE_CHECKLIST.md`
  if present when releasing; do not infer publication from local checks.
- Preserve unrelated changes. Leave work uncommitted unless asked; suggest a
  Conventional Commit message. Push only when explicitly requested.
