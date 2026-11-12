# ReFix for VS Code

Scan a failed Gradle build log, apply the known fix, and undo it from a hashed receipt. This extension is a thin front end for the [`refix-cli`](https://github.com/Codric-Enterprise/ClaudRick/tree/main/refix2) command line tool.

## Requirements

Install the CLI first:

    npm install -g refix-cli

## Commands

Run these from the Command Palette (`ReFix: …`), or right-click a `.log` or `.txt` file for Scan and Apply.

| Command | What it runs |
| --- | --- |
| ReFix: Scan Build Log | `refix scan <log>` |
| ReFix: Apply Fix (Preview, then Confirm) | `refix apply <log> --project <folder> --dry-run`, then, after you confirm, the same command without `--dry-run` |
| ReFix: Revert Last Fix | `refix revert` |
| ReFix: Accept Build Log Repairs | `refix accept <log> <source>` |

Apply always shows the plan first and asks before it writes. Every write leaves a receipt, and Revert refuses if the file changed since ReFix wrote it. Output goes to the **ReFix** output channel.

`apply` can write four kinds of fix: set `compileSdk`, pin the Android Gradle Plugin version, set the `namespace` from the manifest, and create `local.properties` with `sdk.dir`. Other matches are reported and skipped.

## Settings

| Setting | Default | Meaning |
| --- | --- | --- |
| `refix.cliPath` | `refix` | Path to the `refix` executable. |
| `refix.home` | empty | Archive and receipts directory. Empty uses the CLI default (`~/.refix` or `$REFIX_HOME`). |

## Develop

    cd refix2/vscode-extension
    npm test            # node --test, uses the CLI in ../bin
    npm run package     # builds refix-vscode-<version>.vsix via vsce

## License

MIT
