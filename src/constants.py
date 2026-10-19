"""Named constants and IntEnum registry for Mindustry Logic compiler.

Provides a clean, independent symbol table for compile-time named constants,
resolving user-defined IntEnums into literal values with zero runtime overhead.
"""

import ast
from typing import Any, Dict, Optional, Set, Tuple

from .errors import CompileError, SourceLocation
from .parser import get_loc


MIN_INT64 = -9223372036854775808
MAX_INT64 = 9223372036854775807


class NamedConstantRegistry:
    """Independent symbol registry for compile-time named constants and namespaces.

    Stores constant namespaces (such as IntEnum classes) and resolves member
    names to static scalar values during AST validation and compilation.
    """

    def __init__(self):
        # namespace_name -> {member_name: value}
        self._namespaces: Dict[str, Dict[str, int]] = {}
        # namespace_name -> SourceLocation
        self._locations: Dict[str, SourceLocation] = {}

    def register_namespace(
        self, name: str, members: Dict[str, int], loc: Optional[SourceLocation] = None
    ) -> None:
        """Register a new named constant namespace with its members."""
        self._namespaces[name] = dict(members)
        if loc is not None:
            self._locations[name] = loc

    def has_namespace(self, name: str) -> bool:
        """Check if a namespace is registered."""
        return name in self._namespaces

    def has_member(self, namespace: str, member: str) -> bool:
        """Check if a namespace contains a specific member."""
        ns = self._namespaces.get(namespace)
        return ns is not None and member in ns

    def get_value(self, namespace: str, member: str) -> Optional[int]:
        """Get the integer value for a namespace member, or None if not found."""
        ns = self._namespaces.get(namespace)
        if ns is None:
            return None
        return ns.get(member)

    def get_members(self, namespace: str) -> Dict[str, int]:
        """Get all members of a namespace."""
        return dict(self._namespaces.get(namespace, {}))

    @property
    def namespaces(self) -> Set[str]:
        """Get the set of all registered namespace names."""
        return set(self._namespaces.keys())

    def get_location(self, namespace: str) -> Optional[SourceLocation]:
        """Get the source location where the namespace was defined."""
        return self._locations.get(namespace)


def eval_const_int_expr(
    node: ast.AST,
    known_members: Dict[str, int],
    filename: str,
) -> int:
    """Evaluate an AST expression as a compile-time static integer constant.

    Supports:
    - Literal integers (excluding booleans)
    - Unary operators (+, -, ~)
    - Binary bitwise, arithmetic, and power operators with bounds checking
    - References to previously defined members in the same enum

    Raises:
        CompileError: If the expression is dynamic, non-integer, divides by zero,
                     or exceeds 64-bit integer limits.
    """
    loc = get_loc(node, filename)

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool):
            raise CompileError(
                f"IntEnum member value must be an integer, got bool ('{node.value}')",
                loc,
            )
        if isinstance(node.value, int):
            val = node.value
            if val < MIN_INT64 or val > MAX_INT64:
                raise CompileError(
                    f"integer literal {val} exceeds signed 64-bit integer range [{MIN_INT64}, {MAX_INT64}]",
                    loc,
                )
            return val
        raise CompileError(
            f"IntEnum member value must be an integer, got {type(node.value).__name__}",
            loc,
        )

    if isinstance(node, ast.UnaryOp):
        operand_val = eval_const_int_expr(node.operand, known_members, filename)
        if isinstance(node.op, ast.UAdd):
            res = operand_val
        elif isinstance(node.op, ast.USub):
            res = -operand_val
        elif isinstance(node.op, ast.Invert):
            res = ~operand_val
        else:
            raise CompileError(
                f"unsupported unary operator '{type(node.op).__name__}' in IntEnum member definition",
                loc,
            )
        if res < MIN_INT64 or res > MAX_INT64:
            raise CompileError(
                f"integer value {res} exceeds signed 64-bit integer range [{MIN_INT64}, {MAX_INT64}]",
                loc,
            )
        return res

    if isinstance(node, ast.BinOp):
        left_val = eval_const_int_expr(node.left, known_members, filename)
        right_val = eval_const_int_expr(node.right, known_members, filename)

        if isinstance(node.op, ast.Add):
            res = left_val + right_val
        elif isinstance(node.op, ast.Sub):
            res = left_val - right_val
        elif isinstance(node.op, ast.Mult):
            res = left_val * right_val
        elif isinstance(node.op, ast.FloorDiv):
            if right_val == 0:
                raise CompileError("division by zero in IntEnum member definition", loc)
            res = left_val // right_val
        elif isinstance(node.op, ast.Mod):
            if right_val == 0:
                raise CompileError("modulo by zero in IntEnum member definition", loc)
            res = left_val % right_val
        elif isinstance(node.op, ast.Pow):
            if right_val < 0 or right_val > 62:
                raise CompileError(
                    f"exponent {right_val} outside safe integer range [0, 62] in IntEnum member definition",
                    loc,
                )
            res = left_val ** right_val
        elif isinstance(node.op, ast.LShift):
            if right_val < 0 or right_val > 63:
                raise CompileError(
                    f"shift count {right_val} outside safe range [0, 63] in IntEnum member definition",
                    loc,
                )
            res = left_val << right_val
        elif isinstance(node.op, ast.RShift):
            if right_val < 0 or right_val > 63:
                raise CompileError(
                    f"shift count {right_val} outside safe range [0, 63] in IntEnum member definition",
                    loc,
                )
            res = left_val >> right_val
        elif isinstance(node.op, ast.BitOr):
            res = left_val | right_val
        elif isinstance(node.op, ast.BitAnd):
            res = left_val & right_val
        elif isinstance(node.op, ast.BitXor):
            res = left_val ^ right_val
        else:
            raise CompileError(
                f"unsupported binary operator '{type(node.op).__name__}' in IntEnum member definition",
                loc,
            )

        if res < MIN_INT64 or res > MAX_INT64:
            raise CompileError(
                f"integer value {res} exceeds signed 64-bit integer range [{MIN_INT64}, {MAX_INT64}]",
                loc,
            )
        return res

    if isinstance(node, ast.Name):
        if node.id in known_members:
            return known_members[node.id]
        raise CompileError(
            f"unknown identifier '{node.id}' in IntEnum member definition (only earlier members of the same enum can be referenced)",
            loc,
        )

    raise CompileError(
        f"IntEnum member value must be a static integer expression, got {type(node).__name__}",
        loc,
    )


def extract_int_enums(
    tree: ast.Module,
    filename: str,
    registry: Optional[NamedConstantRegistry] = None,
) -> NamedConstantRegistry:
    """Scan top-level ClassDefs in an AST Module and register valid IntEnum definitions."""
    if registry is None:
        registry = NamedConstantRegistry()

    from .mlog_registry import ENUM_CLASS_TO_REGISTRY

    for stmt in tree.body:
        if not isinstance(stmt, ast.ClassDef):
            continue

        loc = get_loc(stmt, filename)

        # 1. Base class validation: must inherit from IntEnum or enum.IntEnum
        if not stmt.bases:
            raise CompileError(
                f"unsupported Python feature: class definition (class '{stmt.name}' must inherit from 'IntEnum')",
                loc,
            )
        if len(stmt.bases) != 1:
            raise CompileError(
                f"multiple inheritance is not supported: enum '{stmt.name}' must inherit only from 'IntEnum'",
                loc,
            )

        base = stmt.bases[0]
        is_int_enum_base = (
            (isinstance(base, ast.Name) and base.id == "IntEnum")
            or (
                isinstance(base, ast.Attribute)
                and isinstance(base.value, ast.Name)
                and base.value.id == "enum"
                and base.attr == "IntEnum"
            )
        )
        if not is_int_enum_base:
            base_repr = (
                base.id
                if isinstance(base, ast.Name)
                else (
                    f"{base.value.id}.{base.attr}"
                    if isinstance(base, ast.Attribute) and isinstance(base.value, ast.Name)
                    else type(base).__name__
                )
            )
            raise CompileError(
                f"unsupported Python feature: class definition (unsupported base class '{base_repr}' for enum '{stmt.name}': only 'IntEnum' is supported in MVP)",
                loc,
            )

        # 2. Decorators and keywords
        if stmt.decorator_list:
            raise CompileError(
                f"decorators are not supported on IntEnum classes ('{stmt.name}')",
                loc,
            )
        if stmt.keywords:
            raise CompileError(
                f"keyword arguments are not supported in class definitions ('{stmt.name}')",
                loc,
            )

        # 3. Name collision checks
        if registry.has_namespace(stmt.name):
            raise CompileError(
                f"duplicate definition of enum '{stmt.name}'",
                loc,
            )
        if stmt.name in ENUM_CLASS_TO_REGISTRY or stmt.name in ("Vars", "draw", "ucontrol", "ulocate", "op"):
            raise CompileError(
                f"enum name '{stmt.name}' conflicts with built-in Mindustry DSL name",
                loc,
            )

        # 4. Member validation
        members: Dict[str, int] = {}
        for item in stmt.body:
            if isinstance(item, ast.Pass):
                continue
            if isinstance(item, ast.Expr) and isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                # Docstring
                continue
            if isinstance(item, ast.FunctionDef):
                raise CompileError(
                    f"methods are not supported in IntEnum '{stmt.name}'",
                    get_loc(item, filename),
                )
            if isinstance(item, ast.Assign):
                if len(item.targets) != 1 or not isinstance(item.targets[0], ast.Name):
                    raise CompileError(
                        f"enum member assignment in '{stmt.name}' must be a simple identifier",
                        get_loc(item, filename),
                    )
                member_name = item.targets[0].id
                if member_name in members:
                    raise CompileError(
                        f"duplicate member '{member_name}' in IntEnum '{stmt.name}'",
                        get_loc(item.targets[0], filename),
                    )
                val = eval_const_int_expr(item.value, members, filename)
                members[member_name] = val
                continue

            raise CompileError(
                f"unsupported statement '{type(item).__name__}' in IntEnum '{stmt.name}': only member assignments are supported",
                get_loc(item, filename),
            )

        registry.register_namespace(stmt.name, members, loc)

    return registry
