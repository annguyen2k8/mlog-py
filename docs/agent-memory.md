# Shared Agent Memory and Handoff

This repository uses plain Markdown files to share working context between
Antigravity (`agy`) and OpenCode V2. There is no custom MCP server, database,
or background service.

## Setup

No installation is required. The memory files are committed with the
repository.

- **OpenCode**: start a session in the repository root. OpenCode loads
  `AGENTS.md` automatically.
- **Antigravity**: ensure the repository is listed in `trustedWorkspaces` in
  `~/.gemini/antigravity-cli/settings.json` (it is already trusted on this
  machine), then start `agy` in the repository root. Antigravity loads
  `AGENTS.md` automatically.
- **After editing memory files**: run the structural check described in
  [Verification](#verification).

## Files

| File | Purpose | Update policy |
| --- | --- | --- |
| `AGENTS.md` | Always-on working rules and memory protocol | Change rarely; keep under 24 KB |
| `.agents/memory/context.md` | Stable project context, architecture map, invariants | Update only when project-wide facts change |
| `.agents/memory/handoff.md` | Current task state for the next agent | Replace at checkpoints and before ending a session |
| `docs/adr/` | Durable technical decisions | Add a new ADR; do not rewrite old ones |
| `docs/adr/README.md` | ADR index | Add a row for each new ADR |

The flow is:

```text
AGENTS.md (always loaded by both tools)
    |
    +-- .agents/memory/context.md   (read at task start)
    +-- .agents/memory/handoff.md   (read and updated during the task)
    +-- docs/adr/README.md          (read for durable decisions)
```

## How the tools discover it

- **OpenCode V2** loads the global `~/.config/opencode/AGENTS.md` (if present)
  and every `AGENTS.md` from the workspace toward the home directory. For
  workspaces outside the home directory, discovery stops at the project root;
  this repository therefore loads its root `AGENTS.md`. OpenCode V2 recognizes
  `AGENTS.md` only; it does not use `CLAUDE.md` as a fallback.
- **Antigravity** walks from the working directory to the repository root and
  loads `GEMINI.md` / `AGENTS.md` rules. It also discovers
  `.agents/rules/*.md`, but this repository intentionally has no such files, so
  the shared rules are not duplicated. Antigravity deduplicates rules by
  resolved file path.
- **Memory files are not auto-injected** by either tool. `AGENTS.md` tells the
  agent to read them at task start. This keeps the always-on token cost low.

Sources:

- OpenCode V2 instructions documentation:
  <https://opencode.ai/v2/docs/instructions/>
- Local Antigravity `agy-customizations` skill docs at
  `C:\Users\Admin\.gemini\antigravity-cli\builtin\skills\agy-customizations\`
- The live CLIs in this workspace; see [Verification](#verification).

## Workflow

### Start a task

1. Read `AGENTS.md` (automatic).
2. Read `.agents/memory/context.md` and `.agents/memory/handoff.md`.
3. Read `docs/adr/README.md` and any relevant ADR.
4. If the handoff is stale, verify against the code and update it before
   planning.

### During a task

- Update `handoff.md` after investigation, after a significant decision, and
  before switching agents.
- Keep `Status` accurate. Use `in-progress`, `blocked`, `ready-for-review`, or
  `done`.
- Record durable choices as an ADR and add it to the index. Do not bury
  rationale in the handoff.

### End a task

1. Run the required tests.
2. Update `handoff.md` with the final status, changed files, verification
   results, and any remaining work.
3. If the user asked for a commit, include the memory changes in the commit.
4. Never push unless the user explicitly asks.

## Handoff template

```markdown
# Task handoff

- **Updated**: YYYY-MM-DD
- **Agent**: OpenCode / model-id
- **Status**: in-progress | blocked | ready-for-review | done
- **Goal**: One or two sentences.

## Done

- Completed work.
- Changed files.

## Next

1. Exact next action.
2. Exact next action.

## Blocked

- None, or a concrete blocker and what is needed.

## Verification

- `command`: result.
```

`AGENTS.md` uses the compact field form. Keep the same field names so
structural checks and agents can parse it.

## Token and size limits

- Antigravity caps each rule file at 24,000 bytes and the aggregate always-on
  rules at 20,000 tokens. `AGENTS.md` is intentionally small; detailed
  material is on demand.
- OpenCode combines instructions rather than resolving conflicts. Keep one
  source of truth for each rule.
- Prefer links to existing docs and ADRs over repeating their content.

## Safety and limitations

- **No locking**: do not run Antigravity and OpenCode in the same working tree
  at the same time. The handoff is last-writer-wins.
- **Not automatic memory**: if an agent ignores `AGENTS.md`, it will not read
  the handoff. The protocol is instruction-based, not a tool-enforced feature.
- **Snapshots, not logs**: replace stale handoff content; do not append
  forever.
- **No secrets**: never write tokens, credentials, or personal data to memory.
- **Git is authoritative**: memory describes intent and state, but code and
  tests decide whether the work is correct.
- **Nested instructions**: if a future subdirectory adds its own `AGENTS.md`,
  both tools may load it in addition to the root file. Avoid conflicting
  rules.

## Verification

Run the structural check after editing memory files:

```bash
python -m unittest tests.test_agent_memory -v
```

Run the full project suite before finishing a code task:

```bash
python run_tests.py --all
```

### Verified results

Latest verification on 2026-10-31 with `agy` 1.4.12 and `opencode` 2.2.0:

| Check | Result |
| --- | --- |
| `python -m unittest tests.test_agent_memory -v` | 6/6 passed |
| `python run_tests.py --all` | 1,309/1,309 passed |
| `python -m src.metadata` | Stubs regenerated without a diff |
| OpenCode fresh-session load | Auto-loaded `AGENTS.md`; read the handoff |
| Antigravity print-mode load | Auto-loaded `AGENTS.md`; read the handoff |
| Controlled memory write (both CLIs) | Passed; scratch file removed |

Do not claim a pass without the command output. Record the latest results in
`.agents/memory/handoff.md` as well.
