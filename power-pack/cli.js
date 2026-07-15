#!/usr/bin/env node
"use strict";

const fs = require("fs");
const path = require("path");
const os = require("os");

const VERSION = "1.0.0";
const PACK_DIR = __dirname;
const CLAUDE_HOME =
  process.env.CLAUDE_HOME || path.join(os.homedir(), ".claude");

const args = process.argv.slice(2);
const dryRun = args.includes("--dry-run");
const uninstall = args.includes("--uninstall");

if (args.includes("--help") || args.includes("-h")) {
  console.log(`
  Usage: words-of-radiance [options]
         npx words-of-radiance [options]

  Options:
    --dry-run    Preview what would be installed/removed
    --uninstall  Remove Power Pack commands and skill
    --help       Show this help
  `);
  process.exit(0);
}

function header() {
  console.log(`
  ╔═══════════════════════════════════════╗
  ║   Words of Radiance  v${VERSION}         ║
  ║   77 Commands + Power Practices       ║
  ╚═══════════════════════════════════════╝
  `);
}

function copyFileSync(src, dest) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(src, dest);
}

function getCommandFiles() {
  const cmdDir = path.join(PACK_DIR, "commands");
  if (!fs.existsSync(cmdDir)) return [];
  return fs.readdirSync(cmdDir).filter((f) => f.endsWith(".md"));
}

function doUninstall() {
  header();
  let removed = 0;

  for (const name of getCommandFiles()) {
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

  // Install commands
  let installed = 0;
  for (const name of getCommandFiles()) {
    const src = path.join(cmdSrc, name);
    const dest = path.join(CLAUDE_HOME, "commands", name);
    if (dryRun) {
      console.log(`  [dry-run] Would install: ${name}`);
    } else {
      copyFileSync(src, dest);
    }
    installed++;
  }
  console.log(`  ✓ Installed ${installed} commands → ${cmdDest}/`);

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
      path.join(CLAUDE_HOME, ".words-of-radiance-version"),
      VERSION + "\n"
    );
  }

  console.log(`
  ┌─────────────────────────────────────────┐
  │  Done. Start a new Claude Code session   │
  │  and type /think, /analyze, /brainstorm  │
  │  or any of the 77 commands.              │
  │                                          │
  │  They work in every project, globally.   │
  └─────────────────────────────────────────┘

  Tip: Run with --dry-run to preview changes.
  Tip: Run with --uninstall to cleanly remove.
  `);
}

if (uninstall) {
  doUninstall();
} else {
  doInstall();
}
