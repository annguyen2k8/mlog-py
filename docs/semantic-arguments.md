# Semantic Argument Recovery

This document explains the architecture, motivation, and rules governing Semantic Argument Recovery in `mlog-py`.

---

## 1. Problem Statement

In Mindustry Logic (`mlog`), tokens are flat strings without quotes. Physical hardware links (`display1`, `cell1`, `message1`, `reactor1`), program variables (`val`, `total`, `idx`), and special registers (`@unit`, `@counter`) appear identically:

```mlog
read val cell1 idx
drawflush display1
printflush message1
sensor hp reactor1 @health
```

If a decompiler naively emits these tokens directly as Python identifiers:

```python
val = read(cell1, idx)      # BROKEN: NameError: name 'cell1' is not defined
drawflush(display1)         # BROKEN: NameError: name 'display1' is not defined
printflush(message1)        # BROKEN: NameError: name 'message1' is not defined
hp = sensor(reactor1, health) # BROKEN: NameError: name 'reactor1' is not defined
```

Python fails at runtime, and static analysis tools (Pylance, mypy, flake8) report undefined variable errors.

---

## 2. The 6 Semantic Argument Roles

`mlog-py` classifies instruction arguments into 6 distinct semantic roles using the Single Source of Truth (`src/metadata.py` and `src/decompiler/semantics.py`):

| Role | Description | MLog Input Example | Emitted Python DSL Representation |
| :--- | :--- | :--- | :--- |
| **1. Program Variable** | Local or global runtime register | `val`, `total`, `idx` | Unquoted Python identifier (`val`, `total`, `idx`) |
| **2. Named Hardware Link** | Physical device linked to processor | `cell1`, `display1`, `message1` | Quoted string literal (`"cell1"`, `"display1"`, `"message1"`) |
| **3. Special Constant** | Game constants starting with `@` | `@unit`, `@counter`, `@health` | Quoted string literal (`"@unit"`, `"@counter"`, `"@health"`) |
| **4. DSL Enum / Keyword** | Known property or mode enum | `clear`, `color`, `shoot` | DSL identifier or enum (`clear`, `SensorProperty.HEALTH`) |
| **5. Numeric / String Literal** | Constant numbers or string texts | `42`, `3.14`, `"hello"` | Python literal (`42`, `3.14`, `"hello"`) |
| **6. Dynamic Block Variable** | Variable bound via `getlink` | `b` from `getlink b 0` | Unquoted Python identifier (`b`) |

---

## 3. Contrast Example: Hardware Link vs Dynamic Variable

The distinction is clearest when contrasting direct hardware block links with dynamic blocks bound via `getlink()`:

```python
# 1. Direct Named Hardware Block Reference:
# "cell1" is a static hardware link on the processor, emitted as a string literal:
val = read("cell1", idx)
write(val + 1, "cell1", idx)
printflush("message1")
drawflush("display1")

# 2. Dynamic Block Reference Bound via getlink():
# b is a program variable holding a block reference dynamically, emitted as an unquoted identifier:
b = getlink(0)
hp = sensor(b, "@health")
```

---

## 4. SSOT-Backed Identification (Zero Hardcoding)

`mlog-py` does not hardcode device names or rely on string prefixes like `"cell"` or `"display"`. Instead:

1. **Opcode Signature Metadata (`src/metadata.py`)**: Defines parameter roles (e.g. `drawflush` parameter 0 is `target_display`, `read` parameter 1 is `cell_block`, `control` parameter 1 is `target_block`).
2. **Dynamic Variable Tracking**: Identifies if a variable was defined via `getlink` or dynamic block lookup.
3. **Registry Validation**: Matches against official registry entries to verify property types.
