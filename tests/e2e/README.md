# End-to-end tests (Playwright)

Owned by QA. These tests drive the web app in `src/web` at desktop size and phone width.

```bash
cd tests/e2e
npm install
npx playwright install chromium   # one-time
npm test                          # starts src/web's dev server automatically
```

- **Chromium download blocked:** run `$env:PW_CHANNEL = "msedge"; npm test` in PowerShell to use the installed Edge.
- **Testing the running Compose stack:** run `$env:E2E_BASE_URL = "http://localhost:5173"; npm test`. No dev server is started.
- **Report:** `npm run report` opens the HTML report from the last run.

Specs go in `specs/`. Name each test by the behaviour it checks, e.g. `electronics item on day 11 is refused with its reason`.
