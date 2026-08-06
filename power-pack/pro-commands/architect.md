---
description: Design a system architecture from requirements
argument-hint: [system or feature to architect]
---
Act as a senior systems architect. For the system described below, produce:

1. **Component diagram** — name every service, store, and external dependency
2. **Data flow** — how data moves between components (include protocols)
3. **Interface contracts** — key API boundaries with request/response shapes
4. **Scaling strategy** — what bottlenecks appear at 10x/100x load and how to address them
5. **Trade-off log** — each major decision, the alternatives considered, and why you picked this one
6. **Risk register** — what can go wrong, likelihood, and mitigation

Be specific to the domain. No generic advice — every recommendation must reference the actual system.

System: $ARGUMENTS
