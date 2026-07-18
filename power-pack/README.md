# S.L.A.S.H.

**Structured Language And System Heuristics**

80 battle-tested prompt-commands for Claude — as slash commands in Claude Code,
or copy-paste prompts in any Claude chat.

Each command is a carefully crafted prompt that turns a vague ask into a
structured, high-quality result.

## What's inside

### Free (80 commands)

| Group | Commands | Examples |
|-------|----------|----------|
| Focus & Context | 10 | `/focus`, `/context`, `/clarify`, `/brief` |
| Think & Solve | 11 | `/think`, `/analyze`, `/model-picker`, `/challenge` |
| Organize & Structure | 9 | `/summary`, `/outline`, `/table`, `/flowchart` |
| Code & Tech | 9 | `/code`, `/debug`, `/test`, `/refactor` |
| Automate & Integrate | 8 | `/workflow`, `/automate`, `/api`, `/checklist` |
| Personalize & Control | 9 | `/tone`, `/style`, `/about-me`, `/reset` |
| Write & Edit | 7 | `/write`, `/improve`, `/shorten`, `/rewrite` |
| Data & Analysis | 5 | `/insights`, `/report`, `/stats`, `/forecast` |
| Learn & Research | 4 | `/research`, `/learn`, `/sources`, `/explore` |
| Collaborate | 2 | `/email`, `/feedback` |
| Content Transforms | 6 | `/eli5`, `/tldr`, `/factcheck`, `/glossary` |

### Pro Pack (30 commands — requires license)

| Category | Commands |
|----------|----------|
| Architecture & Engineering | `/architect`, `/api-design`, `/data-model`, `/ci-cd`, `/performance`, `/migration` |
| Security & Ops | `/security-audit`, `/incident`, `/postmortem`, `/compliance` |
| Business & Strategy | `/pitch`, `/proposal`, `/monetize`, `/competitive`, `/growth`, `/estimate` |
| Product & Design | `/roadmap`, `/ux-review`, `/onboard`, `/ab-test`, `/landing-page` |
| Legal & Contracts | `/contract`, `/legal-draft`, `/negotiate` |
| Leadership & Comms | `/crisis`, `/retrospective`, `/interview-prep`, `/brand`, `/teardown` |

Plus the **power-practices** skill — automatic guardrails for model selection,
prompt structure, truthfulness, and real deliverables.

## Install

### Bash (Unix) — works today

```bash
git clone https://github.com/Codric-Enterprise/ClaudRick.git
cd ClaudRick/power-pack
bash install.sh
```

```bash
# Preview what would change:
bash install.sh --dry-run

# Cleanly remove:
bash install.sh --uninstall
```

### npx (coming soon)

```bash
npx slash-pack
```

This is the target one-command install once `slash-pack` is published to npm
— it isn't yet, so this won't work today. Use the Bash install above until
then; `cli.js` behind it is the same installer either way (`--dry-run`,
`--status`, `--uninstall`, `--activate KEY` all work identically once live).

### Activate Pro

After purchasing a Pro license:

```bash
bash install.sh   # or: npx slash-pack, once published
node cli.js --activate YOUR-LICENSE-KEY
bash install.sh   # re-run to install the 30 pro commands
```

Both paths copy everything to `~/.claude/` so commands are available globally
in every project. Existing commands are backed up automatically.

### Copy & paste (works everywhere)

Every command works as a plain prompt — no CLI required. Open the
[interactive console](../docs/command-console.html), find the command you
need, click **Copy**, and paste it into any Claude chat (claude.ai, the API,
Slack, wherever). Replace `{your input}` with your text.

### Per project (teams)

Drop the commands into any repo — they auto-load for everyone:

```bash
cp -r commands/ your-repo/.claude/commands/
cp -r skills/ your-repo/.claude/skills/
```

## How it works

Each `.md` file in `commands/` is a Claude Code slash command with YAML
frontmatter (`description`, `argument-hint`) and a carefully structured prompt.
When you type `/think some problem` in Claude Code, it reads `think.md`,
substitutes your input for `$ARGUMENTS`, and sends the full prompt to Claude.

The `power-practices` skill in `skills/` loads automatically and applies
guardrails for reasoning, truthfulness, and deliverable quality.

## Notes

- Three commands (`/clear`, `/memory`, `/review`) share names with Claude Code
  built-ins — the built-in takes precedence. Use the paste-ready prompt instead.
- Commands contain no secrets, API keys, or executable code — they're plain
  text prompts. Safe to commit, share, and inspect.

## License

Free tier: MIT — see [LICENSE](LICENSE).
Pro commands: proprietary, single-user, non-transferable — see
[pro-commands/LICENSE](pro-commands/LICENSE). No redistribution or resale.
