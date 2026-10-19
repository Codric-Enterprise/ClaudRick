'use strict';

const vscode = require('vscode');
const cli = require('./lib/cli');

let output;

function channel() {
  if (!output) output = vscode.window.createOutputChannel('ReFix');
  return output;
}

function settings() {
  const c = vscode.workspace.getConfiguration('refix');
  return { cliPath: c.get('cliPath') || 'refix', home: c.get('home') || '' };
}

async function projectRoot() {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    vscode.window.showErrorMessage('ReFix: open a folder first.');
    return undefined;
  }
  if (folders.length === 1) return folders[0].uri.fsPath;
  const picked = await vscode.window.showWorkspaceFolderPick({ placeHolder: 'Project to fix' });
  return picked ? picked.uri.fsPath : undefined;
}

// Use the right-clicked file, else the active editor if it looks like a log,
// else ask.
async function pickLog(uri) {
  if (uri && uri.fsPath) return uri.fsPath;
  const active = vscode.window.activeTextEditor;
  if (active && active.document.uri.scheme === 'file' && /\.(log|txt)$/i.test(active.document.fileName)) {
    return active.document.fileName;
  }
  const picked = await vscode.window.showOpenDialog({
    canSelectMany: false,
    openLabel: 'Use as build log',
    filters: { 'Build logs': ['log', 'txt'], 'All files': ['*'] },
  });
  return picked && picked[0] ? picked[0].fsPath : undefined;
}

async function run(args, cwd) {
  const { cliPath, home } = settings();
  const out = channel();
  out.show(true);
  out.appendLine(`$ ${cliPath} ${args.join(' ')}`);
  const res = await cli.runRefix({ cliPath, args, cwd, home });
  if (res.error) {
    out.appendLine(`could not start "${cliPath}": ${res.error.message}`);
    vscode.window.showErrorMessage(
      `ReFix: could not run "${cliPath}". Install it with "npm install -g refix-cli" or set refix.cliPath.`);
    return undefined;
  }
  if (res.stdout) out.append(res.stdout);
  if (res.stderr) out.append(res.stderr);
  out.appendLine(`(exit ${res.code})`);
  if (res.code !== 0) {
    vscode.window.showErrorMessage(`ReFix exited with code ${res.code}. See the ReFix output.`);
    return undefined;
  }
  return res;
}

async function scan(uri) {
  const log = await pickLog(uri);
  if (!log) return;
  await run(cli.scanArgs(log), undefined);
}

async function apply(uri) {
  const log = await pickLog(uri);
  if (!log) return;
  const root = await projectRoot();
  if (!root) return;

  const preview = await run(cli.applyArgs(log, root, true), root);
  if (!preview) return;
  const plans = cli.countPlans(preview.stdout);
  if (plans === 0) {
    vscode.window.showInformationMessage('ReFix: nothing to apply. See the ReFix output.');
    return;
  }

  const choice = await vscode.window.showWarningMessage(
    `ReFix: apply ${plans} fix${plans === 1 ? '' : 'es'} to ${root}? Each write leaves a receipt you can revert.`,
    { modal: true },
    'Apply',
  );
  if (choice !== 'Apply') return;

  const applied = await run(cli.applyArgs(log, root, false), root);
  if (!applied) return;
  const summary = applied.stdout.match(/applied \d+, skipped \d+, failed \d+\./);
  vscode.window.showInformationMessage(`ReFix: ${summary ? summary[0] : 'done.'}`);
}

async function revert() {
  const res = await run(cli.revertArgs(), undefined);
  if (!res) return;
  if (/^reverted:/m.test(res.stdout)) {
    vscode.window.showInformationMessage('ReFix: reverted the last fix.');
  } else {
    vscode.window.showWarningMessage(`ReFix: ${res.stdout.trim() || 'nothing reverted.'}`);
  }
}

async function accept(uri) {
  const log = await pickLog(uri);
  if (!log) return;
  const source = await vscode.window.showInputBox({
    prompt: 'Source identifier for this log (e.g. the project or repo name)',
    validateInput: v => (v.trim() ? undefined : 'Required'),
  });
  if (!source) return;
  const res = await run(cli.acceptArgs(log, source.trim()), undefined);
  if (res) vscode.window.showInformationMessage(`ReFix: ${res.stdout.trim()}`);
}

function activate(context) {
  const reg = (id, fn) => context.subscriptions.push(vscode.commands.registerCommand(id, fn));
  reg('refix.scan', scan);
  reg('refix.apply', apply);
  reg('refix.revert', revert);
  reg('refix.accept', accept);
}

function deactivate() {
  if (output) output.dispose();
  output = undefined;
}

module.exports = { activate, deactivate };
