---
description: Design a REST or GraphQL API with contracts and documentation
argument-hint: [describe the API's purpose and main resources]
---
Design a complete API:

1. **Resource model** — entities, their relationships, and URL structure
2. **Endpoint catalog** — every endpoint: method, path, description, request/response schema
3. **Authentication** — scheme (API key, OAuth2, JWT), token lifecycle, scopes
4. **Pagination** — strategy (cursor vs. offset), default/max page sizes, response envelope
5. **Error handling** — error code taxonomy, response format, human-readable messages
6. **Versioning** — strategy (URL path, header, query param) with migration policy
7. **Rate limiting** — tiers, headers (X-RateLimit-*), retry-after behavior
8. **Idempotency** — which operations need idempotency keys and how they work
9. **Webhooks** — event catalog, payload format, retry policy, signature verification
10. **OpenAPI spec** — complete YAML/JSON specification ready to import into tools

Follow REST conventions strictly. Every design choice should have a rationale.

API: $ARGUMENTS
