---
description: Curl smoke test — health, static UI, and the messages endpoint.
allowed-tools: Bash(curl:*)
---

With the server running (see `/run-app`), verify the three surfaces:

1. Health:  `curl -s localhost:8000/healthz`  → `{"status": "ok"}`
2. UI:      `curl -s -o /dev/null -w '%{http_code}\n' localhost:8000/`  → `200`
3. API:     `curl -s -X POST localhost:8000/api/messages -d '{"prompt":"hi"}'`

`/healthz` never calls Anthropic. `/api/messages` returns a Claude reply if a
key is set, or an `{"error": {"message": ...}}` payload otherwise. Report the
status code and body for each; flag anything that isn't the expected shape.
