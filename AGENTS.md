# mlog-py agent instructions

Shared entry point for AI agents working in this repository. Both Antigravity
(`agy`) and OpenCode V2 load this file automatically. Keep it short; details
belong in the linked memory files.

## Read before working

1. `.agents/memory/context.md` - stable project context and invariants.
2. `.agents/memory/handoff.md` - current task state and next actions.
3. `docs/adr/README.md` - durable technical decisions. Read any ADR that
   touches the area you will change.
4. `SKILL.md` - deep compiler/decompiler manual. Read the relevant section
   before changing compiler or decompiler behavior.

Do not rely on a previous agent's chat history. If the handoff is stale or
contradicts the code, verify against the code and update the handoff.

## Working rules

- Inspect the existing implementation, tests, and docs before changing
  behavior.
- Treat `src/metadata.py` and `src/mlog_registry.py` as the single source of
  truth for opcode, property, and signature metadata. Do not hardcode token
  maps.
- Preserve the zero-guessing decompiler contract. If semantic equivalence
  cannot be proven, fall back to `UnstructuredNode` with preserved raw
  instructions.
- Add a focused regression test for every bug fix.
- Run `python run_tests.py --fast` while iterating. Before finishing, run
  `python run_tests.py --all` (or record why the JVM tier was unavailable).
- Do not commit unless the user asks. Never push unless explicitly requested.
- Do not hand-edit generated files. Regenerate `mlog.pyi` and `src/mlog.pyi`
  with `python -m src.metadata` when metadata changes.
- Preserve user work and existing configuration. Do not delete unfamiliar
  files without investigating them first.
- Never store secrets, tokens, credentials, or personal data in memory files.

## Memory protocol

The shared memory is plain Markdown on the filesystem. Both agents read and
write the same files; there is no MCP server and no database.

- Read `.agents/memory/context.md` and `.agents/memory/handoff.md` before
  planning.
- Update `.agents/memory/handoff.md` at meaningful checkpoints: after
  investigation, before handing work to another agent, and before ending a
  session. Replace stale status instead of appending an endless log.
- Record durable architecture, semantics, or workflow choices as a new ADR in
  `docs/adr/` and add it to `docs/adr/README.md`. Keep long rationale out of
  the handoff.
- Keep `.agents/memory/context.md` stable. Update it only when project-wide
  facts, commands, or invariants change.
- Do not run two agents in the same working tree at the same time. There is no
  file locking; the last writer wins.
- A handoff must be self-contained: goal, status, changed files, tests,
  blockers, and exact next actions. Never write "see previous chat".

## Handoff format

Use the structure in `.agents/memory/handoff.md`. Required fields:

- `Updated`: date in `YYYY-MM-DD` form.
- `Agent`: tool and model, for example `OpenCode / model-id`.
- `Status`: `in-progress`, `blocked`, `ready-for-review`, or `done`.
- `Goal`: one or two sentences describing the task.
- `Done`: completed work and changed files.
- `Next`: ordered, concrete actions for the next agent.
- `Blocked`: blockers, or `none`.
- `Verification`: commands run and their results.

## Commands

```bash
python run_tests.py --fast   # pure-Python tiers
python run_tests.py --jvm    # real Mindustry v160.7 engine
python run_tests.py --all    # full suite
python -m src.metadata       # regenerate mlog.pyi and src/mlog.pyi
```
