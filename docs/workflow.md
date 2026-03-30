# NLDI-py Development Workflow

Adapted from `~/.claude/feature_branch_workflow.md` for this project.

## Branching model

- `main` — current production code. Untouched during refactor.
- `refactor/v3` — integration branch for the refactor. Functions as "main" for all refactor work.
- Feature branches — short-lived, branch from and merge to `refactor/v3`.
- `refactor/v3` merges to `main` when ready for production cutover.

Tag `pre-refactor` marks the snapshot before the refactor began.

## Feature implementation

1. **Decide** — pick an issue or next item from the phased strategy
2. **Plan** — explore, design the approach, get approval before writing code
3. **Branch + PR** — sync and branch from `refactor/v3`, push, open a PR immediately
   ```
   git checkout refactor/v3 && git pull
   git checkout -b feature/xyz
   git push -u origin feature/xyz
   gh pr create --base refactor/v3 --title "..."
   ```
4. **Comment the plan** — post the implementation plan as the first comment on the PR
5. **Implement** — do the work; multiple commits are fine
6. **Lint + format** — `uv run ruff format . && uv run ruff check --fix .`
7. **Summarize** — add a summary comment on the PR describing what was done
8. **Ready for review** — mark the PR as ready
9. **Cleanup** — after merge, delete local branch
   ```
   git checkout refactor/v3 && git pull && git branch -D feature/xyz
   ```

## Rules

- **Agents never merge** — a human must review and merge all PRs
- **No amending commits** — prefer new commits to keep history clean and reviewable
- **Tests pass before commit** — no exceptions
- **PR is the single source of truth** — plan, commits, and summary all in one place

## Issue vs PR documentation

- **Issue** = the "what" and "why" — problem description, analysis, decision rationale
- **PR** = the "how" — implementation plan, commits, summary of changes

Issues persist as documentation after PRs are merged.

## Release (post-refactor)

1. Bump `version` in `pyproject.toml`
2. Merge `refactor/v3` → `main`
3. Tag: `git tag vX.Y.Z`
4. Push: `git push && git push origin vX.Y.Z`
5. Create release on GitHub
