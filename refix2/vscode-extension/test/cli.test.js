'use strict';

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const cli = require('../lib/cli');

const BIN = path.join(__dirname, '..', '..', 'bin', 'refix');
const LOG_E = path.join(__dirname, '..', '..', 'demo', 'log-e.txt');

function tmp() { return fs.mkdtempSync(path.join(os.tmpdir(), 'refix-vscode-')); }
function refix(args, home, cwd) {
  return cli.runRefix({ cliPath: process.execPath, args: [BIN, ...args], home, cwd });
}

test('argument builders match the CLI usage', () => {
  assert.deepStrictEqual(cli.scanArgs('b.log'), ['scan', 'b.log']);
  assert.deepStrictEqual(cli.acceptArgs('b.log', 'proj'), ['accept', 'b.log', 'proj']);
  assert.deepStrictEqual(cli.revertArgs(), ['revert']);
  assert.deepStrictEqual(cli.applyArgs('b.log', '/p', true), ['apply', 'b.log', '--project', '/p', '--dry-run']);
  assert.deepStrictEqual(cli.applyArgs('b.log', '/p', false), ['apply', 'b.log', '--project', '/p']);
});

test('quote wraps only arguments that need it', () => {
  assert.strictEqual(cli.quote('plain'), 'plain');
  assert.strictEqual(cli.quote('C:\\my logs\\b.log'), '"C:\\my logs\\b.log"');
  assert.strictEqual(cli.quote('a"b'), '"a\\"b"');
});

test('runRefix reports a missing executable as error, not exit code', async () => {
  const res = await cli.runRefix({ cliPath: path.join(tmp(), 'no-such-refix'), args: ['--help'] });
  assert.strictEqual(res.code, null);
  assert.ok(res.error);
});

test('runRefix returns the CLI exit status', async () => {
  const res = await refix(['nonsense'], tmp());
  assert.strictEqual(res.code, 2);
  assert.ok(res.stderr.includes('usage:'));
});

test('scan matches the demo AGP log', async () => {
  const res = await refix(cli.scanArgs(LOG_E), tmp());
  assert.strictEqual(res.code, 0);
  assert.ok(res.stdout.includes('match: gradle.agp_too_old'));
});

test('dry-run, apply and revert round trip through the real CLI', async () => {
  const home = tmp();
  const proj = tmp();
  const original = 'plugins {\n    id("com.android.application") version "7.0.4"\n}\n';
  const gradle = path.join(proj, 'build.gradle');
  fs.writeFileSync(gradle, original);

  const dry = await refix(cli.applyArgs(LOG_E, proj, true), home, proj);
  assert.strictEqual(dry.code, 0);
  assert.strictEqual(cli.countPlans(dry.stdout), 1);
  assert.strictEqual(fs.readFileSync(gradle, 'utf8'), original);

  const applied = await refix(cli.applyArgs(LOG_E, proj, false), home, proj);
  assert.ok(applied.stdout.includes('applied 1, skipped 0, failed 0.'));
  assert.ok(fs.readFileSync(gradle, 'utf8').includes('version "8.5.2"'));

  const reverted = await refix(cli.revertArgs(), home);
  assert.ok(/^reverted:/m.test(reverted.stdout));
  assert.strictEqual(fs.readFileSync(gradle, 'utf8'), original);
});
