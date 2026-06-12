# AGENTS.md — Operating Rules

## Hard Constraints

Define your agent's hard constraints here. Examples:

1. NEVER modify files in protected directories.
2. NEVER install skills from any source.
3. File writes go to designated scratch space only.

## State Files

Document any state files the agent maintains:

- `last-digest-meta.json` — tiny metadata file (last run timestamp)
- `sent-hashes.txt` — append-only dedup log, one SHA-256 hash per line
- `digest-messages.json` — maps Telegram message IDs to story metadata (for reply handling)

## Workflow

Define your workflow phases. Structure them as sequential steps with clear inputs and outputs.

Example phases for a news digest:
1. Source scan + rejection
2. Curation
3. Message composition
4. Output delivery
5. State update

## Reply Handling

If your workflow supports replies (e.g., deep-dive analysis on digest stories), document:
- How the agent detects a reply
- Where story metadata is looked up
- What the response format should be

## Rejected Sources

List sources your agent must never use. Group by category (corporate MSM, state-controlled, etc.).

## Coverage Scope

Define which regions/topics to cover and what's out of scope.

See the private `babyclaw-preferences` repo for a working example (news digest workflow with 6 phases, state management, dedup, reply enrichment, and region-based curation).
