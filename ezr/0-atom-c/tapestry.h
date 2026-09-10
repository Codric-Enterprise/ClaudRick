/*
 * tapestry.h — EZR / Tapestry, the atom
 *
 * The E-particle, restored to E<T>.
 *
 * v1 bound  name -> trust.        Correct for a checker.
 * v2 binds  name -> thing -> trust. Required for a language you write in.
 *
 * A thread in the weave. Every thread carries what it holds, how much it
 * is trusted, where it came from, and an anchor that survives translation
 * into any other language. Pull one thread and you can trace it through
 * the whole cloth.
 *
 * Codric Enterprise · Ricky (Dreid) · 2026
 * Theory of Relative E:  E = MC²
 */

#ifndef TAPESTRY_H
#define TAPESTRY_H

#include <stdint.h>
#include <stddef.h>

/* ─────────────────────────────────────────────
 * The scale. Unchanged from v1 — these are load bearing.
 * ───────────────────────────────────────────── */

#define E_ZERO               0     /* Z. zero-absolute.              */
#define E_CERTAIN            256   /* 4^4. the states of a byte.     */
#define E_EXECUTE_FLOOR      128   /* 256 / 2                        */
#define E_PI_WIDTH_WARN      81    /* floor(256 / pi)                */
#define E_PI_WIDTH_ENUMERATE 25    /* floor(256 / pi^2)              */
#define E_EMULATE_CEILING    3     /* floor(pi)                      */
#define E_PHI_SCALED         1618  /* phi * 1000, integer math       */
#define E_PHI_DENOM          1000
#define E_ASCEND_POINTS      3     /* aligned points to earn a rise  */

/* ─────────────────────────────────────────────
 * Binding modes. A binding is a name pointing at a thing; these are
 * the ways that can stand, and the ways it can fail.
 * ───────────────────────────────────────────── */

typedef enum {
    E_STATE_Z         = 0,  /* unbound. unknown. contagious.            */
    E_STATE_CONFIDENT = 1,  /* bound, trusted 1..255                    */
    E_STATE_CERTAIN   = 2,  /* bound, verified at 256. earned only.     */
    E_STATE_EQUIV     = 3,  /* bound to a range. pi governs width.      */
    E_STATE_EXPRESS   = 4,  /* shape bound, value pending               */
    E_STATE_EMULATING = 5,  /* running on a neighbour's pattern         */
    E_STATE_EVOLVED   = 6,  /* advanced through a closed force loop     */
    E_STATE_ANCHORED  = 7,  /* identity pinned across translation       */
    E_STATE_ABSENT    = 8,  /* not present, reason preserved            */
    E_STATE_ERROR     = 9   /* misbound. archived as a boundary marker. */
} e_state;

/* The five ways a binding fails. Every structurally checkable error in
 * every language reduces to one of these. */
typedef enum {
    E_DEFECT_NONE       = 0,
    E_DEFECT_UNBOUND    = 1,  /* name points at nothing               */
    E_DEFECT_MISBOUND   = 2,  /* name points at the wrong kind        */
    E_DEFECT_UNBOUNDED  = 3,  /* extent never delimited               */
    E_DEFECT_OVERBOUND  = 4,  /* many names, one thing, no order      */
    E_DEFECT_ORPHANED   = 5   /* thing outlives every name reaching it */
} e_defect;

/* Source language. EZR accepts all of them; Assimilate moves between. */
typedef enum {
    E_LANG_C = 0, E_LANG_CPP = 1, E_LANG_PYTHON = 2, E_LANG_RUBY = 3,
    E_LANG_SQL = 4, E_LANG_JAVA = 5, E_LANG_HTML = 6, E_LANG_RUST = 7,
    E_LANG_GO = 8, E_LANG_TS = 9, E_LANG_SWIFT = 10, E_LANG_EVER = 11
} e_lang;

/* What the particle actually holds. This is the T. */
typedef enum {
    E_TYPE_VOID = 0, E_TYPE_INT = 1, E_TYPE_REAL = 2, E_TYPE_TEXT = 3,
    E_TYPE_BOOL = 4, E_TYPE_LIST = 5, E_TYPE_FOREIGN = 6
} e_type;

/* ─────────────────────────────────────────────
 * The thread
 * ───────────────────────────────────────────── */

#define E_IDENT_MAX  64
#define E_REASON_MAX 128
#define E_TEXT_MAX   192

typedef struct {
    /* ── what it holds ── the T that v1 dropped ── */
    e_type   type;
    union {
        int64_t as_int;
        double  as_real;
        int     as_bool;
        int32_t as_ref;              /* index into a list pool */
    } value;
    char     text[E_TEXT_MAX];       /* inline payload for TEXT/FOREIGN */

    /* ── how much it is trusted ── */
    e_state  state;
    e_defect defect;
    int16_t  confidence;             /* 0..256 */
    int16_t  lo, hi;                 /* Equivalence bounds */

    /* ── where it came from ── */
    e_lang   lang;
    uint8_t  error_distance;
    uint8_t  generation;
    uint8_t  ascend_points;          /* aligned evidence toward a rise */

    /* ── the anchor: identity that survives translation ── */
    uint32_t anchor_id;              /* 0 = unanchored */

    int32_t  archive_id;
    int64_t  born_ms;
    char     ident[E_IDENT_MAX];
    char     reason[E_REASON_MAX];
} e_particle;

/* ─────────────────────────────────────────────
 * Constructors
 * ───────────────────────────────────────────── */

e_particle e_z(const char *ident, const char *reason);
e_particle e_z_defect(const char *ident, const char *reason, e_defect d);
e_particle e_int(const char *ident, int64_t v, int16_t conf, e_lang lang);
e_particle e_real(const char *ident, double v, int16_t conf, e_lang lang);
e_particle e_bool(const char *ident, int v, int16_t conf, e_lang lang);
e_particle e_text(const char *ident, const char *v, int16_t conf, e_lang lang);
e_particle e_equivalence(const char *ident, int16_t lo, int16_t hi, e_lang lang);
e_particle e_expression(const char *ident, e_type t, e_lang lang);
e_particle e_error(const char *ident, const char *reason, e_defect d, int16_t at);

/* ─────────────────────────────────────────────
 * Predicates
 * ───────────────────────────────────────────── */

int e_is_z(const e_particle *p);
int e_is_cleared(const e_particle *p);
int e_can_execute(const e_particle *p);
int e_has_value(const e_particle *p);
int e_is_anchored(const e_particle *p);
int e_width(const e_particle *p);

typedef enum {
    E_PI_ACCEPTABLE = 0, E_PI_ENUMERATE = 1, E_PI_APPROACHING_Z = 2
} e_pi_status;

e_pi_status e_pi_check(const e_particle *p);

/* ═════════════════════════════════════════════
 * The six A-operators. Closed over E: every one takes particles and
 * returns particles, so they compose without leaving the system.
 * ═════════════════════════════════════════════ */

/* ANY — lift any source language's binding into a particle.
 * The universal intake. Cannot fail loudly; failure is a Z that says why. */
e_particle a_any(const char *ident, const char *literal, e_lang from);

/* ASSIMILATE — carry a particle across languages, preserving payload and
 * trust. Refuses rather than translating lossily. An unanchored particle
 * loses 1 confidence per crossing; an anchored one loses nothing, which
 * is the entire point of anchoring. */
e_particle a_assimilate(const e_particle *p, e_lang to);

/* ANCHOR — pin an identity that survives every translation. Refuses to
 * anchor anything not cleared: an anchor on an unverified binding is a
 * lie that propagates. */
e_particle a_anchor(const e_particle *p, uint32_t anchor_id);

/* ASCEND — earn confidence through evidence. The only path upward.
 * Three aligned points are required; a single observation never lifts. */
e_particle a_ascend(const e_particle *p, const e_particle *evidence);

/* APPLY2ALL — broadcast one transformation across a corpus.
 * Z-contagion halts the broadcast at the offending particle rather than
 * silently skipping it. Returns the count transformed. */
typedef e_particle (*a_transform)(const e_particle *);
int a_apply2all(e_particle *set, int n, a_transform fn, int *halted_at);

/* AUTO-DIDACT — derive a rule from the archive's own history.
 * C² made executable: the corpus correlating its own correlations.
 * Returns a particle whose text is the derived rule, or Z if the history
 * does not support one. */
e_particle a_autodidact(const e_particle *history, int n, const char *about);

/* ─────────────────────────────────────────────
 * Propagation and arithmetic — unchanged semantics from v1
 * ───────────────────────────────────────────── */

e_particle e_carry(const e_particle *src, const char *new_ident);
e_particle e_cap(const e_particle *src, int16_t ceiling);
int16_t    e_excel_formula(int16_t a, int16_t b);
int16_t    e_phi_equalize(int16_t value, int16_t set_mean);
e_particle e_emulate(const e_particle *broken, const e_particle *working,
                     uint8_t error_distance);

/* ─────────────────────────────────────────────
 * Serialization. Extended for the payload and the anchor.
 * ───────────────────────────────────────────── */

size_t e_serialize(const e_particle *p, char *buf, size_t buflen);
int    e_deserialize(const char *line, e_particle *out);

const char *e_state_name(e_state s);
const char *e_lang_name(e_lang l);
const char *e_type_name(e_type t);
const char *e_defect_name(e_defect d);

#endif /* TAPESTRY_H */
