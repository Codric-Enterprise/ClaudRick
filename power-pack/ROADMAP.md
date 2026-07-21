# power-pack (S.L.A.S.H.) — Roadmap

Roadmap for the standalone `power-pack/` distributable — 77 free commands, a
30-command Pro Pack, and the `slash-pack` installer. See `power-pack/README.md`
for what it does and how to install it; this file only tracks direction.

## Done

- ✅ 77 free prompt-commands + power-practices skill, portable across any
  Claude Code project or plain claude.ai chat.
- ✅ 30-command Pro Pack (architecture, security, business, product, legal,
  leadership categories).
- ✅ Cross-platform installer (`cli.js`, `npx slash-pack`) with `--dry-run`,
  `--status`, `--uninstall`, and per-project drop-in (`cp -r commands/ ...`).
- ✅ Bash installer (`install.sh`) as a non-Node alternative.
- ✅ Copy-paste fallback via `docs/command-console.html` for non-CLI use.
- ✅ Licensing split: MIT for the free tier, proprietary single-user license
  for Pro, gated by a local `--activate KEY` flow.

## Known gap to close before calling Pro "real"

- **License activation doesn't verify anything yet.** `activatePro()` in
  `cli.js` accepts any string ≥8 characters, hashes it, and writes
  `activated: true` to `~/.claude/.slash-pack-license` — there's no call to a
  purchase/license server. Anyone can "activate" Pro with a random string
  today. Before this is sold for real, it needs an actual issuing/verification
  backend (or a signed-key scheme `cli.js` can check offline) — otherwise the
  license gate is decorative.

## Likely next steps

- Publish the package: `slash-pack` is npm-publish-ready (`package.json` has
  the right shape) but isn't on the registry yet — `npm view slash-pack`
  currently 404s. Needs an actual `npm publish` (and a decision on who owns
  that npm account/org).
- Real license issuance tied to the purchase flow referenced in the README
  ("After purchasing a Pro license...") — right now there's no purchase flow
  in this repo to tie it to.
- Update/versioning story: no mechanism today for `slash-pack` to detect or
  pull newer commands after initial install.
- Decide whether `power-pack/index.html` (landing page) is meant to go live
  somewhere, and if so, where it's hosted.
