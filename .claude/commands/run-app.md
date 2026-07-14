---
description: Start the ReVision server locally for manual testing.
argument-hint: "[--host H] [--port P] [--model M]"
allowed-tools: Bash(revision:*), Bash(python:*)
---

Start the ReVision app. If installed (`pip install -e ".[dev]"`), run:

```
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY revision $ARGUMENTS
```

Without an install, run from source:

```
ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY PYTHONPATH=src python -m revision.cli $ARGUMENTS
```

It serves http://127.0.0.1:8000 by default. Without an API key the UI still
loads and `/api/messages` returns a graceful error — fine for smoke-testing the
frontend. Never put the key in `static/index.html`.
