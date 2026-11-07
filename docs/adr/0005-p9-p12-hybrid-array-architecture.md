# ADR-005: Hybrid Array Architecture (`mlog.beta.Array`)

- **Status**: Accepted
- **Date**: 2026-11-07
- **Deciders**: mlog-py Compiler Team
- **Target Engine**: Mindustry v160.7

---

## 1. Context

In Mindustry Logic, memory management faces hard hardware constraints:
1. Processor registers are fast ($O(1)$) and require 0 external hardware buildings, but **cannot be addressed dynamically** (there is no register pointer or indirect addressing opcode in vanilla Mindustry Logic).
2. Physical memory blocks (`memory-cell` with 64 slots, `memory-bank` with 512 slots) support native $O(1)$ dynamic read and write (`read`/`write` opcodes), but require physical structures placed on the map and linked to the processor.
3. The legacy `from mlog import Array` API only supported physical Memory Cell/Bank allocations with static offsets. Developers had no mechanism to express small, in-register fixed collections (such as coordinate vectors or lookup tables) without linking a physical block.

P9 evaluated three architectural options:
- **Model A (Compile-Time / In-Register Array):** Lowers to registers. Ideal for small, statically indexed data; fundamentally unviable for dynamic indexing due to branch tree explosion (up to 31 instructions for $N=16$, threatening the 1,000-instruction processor limit).
- **Model B (Runtime / Hardware Memory Block Array):** Lowers to hardware blocks. Supports $O(1)$ dynamic indexing, but requires physical hardware on the map.
- **Model C (Hybrid Array Architecture):** Provides specialized in-register storage (`LocalArray`) and hardware-backed storage (`BlockArray`) unified under a single factory constructor (`Array`) in `mlog.beta`.

---

## 2. Decision

### 2.1 Dual-Backend Specialization (`LocalArray` and `BlockArray`)

1. **`mlog.beta.LocalArray[T]` (In-Register Array):**
   - Mapped directly to processor registers (`<name>_0`, `<name>_1`, ...).
   - Capacity: $1 \le N \le 64$.
   - Indexing: Strictly compile-time static indexing (`arr[0]`).
   - Dynamic indexing (`arr[i]`) is rejected at compile time with a clear `CompileError` rather than emitting explosive branch jump trees.
   - Requires zero external hardware blocks.

2. **`mlog.beta.BlockArray[T]` (Hardware Memory Block Array):**
   - Mapped 1:1 to a linked Mindustry memory device (`cell1`, `bank1`).
   - Capacity: 64 for `cell`, 512 for `bank`.
   - Dynamic indexing lowers to native `read` and `write` opcodes ($O(1)$ latency, 0 execution yield).
   - Multiple arrays can share a single block through contiguous, non-overlapping base offsets managed by `MemoryBlockAllocator`.

### 2.2 Unified Factory (`mlog.beta.Array`)

- `Array(size)` / `Array(size=N)`: Dispatches to `LocalArray`.
- `Array(block, size)` / `Array(block=B, size=N)`: Dispatches to `BlockArray`.
- Generic subscripting `Array[T](...)` enforces compile-time type validation.
- Metadata constant folding: `len(arr)`, `.size`, `.capacity`, `.block`, `.dtype` are folded to literals at compile-time with 0 runtime instructions.

### 2.3 Legacy API Isolation

- `from mlog import Array` retains 100% of its pre-P12 semantics, allocation rules, and behavior.
- Lexical import shadowing allows legacy and beta APIs to coexist cleanly within the same project and within the same source file.

---

## 3. Consequences

### Positive
- Developers have complete control over performance vs hardware dependencies.
- Zero extra instructions for metadata and static indexing.
- Preserves processor instruction budget (1,000 instructions max).
- 100% backward compatibility preserved for existing codebases.

### Negative / Tradeoffs
- Dynamic indexing on `LocalArray` is not supported (compile-time rejection).
- Dynamic indexing on `BlockArray` does not inject runtime jump ladders for out-of-bounds checking to protect the 1,000-instruction limit (static bounds are checked at compile time for constant indices).

---

## 4. Verification Evidence

- 10 live Mindustry JVM v160.7 experiments (`p9_jvm_experiments.py`) establishing exact memory and instruction behavior.
- 104 specialized unit and integration tests across `tests/test_local_array.py` (26), `tests/test_block_array.py` (30), and `tests/test_unified_array.py` (48).
- Full regression suite: 1,629 passed, 3 skipped, 0 failures on real Mindustry JVM engine.
