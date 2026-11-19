# API Reference (summary)

Full interactive spec: run the API and open http://localhost:8000/docs
(FastAPI generates the OpenAPI document from the code).

Base path: `/api/v1`. Auth: Bearer JWT, except the OAuth authorize/callback
routes and `/healthz`.

## Auth

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/auth/github` | Redirect to GitHub OAuth authorize URL |
| GET | `/api/v1/auth/github/callback` | Exchange code, mint JWT (503 until OAuth is configured) |
| GET | `/api/v1/auth/google` | Redirect to Google OAuth authorize URL |
| GET | `/api/v1/auth/google/callback` | Exchange code, mint JWT (503 until OAuth is configured) |
| GET | `/api/v1/auth/me` | Current user (id, email, role) |

## Labs

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/labs` | List available labs (from `labs/`) |
| GET | `/api/v1/labs/{slug}` | Lab detail: topology, objectives, guide |
| POST | `/api/v1/labs` | Deploy a session for a lab (`{lab_slug, ttl_seconds?}`) |
| GET | `/api/v1/labs/sessions` | My sessions |
| GET | `/api/v1/labs/sessions/{id}` | Session detail + node states |
| POST | `/api/v1/labs/sessions/{id}/destroy` | Destroy the session |
| POST | `/api/v1/labs/sessions/{id}/snapshot` | Snapshot running configs |
| POST | `/api/v1/labs/sessions/{id}/reset` | Destroy + re-deploy from topology |
| GET | `/api/v1/labs/sessions/{id}/nodes/{node}/console-info` | Console method + command for a node |

Deploy returns `202` with a queue position when the host is full.

## Console (WebSocket)

```
GET /ws/console/{session_id}/{node}?token=<jwt>[&observer=1]
```

Frames are JSON: client sends `{"type": "input", "data": "..."}` and
`{"type": "resize", "cols": 80, "rows": 24}`; the server sends
`{"type": "output", "data": "..."}` and `{"type": "status", "state": ...}`.
Instructors with `observer=1` are read-only; input frames are dropped.

## Images (BYO)

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/images` | List uploaded images |
| POST | `/api/v1/images/upload` | Upload a BYO image tarball (multipart, `license_acknowledged=true` required) |
| POST | `/api/v1/images/{id}/load` | `docker load` the tarball on the lab host |
| DELETE | `/api/v1/images/{id}` | Delete the upload (instructor/admin) |

## Grading

| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/labs/sessions/{id}/grade` | Run all objective checks for the session |
| GET | `/api/v1/labs/sessions/{id}/results` | Stored results for the session |

## Instructor

| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/instructor/students` | Students + per-lab progress summary |
| GET | `/api/v1/instructor/labs/{slug}/progress` | Per-objective results across students |

All instructor routes require role `instructor` or `admin`.

## Health and metrics

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness (no auth) |
| GET | `/metrics` | Prometheus metrics (no auth in dev; restrict in production) |
