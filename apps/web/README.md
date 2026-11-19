# netlab web (React + TypeScript + Vite)

## Run

```bash
npm install
npm run dev        # http://localhost:5173 (proxies /api and /ws to :8000)
npm run build      # typecheck + production build
npm run test:e2e   # Playwright (scaffold; live test needs PLAYWRIGHT_LIVE=1)
```

## Auth

The app expects a JWT in `localStorage` under `netlab-token`. In dev, sign
in via the API's OAuth flow (or mint a token for a test user) and store it:

```js
localStorage.setItem('netlab-token', '<jwt>')
```

Set `VITE_API_URL` in `.env` to point at a remote API (default
`http://localhost:8000`).

## Pages

- `/` — lab catalogue + deploy
- `/sessions/:sessionId` — topology canvas (React Flow), live console per
  node (xterm.js over the console WebSocket), objectives + grading, running
  config snapshot browser, student guide
- `/instructor` — students + objectives passed (instructor/admin role)
