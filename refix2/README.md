# ReFix

Stop googling the same Gradle error twice.

ReFix is a zero-dependency command-line tool that reads a captured Gradle build log, matches the error against a library of known error signatures, and applies the fix. Every change ReFix makes is logged with a receipt, so you can undo it.

## Install

    npm install -g refix-cli

Requires Node.js (tested on Node 22). No other dependencies.

## How it works

1. Your Gradle build fails, and you save its output to a log file.
2. `refix scan` matches the log against the signature corpus (`signatures/gradle.json`).
3. `refix apply` shows the plan for each match and writes it, unless you pass `--dry-run`, which shows the plan and changes nothing.
4. Each write gets a receipt, a hashed record appended to `receipts.jsonl` in the ReFix home directory (`$REFIX_HOME`, or `~/.refix` by default).
5. If the fix doesn't work, `refix revert` restores the file from the receipt.

## Usage

Match a build log against the signatures:

    refix scan <build.log>

Preview a fix without touching any files:

    refix apply <build.log> --dry-run

Apply a fix to a specific project:

    refix apply <build.log> --project ./my-android-app

Undo the last applied fix:

    refix revert

Archive the matches from a build log as accepted repairs, tagged with a source name:

    refix accept <build.log> <source-ident>

Other commands:

    refix candidates    # fixtures seen across enough distinct sources to propose
    refix propose       # try to admit each candidate; gated by replay
    refix rules         # admitted and rejected rules
    refix archive       # raw archive as JSON lines on stdout

`apply` can write four kinds of fix: set `compileSdk`, pin the Android Gradle Plugin version, set the `namespace` from the manifest, and create `local.properties` with `sdk.dir`. Matches for other signatures are reported and skipped.

## Safety

- ReFix records a receipt for every write it makes.
- Every receipt is hashed. `refix revert` refuses to restore a file that no longer matches the state ReFix wrote.
- `revert` undoes only the most recent applied fix. Run it again to undo the one before, if that one is still in place.
- Use `--dry-run` to see exactly what would change first.

## Status

v2.1 has 28 passing tests (`npm test`). Accepted repairs are stored in the local archive. A rule is admitted only after the same fix recurs across three distinct sources and passes a replay against the whole archive.

## Source

https://github.com/Codric-Enterprise/ClaudRick/tree/main/refix2

## License

MIT

## Author

Rick Erickson, Codric Enterprise
