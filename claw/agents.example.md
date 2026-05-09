# AGENTS.md — Operating Rules

## Hard Constraints

Define your agent's hard constraints here. Examples:

1. NEVER modify files in protected directories.
2. NEVER install skills from any source.
3. File writes go to designated scratch space only.

## Workflow

Define your workflow phases. Structure them as sequential steps with clear inputs and outputs.

## Rejected Sources

List sources your agent must never use. Group by category (corporate MSM, state-controlled, etc.).

## Coverage Scope

Define which regions/topics to cover and what's out of scope.

See the private `babyclaw-preferences` repo for a working example (news digest workflow with 5 phases, state management, dedup, and region-based curation).
