"""Mindustry Logic Registry, Enums, and Built-in Metadata Layer.

Provides validated metadata extracted directly from Mindustry source code.
Distinguishes between:
1. Python identifier: SensorProperty.HEALTH
2. Compiler enum value: "@health"
3. Mlog output token: @health

Supports explicit raw() bypass for forward-compatibility.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from .errors import CompileError, SourceLocation
from .mlog_registry_data import (
    BUILTIN_CONSTANTS,
    CONDITION_OPERATIONS,
    CONTROL_PROPERTIES,
    GRAPHICS_TYPES,
    ITEMS,
    LIQUIDS,
    LOGIC_OPERATIONS,
    RADAR_SORTS,
    RADAR_TARGETS,
    SENSEABLE_PROPERTIES,
    TEAMS,
    UNIT_CONTROL_ACTIONS,
    UNITS,
)


def to_snake(name: str) -> str:
    """Convert camelCase or hyphen-separated identifier to snake_case."""
    s = name.replace("-", "_")
    if s.isupper():
        return s.lower()
    return "".join(["_" + c.lower() if c.isupper() else c for c in s]).lstrip("_")


@dataclass(frozen=True)
class RegistryEntry:
    """A verified Mindustry enum/property metadata entry."""
    source_name: str
    mlog_token: str
    category: str = ""
    description: str = ""


class BaseRegistry:
    """Generic registry for Mindustry Logic symbols and properties."""

    def __init__(self, name: str, entries: List[RegistryEntry]):
        self.name = name
        self.entries = entries
        self.by_source_name: Dict[str, RegistryEntry] = {}
        self.by_token: Dict[str, RegistryEntry] = {}

        for e in entries:
            src = e.source_name
            snake = to_snake(src)
            self.by_source_name[src] = e
            self.by_source_name[src.upper()] = e
            self.by_source_name[src.lower()] = e
            self.by_source_name[snake.upper()] = e
            self.by_source_name[snake.lower()] = e
            self.by_source_name[src.replace("-", "_").upper()] = e
            self.by_source_name[src.replace("-", "").upper()] = e
            self.by_token[e.mlog_token] = e
            # Also allow token without '@' if it starts with '@'
            if e.mlog_token.startswith("@"):
                self.by_token[e.mlog_token[1:]] = e


    def contains(self, key: str) -> bool:
        """Check if a token or source name exists in this registry."""
        return key in self.by_token or key in self.by_source_name

    def get_token(self, key: str) -> Optional[str]:
        """Get canonical mlog token for a token or source name."""
        if key in self.by_token:
            return self.by_token[key].mlog_token
        if key in self.by_source_name:
            return self.by_source_name[key].mlog_token
        return None

    def validate(self, token: str, loc: Optional[SourceLocation] = None) -> str:
        """Validate token and return canonical mlog token, or raise CompileError."""
        canon = self.get_token(token)
        if canon is None:
            raise CompileError(
                f"unknown {self.name} '{token}'",
                loc or SourceLocation(),
            )
        return canon


# ---------------------------------------------------------------------------
# Specialized Registries
# ---------------------------------------------------------------------------

class SensorPropertyRegistry(BaseRegistry):
    """Validates properties usable with the 'sensor' instruction.
    In Mindustry, sensor can query:
    1. Senseable LAccess properties (e.g. @health, @totalItems, @x, @y)
    2. Items (e.g. @copper, @silicon - queries item count in block)
    3. Liquids (e.g. @water, @cryofluid - queries liquid volume in block)
    """

    def __init__(self):
        entries = []
        for prop in SENSEABLE_PROPERTIES:
            # Convert camelCase to UPPER_SNAKE_CASE for Python enum name
            src_name = self._to_snake(prop).upper()
            entries.append(
                RegistryEntry(
                    source_name=src_name,
                    mlog_token=f"@{prop}",
                    category="laccess",
                )
            )
        for item in ITEMS:
            src_name = self._to_snake(item).upper()
            entries.append(
                RegistryEntry(
                    source_name=src_name,
                    mlog_token=f"@{item}",
                    category="item",
                )
            )
        for liquid in LIQUIDS:
            src_name = self._to_snake(liquid).upper()
            entries.append(
                RegistryEntry(
                    source_name=src_name,
                    mlog_token=f"@{liquid}",
                    category="liquid",
                )
            )
        super().__init__("sensor property", entries)

    @staticmethod
    def _to_snake(name: str) -> str:
        return "".join(
            ["_" + c.lower() if c.isupper() else c for c in name]
        ).lstrip("_")


class ControlRegistry(BaseRegistry):
    """Validates properties usable with the 'control' instruction."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=p.upper(), mlog_token=p, category="control")
            for p in CONTROL_PROPERTIES
        ]
        super().__init__("control property", entries)


class UnitControlRegistry(BaseRegistry):
    """Validates actions usable with the 'ucontrol' instruction."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=a, mlog_token=a, category="ucontrol")
            for a in UNIT_CONTROL_ACTIONS
        ]
        super().__init__("unit control action", entries)


class DrawTypeRegistry(BaseRegistry):
    """Validates draw commands usable with the 'draw' instruction."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=d, mlog_token=d, category="draw")
            for d in GRAPHICS_TYPES
        ]
        super().__init__("draw type", entries)


class LogicOpRegistry(BaseRegistry):
    """Validates arithmetic and logic operations usable with 'op'."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=op, mlog_token=op, category="op")
            for op in LOGIC_OPERATIONS
        ]
        super().__init__("logic operation", entries)


class ConditionRegistry(BaseRegistry):
    """Validates condition operations usable with 'jump'."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=c, mlog_token=c, category="condition")
            for c in CONDITION_OPERATIONS
        ]
        super().__init__("jump condition", entries)


class RadarTargetRegistry(BaseRegistry):
    """Validates target filters for 'radar' and 'uradar'."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=t, mlog_token=t, category="radar_target")
            for t in RADAR_TARGETS
        ]
        super().__init__("radar target", entries)


class RadarSortRegistry(BaseRegistry):
    """Validates sort modes for 'radar' and 'uradar'."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=s, mlog_token=s, category="radar_sort")
            for s in RADAR_SORTS
        ]
        super().__init__("radar sort mode", entries)



class BuiltinConstantRegistry(BaseRegistry):
    """Validates built-in variables and constants."""

    def __init__(self):
        entries = []
        for c in BUILTIN_CONSTANTS:
            clean = c[1:] if c.startswith("@") else c
            entries.append(
                RegistryEntry(
                    source_name=clean.upper(),
                    mlog_token=c,
                    category="builtin",
                )
            )
        super().__init__("builtin constant", entries)


class ItemRegistry(BaseRegistry):
    """Validates item content constants."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=i.upper(), mlog_token=f"@{i}", category="item")
            for i in ITEMS
        ]
        super().__init__("item", entries)


class LiquidRegistry(BaseRegistry):
    """Validates liquid content constants."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=liq.upper(), mlog_token=f"@{liq}", category="liquid")
            for liq in LIQUIDS
        ]
        super().__init__("liquid", entries)


class UnitTypeRegistry(BaseRegistry):
    """Validates unit type constants."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=u.upper().replace("-", "_"), mlog_token=f"@{u}", category="unit")
            for u in UNITS
        ]
        super().__init__("unit type", entries)


class TeamRegistry(BaseRegistry):
    """Validates team constants."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=t.upper(), mlog_token=f"@{t}", category="team")
            for t in TEAMS
        ]
        super().__init__("team", entries)


class OpcodeRegistry(BaseRegistry):
    """Validates mlog opcodes."""

    def __init__(self):
        opcodes = [
            "read", "write", "draw", "drawflush", "print", "printflush",
            "getlink", "control", "radar", "sensor", "set", "op", "lookup",
            "packcolor", "unpackcolor", "wait", "stop", "end", "jump",
            "ubind", "ucontrol", "uradar", "ulocate",
        ]
        entries = [
            RegistryEntry(source_name=op.upper(), mlog_token=op, category="opcode")
            for op in opcodes
        ]
        super().__init__("opcode", entries)


class LookupTypeRegistry(BaseRegistry):
    """Validates content types usable with 'lookup'."""

    def __init__(self):
        types = ["item", "block", "unit", "liquid", "team"]
        entries = [
            RegistryEntry(source_name=t.upper(), mlog_token=t, category="lookup_type")
            for t in types
        ]
        super().__init__("lookup type", entries)


# Registry Singletons
REG_SENSOR_PROPERTIES = SensorPropertyRegistry()
REG_CONTROL_PROPERTIES = ControlRegistry()
REG_UNIT_CONTROL = UnitControlRegistry()
REG_DRAW_TYPES = DrawTypeRegistry()
REG_LOGIC_OPS = LogicOpRegistry()
REG_CONDITIONS = ConditionRegistry()
REG_RADAR_TARGETS = RadarTargetRegistry()
REG_RADAR_SORTS = RadarSortRegistry()
REG_BUILTIN_CONSTANTS = BuiltinConstantRegistry()
REG_ITEMS = ItemRegistry()
REG_LIQUIDS = LiquidRegistry()
REG_UNIT_TYPES = UnitTypeRegistry()
REG_TEAMS = TeamRegistry()
REG_OPCODES = OpcodeRegistry()
REG_LOOKUP_TYPES = LookupTypeRegistry()


# ---------------------------------------------------------------------------
# Python DSL Enums
# ---------------------------------------------------------------------------

def _build_enum_from_registry(name: str, registry: BaseRegistry) -> type:
    """Dynamically construct a Python Enum class from a registry."""
    members = {}
    for entry in registry.entries:
        src = entry.source_name
        snake = to_snake(src).upper()
        members[snake] = entry.mlog_token
        clean = src.replace("-", "_").upper()
        if clean not in members:
            members[clean] = entry.mlog_token
    return Enum(name, members)



SensorProperty = _build_enum_from_registry("SensorProperty", REG_SENSOR_PROPERTIES)
ControlProperty = _build_enum_from_registry("ControlProperty", REG_CONTROL_PROPERTIES)
UnitControl = _build_enum_from_registry("UnitControl", REG_UNIT_CONTROL)
DrawType = _build_enum_from_registry("DrawType", REG_DRAW_TYPES)
LogicOp = _build_enum_from_registry("LogicOp", REG_LOGIC_OPS)
Condition = _build_enum_from_registry("Condition", REG_CONDITIONS)
RadarTarget = _build_enum_from_registry("RadarTarget", REG_RADAR_TARGETS)
RadarSort = _build_enum_from_registry("RadarSort", REG_RADAR_SORTS)
Items = _build_enum_from_registry("Items", REG_ITEMS)
Liquids = _build_enum_from_registry("Liquids", REG_LIQUIDS)
Units = _build_enum_from_registry("Units", REG_UNIT_TYPES)
Teams = _build_enum_from_registry("Teams", REG_TEAMS)
LookupType = _build_enum_from_registry("LookupType", REG_LOOKUP_TYPES)

# Mapping from Python enum class name to its registry
ENUM_CLASS_TO_REGISTRY = {
    "SensorProperty": REG_SENSOR_PROPERTIES,
    "ControlProperty": REG_CONTROL_PROPERTIES,
    "UnitControl": REG_UNIT_CONTROL,
    "DrawType": REG_DRAW_TYPES,
    "LogicOp": REG_LOGIC_OPS,
    "Condition": REG_CONDITIONS,
    "RadarTarget": REG_RADAR_TARGETS,
    "RadarSort": REG_RADAR_SORTS,
    "Items": REG_ITEMS,
    "Liquids": REG_LIQUIDS,
    "Units": REG_UNIT_TYPES,
    "Teams": REG_TEAMS,
    "LookupType": REG_LOOKUP_TYPES,
}

