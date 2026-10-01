// apply.js — turn a Fixture into a real edit on disk.
//
// Codric rule: every repair carries its own revert.
//
// The engine works from the fixture_form column, never from the prose
// text of fixture_text — prose is for humans, form is for machines
// (SEMANTICS.md §9.5). Each applier is a small named function; adding
// a new fixture_form kind means adding one function here and one
// signature in gradle.json. Nothing to search-and-replace across
// files.
//
// Applied edits produce a receipt. The receipt has enough information
// to undo the edit deterministically without re-reading the log — the
// file's pre-image is stored, hashed, and dated. Revert refuses if
// the file's current hash does not match the post-image, because
// then something else has edited the file since and we would silently
// erase that work.

'use strict';

const fs   = require('fs');
const path = require('path');
const os   = require('os');
const crypto = require('crypto');

const RECEIPTS = 'receipts.jsonl';

function sha256(s) { return crypto.createHash('sha256').update(s).digest('hex'); }

// ─────────────────────────────────────────────
// Appliers. Each returns a Plan describing exactly what will change.
// A plan is not the edit; it is the edit's description, which the
// caller reviews (dry-run) or executes (apply).
//
// A Plan has:
//   file       — absolute path being edited
//   before     — verbatim current content
//   after      — verbatim proposed content
//   summary    — one line for humans
// A Plan with before === after is a no-op and is reported as such.
// ─────────────────────────────────────────────

function _readOrEmpty(file) {
  try { return fs.readFileSync(file, 'utf8'); } catch { return ''; }
}

function _writeCreatingDirs(file, content) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content);
}

// SET_COMPILE_SDK:<n> — set android.compileSdk in a module build file
function planSetCompileSdk(projectRoot, arg) {
  const n = parseInt(arg, 10);
  if (!Number.isFinite(n) || n <= 0)
    throw new Error(`SET_COMPILE_SDK: bad value "${arg}"`);
  const file = _findGradleBuildFile(projectRoot);
  const before = _readOrEmpty(file);
  const after  = _rewriteScalar(before, /compileSdk(?:Version)?\s*=?\s*(\d+)/,
                                m => m.replace(/\d+/, String(n)),
                                `compileSdk = ${n}`);
  return { file, before, after,
           summary: `set android.compileSdk = ${n} in ${path.basename(file)}` };
}

// SET_AGP_VERSION:<v> — pin AGP classpath in the top-level build file
function planSetAgpVersion(projectRoot, arg) {
  const v = arg.trim();
  if (!/^\d+(?:\.\d+)*$/.test(v))
    throw new Error(`SET_AGP_VERSION: bad version "${arg}"`);
  const file = _findTopLevelBuildFile(projectRoot);
  const before = _readOrEmpty(file);
  // Handle both `com.android.application` (plugins block) and classpath styles
  let after = before.replace(
    /(id\(\s*["']com\.android\.(?:application|library)["']\s*\)\s*version\s*["'])([^"']+)(["'])/g,
    `$1${v}$3`);
  after = after.replace(
    /(classpath\s*[("'`]+com\.android\.tools\.build:gradle:)([^"'`)]+)/g,
    `$1${v}`);
  return { file, before, after,
           summary: `pin Android Gradle Plugin to ${v} in ${path.basename(file)}` };
}

// SET_NAMESPACE:from_manifest — read AndroidManifest.xml, set android { namespace = ... }
function planSetNamespace(projectRoot /* , arg */) {
  const manifest = _findManifest(projectRoot);
  const mtext    = _readOrEmpty(manifest);
  const pkg      = (mtext.match(/\bpackage\s*=\s*"([^"]+)"/) || [])[1];
  if (!pkg)
    throw new Error(`SET_NAMESPACE: no package="..." in ${manifest || 'AndroidManifest.xml'}`);
  const file   = _findGradleBuildFile(projectRoot);
  const before = _readOrEmpty(file);
  const after  = _insertOrReplaceNamespace(before, pkg);
  return { file, before, after,
           summary: `add android { namespace = "${pkg}" } (from manifest)` };
}

// CREATE_LOCAL_PROPERTIES:sdk.dir — write local.properties if it does not exist
function planCreateLocalProperties(projectRoot /* , arg */) {
  const file = path.join(projectRoot, 'local.properties');
  const before = _readOrEmpty(file);
  if (/^\s*sdk\.dir\s*=/m.test(before)) {
    return { file, before, after: before,
             summary: `local.properties already declares sdk.dir; no change` };
  }
  const sdk = process.env.ANDROID_HOME || process.env.ANDROID_SDK_ROOT;
  if (!sdk)
    throw new Error(
      `CREATE_LOCAL_PROPERTIES: ANDROID_HOME is not set. Export it, ` +
      `or write local.properties by hand with sdk.dir=/absolute/path.`);
  const line = `sdk.dir=${sdk}\n`;
  const after = before ? (before.replace(/\n?$/, '\n') + line) : line;
  return { file, before, after,
           summary: `write sdk.dir=${sdk} into local.properties` };
}

// ─────────────────────────────────────────────
// Registry — one entry per supported fixture_form. Signatures whose
// form is not in this map cannot be applied; the tool says so and
// stops. This is deliberate. Silently ignoring a form is exactly the
// class of bug the archive discipline forbids.
// ─────────────────────────────────────────────

const APPLIERS = new Map([
  ['SET_COMPILE_SDK',        planSetCompileSdk],
  ['SET_AGP_VERSION',        planSetAgpVersion],
  ['SET_NAMESPACE',          planSetNamespace],
  ['CREATE_LOCAL_PROPERTIES',planCreateLocalProperties],
]);

function plan(fixtureForm, projectRoot) {
  const colon = fixtureForm.indexOf(':');
  const head = colon === -1 ? fixtureForm : fixtureForm.slice(0, colon);
  const arg  = colon === -1 ? ''          : fixtureForm.slice(colon + 1);
  const fn = APPLIERS.get(head);
  if (!fn) {
    const known = [...APPLIERS.keys()].sort().join(', ');
    throw new Error(
      `apply: no applier registered for fixture_form "${head}". ` +
      `Known: ${known}. This fixture can be archived but not applied.`);
  }
  return fn(projectRoot, arg);
}

// ─────────────────────────────────────────────
// Execute a plan and write a receipt.
// ─────────────────────────────────────────────

function execute({ plan, projectRoot, fixtureForm, signatureId, receiptsDir }) {
  if (plan.before === plan.after) {
    return { applied: false, reason: 'no-op', plan, receipt: null };
  }
  _writeCreatingDirs(plan.file, plan.after);
  const receipt = {
    v: 1,
    ts_ms: Date.now(),
    project_root: projectRoot,
    signature_id: signatureId,
    fixture_form: fixtureForm,
    file: plan.file,
    summary: plan.summary,
    hash_before: sha256(plan.before),
    hash_after:  sha256(plan.after),
    before: plan.before,          // pre-image kept for deterministic revert
  };
  fs.mkdirSync(receiptsDir, { recursive: true });
  fs.appendFileSync(path.join(receiptsDir, RECEIPTS),
                    JSON.stringify(receipt) + '\n');
  return { applied: true, plan, receipt };
}

// ─────────────────────────────────────────────
// Revert — undo the last applied edit.
//
// Refuses if the file's current SHA does not match hash_after: that
// means something else has changed the file, and blindly restoring
// the pre-image would erase that change. The right response is to
// tell the user and stop.
// ─────────────────────────────────────────────

function loadReceipts(receiptsDir) {
  const f = path.join(receiptsDir, RECEIPTS);
  if (!fs.existsSync(f)) return [];
  return fs.readFileSync(f, 'utf8').split('\n').filter(Boolean).map(JSON.parse);
}

function revertLast(receiptsDir) {
  const receipts = loadReceipts(receiptsDir);
  const active   = receipts.filter(r => !r.reverted_ms);
  if (!active.length) return { reverted: false, reason: 'no applied edits' };
  const last = active[active.length - 1];
  const cur  = _readOrEmpty(last.file);
  if (sha256(cur) !== last.hash_after) {
    return { reverted: false, reason:
      `file changed since apply — refusing to blindly overwrite. ` +
      `Restore ${last.file} by hand or check git.` };
  }
  fs.writeFileSync(last.file, last.before);
  last.reverted_ms = Date.now();
  // Append a superseding entry rather than rewrite the file.
  fs.appendFileSync(path.join(receiptsDir, RECEIPTS),
                    JSON.stringify(last) + '\n');
  return { reverted: true, file: last.file, summary: last.summary };
}

// ─────────────────────────────────────────────
// File finders — narrow, best-effort, transparent about ambiguity.
// ─────────────────────────────────────────────

function _findTopLevelBuildFile(root) {
  for (const n of ['build.gradle.kts', 'build.gradle']) {
    const p = path.join(root, n);
    if (fs.existsSync(p)) return p;
  }
  throw new Error(`apply: no top-level build.gradle(.kts) in ${root}`);
}

function _findGradleBuildFile(root) {
  // Prefer app/, then any single module with a build file, then root.
  const candidates = [];
  const app = path.join(root, 'app');
  if (fs.existsSync(app)) candidates.push(app);
  for (const entry of fs.readdirSync(root, { withFileTypes: true })) {
    if (!entry.isDirectory() || entry.name.startsWith('.')) continue;
    if (entry.name === 'app') continue;
    const dir = path.join(root, entry.name);
    if (['build.gradle.kts','build.gradle'].some(n => fs.existsSync(path.join(dir, n))))
      candidates.push(dir);
  }
  if (!candidates.length) return _findTopLevelBuildFile(root);
  for (const dir of candidates) {
    for (const n of ['build.gradle.kts','build.gradle']) {
      const p = path.join(dir, n);
      if (fs.existsSync(p)) return p;
    }
  }
  return _findTopLevelBuildFile(root);
}

function _findManifest(root) {
  const guesses = [
    'app/src/main/AndroidManifest.xml',
    'src/main/AndroidManifest.xml',
    'AndroidManifest.xml',
  ];
  for (const g of guesses) {
    const p = path.join(root, g);
    if (fs.existsSync(p)) return p;
  }
  return null;
}

function _rewriteScalar(text, re, replacer, insertLine) {
  if (re.test(text)) return text.replace(re, replacer);
  // Insert into an existing `android { ... }` block, or append one.
  const androidRe = /android\s*\{([\s\S]*?)\n\}/m;
  if (androidRe.test(text))
    return text.replace(androidRe, (m, body) =>
      `android {${body}\n    ${insertLine}\n}`);
  return text.replace(/\n?$/, `\nandroid {\n    ${insertLine}\n}\n`);
}

function _insertOrReplaceNamespace(text, pkg) {
  const nsRe = /namespace\s*=?\s*["'][^"']*["']/;
  if (nsRe.test(text)) return text.replace(nsRe, `namespace = "${pkg}"`);
  const androidRe = /android\s*\{([\s\S]*?)\n\}/m;
  if (androidRe.test(text))
    return text.replace(androidRe, (_m, body) =>
      `android {${body}\n    namespace = "${pkg}"\n}`);
  return text.replace(/\n?$/, `\nandroid {\n    namespace = "${pkg}"\n}\n`);
}

module.exports = { plan, execute, revertLast, loadReceipts, sha256 };
