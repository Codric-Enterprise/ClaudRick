package com.codric.ezr;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * The runner. Layer 5's entry point, and the thing that makes this a runtime
 * rather than a library.
 *
 * <pre>
 *   java -cp out com.codric.ezr.Ezr program.ezr
 *   java -cp out com.codric.ezr.Ezr -e 'let x = 5 in x + 1'
 *   echo 'def main() = 6 * 7' | java -cp out com.codric.ezr.Ezr -
 * </pre>
 *
 * <p>Exit codes, matching {@code 2-interpreter-python/ezrun.py} exactly:
 * <strong>0</strong> a value, <strong>1</strong> a refusal (Z),
 * <strong>2</strong> input that would not compile. The output format matches
 * too — not for tidiness, but because {@code differential.py} compares the
 * two runners byte for byte, and a runtime nothing checks is a runtime
 * nobody should trust.
 */
public final class Ezr {

    public static final int EXIT_OK       = 0;
    public static final int EXIT_REFUSED  = 1;
    public static final int EXIT_BAD_INPUT = 2;

    private Ezr() { }

    public static void main(String[] args) {
        System.exit(run(args));
    }

    static int run(String[] argv) {
        String  file = null, expr = null, call = null;
        int     depth = 100;
        boolean quiet = false;

        for (int i = 0; i < argv.length; i++) {
            String a = argv[i];
            switch (a) {
                case "-h", "--help" -> { usage(System.out); return EXIT_OK; }
                case "-q", "--quiet" -> quiet = true;
                case "-e", "--eval" -> {
                    if (++i >= argv.length) return fail("-e needs an expression");
                    expr = argv[i];
                }
                case "-c", "--call" -> {
                    if (++i >= argv.length) return fail("-c needs an expression");
                    call = argv[i];
                }
                case "-d", "--depth" -> {
                    if (++i >= argv.length) return fail("-d needs a number");
                    try {
                        depth = Integer.parseInt(argv[i]);
                    } catch (NumberFormatException e) {
                        return fail("-d needs a number, got '" + argv[i] + "'");
                    }
                }
                default -> {
                    if (a.startsWith("-") && a.length() > 1 && !a.equals("-")) {
                        return fail("unknown option '" + a + "'");
                    }
                    if (file != null) return fail("more than one program given");
                    file = a;
                }
            }
        }
        if (file == null && expr == null) {
            return fail("one of the arguments file -e/--eval is required");
        }
        if (file != null && expr != null) {
            return fail("give a file or -e, not both");
        }

        String source, where;
        if (expr != null) {
            source = expr; where = "-e";
        } else if (file.equals("-")) {
            source = readAll(System.in); where = "<stdin>";
            if (source == null) return fail("cannot read stdin");
        } else {
            Path p = Path.of(file);
            if (Files.isDirectory(p)) {
                return fail(file + " is a directory, not a program");
            }
            if (!Files.exists(p)) return fail("no such file: " + file);
            try {
                source = Files.readString(p, StandardCharsets.UTF_8);
            } catch (IOException e) {
                return fail("cannot read " + file + ": " + e.getMessage());
            }
            where = file;
        }
        return execute(source, where, call, depth, quiet);
    }

    /* ── the four stages ────────────────────────────────────────────── */

    static int execute(String source, String where, String call,
                       int depth, boolean quiet) {
        Parser.Out parsed = Parser.parse(source);
        if (!parsed.ok()) {
            // stage names match the Python runner so the two are comparable
            String stage = parsed.error().reason.contains("character")
                        || parsed.error().reason.contains("unterminated")
                           ? "lex" : "parse";
            System.err.println("ezr: " + where + ": " + stage + ": "
                               + parsed.error().reason);
            return EXIT_BAD_INPUT;
        }

        Semantic.Analysis analysis = new Semantic().analyse(parsed.ast());
        if (!analysis.ok()) {
            System.err.println("ezr: " + where + ": semantic: "
                               + analysis.errors.get(0));
            return EXIT_BAD_INPUT;
        }

        Map<String, Eval.Fn> fns = Eval.definitions(parsed.ast());
        Ast ast = parsed.ast();

        // a bare expression runs as it stands
        if (ast instanceof Ast.Prog p && p.expr() != null) {
            return report(new Eval(fns, depth).run(p.expr()), quiet);
        }

        // otherwise: --call wins, else main(), else say what is defined
        String entry = (call != null) ? call
                     : fns.containsKey("main") ? "main()" : null;
        if (entry == null) {
            List<String> names = new ArrayList<>(fns.keySet());
            System.err.println("ezr: " + where + " defines " + names
                + " and does not say what to run.\n"
                + "     Define main(), or pass --call 'expr'.");
            return EXIT_BAD_INPUT;
        }

        Parser.Out entryParse = Parser.parse(entry);
        if (!entryParse.ok()) {
            System.err.println("ezr: --call " + entry + ": parse: "
                               + entryParse.error().reason);
            return EXIT_BAD_INPUT;
        }
        Ast body = (entryParse.ast() instanceof Ast.Prog ep && ep.expr() != null)
                 ? ep.expr() : entryParse.ast();
        return report(new Eval(fns, depth).run(body), quiet);
    }

    /** Render the result the way ezrun.py does, and pick the exit code. */
    static int report(Particle result, boolean quiet) {
        if (result.isZ()) {
            System.err.println("Z(" + result.defect + ") — " + result.reason);
            return EXIT_REFUSED;
        }
        if (quiet) {
            System.out.println(result.render());
        } else {
            System.out.println(result.render() + "  @ " + result.confidence
                               + "/" + Particle.CERTAIN);
        }
        return EXIT_OK;
    }

    /* ── plumbing ───────────────────────────────────────────────────── */

    private static int fail(String msg) {
        System.err.println("ezr: " + msg);
        return EXIT_BAD_INPUT;
    }

    private static String readAll(InputStream in) {
        try {
            return new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            return null;
        }
    }

    private static void usage(java.io.PrintStream out) {
        out.println("""
            usage: ezr [-h] [-e EXPR] [-c EXPR] [-d DEPTH] [-q] [file]

            Run an EZR program.

              file          program to run, or - for stdin
              -e, --eval    run one expression instead of a file
              -c, --call    which expression to run after the definitions
              -d, --depth   call-depth limit (default 100)
              -q, --quiet   print the value only, without its confidence

            Exit codes: 0 a value, 1 a refusal (Z), 2 would not compile.""");
    }
}
