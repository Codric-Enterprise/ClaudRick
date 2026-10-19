'use strict';

const { execFile } = require('node:child_process');

function scanArgs(log)              { return ['scan', log]; }
function acceptArgs(log, source)    { return ['accept', log, source]; }
function revertArgs()               { return ['revert']; }
function applyArgs(log, project, dryRun) {
  const args = ['apply', log, '--project', project];
  if (dryRun) args.push('--dry-run');
  return args;
}

// `apply` prints one "  plan:" line per fix it would write.
function countPlans(stdout) {
  return (stdout.match(/^\s+plan:/gm) || []).length;
}

// On Windows the refix shim is a .cmd file, which only runs through a shell.
function quote(arg) {
  return /[\s"]/.test(arg) ? `"${arg.replace(/"/g, '\\"')}"` : arg;
}

// Resolves with { code, error, stdout, stderr }. code is the exit status;
// error is set only when the process could not be started (e.g. ENOENT).
function runRefix({ cliPath = 'refix', args, cwd, home, platform = process.platform }) {
  const env = { ...process.env };
  if (home) env.REFIX_HOME = home;
  const shell = platform === 'win32';
  return new Promise(resolve => {
    execFile(
      cliPath,
      shell ? args.map(quote) : args,
      { cwd, env, shell, encoding: 'utf8', maxBuffer: 10 * 1024 * 1024 },
      (err, stdout, stderr) => {
        if (!err) return resolve({ code: 0, error: null, stdout, stderr });
        if (typeof err.code === 'number') return resolve({ code: err.code, error: null, stdout, stderr });
        resolve({ code: null, error: err, stdout, stderr });
      },
    );
  });
}

module.exports = { scanArgs, acceptArgs, revertArgs, applyArgs, countPlans, quote, runRefix };
