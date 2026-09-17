# CLAUDE.md

Guidance for AI assistants (and humans) working in this repository.

## Project overview

**ReVision** is a Claude-powered document toolkit exposed as a single-page web
app with four tools:

- **Fine Print Analyzer** — detects manipulative language and scores risk.
- **Enhance** — rewrites drafts along tone / clarity / persuasiveness spectrums.
- **Translate** — translates across 20+ languages, preserving legal meaning.
- **Jargonary** — simplifies dense text and builds a jargon glossary.

The UI is a static page; a small Python backend serves it and proxies AI
requests to the Anthropic API so the API key stays server-side.

## Architecture

```
browser (static/index.html)  ──POST /api/messages──►  Python server  ──►  Anthropic API
        callClaude()                                   (injects x-api-key,
                                                         chooses the model)
```

Key design decisions:

- **Server-side key.** The browser calls the same-origin `/api/messages`
  endpoint, never `api.anthropic.com` directly. `anthropic_client.py` adds the
  `x-api-key` and `anthropic-version` headers server-side. **Never** move the
  key or a direct Anthropic call into `static/index.html`.
- **Model is server-controlled.** The model id lives in `config.py`
  (`REVISION_MODEL`, default `claude-sonnet-5`), not in the frontend. Use a real
  model id — the original prototype used an invalid one.
- **Zero runtime dependencies.** The backend uses only the standard library
  (`http.server`, `urllib`). Keep it that way unless there's a strong reason;
  `pytest`/`ruff` are dev-only.

## Repository structure

```
.
├── src/revision/
│   ├── __init__.py            # package metadata (__version__)
│   ├── config.py             # Config.from_env(); model/host/port/key/auth/limits
│   ├── anthropic_client.py   # AnthropicClient.create_message() (stdlib urllib)
│   ├── ratelimit.py          # RateLimiter: thread-safe sliding window
│   ├── server.py             # RevisionHandler, create_server(), serve()
│   ├── cli.py                # `revision` console entry point
│   └── static/index.html     # the single-page UI (all four tools)
├── tests/
│   ├── test_config.py
│   ├── test_anthropic_client.py   # mocks urllib.request.urlopen
│   ├── test_ratelimit.py          # limiter unit tests (monkeypatched clock)
│   └── test_server.py             # runs a live server on port 0, fake client
├── .claude/                  # checked-in Claude Code tooling (see "Claude tooling" below)
│   ├── settings.json         # permissions allowlist + PreToolUse/PostToolUse/SessionStart hooks
│   ├── hooks/session-start.sh     # SessionStart: loads .env, installs ReVision dev deps, verifies ezr's toolchain
│   ├── hooks/git-safety-guard.sh  # PreToolUse (Bash): blocks force-push/reset --hard/clean -f/--no-verify/…
│   ├── hooks/secret-scan-precommit.sh # PreToolUse (Bash): blocks `git commit` on a likely-secret staged diff
│   ├── commands/             # custom slash commands (/analyze, /think, /check, /run-app, /prd, …)
│   ├── skills/               # claude-power-practices + dev skills (dev-check, run-app, add-tool, test-and-lint, prompt-library)
│   ├── agents/                # standalone subagents: code-reviewer, test-writer, security-auditor (each read-only/single-purpose)
│   └── README.md             # explains the whole .claude/ setup
├── docs/claude-playbook.md   # full Claude tips + command reference (source of the above)
├── docs/claude-2026-cheatsheet.md # 2026 sheets: 5 surfaces, model stack, core files, app workflow
├── docs/commands-pack.md     # paste-ready prompt for each command (78 of the 84 in .claude/commands/)
├── docs/prompt-library.md    # saved prompts that worked well, maintained by the prompt-library skill
├── docs/command-console.html # interactive searchable console (shareable artifact)
├── mastery-system/index.html # "Mastery Protocol" — standalone 6-levels tool (model tree, prompt formula, core files)
├── claude-md-generator/index.html # guided-form CLAUDE.md builder — static, client-side only, no network calls
├── power-pack/               # "S.L.A.S.H." — standalone distributable (see below)
│   ├── commands/             # 80 free, portable commands (excludes repo-specific dev ones)
│   ├── pro-commands/         # 30 licensed "Pro Pack" commands (unlocked via cli.js --activate KEY)
│   │   └── LICENSE           # proprietary, single-user — NOT MIT, carved out of the root LICENSE
│   ├── skills/               # power-practices skill
│   ├── cli.js                # cross-platform Node installer (npx slash-pack); install/uninstall/status/--activate
│   ├── package.json          # npm-publishable package; license: "SEE LICENSE IN LICENSE" (mixed, not blanket MIT)
│   ├── install.sh            # Unix bash installer (--dry-run, --uninstall, backup)
│   ├── index.html            # product landing page
│   ├── README.md             # standalone product README
│   └── LICENSE               # MIT — everything except pro-commands/ (see notice at top of file)
├── .github/workflows/ci.yml           # ruff + pytest (3.11-3.13) + docker build + `languages`
│   #   `languages` job: ezr's 29-suite gate, the forge (81), the rhyming corpus (35),
│   #   the Java runtime (98) and Rime (74) — the suites the other jobs never touch.
│   #   Each suite step carries `if: !cancelled()`, so one red suite fails the job
│   #   without skipping the other five (it used to hide 288 assertions when it tripped).
├── .github/workflows/deploy-pages.yml # publishes mastery-system/ to GitHub Pages on push to main
├── .github/workflows/publish-image.yml # GHCR image publish — v*.*.* tag or manual; dry_run defaults true
├── .github/workflows/publish-npm.yml  # power-pack/ -> npm as `slash-pack`; manual only, needs NPM_TOKEN
├── .github/workflows/security.yml     # pip-audit (root) + npm audit (power-pack/); push/PR + weekly Mon 06:00 UTC cron
│   # NOTE: CodeQL also runs on every PR — "Analyze (ruby)" and "Analyze (java-kotlin)",
│   # so 14 check runs, not 12. It is GitHub default setup (repo settings), NOT a workflow
│   # in this tree — you will not find a file for it, and the language list grows by itself:
│   # java-kotlin appeared on its own once ezr/5-runtime-java/ landed.
├── .devcontainer/devcontainer.json    # generic universal devcontainer (no repo-specific setup)
├── Dockerfile                # stdlib-only image; binds 0.0.0.0:8000; HEALTHCHECK /healthz
├── .dockerignore
├── pyproject.toml            # hatchling build; pytest + ruff config
├── .env.example              # local env template (ANTHROPIC_API_KEY, GITHUB_TOKEN, …); copy to gitignored .env
├── ezr/                      # Ever / Tapestry — a separate language project (see below)
│   ├── 0-atom-c/ 1-phase-cpp/ 2-interpreter-python/ 3-dsl-ruby/
│   ├── 4-archive-sql/ 6-interface-html/
│   ├── 5-runtime-java/       # the core again, in Java, + a differential harness
│   ├── 7-forge/              # the language forge: 20 front ends, one core
│   ├── tests/                # run_all.py — the 29-suite gate ezr/CLAUDE.md names
│   ├── examples/             # runnable programs, both lineages — start here
│   ├── edapt/ archive/       # adaptive layer; repair archive
│   ├── CLAUDE.md             # ezr's own rules — read it before touching ezr/
│   ├── CORE.md               # the core the forge settled on (the 5-runtime-java language)
│   ├── SEMANTICS.md PIPELINE.md VOWELS.md ABI.md   # the specs `ever run` follows
│   ├── FINDINGS.md           # what was computed, not asserted (research.py corroborates it)
│   ├── .claude/skills/verify/  # directory-scoped skill: how to drive EZR's surfaces
│   └── run.sh                # 22 layers. NOT 7-forge or 5-runtime-java — see below
├── realm/                    # Rime — a language whose grammar rhymes (see below)
│   ├── contract.py           # tokens, the vocabulary, trees, printing
│   ├── lexers.py parsers.py  # 3 scanners x 3 parsers = 9 front ends
│   ├── machine.py            # the stack, the store, the voice
│   ├── rhyme.py              # the rhyme rule, run backwards as a generator
│   ├── realm.py              # the matrix, the laws, the corpus, the CLI
│   ├── realm_test.py         # the gate: 74 assertions
│   └── LANGUAGE.md           # the spec — start here
├── README.md
└── .gitignore
```

> The "zero runtime dependencies" rule above applies to the `src/revision`
> Python backend. An unrelated GitHub Models/Azure AI demo script
> (`package.json` / `sample.js`) previously sat at the repo root; it was
> removed as catalogue cleanup — it had no relationship to ReVision or the
> Claude tooling here, and `security.yml`'s npm audit was auditing it by
> accident instead of the thing that actually ships (`power-pack/`).

## HTTP endpoints

- `GET /` and other paths → static files from `src/revision/static/` (traversal-guarded).
- `GET /healthz` → `{"status": "ok"}`; does not call Anthropic (used by Docker HEALTHCHECK).
- `POST /api/messages` → `{prompt, max_tokens?, stream?}`; enforces optional
  bearer auth, then rate limiting, then proxies to Claude. When `stream` is
  true, the response is `text/event-stream` — the upstream Anthropic SSE
  payload forwarded through byte-for-byte (see `AnthropicClient.open_message_stream`
  / `RevisionHandler._handle_stream`); otherwise it's the full JSON message.
  Errors are `{"error": {"message"}}` with `400` (bad input), `401` (auth),
  `429` (rate limit, sends `Retry-After`), or `502` (Anthropic error) — the
  same shape whether or not streaming was requested, since stream errors
  surface before any SSE bytes are written.

Uses a **src layout**: importable code is under `src/`; `pyproject.toml` sets
`pythonpath = ["src"]` so tests run without an editable install. The
`static/` directory lives inside the package so it ships in the wheel.

## Getting started

- **Python:** requires `>=3.11`.
- **Install (editable, with dev tools):**
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"
  ```
- **Run:** `ANTHROPIC_API_KEY=sk-ant-... revision` (serves http://127.0.0.1:8000).

## Development workflows

- **Run tests:** `pytest`
- **One test file / one test:** `pytest tests/test_server.py`,
  `pytest tests/test_server.py::test_healthz`, or `pytest -k ratelimit`
- **Lint:** `ruff check .`
- **Format:** `ruff format .`
- **Run the app:** `revision [--host H --port P --model M]`, or without install
  `ANTHROPIC_API_KEY=... PYTHONPATH=src python -m revision.cli`
- **Manual smoke test:** start the server, then
  `curl localhost:8000/` (UI) and
  `curl -X POST localhost:8000/api/messages -d '{"prompt":"hi"}'`
  (returns a graceful error if no key is set).

> Note: in some environments `pytest`/`ruff` are standalone binaries, not in the
> interpreter's site-packages. If `python -m pytest` says "No module named
> pytest", call `pytest` / `ruff` directly.

### EZR's loop (separate from ReVision's — see the EZR section)

```bash
cd ezr && python3 tests/run_all.py     # the gate ezr/CLAUDE.md names: 29 suites
cd ezr && ./run.sh                     # 22 layers, a superset in breadth; ~minutes
cd ezr/2-interpreter-python && python3 syntax_test.py    # one layer, seconds
cd ezr/2-interpreter-python && python3 ezrun_test.py     # the runner + [EXAMPLE]/[ANCHOR]
cd ezr/7-forge && python3 forge_test.py                  # 81 assertions; not in run.sh
cd ezr/7-forge && python3 quantum_test.py                # 35 assertions; not in run.sh
cd ezr/5-runtime-java && ./build.sh \
  && env -u JAVA_TOOL_OPTIONS java -cp out com.codric.ezr.RuntimeTest   # 98; not in run.sh
cd ezr/5-runtime-java && python3 differential.py         # RED, and deliberately so
```

`run.sh` and `run_all.py` overlap but neither contains the other, and
**neither drives `7-forge/` or `5-runtime-java/`** — both still pass their
own suites (81 + 35 and 98 assertions). Locally, nothing runs them for
you; in CI the `languages` job in `ci.yml` does, along with Rime's gate.

> **`tests/algebra_parity.py` skips Java unless the Java runtime is
> built.** `java_vectors()` requires both `which javac` *and*
> `5-runtime-java/out/` to exist, and `out/` is build output. So on a
> fresh checkout the Java arm skips, `run_all.py` still prints
> `29 passed 0 skipped 0 failed`, and a quarter of the parity check has
> silently vanished. Measured here: `3 agreed, 1 skipped` before
> `5-runtime-java/build.sh`, `4 agreed, 0 skipped` after. The `languages`
> job builds the runtime first for exactly this reason and then asserts
> `0 skipped` separately, because the 29/29 line cannot show it.

`differential.py` is red on purpose: 128 programs, 123 agreed, **5
diverged**. It read 27 diverged for as long as `syntax.py`'s `eval_ast`
had no case for `let ... in`, list literals, or the `len`/`head`/`tail`/
`show` builtins — present in the Java runtime and the forge's `CORE.md`,
absent from the Python side purely because nobody had written them.
That gap is closed (`ezr/FINDINGS.md` §7.11): `eval_ast` now implements
all four, ported from `Eval.java` line for line, and all four
`.ezr` example files run under `ezrun.py` directly with no Java build.
The 5 that remain are genuine findings, not missing features — a
numeric-precision limit past 2^53 (Python's arbitrary-precision `int`
against Java's `double`-backed value), two arity/unbound checks Java
makes at compile time and Python defers to runtime, and two grammar
questions (`GRAMMAR.ebnf`'s settled `trailing_comma = False` and
`trailing_expression = False`) where v4.10 permits what the forge's
doctrine forbids. Each is a finding about the language, not a bug in
either runner — do not "fix" one by editing it to match the other.

`run.sh` has no flag to select a layer — run that layer's own test file
directly. Each `*_test.py` is a plain script that reports its own tally and
calls `raise SystemExit`, not a pytest module. `testpaths = ["tests"]`, so
`pytest` never looks under `ezr/`; pointing it there deliberately does not
just collect nothing, it dies with `INTERNALERROR> SystemExit: 0`.

## Conventions

- **Layout:** shippable code under `src/revision/`; tests under `tests/` mirror
  the module they cover (`server.py` -> `test_server.py`).
- **Style/lint:** ruff, line length 100, rules `E, F, I, UP, B, SIM`
  (see `[tool.ruff.lint]`). Run `ruff format` before committing.
- **Typing:** type-hint public functions.
- **HTTP handlers:** `do_GET` / `do_POST` are the `http.server` API and carry
  `# noqa: N802`; keep the handler bound to its client via `make_handler`.
- **Testability:** `create_server(config, client=...)` accepts an injected
  client so tests can run a real server against a fake Anthropic client with no
  network. Preserve this seam.
- **Errors to the browser:** return `{"error": {"message": ...}}` JSON with an
  appropriate status; the frontend's `callClaude` reads `data.error.message`.
- **Adding a dependency:** prefer not to (stdlib backend). If unavoidable, add
  to `[project].dependencies` (runtime) or `[project.optional-dependencies].dev`.

## Security notes

- The API key is read only server-side; it must never reach the browser.
- The static file server is confined to `src/revision/static/` and rejects path
  traversal — keep that guard when touching `do_GET`.
- Rate limiting (on by default) and optional bearer auth guard `/api/messages`;
  see `config.py`. Before any public deployment, additionally serve over HTTPS
  (terminate TLS at a reverse proxy) and set `REVISION_TRUST_PROXY=true` so rate
  limiting keys off the real client IP.

## Roadmap / "going mainstream" notes

Done:

- ✅ Per-client rate limiting and optional bearer auth on `/api/messages`.
- ✅ Docker image with `/healthz` HEALTHCHECK.
- ✅ CI: ruff (lint + format) and pytest on 3.11–3.13, plus a Docker build.
- ✅ Streaming responses (SSE) — `/api/messages` accepts `stream: true` and
  proxies Anthropic's SSE stream straight through; the frontend's `callClaude`
  reads it incrementally and reports live progress on each tool's button
  while still returning/parsing the full text once the stream ends.
- ✅ Dependency auditing — `.github/workflows/security.yml` runs `pip-audit`
  (root Python deps) and `npm audit --audit-level=high` (`power-pack/`) on
  push/PR plus a weekly cron.

- ✅ Release pipelines — `publish-image.yml` builds the image, proves it
  answers `/healthz`, and pushes it to GHCR on a `v*.*.*` tag or a manual
  dispatch; `publish-npm.yml` publishes `power-pack/` to npm. Neither fires
  on a push to `main`: publishing is a release act, so both want a human
  choosing the moment. Both default to a dry run.

Likely next steps toward production:

- Persisting the model/config and per-tool token limits.
- A deploy target for the image (nothing hosts it yet — the pipeline
  publishes, it does not run it anywhere).
- A proper ASGI stack (e.g. FastAPI + uvicorn) *if* concurrency needs outgrow
  the stdlib `ThreadingHTTPServer` — this would add the first runtime deps.
- Shared/persistent rate-limit store (e.g. Redis) if run multi-process.

## Publishing (release pipelines)

Neither pipeline runs on a push to `main`, and both default to a dry run.
CI already builds the image on every PR, which is what catches a broken
Dockerfile; publishing is a separate act with different consequences.

- **Image → GHCR** (`publish-image.yml`). Fires on a `v*.*.*` tag, or a
  manual dispatch with `dry_run=false`. No secret needed — it authenticates
  with the built-in `GITHUB_TOKEN` under `packages: write`. Before pushing
  it starts the container and waits for `/healthz` to answer, because CI's
  `docker build` only proves the Dockerfile parses, not that the image
  serves.
- **`power-pack/` → npm** (`publish-npm.yml`). Manual dispatch only.
  Requires an `NPM_TOKEN` repository secret (automation token; a read-only
  one fails at publish). It refuses to republish a version that already
  exists — bump `power-pack/package.json` instead.

> **The npm one ships proprietary content.** `package.json`'s `files` list
> includes `pro-commands/`, which is under a proprietary single-user
> licence, *not* the MIT covering the rest of `power-pack/`. Publishing
> makes those 30 commands publicly installable by anyone. The workflow
> prints this and will not publish unless `confirm_proprietary` is typed
> exactly, so the decision is recorded in the run rather than assumed.
> `slash-pack` is currently **unclaimed on npm**, so the first publish
> takes that global name permanently.

## Git & branching

- **Feature branches:** start each change on a fresh branch off the latest
  `main` (e.g. `claude/<short-topic>`); don't develop directly on `main`.
- **Push:** `git push -u origin <branch-name>`.
- **Pull requests:** only open a PR when explicitly requested.
- A merged PR is finished — start follow-up work from a fresh branch off the
  latest default branch rather than stacking onto merged history.

## Claude tooling (commands, skills, playbook)

This repo ships Claude Code helpers under `.claude/`, distilled from power-user
cheat-sheets (see `docs/claude-playbook.md` for the original source, and
`docs/claude-2026-cheatsheet.md` for the 2026 update — the 5 surfaces, the
model stack, the core-files framework, and the Claude Code app workflow):

- **Commands pack** — `docs/commands-pack.md` lists every command's slash form
  alongside its paste-ready prompt (for use in a plain claude.ai chat, where
  slash commands aren't available).
- **Slash commands** in `.claude/commands/` — the full command reference as
  reusable prompt shortcuts across six groups (focus/context, think/solve,
  organize, code, automate, personalize): `/think`, `/analyze`, `/challenge`,
  `/compare`, `/recommend`, `/solve`, `/summary`, `/outline`, `/table`,
  `/mindmap`, `/flowchart`, `/explain`, `/debug`, `/optimize`, `/refactor`,
  `/test`, `/convert`, `/workflow`, `/automate`, `/tasklist`, `/checklist`,
  `/brief`, `/about-me`, `/model-picker`, and more. Invoke with `/name [args]`. Note: `/clear`,
  `/memory`, and `/review` collide with Claude Code built-ins, which take
  precedence.
- **Skills** in `.claude/skills/` —
  - `claude-power-practices`: auto-applied guardrails for high-stakes work (pick
    the right model, structure prompts with XML tags, use extended thinking,
    verify facts / never fabricate links, produce real deliverables).
  - `dev-check` / `test-and-lint`: run the CI gate locally (ruff + pytest).
  - `run-app`: start and smoke-test the ReVision server.
  - `add-tool`: add a new document tool (tab) to the single-page UI.
  - `prompt-library`: save/retrieve prompts that worked well, backed by
    `docs/prompt-library.md` — a library of wins, not a full transcript log.
- **Subagents** in `.claude/agents/` — each one standalone and single-purpose
  (not bundled): `code-reviewer` (read-only diff review against this file's
  invariants), `test-writer` (adds pytest coverage mirroring existing
  conventions), `security-auditor` (read-only audit against the Security
  notes checklist below).
- **`settings.json` + `hooks/`** — a `permissions.allow` list pre-authorizing
  `ruff`/`pytest`/`python`/`revision`/`curl`; a `SessionStart` hook
  (`hooks/session-start.sh`) that installs dev deps on a cold remote container
  and verifies the C/C++/Ruby/Java toolchains `ezr/`'s gate needs — because
  `run.sh` and `algebra_parity.py` *skip* a layer whose toolchain is absent and
  still exit 0, so a degraded container reads green (measured: hiding `/usr/bin`
  takes `algebra_parity` from 4 agreed to 2 agreed / 2 skipped, exit 0 both
  times; that measurement was not reproducible in the 2026-09 container,
  where hiding `/usr/bin` changed nothing and the arm that skipped was
  Java, gated on `5-runtime-java/out/` rather than on `PATH` — the class
  of problem is the same, the trigger was not). It also warns when `JAVA_TOOL_OPTIONS` is set, per the gotcha below;
  and two `PreToolUse` hooks matched on `Bash` calls — `git-safety-guard.sh`
  (hard-blocks force-push without `--force-with-lease`, `reset --hard`,
  `clean -f`, `branch -D`, discard-all `checkout`/`restore .`, and
  `--no-verify`/`--no-gpg-sign`) and `secret-scan-precommit.sh` (blocks
  `git commit` when the staged diff matches an Anthropic/AWS/GitHub/Slack key
  or a PEM private-key block). Both are backstops, not a substitute for
  judgment, and both are line-based text scanners (each check requires the
  dangerous pattern and an actual `git <verb>` on the same physical line) —
  precise enough to ignore prose that merely *mentions* a flag, but a
  contrived one-liner could still evade or false-positive it. See
  `.claude/README.md` for the full rundown.

> Gotcha: Claude Code only watches `.claude/` dirs that had a settings file when
> the session **started**. Editing `settings.json` or the hooks mid-session
> doesn't take effect until the next session (or opening `/hooks` once).

The prompt/command aids don't touch the ReVision app's runtime code, endpoints,
or the server-side-key rules above.

## EZR (`ezr/`) — a separate project in the same repo

`ezr/` is **not part of ReVision**. It is the EZR language
project: a multi-layer language where every value carries how much it is
trusted (C atom → C++ phase engine → Python interpreter → Ruby DSL → SQL
archive → Java runtime → HTML interface). It shares nothing with
`src/revision/` — no imports, no endpoints, no configuration — and the
two are verified by separate commands.

- **Verify it:** `cd ezr && ./run.sh` — 22 layers (needs gcc, g++,
  python3 and ruby; skips any layer whose toolchain is absent rather
  than failing). `ezr/CLAUDE.md` names `python3 tests/run_all.py` (29
  suites) as the gate to be green before and after a change; run both.
- **In a container:** `cd ezr && docker compose run --rm verify`.
  The image verifies itself at build time.
- **`ezr/7-forge/`** is the language forge: four independent lexers and
  five independent parsers, run as all twenty pairings against a shared
  conformance corpus and seven universal laws, with a fuzz budget that
  doubles after every clean generation. Where the pairs disagree, the
  language was never specified; the forge arbitrates by published doctrine,
  then cross-stage coverage, then its own laws, then consensus, and
  withholds below all four. `ezr/CORE.md` records what it settled;
  `ezr/7-forge/GRAMMAR.ebnf` is emitted from the chart parser's rule
  table so it cannot drift from the code.
  `ezr/7-forge/quantum.py` is a second generator alongside `corpus.py`'s
  seeded fuzzer: it collapses each construction site from a phrase by
  *address* (FNV-1a over the path) rather than by a draw, so any subtree
  regenerates alone and `PYTHONHASHSEED` cannot change the corpus. It
  emits rhyming couplets — two programs whose last k token kinds match
  and whose skeletons differ — which makes the scanners' agreement about
  where a program *ends* directly checkable (`law_rhyme`). Do not
  reintroduce `random` or `hash()` there, and note `--emit` writes a
  `.ezr` into `7-forge/generated/`, which is build output and not an
  entry for `ezr/examples/`.
- **`ezr/5-runtime-java/`** is a second implementation of the core, in a
  language that shares no interpreter, type system or habits with the
  Python one. It is checked twice, as two separate layers: `RuntimeTest`
  against `SEMANTICS.md`, and `differential.py` running one corpus
  through both the Python runner and the Java runner as processes and
  comparing value, exit code, refusing stage and binding defect. A
  divergence there is a finding about the language, not a bug report
  against one side. It found three, recorded in `ezr/FINDINGS.md` §7.
- **Boundaries matter here.** Each numbered directory is a distinct language
  and toolchain. Do not let Python interpretation rules leak into the C++
  phase, or vice versa; do not add language features that `SEMANTICS.md`
  does not already imply.

ReVision's own gate (`pytest`, `ruff check .`) does not cover `ezr/`,
and `ezr/run.sh` does not cover ReVision. Run whichever matches what
you touched.

## Rime (`realm/`) — a third project in the same repo

`realm/` is **not part of ReVision and not part of EZR**. It is Rime, a
small postfix language whose *well-formedness condition is rhyme*: a
program is a sequence of couplets, a line ends in a verb, and a couplet
is legal only when its two verbs rhyme. It shares no code with
`src/revision/` or `ezr/` — no imports, no tokens, no trees.

- **Verify it:** `cd realm && python3 realm_test.py` — 74 assertions,
  a plain script that reports its own tally and calls `raise
  SystemExit`, like `ezr/`'s suites and unlike a pytest module.
  `testpaths = ["tests"]`, so `pytest` never looks here.
- **See it run:** `cd realm && python3 realm.py` — writes a poem from a
  phrase, runs it, then puts the whole corpus to nine front ends and
  reports whether they converged. Exits non-zero if a law breaks.
- **The one idea.** The vocabulary is built so that **a rhyme class is
  exactly an operation family** (`-ow` moves numbers, `-eep` touches the
  store, and so on). Rhyme is a typing discipline written as verse, not
  decoration. Do not add a verb without placing it in the family its
  sound already claims — `law_family` exists to catch precisely that.
- **Deterministic generation.** Because a class is a finite *ordered*
  list, the answering verb of a couplet is simply the next one, so half
  of every program is derived rather than chosen. The rest collapses
  from a phrase via a hand-written FNV-1a, addressed by path. There is
  no random source in `realm/`, and `hash()` is never touched — keep it
  that way, or `PYTHONHASHSEED` starts changing the corpus.
- **The order of complaint is part of the language.** A program can be
  wrong several ways at once; the phases (shape → vocabulary → pairing
  → rhyme) are published in `parsers.py` so three parsers cannot each
  pick a favourite fault. Changing that order changes Rime.

`realm/` is in ruff's `extend-exclude` for the same reason `ezr/` is: it
keeps its own conventions, its vocabulary table is hand-aligned so a
rhyme class reads as a block, and `ruff format` would explode it. So
ReVision's gate does not cover `realm/`, and `realm_test.py` does not
cover ReVision. Run whichever matches what you touched.

## Two gotchas that cost real time

**The format-on-write hook ignores ruff's own exclusion.** `.claude/settings.json`
has a `PostToolUse` hook matched on `Write|Edit` that runs
`ruff check --fix --select I` and `ruff format` on any `.py` path it is handed.
It has no path filter, and passing ruff an explicit file path overrides
`pyproject.toml`'s `extend-exclude = ["ezr"]` (ruff only honours exclusions for
explicit paths when given `--force-exclude`). So editing any file under `ezr/`
with Write/Edit silently reformats it — re-sorting imports and exploding the
hand-aligned tables that layer uses. A two-line fix to `syntax.py` came back as
a 331-line diff this way. Either add `--force-exclude` to the hook, or make
edits under `ezr/` through Bash (`python3`/`sed`), which the hook does not match.

**`ezr/5-runtime-java` needs JDK 21 or newer.** It uses pattern matching in
`switch`, which was a *preview* feature through JDK 20 and only became final
in 21 (JEP 441). `build.sh` passes no `--release`, so it compiles against
whichever JDK is on `PATH`: on 21 it builds 35 classes, on 17 it dies with
four `patterns in switch statements are a preview feature` errors. Nothing
in the tree pins this, so CI's `languages` job asserts the major version and
says so plainly rather than letting javac's preview-feature error stand as
the explanation.

**`JAVA_TOOL_OPTIONS` corrupts the Java runtime's output.** When the environment
sets it, the JVM prints `Picked up JAVA_TOOL_OPTIONS: ...` to stderr on every
start, which breaks the byte comparison `ezr/5-runtime-java/differential.py`
depends on. Setting it empty does **not** help — the banner still prints with an
empty value. It has to be removed: `env -u JAVA_TOOL_OPTIONS java ...`. The
`ezr/5-runtime-java/ezr` wrapper already does this; a raw `java -cp out` does not.

## Notes for AI assistants

- Verify claims against the actual repository before acting.
- Run `pytest` and `ruff check .` before committing non-trivial changes to
  ReVision; run `ezr/run.sh` for changes under `ezr/`.
- Keep this file updated as the codebase evolves; treat documentation drift as a
  bug. When you add a top-level directory, tool, endpoint, or workflow, update
  the relevant section here in the same change.
