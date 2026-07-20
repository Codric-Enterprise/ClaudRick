---
name: figma-design-bridge
description: >-
  Deep guide to bridging Figma and code through a connected Figma MCP server
  in both directions — reading a design into implementable context
  (get_design_context, get_screenshot, get_metadata), writing code/intent
  into a new or existing Figma file (use_figma, create_new_file), and
  mapping components to code via Code Connect. Use whenever the user wants
  to implement a Figma design as code, push a UI into Figma, sync a design
  system, or shares a figma.com URL. Triggers on "figma", "design-to-code",
  "mock this up", "implement this design", "push to figma", "design
  system".
---

# Figma design bridge

Figma MCP work is fundamentally bidirectional: **design → code** (you're
implementing something that already exists in Figma) or **code → design**
(you're pushing an app page, component, or idea into Figma). Pick the
direction before reaching for tools — using the wrong one wastes calls and
produces the wrong artifact.

## Before you start

1. Confirm the Figma MCP server is connected and authorized in this session.
   If it needs authorization, tell the user rather than guessing at a
   workaround — there is no way to fetch a private Figma file without it.
2. Always load the server's own `/figma-use` skill (or its fallback resource
   `skill://figma/figma-use/SKILL.md`) **before** calling `use_figma` — it
   carries the current tool-call contract for that specific mutation path,
   which changes independently of this skill.
3. `whoami` early if you're unsure which Figma account/team context you're
   in, especially before any write (`create_new_file`, `upload_assets`,
   `send_code_connect_mappings`) — writes land in a real team's file space.

## Design → code

1. `get_metadata` first on a large/unfamiliar file to get the node tree
   cheaply before pulling full context — `get_design_context` on an entire
   page can be expensive and returns more than you need if you only care
   about one component.
2. `get_design_context` on the specific frame/component you're implementing
   — this is the primary source for structure, styles, and layout, not the
   screenshot.
3. `get_screenshot` as a visual cross-check, not a substitute for
   `get_design_context` — screenshots don't carry exact spacing/color tokens,
   only how it should look.
4. `get_variable_defs` for design tokens (color, spacing, typography scales)
   so implemented code references the same source of truth as the design
   rather than hardcoding pixel values read off a screenshot.
5. Check `get_code_connect_map` / `list_file_components_for_code_connect`
   before hand-implementing a component that might already have a mapped
   code counterpart — reimplementing a component that already has a Code
   Connect mapping duplicates work and diverges from the design system.
6. For motion/interaction-heavy designs, `get_motion_context` before
   guessing at animation timing/easing from the static screenshot.

## Code → design

1. Use `use_figma` (after loading `/figma-use`) as the primary write path for
   generating or editing Figma content from code, intent, or existing
   components — it's built for this direction, not `create_new_file` plus
   manual node construction.
2. `create_new_file` only when the target genuinely doesn't exist yet as a
   Figma file; otherwise write into the existing file so version history and
   comments stay attached to one artifact.
3. `upload_assets` for images/icons referenced by the design before or
   alongside the node creation that uses them — a node referencing an asset
   that hasn't been uploaded yet will render broken.
4. For diagrams/flowcharts rather than UI, prefer `generate_diagram` or
   `get_figjam` (loading `/figma-use-figjam` first) — FigJam is a different
   surface from a design file and has different conventions.

## Code Connect (bridging existing components)

Code Connect maps a Figma component to its real implementation so that
"design → code" for anyone using that component becomes a lookup instead of
a reimplementation.

1. `get_context_for_code_connect` / `get_code_connect_suggestions` to see
   what Figma already suggests as the match.
2. `add_code_connect_map` to record a mapping locally; `send_code_connect_mappings`
   to publish it back to Figma so the mapping is visible to everyone using
   that file, not just this session.
3. Load `/figma-code-connect` first for the exact mapping-file conventions
   for the language/framework in play — mapping syntax is
   framework-specific.

## Design systems and libraries

- `search_design_system` / `get_libraries` to check whether a component,
  token, or pattern already exists in the team's library before creating a
  near-duplicate.
- Load `/figma-generate-library` when the actual task is building out a
  design system from code, not implementing one page.

## Common pitfalls

- **Screenshot-driven implementation.** Reading pixel positions off
  `get_screenshot` instead of structured data from `get_design_context`
  produces code that looks right at one viewport and breaks everywhere else.
- **Skipping `/figma-use` before `use_figma`.** The tool's exact call
  contract is versioned separately from this skill; calling it cold risks
  malformed requests.
- **Reinventing mapped components.** Not checking Code Connect before
  hand-rolling a component that's already mapped to a real implementation.
- **Ignoring account/team context on writes.** `create_new_file` and
  `upload_assets` land in a specific team's Figma space — verify with
  `whoami` first if there's any doubt.

## Checklist

- [ ] Direction (design→code or code→design) identified before tool calls
- [ ] `/figma-use` (or its fallback) loaded before any `use_figma` call
- [ ] `get_design_context` used as the structural source of truth; screenshot
      only for visual confirmation
- [ ] Design tokens (`get_variable_defs`) used instead of hardcoded values
      where the design system defines them
- [ ] Code Connect checked before reimplementing an existing component
