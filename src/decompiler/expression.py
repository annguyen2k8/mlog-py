"""Expression Intermediate Representation (IR) for Mindustry Logic decompiler.

Represents expressions (Constant, Variable, Unary, Binary, Call, Unknown) with
exact operator precedence and minimal parenthesization rules.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Set


# Operator Precedence Hierarchy (higher number = tighter binding)
PREC_ATOMIC = 100       # Literals, Variables
PREC_CALL = 90          # Call expressions: f(x)
PREC_UNARY = 80         # Unary ops: -, ~, not
PREC_EXPONENT = 70      # Exponent: **
PREC_MULTIPLICATIVE = 60 # *, /, //, %
PREC_ADDITIVE = 50      # +, -
PREC_SHIFT = 45         # <<, >>
PREC_BIT_AND = 40       # &
PREC_BIT_XOR = 35       # ^
PREC_BIT_OR = 30        # |
PREC_COMPARISON = 25    # ==, !=, <, <=, >, >=, is
PREC_LOGICAL_NOT = 20   # not
PREC_LOGICAL_AND = 15   # and
PREC_LOGICAL_OR = 10    # or
PREC_MIN = 0            # Unknown / lowest

BINARY_OP_PRECEDENCE = {
    "**": PREC_EXPONENT,
    "*": PREC_MULTIPLICATIVE,
    "/": PREC_MULTIPLICATIVE,
    "//": PREC_MULTIPLICATIVE,
    "%": PREC_MULTIPLICATIVE,
    "+": PREC_ADDITIVE,
    "-": PREC_ADDITIVE,
    "<<": PREC_SHIFT,
    ">>": PREC_SHIFT,
    "&": PREC_BIT_AND,
    "^": PREC_BIT_XOR,
    "|": PREC_BIT_OR,
    "==": PREC_COMPARISON,
    "!=": PREC_COMPARISON,
    "<": PREC_COMPARISON,
    "<=": PREC_COMPARISON,
    ">": PREC_COMPARISON,
    ">=": PREC_COMPARISON,
    "is": PREC_COMPARISON,
    "and": PREC_LOGICAL_AND,
    "or": PREC_LOGICAL_OR,
}

MLOG_TO_PY_BINARY_OPS = {
    "add": "+",
    "sub": "-",
    "mul": "*",
    "div": "/",
    "idiv": "//",
    "mod": "%",
    "pow": "**",
    "shl": "<<",
    "shr": ">>",
    "or": "|",
    "and": "&",
    "xor": "^",
    "equal": "==",
    "notEqual": "!=",
    "lessThan": "<",
    "lessThanEq": "<=",
    "greaterThan": ">",
    "greaterThanEq": ">=",
    "strictEqual": "==",
    "land": "and",
}


class Expr(ABC):
    """Base class for all expression nodes."""

    @property
    @abstractmethod
    def precedence(self) -> int:
        """Operator precedence level."""
        pass

    @property
    @abstractmethod
    def is_constant(self) -> bool:
        """True if the expression is a compile-time constant."""
        pass

    @property
    @abstractmethod
    def variables_used(self) -> Set[str]:
        """Set of variable names referenced in this expression."""
        pass

    @property
    def has_side_effects(self) -> bool:
        """True if evaluating this expression may cause side effects."""
        return False

    @abstractmethod
    def to_python(self) -> str:
        """Render the expression as valid Python source code."""
        pass

    def __str__(self) -> str:
        return self.to_python()


@dataclass(frozen=True)
class ConstantExpr(Expr):
    """Represents a literal constant (int, float, str, bool, None)."""
    value: Any
    raw_str: str = ""

    @property
    def precedence(self) -> int:
        return PREC_ATOMIC

    @property
    def is_constant(self) -> bool:
        return True

    @property
    def variables_used(self) -> Set[str]:
        return set()

    def to_python(self) -> str:
        if isinstance(self.value, bool):
            return "True" if self.value else "False"
        if self.value is None:
            return "None"
        if isinstance(self.value, (int, float)):
            return str(self.value)
        if isinstance(self.value, str):
            # Check if this is a Mindustry builtin constant token like @unit, @time
            if self.value.startswith("@"):
                return repr(self.value)
            if self.value.startswith('"') and self.value.endswith('"'):
                return self.value
            # Normal string literal with canonical double quotes
            escaped = self.value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            return f'"{escaped}"'
        return str(self.value)


@dataclass(frozen=True)
class VariableExpr(Expr):
    """Represents a variable identifier."""
    name: str

    @property
    def precedence(self) -> int:
        return PREC_ATOMIC

    @property
    def is_constant(self) -> bool:
        return False

    @property
    def variables_used(self) -> Set[str]:
        return {self.name}

    def to_python(self) -> str:
        return self.name


@dataclass(frozen=True)
class UnaryExpr(Expr):
    """Represents a unary operation (e.g., -x, ~x, not x)."""
    op: str
    operand: Expr

    @property
    def precedence(self) -> int:
        return PREC_UNARY

    @property
    def is_constant(self) -> bool:
        return self.operand.is_constant

    @property
    def variables_used(self) -> Set[str]:
        return self.operand.variables_used

    @property
    def has_side_effects(self) -> bool:
        return self.operand.has_side_effects

    def to_python(self) -> str:
        inner = self.operand.to_python()
        if self.operand.precedence < self.precedence:
            inner = f"({inner})"
        if self.op.isalpha():
            return f"{self.op} {inner}"
        return f"{self.op}{inner}"


@dataclass(frozen=True)
class BinaryExpr(Expr):
    """Represents a binary operation (e.g., a + b, x * y, a == b)."""
    op: str
    left: Expr
    right: Expr

    @property
    def precedence(self) -> int:
        return BINARY_OP_PRECEDENCE.get(self.op, PREC_MIN)

    @property
    def is_constant(self) -> bool:
        return self.left.is_constant and self.right.is_constant

    @property
    def variables_used(self) -> Set[str]:
        return self.left.variables_used | self.right.variables_used

    @property
    def has_side_effects(self) -> bool:
        return self.left.has_side_effects or self.right.has_side_effects

    def to_python(self) -> str:
        # Left operand: parenthesize if strictly lower precedence
        left_str = self.left.to_python()
        if self.left.precedence < self.precedence:
            left_str = f"({left_str})"

        # Right operand: parenthesize if lower precedence, or equal precedence for non-associative ops
        right_str = self.right.to_python()
        if self.right.precedence < self.precedence:
            right_str = f"({right_str})"
        elif self.right.precedence == self.precedence and self.op in ("-", "/", "//", "%", "**"):
            right_str = f"({right_str})"

        return f"{left_str} {self.op} {right_str}"


@dataclass(frozen=True)
class CallExpr(Expr):
    """Represents a function or intrinsic invocation (e.g. op('max', a, b), wait(0.5))."""
    func: str
    args: List[Expr] = field(default_factory=list)

    @property
    def precedence(self) -> int:
        return PREC_CALL

    @property
    def is_constant(self) -> bool:
        return False

    @property
    def variables_used(self) -> Set[str]:
        vars_set = set()
        for a in self.args:
            vars_set.update(a.variables_used)
        return vars_set

    @property
    def has_side_effects(self) -> bool:
        # Pure arithmetic op call has no side effects, other calls might
        if self.func == "op" and len(self.args) >= 1:
            first = self.args[0]
            if isinstance(first, ConstantExpr) and first.value in ("max", "min", "abs", "floor", "ceil", "round", "sqrt"):
                return False
        return True

    def to_python(self) -> str:
        args_str = ", ".join(a.to_python() for a in self.args)
        return f"{self.func}({args_str})"


@dataclass(frozen=True)
class UnknownExpr(Expr):
    """Fallback representation for unparsed or unrecognized expressions."""
    raw_text: str

    @property
    def precedence(self) -> int:
        return PREC_MIN

    @property
    def is_constant(self) -> bool:
        return False

    @property
    def variables_used(self) -> Set[str]:
        return set()

    def to_python(self) -> str:
        return self.raw_text


def parse_operand_to_expr(token: str) -> Expr:
    """Parse a single mlog token string into a ConstantExpr or VariableExpr."""
    if token == "true":
        return ConstantExpr(value=True, raw_str=token)
    if token == "false":
        return ConstantExpr(value=False, raw_str=token)
    if token == "null":
        return ConstantExpr(value=None, raw_str=token)

    # String literal in quotes
    if token.startswith('"') and token.endswith('"'):
        return ConstantExpr(value=token[1:-1], raw_str=token)

    # Integer
    if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
        try:
            return ConstantExpr(value=int(token), raw_str=token)
        except ValueError:
            pass

    # Floating point
    try:
        val = float(token)
        return ConstantExpr(value=val, raw_str=token)
    except ValueError:
        pass

    # Mindustry builtin constant token like @unit, @time
    if token.startswith("@"):
        return ConstantExpr(value=token, raw_str=token)

    # Valid identifier
    return VariableExpr(name=token)
