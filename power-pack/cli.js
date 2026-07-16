#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");
const crypto = require("crypto");

const VERSION = "1.0.0";
const PACK_DIR = __dirname;
const CLAUDE_HOME =
  process.env.CLAUDE_HOME || path.join(os.homedir(), ".claude");

const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const uninstall = args.includes("--uninstall");
const activateIdx = args.indexOf("--activate");
const statusCheck = args.includes("--status");

if (args.includes("--help") || args.includes("-h")) {
  console.log(`
  S.L.A.S.H. — Structured Language And System Heuristics

  Usage: slash-pack [options]
         npx slash-pack [options]

  Options:
    --dry-run        Preview what would be installed/removed
    --uninstall      Remove S.L.A.S.H. commands and skill
    --activate KEY   Activate Pro Pack with your license key
    --status         Show installation and license status
    --help           Show this help

  Free:  77 commands + power-practices skill
  Pro:   30 additional professional commands (requires license)
  `);
  process.exit(0);
}

const LICENSE_FILE = path.join(CLAUDE_HOME, ".slash-pack-license");
const LICENSE_SALT = "slash-pack-v1";

function hashKey(key) {
  return crypto
    .createHash("sha256")
    .update(LICENSE_SALT + ":" + key.trim())
    .digest("hex")
    .slice(0, 16);
}

function isProActivated() {
  if (!fs.existsSync(LICENSE_FILE)) return false;
  try {
    const data = JSON.parse(fs.readFileSync(LICENSE_FILE, "utf8"));
    return data.activated === true && typeof data.hash === "string";
  } catch {
    return false;
  }
}

function activatePro(key) {
  const trimmed = key.trim();
  if (!trimmed || trimmed.length < 8) {
    console.log("  ✗ Invalid license key. Check your purchase confirmation email.\n");
    process.exit(1);
  }
  fs.mkdirSync(CLAUDE_HOME, { recursive: true });
  const record = {
    activated: true,
    hash: hashKey(trimmed),
    activatedAt: new Date().toISOString(),
    version: VERSION,
  };
  fs.writeFileSync(LICENSE_FILE, JSON.stringify(record, null, 2) + "\n");
  console.log(`
  ╔═══════════════════════════════════════╗
  ║   S.L.A.S.H. Pro — Activated!        ║
  ╚═══════════════════════════════════════╝

  ✓ 30 Pro commands unlocked.
  Run 'npx slash-pack' to install them.
  `);
}

function showStatus() {
  header();
  const cmdDest = path.join(CLAUDE_HOME, "commands");
  const freeInstalled = fs.existsSync(cmdDest)
    ? fs.readdirSync(cmdDest).filter((f) => f.endsWith(".md")).length
    : 0;
  const proActive = isProActivated();

  console.log(`  Installation: ${freeInstalled > 0 ? freeInstalled + " commands installed" : "not installed"}`);
  console.log(`  Location:     ${CLAUDE_HOME}`);
  console.log(`  Version:      ${VERSION}`);
  console.log(`  Pro license:  ${proActive ? "✓ activated" : "✗ not activated"}`);
  console.log(`  Pro commands: ${proActive ? "30 unlocked" : "locked (use --activate KEY)"}`);
  console.log();
}

function header() {
  console.log(`
  ╔═══════════════════════════════════════╗
  ║   S.L.A.S.H.  v${VERSION}                ║
  ║   77 Commands + Power Practices       ║
  ╚═══════════════════════════════════════╝
  `);
}

function copyFileSync(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
}

function getCommandFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  return fs.readdirSync(dir).filter((f) => f.endsWith(".md"));
}

function doUninstall() {
  header();
  let removed = 0;

  for (const name of getCommandFiles(path.join(PACK_DIR, "commands"))) {
    const dest = path.join(CLAUDE_HOME, "commands", name);
    if (fs.existsSync(dest)) {
      if (dryRun) {
        console.log(`  [dry-run] Would remove: ${dest}`);
      } else {
        fs.unlinkSync(dest);
      }
      removed++;
    }
  }

  // Remove pro commands too
  for (const name of getCommandFiles(path.join(PACK_DIR, "pro-commands"))) {
    const dest = path.join(CLAUDE_HOME, "commands", name);
    if (fs.existsSync(dest)) {
      if (dryRun) {
        console.log(`  [dry-run] Would remove: ${dest}`);
      } else {
        fs.unlinkSync(dest);
      }
      removed++;
    }
  }

  const skillDest = path.join(
    CLAUDE_HOME,
    "skills",
    "claude-power-practices",
    "SKILL.md"
  );
  if (fs.existsSync(skillDest)) {
    if (dryRun) {
      console.log(`  [dry-run] Would remove: ${skillDest}`);
    } else {
      fs.unlinkSync(skillDest);
      try {
        fs.rmdirSync(path.dirname(skillDest));
      } catch (_) {}
    }
    console.log("  ✓ Removed power-practices skill");
  }

  console.log(`  ✓ Removed ${removed} commands\n`);
}

function doInstall() {
  header();

  const cmdSrc = path.join(PACK_DIR, "commands");
  if (!fs.existsSync(cmdSrc)) {
    console.error("  ✗ Cannot find commands directory.");
    console.error("    Package may be corrupted — try reinstalling.");
    process.exit(1);
  }

  if (dryRun) {
    console.log("  [dry-run mode — no files will be written]\n");
  }

  console.log(`  Source:  ${PACK_DIR}`);
  console.log(`  Target:  ${CLAUDE_HOME}\n`);

  // Backup existing commands
  const cmdDest = path.join(CLAUDE_HOME, "commands");
  if (fs.existsSync(cmdDest)) {
    const existing = fs.readdirSync(cmdDest).filter((f) => f.endsWith(".md"));
    if (existing.length > 0) {
      const ts = new Date()
        .toISOString()
        .replace(/[-:T]/g, "")
        .slice(0, 14);
      const backup = `${cmdDest}.backup.${ts}`;
      if (dryRun) {
        console.log(`  [dry-run] Would back up ${existing.length} existing commands to:`);
        console.log(`    ${backup}`);
      } else {
        console.log(`  → Backing up ${existing.length} existing commands to:`);
        console.log(`    ${backup}`);
        fs.cpSync(cmdDest, backup, { recursive: true });
      }
    }
  }

  // Install free commands
  let installed = 0;
  for (const name of getCommandFiles(cmdSrc)) {
    const src = path.join(cmdSrc, name);
    const dest = path.join(CLAUDE_HOME, "commands", name);
    if (dryRun) {
      console.log(`  [dry-run] Would install: ${name}`);
    } else {
      copyFileSync(src, dest);
    }
    installed++;
  }
  console.log(`  ✓ Installed ${installed} free commands → ${cmdDest}/`);

  // Install pro commands if activated
  const proSrc = path.join(PACK_DIR, "pro-commands");
  if (isProActivated() && fs.existsSync(proSrc)) {
    let proInstalled = 0;
    for (const name of getCommandFiles(proSrc)) {
      const src = path.join(proSrc, name);
      const dest = path.join(CLAUDE_HOME, "commands", name);
      if (dryRun) {
        console.log(`  [dry-run] Would install pro: ${name}`);
      } else {
        copyFileSync(src, dest);
      }
      proInstalled++;
    }
    console.log(`  ✓ Installed ${proInstalled} pro commands → ${cmdDest}/`);
  } else if (fs.existsSync(proSrc)) {
    const proCount = getCommandFiles(proSrc).length;
    console.log(`  ○ ${proCount} Pro commands available (use --activate KEY to unlock)`);
  }

  // Install power-practices skill
  const skillSrc = path.join(
    PACK_DIR,
    "skills",
    "claude-power-practices",
    "SKILL.md"
  );
  if (fs.existsSync(skillSrc)) {
    const skillDest = path.join(
      CLAUDE_HOME,
      "skills",
      "claude-power-practices",
      "SKILL.md"
    );
    if (dryRun) {
      console.log(`  [dry-run] Would install: power-practices skill`);
    } else {
      copyFileSync(skillSrc, skillDest);
    }
    console.log(
      `  ✓ Installed power-practices skill → ${path.dirname(skillDest)}/`
    );
  }

  // Version stamp
  if (!dryRun) {
    fs.writeFileSync(
      path.join(CLAUDE_HOME, ".slash-pack-version"),
      VERSION + "\n"
    );
  }

  const proActive = isProActivated();
  console.log(`
  ┌─────────────────────────────────────────┐
  │  Done. ${proActive ? "107" : " 77"} commands ready.               │
  │                                         │
  │  Start a new Claude Code session        │
  │  and type /think, /analyze, /brainstorm │
  │  or any of the ${proActive ? "107" : " 77"} commands.             │
  │                                         │
  │  They work in every project, globally.  │
  └─────────────────────────────────────────┘
${proActive ? "" : `
  ┌─────────────────────────────────────────┐
  │  Upgrade to Pro: 30 more commands       │
  │  /architect, /security-audit, /pitch,   │
  │  /contract, /negotiate, /growth + 24    │
  │                                         │
  │  → Purchase at your Gumroad link        │
  │  → Then: npx slash-pack --activate KEY  │
  └─────────────────────────────────────────┘
`}
  Tip: Run with --dry-run to preview changes.
  Tip: Run with --uninstall to cleanly remove.
  `);
}

// Route commands
if (activateIdx !== -1 && args[activateIdx + 1]) {
  activatePro(args[activateIdx + 1]);
} else if (statusCheck) {
  showStatus();
} else if (uninstall) {
  doUninstall();
} else {
  doInstall();
}
