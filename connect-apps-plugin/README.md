# Connect Apps

A Claude Code plugin: a small set of deep, workflow-level skills for connecting
Claude to external apps and cloud infrastructure. Load it directly without
installing from a marketplace:

```bash
claude --plugin-dir ./connect-apps-plugin
```

Or install it into an existing Claude Code setup by copying (or symlinking)
this directory somewhere Claude Code's plugin system scans, then enabling it
with `/plugin` or `claude plugin enable connect-apps-plugin`.

## What's here

**App connectors** — one deep skill per external service, covering auth
model, core workflow, gotchas, and a pre-flight checklist:

| Skill | Covers |
| :--- | :--- |
| `docusign-esignature` | Envelope creation from templates, recipient/routing/tabs management, workflow triggers, status polling |
| `figma-design-bridge` | Design-to-code (`get_design_context`, `get_screenshot`) and code-to-design (`use_figma`), Code Connect mapping |
| `github-collaboration` | PR lifecycle (create → review → resolve threads → merge), issue triage, avoiding duplicate work |
| `clerk-auth` | Wiring Clerk authentication into a frontend/backend via SDK snippets, session/JWT verification |
| `scite-research` | Literature search with Smart Citations, retraction checks, mandatory citation format |
| `exa-web-research` | Neural web search vs. direct fetch, when each beats a generic search tool |

**Cloud infrastructure** — three deep skills, each spanning the workflow end
to end rather than one command at a time:

| Skill | Covers |
| :--- | :--- |
| `cloud-providers` | AWS / GCP / Azure: identity & least-privilege, core compute/storage/network primitives mapped across the three, cost and blast-radius discipline |
| `infrastructure-as-code` | Terraform (state, modules, plan/apply discipline) plus where CloudFormation/CDK fit instead |
| `containers-orchestration` | Docker image hygiene, Kubernetes objects and rollout strategy, CI/CD pipeline shape |

## Design notes

- **Fewer, deeper skills** rather than one skill per tool call. Each skill
  assumes the reader already knows general engineering but not this specific
  service's shape, and front-loads the workflow that actually gets used
  (e.g. "create an envelope from a template," not a tool-by-tool API dump).
- **No fabricated links.** Skills point at a provider's root docs domain
  (e.g. `docs.aws.amazon.com`) rather than deep-linking to pages that may not
  exist or may have moved.
- **Session-aware where relevant.** The app-connector skills assume the
  matching MCP server (Docusign, Figma, GitHub, Clerk, Scite, Exa) may or may
  not be connected in the current session — each skill says what to check
  and how to degrade gracefully (e.g. tell the user to authorize the
  connector) rather than assuming it's always live.
