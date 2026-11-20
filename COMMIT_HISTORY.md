# Commit History: Team 22

A log of every commit to this team's work, newest first. Add a row each time you commit.

## How to add an entry

1. Commit as usual.
2. Get the short hash: `git log -1 --format=%h`
3. Add a row at the **top** of the table for that branch. Fill in the date, hash, author, type, a summary, and the area changed.
4. Commit this file along with your next change, or on its own as `docs: update commit history`.

To list recent commits ready to paste into a table:

```bash
git log --format='| %ad | `%h` | %an | %s |' --date=short -10
```

## Commit message format

`<type>: <short summary>` in present tense, at most 72 characters. Examples: `feat: add expense form`, `fix: total not updating`.

| Type | Use for |
| --- | --- |
| `feat` | New feature or screen |
| `fix` | Bug fix |
| `test` | Adding or changing tests |
| `docs` | Documentation, README, this file |
| `chore` | Setup, config, dependencies, tooling |
| `refactor` | Code change with no behaviour change |
| `style` | Formatting or CSS only |

## Branches

| Branch | Purpose | Based on |
| --- | --- | --- |
| `main` | Always runs; stories merge here after review | — |
| `frontend` | Frontend scaffold (`src/web`), e2e tests (`tests/e2e`), team docs | `main` at `1475fde` |
| `feature/user-interface` | UI for every persona on a mock backend, then the professional redesign; merged to `main` in PR #8 | `main` |

Repository: `tanu-rathore-nucleusteq/manthan-d1-a-team22` on GitHub. It was re-created on 2026-11-20; history from the earlier shared repo was not carried over.

## History

### `feature/user-interface`

| Date | Commit | Author | Type | Summary | Area |
| --- | --- | --- | --- | --- | --- |
| 2026-11-20 | `ec72bbd` | tanu-rathore02 | chore | Merge `origin/main` (order lookup and eligibility rules, PR #6) into the branch; no conflicts | repo |
| 2026-11-20 | `905f3ef` | tanu-rathore02 | feat | Professional UI redesign: staff sidebar shell with mobile menu, customer hero lookup, split-screen login, inline SVG icon set, refined light/dark tokens, stat tiles with icons, 44px touch targets | `src/web/` |
| 2026-11-20 | `d9e5f87` | tanu-rathore02 | feat | Build the complete UI for all personas on a mock backend | `src/web/` |

### `frontend`

| Date | Commit | Author | Type | Summary | Area |
| --- | --- | --- | --- | --- | --- |
| 2026-11-20 | `12a897f` | tanu-rathore02 | chore | Add Node, Playwright, IDE and Claude entries to `.gitignore`; Prettier `endOfLine: auto` so Windows CRLF checkouts pass | `.gitignore`, `src/web/` |
| 2026-11-20 | `3246e5b` | tanu-rathore02 | docs | Update commit and prompt history | docs |
| 2026-11-20 | `f9aa8f0` | tanu-rathore02 | feat | Frontend scaffold: React 19 + Vite 8 + TypeScript 5.9, ESLint + Prettier, persona feature folders, typed API client; Playwright e2e package; `read-ppt` skill; history files | `src/web/`, `tests/e2e/`, `.claude/`, docs |

### `main`

| Date | Commit | Author | Type | Summary | Area |
| --- | --- | --- | --- | --- | --- |
| 2026-11-20 | `1475fde` | Akash Ping | docs | Add API and gateway READMEs | `src/api/`, `src/gateway/` |
| 2026-11-20 | `554496f` | Akash Ping | test | Add test folder layout | `tests/` |
| 2026-11-20 | `7c5c59a` | Akash Ping | feat | Add mock payment gateway service structure and DTOs | `src/gateway/` |
| 2026-11-20 | `358dccb` | Akash Ping | chore | Add API container, requirements and start script | `src/api/` |
| 2026-11-20 | `738a8ee` | Akash Ping | feat | Add request, response and internal DTOs | `src/api/` |
| 2026-11-20 | `3e8b3a0` | Akash Ping | feat | Add domain enums for returns, refunds and roles | `src/api/` |
| 2026-11-20 | `98601cc` | Akash Ping | chore | Add API package structure with layer placeholders | `src/api/` |
| 2026-11-20 | `324c5a8` | Akash Ping | chore | Add repository tooling for Black, Ruff and pytest | repo root |
