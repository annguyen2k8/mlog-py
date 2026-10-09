# Source Mapping & Debug Mode

This document details the source mapping and provenance tracking architecture in `mlog-py`.

---

## 1. Overview & Provenance Guarantee

In an optimizing decompiler, statements are frequently synthesized from multiple low-level instructions (for example, collapsing two `set`s and an `op` into `x = a + b`).

The `mlog-py` Source Mapping subsystem tracks full-pipeline provenance:

- Every high-level Python statement or AST node tracks all constituent MLog instruction addresses.
- Collapsed temporaries preserve the addresses of every collapsed instruction:

  ```text
  MLog[0]: set __tmp0 a
  MLog[1]: op add __tmp1 __tmp0 1
  MLog[2]: set x __tmp1
       │
       ▼
  Python Statement: x = a + 1   ──► maps to addresses [0, 1, 2]
  ```

---

## 2. Debug Mode (`debug=True`)

When `debug=True` is passed to `decompile()`, the decompiler emits informative provenance annotations directly above each statement in the generated Python code:

```python
# mlog[0]
heat = sensor("reactor1", "@heat")
# mlog[1, 3]
if heat > 0.5:
    # mlog[2]
    control("enabled", "reactor1", 0, 0, 0, 0)
else:
    # mlog[4]
    control("enabled", "reactor1", 1, 0, 0, 0)
# mlog[5]
wait(0.5)
```

- `# mlog[<addr>]`: Single MLog instruction origin.
- `# mlog[<addr1>, <addr2>]`: Compound condition or collapsed statement origin.

---

## 3. Bi-Directional Lookup API

The `SourceMap` object (`src/decompiler/sourcemap.py`) provides constant-time $O(1)$ bi-directional querying:

```python
from src.decompiler import decompile_with_source_map

code, sm = decompile_with_source_map(mlog_text)

# Query MLog addresses that produced Python line 2
mlog_addrs = sm.python_to_mlog(python_line=2)
# Returns: [1, 3]

# Query Python line corresponding to MLog instruction address 4
py_line = sm.mlog_to_python(mlog_address=4)
# Returns: 5

# Get original MlogInstruction objects for Python line 1
instrs = sm.get_instructions_for_python_line(python_line=1)
```

---

## 4. Machine-Readable SourceMap JSON Schema

`SourceMap` serializes into a standard JSON representation (`sm.to_json(indent=2)`):

```json
{
  "version": "1.0",
  "mappings": [
    {
      "python_line": 1,
      "python_end_line": 1,
      "node_type": "Instruction",
      "mlog_addresses": [0],
      "instructions": ["sensor heat reactor1 @heat"],
      "source_lines": [1],
      "address_range": [0, 0]
    },
    {
      "python_line": 2,
      "python_end_line": 2,
      "node_type": "If",
      "mlog_addresses": [1, 3],
      "instructions": [
        "jump 4 lessThanEq heat 0.5",
        "jump 5 always 0 0"
      ],
      "source_lines": [2, 4],
      "address_range": [1, 3]
    }
  ],
  "python_to_mlog": {
    "1": [0],
    "2": [1, 3]
  },
  "mlog_to_python": {
    "0": 1,
    "1": 2,
    "3": 2,
    "2": 3,
    "4": 5
  }
}
```

This format can be consumed by external debuggers, IDE extensions, and automated regression test harnesses.
