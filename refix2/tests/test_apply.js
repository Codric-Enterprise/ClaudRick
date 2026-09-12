// test_apply.js — apply and revert on synthetic project trees.
'use strict';

const fs   = require('fs');
const os   = require('os');
const path = require('path');
const assert = require('assert');

const { plan, execute, revertLast, sha256 } = require('../src/apply');

let pass = 0, fail = 0;
function t(name, fn) { try { fn(); pass++; console.log('  ok ' + name); }
  catch (e) { fail++; console.log('FAIL ' + name + ': ' + e.message); } }

function tmpProject(spec) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'refix-apply-'));
  for (const [rel, content] of Object.entries(spec)) {
    const p = path.join(dir, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, content);
  }
  return dir;
}
function tmpReceipts() {
  return fs.mkdtempSync(path.join(os.tmpdir(), 'refix-receipts-'));
}

// ─── planners ──────────────────────────────────────────────────────

t('SET_COMPILE_SDK inserts into an app/build.gradle.kts with no android block', () => {
  const root = tmpProject({ 'app/build.gradle.kts': 'plugins {\n    id("com.android.application")\n}\n' });
  const p = plan('SET_COMPILE_SDK:34', root);
  assert.ok(p.after.includes('compileSdk = 34'), p.after);
  assert.ok(p.after.includes('android {'),       p.after);
});

t('SET_COMPILE_SDK rewrites existing compileSdk without duplicating', () => {
  const root = tmpProject({ 'app/build.gradle.kts':
    'android {\n    compileSdk = 30\n}\n' });
  const p = plan('SET_COMPILE_SDK:34', root);
  assert.strictEqual((p.after.match(/compileSdk/g) || []).length, 1);
  assert.ok(p.after.includes('compileSdk = 34'));
});

t('SET_AGP_VERSION pins plugins-block version', () => {
  const root = tmpProject({ 'build.gradle.kts':
    'plugins {\n    id("com.android.application") version "7.0.4" apply false\n}\n' });
  const p = plan('SET_AGP_VERSION:8.5.2', root);
  assert.ok(p.after.includes('version "8.5.2"'), p.after);
});

t('SET_AGP_VERSION refuses a malformed version', () => {
  const root = tmpProject({ 'build.gradle.kts': 'plugins {}\n' });
  assert.throws(() => plan('SET_AGP_VERSION:not-a-version', root));
});

t('SET_NAMESPACE reads package= from AndroidManifest.xml', () => {
  const root = tmpProject({
    'app/build.gradle.kts': 'android {\n}\n',
    'app/src/main/AndroidManifest.xml':
      '<manifest package="com.codric.eng"\n xmlns:android="http://schemas.android.com/apk/res/android"/>\n' });
  const p = plan('SET_NAMESPACE:from_manifest', root);
  assert.ok(p.after.includes('namespace = "com.codric.eng"'), p.after);
});

t('SET_NAMESPACE refuses when no package in manifest', () => {
  const root = tmpProject({
    'app/build.gradle.kts': 'android {}\n',
    'app/src/main/AndroidManifest.xml': '<manifest/>' });
  assert.throws(() => plan('SET_NAMESPACE:from_manifest', root));
});

t('CREATE_LOCAL_PROPERTIES no-ops if sdk.dir already present', () => {
  const root = tmpProject({
    'build.gradle.kts': '',
    'local.properties': 'sdk.dir=/existing/path\n' });
  const p = plan('CREATE_LOCAL_PROPERTIES:sdk.dir', root);
  assert.strictEqual(p.before, p.after);
});

t('CREATE_LOCAL_PROPERTIES refuses cleanly when ANDROID_HOME unset', () => {
  const root = tmpProject({ 'build.gradle.kts': '' });
  const savedHome = process.env.ANDROID_HOME;
  const savedRoot = process.env.ANDROID_SDK_ROOT;
  delete process.env.ANDROID_HOME;
  delete process.env.ANDROID_SDK_ROOT;
  try { assert.throws(() => plan('CREATE_LOCAL_PROPERTIES:sdk.dir', root)); }
  finally {
    if (savedHome !== undefined) process.env.ANDROID_HOME = savedHome;
    if (savedRoot !== undefined) process.env.ANDROID_SDK_ROOT = savedRoot;
  }
});

t('unknown fixture_form is refused with a helpful message', () => {
  const root = tmpProject({ 'build.gradle.kts': '' });
  try { plan('MADE_UP:foo', root); assert.fail('should have thrown'); }
  catch (e) { assert.ok(e.message.includes('MADE_UP')); assert.ok(e.message.includes('Known')); }
});

// ─── apply / revert receipt loop ───────────────────────────────────

t('execute writes the file and records a receipt', () => {
  const root = tmpProject({ 'app/build.gradle.kts': 'android {\n    compileSdk = 30\n}\n' });
  const rec  = tmpReceipts();
  const p = plan('SET_COMPILE_SDK:34', root);
  const res = execute({ plan: p, projectRoot: root, fixtureForm: 'SET_COMPILE_SDK:34',
                        signatureId: 'gradle.compilesdk_too_low', receiptsDir: rec });
  assert.ok(res.applied);
  const written = fs.readFileSync(path.join(root, 'app/build.gradle.kts'), 'utf8');
  assert.ok(written.includes('compileSdk = 34'));
  const receipts = fs.readFileSync(path.join(rec, 'receipts.jsonl'), 'utf8').trim().split('\n');
  assert.strictEqual(receipts.length, 1);
  const r = JSON.parse(receipts[0]);
  assert.strictEqual(r.hash_after, sha256(written));
});

t('revert restores the pre-image exactly', () => {
  const root = tmpProject({ 'app/build.gradle.kts': 'android {\n    compileSdk = 30\n}\n' });
  const rec  = tmpReceipts();
  const p    = plan('SET_COMPILE_SDK:34', root);
  const original = p.before;
  execute({ plan: p, projectRoot: root, fixtureForm: 'SET_COMPILE_SDK:34',
            signatureId: 'gradle.compilesdk_too_low', receiptsDir: rec });
  const r = revertLast(rec);
  assert.ok(r.reverted, JSON.stringify(r));
  const after = fs.readFileSync(path.join(root, 'app/build.gradle.kts'), 'utf8');
  assert.strictEqual(after, original);
});

t('revert refuses when the file has changed since apply', () => {
  const root = tmpProject({ 'app/build.gradle.kts': 'android {\n    compileSdk = 30\n}\n' });
  const rec  = tmpReceipts();
  const p    = plan('SET_COMPILE_SDK:34', root);
  execute({ plan: p, projectRoot: root, fixtureForm: 'SET_COMPILE_SDK:34',
            signatureId: 'gradle.compilesdk_too_low', receiptsDir: rec });
  // Simulate a subsequent human edit.
  fs.writeFileSync(path.join(root, 'app/build.gradle.kts'),
                   'android {\n    compileSdk = 35 // human tweak\n}\n');
  const r = revertLast(rec);
  assert.strictEqual(r.reverted, false);
  assert.ok(/changed since apply/i.test(r.reason), r.reason);
});

t('revert with no receipts reports plainly', () => {
  const rec = tmpReceipts();
  const r   = revertLast(rec);
  assert.strictEqual(r.reverted, false);
  assert.ok(/no applied edits/i.test(r.reason));
});

// ──────────────────────────────────────────────────────────────

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
