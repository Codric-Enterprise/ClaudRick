---
description: Design a data model / database schema
argument-hint: [describe the domain and key entities]
---
Design a data model for the following domain:

1. **Entity inventory** — every entity with its purpose and real-world meaning
2. **Attributes** — for each entity: fields, types, constraints, defaults, and why each exists
3. **Relationships** — cardinality (1:1, 1:N, M:N), required vs. optional, cascade behavior
4. **Schema DDL** — CREATE TABLE statements ready to run (PostgreSQL syntax)
5. **Indexes** — which columns to index and why (query patterns they serve)
6. **Normalization** — current normal form; any intentional denormalization with justification
7. **Migration path** — if evolving an existing schema, the ALTER sequence with rollback
8. **Sample queries** — the 5 most common queries this schema serves, with EXPLAIN analysis
9. **Edge cases** — soft deletes, audit trails, multi-tenancy, temporal data if applicable
10. **Scaling notes** — partitioning strategy, estimated row counts, and when to shard

Domain: $ARGUMENTS
