# Claude Prompt History: Team 22

A log of the prompts the team gives Claude (chat or Claude Code) and what came out of each. Add an entry for every prompt that produced code, a document, or a decision.

## How to add an entry

1. Copy the template below to the **top** of the History section.
2. Paste the prompt exactly as you sent it.
3. Write what Claude produced, the files it changed, and whether you kept the result.
4. If the work was committed, add the commit hash. It should match a row in [COMMIT_HISTORY.md](COMMIT_HISTORY.md).

Hackathon rule: prompts must contain only synthetic or public data. Never paste client or confidential data into a prompt or into this file.

### Template

```markdown
### P<number>: <short title>

| Date | Author | Tool | Phase | Commit |
| --- | --- | --- | --- | --- |
| YYYY-MM-DD | <name> | Claude Code / Claude chat | Setup / Design / Build / Test / Docs | `<hash>` or — |

**Prompt**
> <exact prompt text>

**Outcome**
- <what Claude did or produced>

**Files changed:** `<paths>`
**Kept?** Yes / Partly (<what changed>) / No (<why>)
```

## History

### P7: Commit and push to the new repo

| Date | Author | Tool | Phase | Commit |
| --- | --- | --- | --- | --- |
| 2026-11-20 | tanu-rathore02 | Claude Code | Setup | `64bb5fe`, `25a2b44` |

**Prompt**
> commit the changes and push to new repo in separate frontend branch

**Outcome**
- `main` holds only `.gitignore` and `readme.md` (`74c6505`). Everything else is on the `frontend` branch.
- Added `.gitattributes` to force LF line endings, so Prettier passes on Windows checkouts.
- Reset `COMMIT_HISTORY.md` for the new repo, then pushed `main` and `frontend` to origin.

**Files changed:** all; `.gitattributes`, `COMMIT_HISTORY.md`
**Kept?** Yes

---

### P6: New git remote

| Date | Author | Tool | Phase | Commit |
| --- | --- | --- | --- | --- |
| 2026-11-20 | tanu-rathore02 | Claude Code | Setup | — |

**Prompt**
> i deleted the git repo, set this as new git remote repo
>
> https://github.com/tanu-rathore-nucleusteq/manthan-d1-a-team22.git

**Outcome**
- Ran `git init -b main` in the team folder `manthan-d1-a-team-22`, so the repo root is the team folder, and added the GitHub repo as `origin`.
- Added a root `.gitignore` covering Python, Node, Playwright, `.env` files and Claude Code personal settings.

**Files changed:** `.gitignore`
**Kept?** Yes

---

### P5: Review architecture doc and build frontend structure

| Date | Author | Tool | Phase | Commit |
| --- | --- | --- | --- | --- |
| 2026-11-20 | tanu-rathore02 | Claude Code | Design / Setup | — |

**Prompt**
> this is the link to the architure design artifact. everything is mentioned here. go through it. and if any change is needed then add the change at the bottom of the artifact under my name section.
>
> \<link to the ReturnRight Implementation Plan artifact\>
>
> and create frontend folder structure according to this architecture design

**Outcome**
- Read the ReturnRight Implementation Plan. It puts the frontend in `src/web` (TypeScript, ESLint + Prettier, built against `/openapi.json`) and end-to-end tests in a top-level `tests/e2e`.
- Moved `frontend/` to `src/web` and converted it to TypeScript 5.9. Replaced oxlint with ESLint + Prettier. Added react-router, TanStack Query, `openapi-fetch` and `openapi-typescript` (`npm run gen:api`).
- Added a structure with one folder per persona (`returns`, `warehouse`, `finance`, `dashboard`, `auth`), routes guarded by staff role, a typed API client, shared loading, empty and error states, and a dev proxy from `/api` to `:8000`.
- Moved Playwright into its own `tests/e2e` package.
- Results: typecheck, lint, Prettier, build and 4 e2e tests (desktop + phone width) passed.
- Added a "Proposed changes" section under my name at the end of the doc. It has 8 changes, each with a Decision dropdown for the tech lead.
- Correction: Vite 8 installs TypeScript 7, but `openapi-typescript` and `typescript-eslint` need TypeScript 5. Pinned 5.9.

**Files changed:** `src/web/**`, `tests/e2e/**`
**Kept?** Yes

---

### P4: Prompt history file

| Date | Author | Tool | Phase | Commit |
| --- | --- | --- | --- | --- |
| 2026-11-20 | tanu-rathore02 | Claude Code | Docs | — |

**Prompt**
> now create a md file for claude prompt history

**Outcome**
- Created this file. It has an entry template and the session's earlier prompts filled in.

**Files changed:** `PROMPT_HISTORY.md`
**Kept?** Yes

---

### P3: Commit history file

| Date | Author | Tool | Phase | Commit |
| --- | --- | --- | --- | --- |
| 2026-11-20 | tanu-rathore02 | Claude Code | Docs | — |

**Prompt**
> create an md file to maintain commit history

**Outcome**
- Created `COMMIT_HISTORY.md`, filled in with the three existing commits grouped by branch.
- Added steps for adding entries, a `git log` command to generate table rows, a commit message format (`feat`, `fix`, `chore`, …), and a branch table.

**Files changed:** `COMMIT_HISTORY.md`
**Kept?** Yes

---

### P2: Skill to read PowerPoint decks

| Date | Author | Tool | Phase | Commit |
| --- | --- | --- | --- | --- |
| 2026-11-20 | tanu-rathore02 | Claude Code | Setup | `68896e4` |

**Prompt**
> add a skill to read ppt

**Outcome**
- Added a project Claude skill, `read-ppt`. It turns a `.pptx` file into Markdown: slide titles, bullets with their levels, tables, image counts, and speaker notes.
- The script uses only the Python standard library, so nothing has to be installed. It runs with `py -3.13`.
- Tested on a generated 3-slide deck with a title slide, nested bullets, speaker notes and a table.

**Files changed:** `.claude/skills/read-ppt/SKILL.md`, `.claude/skills/read-ppt/scripts/read_pptx.py`
**Kept?** Yes

---

### P1: Frontend project setup

| Date | Author | Tool | Phase | Commit |
| --- | --- | --- | --- | --- |
| 2026-11-20 | tanu-rathore02 | Claude Code | Setup | `68896e4` |

**Prompt**
> \<link to the AI Manthan Hackathon Prerequisites Guide (Google Doc)\>
>
> according to this doc. setup the frontend project inside this folder on a separate branch
>
> C:\Users\DELL\Desktop\hackathon\nt-AI-Manthan-hackathon-\manthan-d1-a-team-22

**Outcome**
- Read the prerequisites guide. The Track A frontend stack is React 19 + Vite 7 or later on Node 26.13.1, with Playwright 1.60 or later for UI tests.
- Created the `frontend-setup` branch from `manthan-d1-a-team22`.
- Created a React 19.3 + Vite 8 project in `frontend/`, pinned Node with `.nvmrc` and `engines`, and added Playwright 1.65.1. The Playwright config tests at desktop and phone width and falls back to the installed Edge or Chrome (`PW_CHANNEL`).
- Added a smoke test, `test:e2e` scripts, Playwright entries in `.gitignore`, and a README.
- Results: build, lint, and both e2e tests passed.
- Problem found: `npm` fails in PowerShell on this laptop because `npm.cmd` is missing. Use Git Bash until it is fixed.

**Files changed:** `frontend/` (21 files)
**Kept?** Yes
