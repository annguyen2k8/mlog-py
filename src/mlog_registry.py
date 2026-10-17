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
    BUILTIN_VARS_SPEC,
    CONDITION_OPERATIONS,
    CONTROL_PROPERTIES,
    CUTSCENE_ACTIONS,
    FETCH_TYPES,
    GRAPHICS_TYPES,
    ITEMS,
    LIQUIDS,
    LOGIC_FX,
    LOGIC_OPERATIONS,
    LOGIC_RULES,
    MARKER_CONTROLS,
    MARKER_TYPES,
    MESSAGE_TYPES,
    RADAR_SORTS,
    RADAR_TARGETS,
    SENSEABLE_PROPERTIES,
    STATUS_EFFECTS,
    TEAMS,
    UNIT_CONTROL_ACTIONS,
    UNITS,
    WEATHERS,
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
    arity: int = 0


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
            # Also allow token with or without '@'
            if e.mlog_token.startswith("@"):
                self.by_token[e.mlog_token[1:]] = e
            else:
                self.by_token["@" + e.mlog_token] = e


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
        for status in STATUS_EFFECTS:
            src_name = self._to_snake(status).upper()
            entries.append(
                RegistryEntry(
                    source_name=src_name,
                    mlog_token=f"@status-{status}",
                    category="status_effect",
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


UNARY_LOGIC_OPS: frozenset = frozenset({
    "not", "abs", "sign", "log", "log10", "floor", "ceil",
    "round", "sqrt", "rand", "sin", "cos", "tan", "asin", "acos", "atan",
})


class LogicOpRegistry(BaseRegistry):
    """Validates arithmetic and logic operations usable with 'op'."""

    def __init__(self):
        entries = [
            RegistryEntry(
                source_name=op,
                mlog_token=op,
                category="op",
                arity=1 if op in UNARY_LOGIC_OPS else 2,
            )
            for op in LOGIC_OPERATIONS
        ]
        super().__init__("logic operation", entries)

    def get_arity(self, key: str) -> Optional[int]:
        """Return the arity of the logic operation (1 for unary, 2 for binary)."""
        token = self.get_token(key)
        if token and token in self.by_token:
            return self.by_token[token].arity
        return None

    def is_unary(self, key: str) -> bool:
        """Check if an operation is unary."""
        return self.get_arity(key) == 1

    def is_binary(self, key: str) -> bool:
        """Check if an operation is binary."""
        return self.get_arity(key) == 2


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
        standard_opcodes = [
            "read", "write", "draw", "drawflush", "print", "printchar", "format", "printflush",
            "getlink", "control", "radar", "sensor", "set", "setrate", "op", "lookup",
            "packcolor", "unpackcolor", "wait", "stop", "end", "jump",
            "ubind", "ucontrol", "uradar", "ulocate", "noop", "select",
        ]
        world_opcodes = [
            # Tier 4: World Processor opcodes (Group A, Group B, Group C, Group D & Group E)
            "query", "getblock", "setblock",
            "spawn", "bullet", "status", "explosion",
            "getflag", "setflag", "setprop", "fetch", "sync", "setrule",
            "weathersense", "weatherset", "spawnwave", "effect",
            "message", "cutscene",
            "playsound", "playmusic", "makemarker", "setmarker", "localeprint", "clientdata",
        ]
        entries = [
            RegistryEntry(source_name=op.upper(), mlog_token=op, category="standard")
            for op in standard_opcodes
        ] + [
            RegistryEntry(source_name=op.upper(), mlog_token=op, category="world")
            for op in world_opcodes
        ]
        super().__init__("opcode", entries)
        self.standard_opcodes = set(standard_opcodes)
        self.world_opcodes = set(world_opcodes)


class StatusEffectRegistry(BaseRegistry):
    """Validates status effects for 'status' instruction and sensor property."""

    def __init__(self):
        entries = [
            RegistryEntry(
                source_name=s.upper().replace("-", "_"),
                mlog_token=f"@status-{s}",
                category="status_effect",
            )
            for s in STATUS_EFFECTS
        ]
        super().__init__("status effect", entries)


class TileLayerRegistry(BaseRegistry):
    """Validates tile layers for 'getblock' and 'setblock'."""

    def __init__(self):
        layers = ["floor", "ore", "block", "building"]
        entries = [
            RegistryEntry(source_name=l.upper(), mlog_token=l, category="tile_layer")
            for l in layers
        ]
        super().__init__("tile layer", entries)


class QueryShapeRegistry(BaseRegistry):
    """Validates spatial query shapes for 'query'."""

    def __init__(self):
        shapes = ["circle", "rect"]
        entries = [
            RegistryEntry(source_name=s.upper(), mlog_token=s, category="query_shape")
            for s in shapes
        ]
        super().__init__("query shape", entries)


class QueryTypeRegistry(BaseRegistry):
    """Validates queryable entity types for 'query'."""

    def __init__(self):
        types = ["unit", "building"]
        entries = [
            RegistryEntry(source_name=t.upper(), mlog_token=t, category="query_type")
            for t in types
        ]
        super().__init__("query type", entries)


class LookupTypeRegistry(BaseRegistry):
    """Validates content types usable with 'lookup'."""

    def __init__(self):
        types = ["item", "block", "unit", "liquid", "team"]
        entries = [
            RegistryEntry(source_name=t.upper(), mlog_token=t, category="lookup_type")
            for t in types
        ]
        super().__init__("lookup type", entries)


class AlignRegistry(BaseRegistry):
    """Validates print text alignments used by 'draw.print' matching Mindustry LStatement.nameToAlign."""

    def __init__(self):
        aligns = [
            ("center", "@center"),
            ("top", "@top"),
            ("bottom", "@bottom"),
            ("left", "@left"),
            ("right", "@right"),
            ("topLeft", "@topLeft"),
            ("topRight", "@topRight"),
            ("bottomLeft", "@bottomLeft"),
            ("bottomRight", "@bottomRight"),
        ]
        entries = [
            RegistryEntry(source_name=name, mlog_token=token, category="align")
            for name, token in aligns
        ]
        super().__init__("align", entries)


class FetchTypeRegistry(BaseRegistry):
    """Validates entity fetch query types for 'fetch'."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=t, mlog_token=t, category="fetch_type")
            for t in FETCH_TYPES
        ]
        super().__init__("fetch type", entries)


class LogicRuleRegistry(BaseRegistry):
    """Validates game and team rules for 'setrule'."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=r, mlog_token=r, category="logic_rule")
            for r in LOGIC_RULES
        ]
        super().__init__("logic rule", entries)


class WeatherRegistry(BaseRegistry):
    """Validates weather types for 'weathersense' and 'weatherset'."""

    def __init__(self):
        entries = [
            RegistryEntry(
                source_name=w.upper().replace("-", "_"),
                mlog_token=f"@{w}",
                category="weather",
            )
            for w in WEATHERS
        ]
        entries.append(
            RegistryEntry(
                source_name="SNOW",
                mlog_token="@snowing",
                category="weather",
            )
        )
        super().__init__("weather", entries)


class LogicFxRegistry(BaseRegistry):
    """Validates visual effects for 'effect'."""

    def __init__(self):
        entries = [
            RegistryEntry(
                source_name=to_snake(fx).upper(),
                mlog_token=fx,
                category="logic_fx",
            )
            for fx in LOGIC_FX
        ]
        super().__init__("logic effect", entries)


class MessageTypeRegistry(BaseRegistry):
    """Validates message display types for 'message'."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=m.upper(), mlog_token=m, category="message_type")
            for m in MESSAGE_TYPES
        ]
        super().__init__("message type", entries)


class CutsceneActionRegistry(BaseRegistry):
    """Validates cutscene actions for 'cutscene'."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=to_snake(a).upper(), mlog_token=a, category="cutscene_action")
            for a in CUTSCENE_ACTIONS
        ]
        super().__init__("cutscene action", entries)


class MarkerTypeRegistry(BaseRegistry):
    """Validates marker types for 'makemarker'."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=to_snake(t).upper(), mlog_token=t, category="marker_type")
            for t in MARKER_TYPES
        ]
        super().__init__("marker type", entries)


class MarkerControlRegistry(BaseRegistry):
    """Validates marker control actions for 'setmarker'."""

    def __init__(self):
        entries = [
            RegistryEntry(source_name=to_snake(c).upper(), mlog_token=c, category="marker_control")
            for c in MARKER_CONTROLS
        ]
        super().__init__("marker control", entries)


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
REG_ALIGN = AlignRegistry()
REG_TILE_LAYERS = TileLayerRegistry()
REG_QUERY_SHAPES = QueryShapeRegistry()
REG_QUERY_TYPES = QueryTypeRegistry()
REG_STATUS_EFFECTS = StatusEffectRegistry()
REG_FETCH_TYPES = FetchTypeRegistry()
REG_LOGIC_RULES = LogicRuleRegistry()
REG_WEATHERS = WeatherRegistry()
REG_LOGIC_FX = LogicFxRegistry()
REG_MESSAGE_TYPES = MessageTypeRegistry()
REG_CUTSCENE_ACTIONS = CutsceneActionRegistry()
REG_MARKER_TYPES = MarkerTypeRegistry()
REG_MARKER_CONTROLS = MarkerControlRegistry()


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
Align = _build_enum_from_registry("Align", REG_ALIGN)
TileLayer = _build_enum_from_registry("TileLayer", REG_TILE_LAYERS)
QueryShape = _build_enum_from_registry("QueryShape", REG_QUERY_SHAPES)
QueryType = _build_enum_from_registry("QueryType", REG_QUERY_TYPES)
StatusEffects = _build_enum_from_registry("StatusEffects", REG_STATUS_EFFECTS)
FetchType = _build_enum_from_registry("FetchType", REG_FETCH_TYPES)
LogicRules = _build_enum_from_registry("LogicRules", REG_LOGIC_RULES)
Weathers = _build_enum_from_registry("Weathers", REG_WEATHERS)
Fx = _build_enum_from_registry("Fx", REG_LOGIC_FX)
MessageType = _build_enum_from_registry("MessageType", REG_MESSAGE_TYPES)
CutsceneAction = _build_enum_from_registry("CutsceneAction", REG_CUTSCENE_ACTIONS)
MarkerType = _build_enum_from_registry("MarkerType", REG_MARKER_TYPES)
MarkerControl = _build_enum_from_registry("MarkerControl", REG_MARKER_CONTROLS)

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
    "Align": REG_ALIGN,
    "TileLayer": REG_TILE_LAYERS,
    "QueryShape": REG_QUERY_SHAPES,
    "QueryType": REG_QUERY_TYPES,
    "StatusEffects": REG_STATUS_EFFECTS,
    "FetchType": REG_FETCH_TYPES,
    "LogicRules": REG_LOGIC_RULES,
    "Weathers": REG_WEATHERS,
    "Fx": REG_LOGIC_FX,
    "MessageType": REG_MESSAGE_TYPES,
    "CutsceneAction": REG_CUTSCENE_ACTIONS,
    "MarkerType": REG_MARKER_TYPES,
    "MarkerControl": REG_MARKER_CONTROLS,
}


# ---------------------------------------------------------------------------
# Mindustry Built-in Variables & Registers Namespace (Vars API)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BuiltinVarToken:
    """Mindustry Logic built-in variable token representation."""

    name: str
    token: str
    readonly: bool = True
    category: str = ""
    type: str = "Any"
    doc: str = ""

    def __repr__(self) -> str:
        return f"<BuiltinVar {self.token}>"

    def __str__(self) -> str:
        return self.token

    def __hash__(self) -> int:
        return hash(self.token)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BuiltinVarToken):
            return self.token == other.token
        if isinstance(other, str):
            return self.token == other
        return False


class _VarsMeta(type):
    """Metaclass for Vars providing attribute access and read-only enforcement."""

    def __setattr__(cls, name: str, value: object):
        if getattr(cls, "_initialized", False):
            tokens = getattr(cls, "_tokens", {})
            token = tokens.get(name)
            if token is not None and token.readonly:
                raise AttributeError(
                    f"Cannot assign to read-only Mindustry built-in variable 'Vars.{name}' ({token.token})"
                )
        super().__setattr__(name, value)

    def __getattr__(cls, name: str):
        tokens = getattr(cls, "_tokens", {})
        token = tokens.get(name)
        if token is None:
            raise AttributeError(f"Unknown Mindustry built-in variable 'Vars.{name}'")
        return token

    def __iter__(cls):
        tokens = getattr(cls, "_tokens", {})
        return iter(tokens.values())

    def __contains__(cls, item: object) -> bool:
        tokens = getattr(cls, "_tokens", {})
        if isinstance(item, str):
            return item in tokens or ("@" + item) in BUILTIN_CONSTANTS
        if isinstance(item, BuiltinVarToken):
            return item.name in tokens
        return False


class Vars(metaclass=_VarsMeta):
    """Mindustry Logic built-in variables namespace.

    Provides direct access to native Mindustry built-in variables and hardware registers
    using their canonical names (e.g. Vars.tick, Vars.waveNumber, Vars.clientName, Vars.blockCount).
    """

    _tokens: Dict[str, BuiltinVarToken] = {}
    _initialized: bool = False


BUILTIN_VARIABLES_DATA: Dict[str, BuiltinVarToken] = {}
BUILTIN_TOKEN_TO_VAR: Dict[str, BuiltinVarToken] = {}

for spec in BUILTIN_VARS_SPEC:
    token_obj = BuiltinVarToken(
        name=str(spec["name"]),
        token=str(spec["token"]),
        readonly=bool(spec.get("readonly", True)),
        category=str(spec.get("category", "")),
        type=str(spec.get("type", "Any")),
        doc=str(spec.get("doc", "")),
    )
    Vars._tokens[token_obj.name] = token_obj
    setattr(Vars, token_obj.name, token_obj)
    BUILTIN_VARIABLES_DATA[token_obj.name] = token_obj
    BUILTIN_TOKEN_TO_VAR[token_obj.token] = token_obj

Vars._initialized = True
