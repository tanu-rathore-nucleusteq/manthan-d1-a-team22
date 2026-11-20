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
| `frontend` | Frontend scaffold (`src/web`), e2e tests (`tests/e2e`), team docs | `main` |

Repository: `tanu-rathore-nucleusteq/manthan-d1-a-team22` on GitHub. It was re-created on 2026-11-20; history from the earlier shared repo was not carried over.

## History

### `frontend`

| Date | Commit | Author | Type | Summary | Area |
| --- | --- | --- | --- | --- | --- |

### `main`

| Date | Commit | Author | Type | Summary | Area |
| --- | --- | --- | --- | --- | --- |
| 2026-11-20 | `74c6505` | tanu-rathore02 | chore | Initialize repository: `.gitignore`, `readme.md` | repo root |
