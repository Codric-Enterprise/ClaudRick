---
description: Deep performance analysis and optimization plan
argument-hint: [code, query, or system to optimize]
---
Analyze the following for performance. Produce:

1. **Bottleneck map** — identify the hot path and every operation on it with estimated cost (time complexity, I/O calls, memory allocation)
2. **Measurement plan** — specific metrics to capture, tools to use, and baseline targets
3. **Quick wins** — changes that take <1 hour and yield measurable improvement
4. **Structural optimizations** — algorithmic or architectural changes with expected impact
5. **Caching strategy** — what to cache, where, TTL policy, invalidation approach
6. **Before/after** — show optimized code side-by-side with the original for the top 3 changes

Quantify everything. "Faster" is not a finding — "reduces O(n²) to O(n log n), saving ~200ms at 10k items" is.

Target: $ARGUMENTS
