'use strict';

// Runs extension.js against a stubbed `vscode` module and the real refix CLI.

const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const Module = require('node:module');

const BIN = path.join(__dirname, '..', '..', 'bin', 'refix');
const LOG_E = path.join(__dirname, '..', '..', 'demo', 'log-e.txt');
const ORIGINAL = 'plugins {\n    id("com.android.application") version "7.0.4"\n}\n';

function tmp() { return fs.mkdtempSync(path.join(os.tmpdir(), 'refix-vscode-')); }

function makeVscode({ cliPath, home, root }) {
  const v = {
    handlers: {},
    infos: [], warnings: [], errors: [], modals: [], lines: [],
    answers: { warning: 'Apply', input: 'my-project' },
  };
  v.commands = { registerCommand: (id, fn) => { v.handlers[id] = fn; return { dispose() {} }; } };
  v.workspace = {
    workspaceFolders: [{ uri: { fsPath: root } }],
    getConfiguration: () => ({ get: key => ({ cliPath, home })[key] }),
  };
  v.window = {
    activeTextEditor: undefined,
    createOutputChannel: () => ({
      show() {}, dispose() {},
      append: s => v.lines.push(s),
      appendLine: s => v.lines.push(`${s}\n`),
    }),
    showInformationMessage: async m => { v.infos.push(m); },
    showWarningMessage: async (m, opts) => {
      if (opts && opts.modal) { v.modals.push(m); return v.answers.warning; }
      v.warnings.push(m);
      return undefined;
    },
    showErrorMessage: async m => { v.errors.push(m); },
    showInputBox: async () => v.answers.input,
    showOpenDialog: async () => undefined,
    showWorkspaceFolderPick: async () => undefined,
  };
  return v;
}

function load(vscode) {
  const realLoad = Module._load;
  Module._load = function (request, ...rest) {
    return request === 'vscode' ? vscode : realLoad.call(this, request, ...rest);
  };
  const file = require.resolve('../extension.js');
  delete require.cache[file];
  try {
    const ext = require(file);
    const context = { subscriptions: [] };
    ext.activate(context);
    return { ext, context };
  } finally {
    Module._load = realLoad;
  }
}

function setup(overrides = {}) {
  const root = tmp();
  fs.writeFileSync(path.join(root, 'build.gradle'), ORIGINAL);
  const vscode = makeVscode({ cliPath: BIN, home: tmp(), root, ...overrides });
  const loaded = load(vscode);
  return { root, vscode, ...loaded, gradle: path.join(root, 'build.gradle') };
}

const uri = fsPath => ({ fsPath });

test('activate registers the four commands', () => {
  const { vscode, context } = setup();
  assert.deepStrictEqual(Object.keys(vscode.handlers).sort(),
    ['refix.accept', 'refix.apply', 'refix.revert', 'refix.scan']);
  assert.strictEqual(context.subscriptions.length, 4);
});

test('scan writes the match to the output channel', async () => {
  const { vscode } = setup();
  await vscode.handlers['refix.scan'](uri(LOG_E));
  assert.ok(vscode.lines.join('').includes('match: gradle.agp_too_old'));
});

test('apply previews, asks, then writes; revert restores; second revert says nothing to undo', async () => {
  const { vscode, gradle } = setup();

  await vscode.handlers['refix.apply'](uri(LOG_E));
  assert.strictEqual(vscode.modals.length, 1);
  assert.ok(vscode.modals[0].includes('apply 1 fix '));
  assert.ok(fs.readFileSync(gradle, 'utf8').includes('version "8.5.2"'));
  assert.deepStrictEqual(vscode.infos, ['ReFix: applied 1, skipped 0, failed 0.']);

  await vscode.handlers['refix.revert']();
  assert.strictEqual(fs.readFileSync(gradle, 'utf8'), ORIGINAL);
  assert.ok(vscode.infos.includes('ReFix: reverted the last fix.'));

  await vscode.handlers['refix.revert']();
  assert.strictEqual(vscode.warnings.length, 1);
  assert.ok(vscode.warnings[0].includes('no applied edits'));
});

test('apply writes nothing when the confirmation is declined', async () => {
  const { vscode, gradle } = setup();
  vscode.answers.warning = undefined;
  await vscode.handlers['refix.apply'](uri(LOG_E));
  assert.strictEqual(vscode.modals.length, 1);
  assert.strictEqual(fs.readFileSync(gradle, 'utf8'), ORIGINAL);
  assert.deepStrictEqual(vscode.infos, []);
});

test('apply with no matching signature never asks', async () => {
  const { vscode, gradle } = setup();
  const log = path.join(tmp(), 'empty.log');
  fs.writeFileSync(log, 'BUILD SUCCESSFUL\n');
  await vscode.handlers['refix.apply'](uri(log));
  assert.strictEqual(vscode.modals.length, 0);
  assert.strictEqual(fs.readFileSync(gradle, 'utf8'), ORIGINAL);
  assert.ok(vscode.infos[0].includes('nothing to apply'));
});

test('accept archives with the entered source name', async () => {
  const { vscode } = setup();
  await vscode.handlers['refix.accept'](uri(LOG_E));
  assert.deepStrictEqual(vscode.infos, ['ReFix: archived 1 repair(s) from my-project.']);
});

test('a missing CLI gives an install hint instead of a stack trace', async () => {
  const { vscode } = setup({ cliPath: path.join(tmp(), 'no-such-refix') });
  await vscode.handlers['refix.scan'](uri(LOG_E));
  assert.strictEqual(vscode.errors.length, 1);
  assert.ok(vscode.errors[0].includes('npm install -g refix-cli'));
});
