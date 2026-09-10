#!/usr/bin/env bash
# EZR / Tapestry — build and verify every layer
set -u
cd "$(dirname "${BASH_SOURCE[0]}")"
P=0; S=0; F=0; declare -a N
have(){ command -v "$1" >/dev/null 2>&1; }
pass(){ P=$((P+1)); N+=("PASSED   $1"); }
fail(){ F=$((F+1)); N+=("FAILED   $1"); }
skip(){ S=$((S+1)); N+=("SKIPPED  $1 — $2"); printf '\n  ~ skipped: %s\n' "$2"; }

echo; echo "════════════════════════════════════════════════"
echo "EZR / TAPESTRY"; echo "Codric Enterprise"
echo "════════════════════════════════════════════════"

echo; echo "[0] C — the atom (carries T)"
if have gcc; then
  ( cd 0-atom-c && gcc -std=c99 -Wall -o tapestry_test tapestry.c tapestry_test.c -lm && ./tapestry_test | tail -2 ) && pass "Layer 0 (C)" || fail "Layer 0 (C)"
else skip "Layer 0 (C)" "gcc not found"; fi

echo; echo "[1] C++ — the phase engine"
if have gcc && have g++; then
  ( cd 1-phase-cpp \
    && gcc -std=c99 -Wall -c ../0-atom-c/tapestry.c -o tapestry.o \
    && g++ -std=c++14 -Wall -Wno-format-truncation -c phase.cpp -o phase.o \
    && g++ -std=c++14 -Wall -Wno-format-truncation -c phase_test.cpp -o phase_test.o \
    && g++ -o phase_test phase_test.o phase.o tapestry.o -lm && ./phase_test | tail -2 ) \
    && pass "Layer 1 (C++)" || fail "Layer 1 (C++)"
else skip "Layer 1 (C++)" "gcc and g++ required"; fi

echo; echo "[2] Python — the interpreter"
if have python3; then
  ( cd 2-interpreter-python && python3 ezr_test.py | tail -2 ) && pass "Layer 2 (Python)" || fail "Layer 2 (Python)"
else skip "Layer 2 (Python)" "python3 not found"; fi

echo; echo "[T] Python — teaching layer (Code for Dummies)"
if have python3; then
  ( cd 2-interpreter-python && python3 teach_test.py | tail -2 ) && pass "Teaching" || fail "Teaching"
else skip "Teaching" "python3 not found"; fi

echo; echo "[2a] Python — pipeline (lexer, parser, AST, semantic)"
if have python3; then
  ( cd 2-interpreter-python && python3 syntax_test.py | tail -2 ) && pass "Pipeline" || fail "Pipeline"
else skip "Pipeline" "python3 not found"; fi

echo; echo "[2b] Python — abstraction (functions, recursion)"
if have python3; then
  ( cd 2-interpreter-python && python3 abstract_test.py | tail -2 ) && pass "Abstraction" || fail "Abstraction"
else skip "Abstraction" "python3 not found"; fi

echo; echo "[2c] Python — vowel operators (I O U, synthesis)"
if have python3; then
  ( cd 2-interpreter-python && python3 vowels_test.py | tail -2 ) && pass "Vowels" || fail "Vowels"
else skip "Vowels" "python3 not found"; fi

echo; echo "[2d] Python — notebook batch (13 cells)"
if have python3; then
  ( cd 2-interpreter-python && python3 notebook.py | tail -6 ) && pass "Notebook" || fail "Notebook"
else skip "Notebook" "python3 not found"; fi

echo; echo "[7] Python — the forge (16 front ends, one core)"
if have python3; then
  ( cd 7-forge && python3 forge_test.py | tail -2 ) && pass "Layer 7 (Forge)" || fail "Layer 7 (Forge)"
else skip "Layer 7 (Forge)" "python3 not found"; fi

echo; echo "[3] Ruby — the DSL"
if have ruby; then
  ( cd 3-dsl-ruby && ruby ezr.rb | tail -2 ) && pass "Layer 3 (Ruby)" || fail "Layer 3 (Ruby)"
else skip "Layer 3 (Ruby)" "ruby not found (macOS: brew install ruby)"; fi

echo; echo "[4] SQL — the archive"
if have python3; then
  ( cd 4-archive-sql && python3 archive_test.py | tail -2 ) && pass "Layer 4 (SQL)" || fail "Layer 4 (SQL)"
else skip "Layer 4 (SQL)" "python3 required"; fi

echo; echo "[R] Research team"
if have python3; then
  python3 research.py | tail -22 && pass "Research" || fail "Research"
else skip "Research" "python3 required"; fi

echo; echo "════════════════════════════════════════════════"
echo "SUMMARY"; echo "════════════════════════════════════════════════"
for n in "${N[@]}"; do printf '  %s\n' "$n"; done
printf '\n  verified %d   skipped %d   failed %d\n\n' "$P" "$S" "$F"
[ "$F" -gt 0 ] && exit 1
exit 0
