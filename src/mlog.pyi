"""Auto-generated IDE typing stub for Mindustry Logic (mlog) Python DSL.
Single Source of Truth: src/metadata.py and src/mlog_registry.py.
Do not edit directly; regenerated and verified via test suite.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, overload

# Package version
__version__: str

# Null constant representing null in Mindustry Logic
null: Any = None

# ---------------------------------------------------------------------------
# Mindustry Logic Built-in Variables Namespace (Vars API)
# ---------------------------------------------------------------------------

class BuiltinVarToken:
    """Mindustry Logic built-in variable token representation."""
    name: str
    token: str
    readonly: bool
    category: str
    type: str
    doc: str

class Vars:
    """Mindustry Logic built-in variables namespace.
    Provides direct access to native Mindustry built-in variables
    and hardware registers using canonical Mindustry names.
    """
    blockCount: int
    client: int
    clientCurrentMusic: str
    clientLocale: str
    clientMobile: int
    clientMusicPlaying: int
    clientName: str
    clientTeam: int
    clientUnit: Any
    counter: int
    ctrlCommand: int
    ctrlPlayer: int
    ctrlProcessor: int
    degToRad: float
    e: float
    ipt: float
    itemCount: int
    links: int
    liquidCount: int
    maph: int
    mapw: int
    minute: float
    pi: float
    radToDeg: float
    second: float
    server: int
    this: Any
    thisx: float
    thisy: float
    tick: int
    time: float
    unit: Any
    unitCount: int
    wait: Any
    waveNumber: int
    waveTime: float

# ---------------------------------------------------------------------------
# Mindustry Logic Enums (Three-Tier Tier 1)
# ---------------------------------------------------------------------------

class Condition(Enum):
    """Mindustry Logic Condition registry enum."""
    ALWAYS: 'Condition'
    EQUAL: 'Condition'
    GREATERTHAN: 'Condition'
    GREATERTHANEQ: 'Condition'
    GREATER_THAN: 'Condition'
    GREATER_THAN_EQ: 'Condition'
    LESSTHAN: 'Condition'
    LESSTHANEQ: 'Condition'
    LESS_THAN: 'Condition'
    LESS_THAN_EQ: 'Condition'
    NOTEQUAL: 'Condition'
    NOT_EQUAL: 'Condition'
    STRICTEQUAL: 'Condition'
    STRICT_EQUAL: 'Condition'

class ControlProperty(Enum):
    """Mindustry Logic ControlProperty registry enum."""
    COLOR: 'ControlProperty'
    CONFIG: 'ControlProperty'
    ENABLED: 'ControlProperty'
    SHOOT: 'ControlProperty'
    SHOOTP: 'ControlProperty'

class DrawType(Enum):
    """Mindustry Logic DrawType registry enum."""
    CLEAR: 'DrawType'
    COL: 'DrawType'
    COLOR: 'DrawType'
    IMAGE: 'DrawType'
    LINE: 'DrawType'
    LINEPOLY: 'DrawType'
    LINERECT: 'DrawType'
    LINE_POLY: 'DrawType'
    LINE_RECT: 'DrawType'
    POLY: 'DrawType'
    PRINT: 'DrawType'
    RECT: 'DrawType'
    RESET: 'DrawType'
    ROTATE: 'DrawType'
    SCALE: 'DrawType'
    STROKE: 'DrawType'
    TRANSLATE: 'DrawType'
    TRIANGLE: 'DrawType'

class Items(Enum):
    """Mindustry Logic Items registry enum."""
    BERYLLIUM: 'Items'
    BLAST_COMPOUND: 'Items'
    CARBIDE: 'Items'
    COAL: 'Items'
    COPPER: 'Items'
    DORMANT_CYST: 'Items'
    FISSILE_MATTER: 'Items'
    GRAPHITE: 'Items'
    LEAD: 'Items'
    METAGLASS: 'Items'
    OXIDE: 'Items'
    PHASE_FABRIC: 'Items'
    PLASTANIUM: 'Items'
    PYRATITE: 'Items'
    SAND: 'Items'
    SCRAP: 'Items'
    SILICON: 'Items'
    SPORE_POD: 'Items'
    SURGE_ALLOY: 'Items'
    THORIUM: 'Items'
    TITANIUM: 'Items'
    TUNGSTEN: 'Items'

class Liquids(Enum):
    """Mindustry Logic Liquids registry enum."""
    ARKYCITE: 'Liquids'
    CRYOFLUID: 'Liquids'
    CYANOGEN: 'Liquids'
    GALLIUM: 'Liquids'
    HYDROGEN: 'Liquids'
    NITROGEN: 'Liquids'
    OIL: 'Liquids'
    OZONE: 'Liquids'
    SLAG: 'Liquids'
    WATER: 'Liquids'

class LogicOp(Enum):
    """Mindustry Logic LogicOp registry enum."""
    ABS: 'LogicOp'
    ACOS: 'LogicOp'
    ADD: 'LogicOp'
    AND: 'LogicOp'
    ANGLE: 'LogicOp'
    ANGLEDIFF: 'LogicOp'
    ANGLE_DIFF: 'LogicOp'
    ASIN: 'LogicOp'
    ATAN: 'LogicOp'
    CEIL: 'LogicOp'
    COS: 'LogicOp'
    DIV: 'LogicOp'
    EMOD: 'LogicOp'
    EQUAL: 'LogicOp'
    FLOOR: 'LogicOp'
    GREATERTHAN: 'LogicOp'
    GREATERTHANEQ: 'LogicOp'
    GREATER_THAN: 'LogicOp'
    GREATER_THAN_EQ: 'LogicOp'
    IDIV: 'LogicOp'
    LAND: 'LogicOp'
    LEN: 'LogicOp'
    LESSTHAN: 'LogicOp'
    LESSTHANEQ: 'LogicOp'
    LESS_THAN: 'LogicOp'
    LESS_THAN_EQ: 'LogicOp'
    LOG: 'LogicOp'
    LOG10: 'LogicOp'
    LOGN: 'LogicOp'
    MAX: 'LogicOp'
    MIN: 'LogicOp'
    MOD: 'LogicOp'
    MUL: 'LogicOp'
    NOISE: 'LogicOp'
    NOT: 'LogicOp'
    NOTEQUAL: 'LogicOp'
    NOT_EQUAL: 'LogicOp'
    OR: 'LogicOp'
    POW: 'LogicOp'
    RAND: 'LogicOp'
    ROUND: 'LogicOp'
    SHL: 'LogicOp'
    SHR: 'LogicOp'
    SIGN: 'LogicOp'
    SIN: 'LogicOp'
    SQRT: 'LogicOp'
    STRICTEQUAL: 'LogicOp'
    STRICT_EQUAL: 'LogicOp'
    SUB: 'LogicOp'
    TAN: 'LogicOp'
    USHR: 'LogicOp'
    XOR: 'LogicOp'

class LookupType(Enum):
    """Mindustry Logic LookupType registry enum."""
    BLOCK: 'LookupType'
    ITEM: 'LookupType'
    LIQUID: 'LookupType'
    TEAM: 'LookupType'
    UNIT: 'LookupType'

class RadarSort(Enum):
    """Mindustry Logic RadarSort registry enum."""
    ARMOR: 'RadarSort'
    DISTANCE: 'RadarSort'
    HEALTH: 'RadarSort'
    MAXHEALTH: 'RadarSort'
    MAX_HEALTH: 'RadarSort'
    SHIELD: 'RadarSort'

class RadarTarget(Enum):
    """Mindustry Logic RadarTarget registry enum."""
    ALLY: 'RadarTarget'
    ANY: 'RadarTarget'
    ATTACKER: 'RadarTarget'
    BOSS: 'RadarTarget'
    ENEMY: 'RadarTarget'
    FLYING: 'RadarTarget'
    GROUND: 'RadarTarget'
    PLAYER: 'RadarTarget'

class SensorProperty(Enum):
    """Mindustry Logic SensorProperty registry enum."""
    AMMO: 'SensorProperty'
    AMMO_CAPACITY: 'SensorProperty'
    ARKYCITE: 'SensorProperty'
    ARMOR: 'SensorProperty'
    BERYLLIUM: 'SensorProperty'
    BLAST_COMPOUND: 'SensorProperty'
    BOOSTING: 'SensorProperty'
    BREAKING: 'SensorProperty'
    BUFFER_SIZE: 'SensorProperty'
    BUILDING: 'SensorProperty'
    BUILD_X: 'SensorProperty'
    BUILD_Y: 'SensorProperty'
    BULLET_LIFETIME: 'SensorProperty'
    BULLET_TIME: 'SensorProperty'
    CARBIDE: 'SensorProperty'
    COAL: 'SensorProperty'
    COLOR: 'SensorProperty'
    CONFIG: 'SensorProperty'
    CONTROLLED: 'SensorProperty'
    CONTROLLER: 'SensorProperty'
    COPPER: 'SensorProperty'
    CRYOFLUID: 'SensorProperty'
    CURRENT_AMMO_TYPE: 'SensorProperty'
    CYANOGEN: 'SensorProperty'
    DEAD: 'SensorProperty'
    DISPLAY_HEIGHT: 'SensorProperty'
    DISPLAY_WIDTH: 'SensorProperty'
    DORMANT_CYST: 'SensorProperty'
    EFFICIENCY: 'SensorProperty'
    ENABLED: 'SensorProperty'
    FIRST_ITEM: 'SensorProperty'
    FISSILE_MATTER: 'SensorProperty'
    FLAG: 'SensorProperty'
    FLYING: 'SensorProperty'
    GALLIUM: 'SensorProperty'
    GRAPHITE: 'SensorProperty'
    HEALTH: 'SensorProperty'
    HEAT: 'SensorProperty'
    HYDROGEN: 'SensorProperty'
    ID: 'SensorProperty'
    ITEM_CAPACITY: 'SensorProperty'
    LEAD: 'SensorProperty'
    LIQUID_CAPACITY: 'SensorProperty'
    MAX_HEALTH: 'SensorProperty'
    MAX_UNITS: 'SensorProperty'
    MEMORY_CAPACITY: 'SensorProperty'
    METAGLASS: 'SensorProperty'
    MINE_X: 'SensorProperty'
    MINE_Y: 'SensorProperty'
    MINING: 'SensorProperty'
    NAME: 'SensorProperty'
    NITROGEN: 'SensorProperty'
    OIL: 'SensorProperty'
    OPERATIONS: 'SensorProperty'
    OXIDE: 'SensorProperty'
    OZONE: 'SensorProperty'
    PAYLOAD_CAPACITY: 'SensorProperty'
    PAYLOAD_COUNT: 'SensorProperty'
    PAYLOAD_TYPE: 'SensorProperty'
    PHASE_FABRIC: 'SensorProperty'
    PING_TEXT: 'SensorProperty'
    PING_X: 'SensorProperty'
    PING_Y: 'SensorProperty'
    PLASTANIUM: 'SensorProperty'
    POWER_CAPACITY: 'SensorProperty'
    POWER_NET_CAPACITY: 'SensorProperty'
    POWER_NET_IN: 'SensorProperty'
    POWER_NET_OUT: 'SensorProperty'
    POWER_NET_STORED: 'SensorProperty'
    PROGRESS: 'SensorProperty'
    PYRATITE: 'SensorProperty'
    RANGE: 'SensorProperty'
    ROTATION: 'SensorProperty'
    SAND: 'SensorProperty'
    SCRAP: 'SensorProperty'
    SELECTED_BLOCK: 'SensorProperty'
    SELECTED_ROTATION: 'SensorProperty'
    SHIELD: 'SensorProperty'
    SHOOTING: 'SensorProperty'
    SHOOT_X: 'SensorProperty'
    SHOOT_Y: 'SensorProperty'
    SILICON: 'SensorProperty'
    SIZE: 'SensorProperty'
    SLAG: 'SensorProperty'
    SOLID: 'SensorProperty'
    SPEED: 'SensorProperty'
    SPORE_POD: 'SensorProperty'
    SURGE_ALLOY: 'SensorProperty'
    TEAM: 'SensorProperty'
    THORIUM: 'SensorProperty'
    TIMESCALE: 'SensorProperty'
    TITANIUM: 'SensorProperty'
    TOTAL_ITEMS: 'SensorProperty'
    TOTAL_LIQUIDS: 'SensorProperty'
    TOTAL_PAYLOAD: 'SensorProperty'
    TOTAL_POWER: 'SensorProperty'
    TUNGSTEN: 'SensorProperty'
    TYPE: 'SensorProperty'
    VELOCITY_X: 'SensorProperty'
    VELOCITY_Y: 'SensorProperty'
    WATER: 'SensorProperty'
    X: 'SensorProperty'
    Y: 'SensorProperty'

class Teams(Enum):
    """Mindustry Logic Teams registry enum."""
    BLUE: 'Teams'
    CRUX: 'Teams'
    DERELICT: 'Teams'
    GREEN: 'Teams'
    MALIS: 'Teams'
    NEOPLASTIC: 'Teams'
    SHARDED: 'Teams'

class UnitControl(Enum):
    """Mindustry Logic UnitControl registry enum."""
    APPROACH: 'UnitControl'
    AUTOPATHFIND: 'UnitControl'
    AUTO_PATHFIND: 'UnitControl'
    BOOST: 'UnitControl'
    BUILD: 'UnitControl'
    DECONSTRUCT: 'UnitControl'
    FLAG: 'UnitControl'
    GETBLOCK: 'UnitControl'
    GET_BLOCK: 'UnitControl'
    IDLE: 'UnitControl'
    ITEMDROP: 'UnitControl'
    ITEMTAKE: 'UnitControl'
    ITEM_DROP: 'UnitControl'
    ITEM_TAKE: 'UnitControl'
    MINE: 'UnitControl'
    MOVE: 'UnitControl'
    PATHFIND: 'UnitControl'
    PAYDROP: 'UnitControl'
    PAYENTER: 'UnitControl'
    PAYTAKE: 'UnitControl'
    PAY_DROP: 'UnitControl'
    PAY_ENTER: 'UnitControl'
    PAY_TAKE: 'UnitControl'
    STOP: 'UnitControl'
    TARGET: 'UnitControl'
    TARGETP: 'UnitControl'
    UNBIND: 'UnitControl'
    WITHIN: 'UnitControl'

class Units(Enum):
    """Mindustry Logic Units registry enum."""
    AEGIRES: 'Units'
    ALPHA: 'Units'
    ANTHICUS: 'Units'
    ANTHICUS_WEAPON: 'Units'
    ANTUMBRA: 'Units'
    ARKYID: 'Units'
    ARTILLERY: 'Units'
    ARTILLERY_MOUNT: 'Units'
    ASSEMBLY_DRONE: 'Units'
    ATRAX: 'Units'
    ATRAX_WEAPON: 'Units'
    AVERT: 'Units'
    AVERT_WEAPON: 'Units'
    BEAM_WEAPON: 'Units'
    BETA: 'Units'
    BRYDE: 'Units'
    BUILD_WEAPON: 'Units'
    CLEROI: 'Units'
    CLEROI_POINT_DEFENSE: 'Units'
    CLEROI_WEAPON: 'Units'
    COLLARIS: 'Units'
    COLLARIS_WEAPON: 'Units'
    CONQUER: 'Units'
    CONQUER_WEAPON: 'Units'
    CORVUS: 'Units'
    CORVUS_WEAPON: 'Units'
    CRAWLER: 'Units'
    CYERCE: 'Units'
    DAGGER: 'Units'
    DISRUPT: 'Units'
    DISRUPT_WEAPON: 'Units'
    DUMMY: 'Units'
    ECLIPSE: 'Units'
    ELUDE: 'Units'
    ELUDE_WEAPON: 'Units'
    EMANATE: 'Units'
    EMP_CANNON_MOUNT: 'Units'
    EVOKE: 'Units'
    FLAMETHROWER: 'Units'
    FLARE: 'Units'
    FORTRESS: 'Units'
    GAMMA: 'Units'
    HEAL_SHOTGUN_WEAPON: 'Units'
    HEAL_WEAPON: 'Units'
    HEAL_WEAPON_MOUNT: 'Units'
    HORIZON: 'Units'
    INCITE: 'Units'
    LARGE_ARTILLERY: 'Units'
    LARGE_BULLET_MOUNT: 'Units'
    LARGE_LASER_MOUNT: 'Units'
    LARGE_PURPLE_MOUNT: 'Units'
    LARGE_WEAPON: 'Units'
    LATUM: 'Units'
    LOCUS: 'Units'
    LOCUS_WEAPON: 'Units'
    MACE: 'Units'
    MANIFOLD: 'Units'
    MEGA: 'Units'
    MERUI: 'Units'
    MERUI_WEAPON: 'Units'
    MINKE: 'Units'
    MISSILES_MOUNT: 'Units'
    MONO: 'Units'
    MOUNT_PURPLE_WEAPON: 'Units'
    MOUNT_WEAPON: 'Units'
    NAVANAX: 'Units'
    NOVA: 'Units'
    OBVIATE: 'Units'
    OCT: 'Units'
    OMURA: 'Units'
    OMURA_CANNON: 'Units'
    OXYNOE: 'Units'
    PLASMA_LASER_MOUNT: 'Units'
    PLASMA_MISSILE_MOUNT: 'Units'
    PLASMA_MOUNT_WEAPON: 'Units'
    POINT_DEFENSE_MOUNT: 'Units'
    POLY: 'Units'
    POLY_WEAPON: 'Units'
    PRECEPT: 'Units'
    PRECEPT_WEAPON: 'Units'
    PULSAR: 'Units'
    QUAD: 'Units'
    QUASAR: 'Units'
    QUELL: 'Units'
    QUELL_WEAPON: 'Units'
    REIGN: 'Units'
    REIGN_WEAPON: 'Units'
    RENALE: 'Units'
    REPAIR_BEAM_WEAPON_CENTER: 'Units'
    REPAIR_BEAM_WEAPON_CENTER_LARGE: 'Units'
    RETUSA: 'Units'
    RETUSA_WEAPON: 'Units'
    RISSO: 'Units'
    SCEPTER: 'Units'
    SCEPTER_MOUNT: 'Units'
    SCEPTER_WEAPON: 'Units'
    SEI: 'Units'
    SEI_LAUNCHER: 'Units'
    SMALL_BASIC_WEAPON: 'Units'
    SMALL_MOUNT_WEAPON: 'Units'
    SPIROCT: 'Units'
    SPIROCT_WEAPON: 'Units'
    STELL: 'Units'
    STELL_WEAPON: 'Units'
    TECTA: 'Units'
    TECTA_WEAPON: 'Units'
    TOXOPID: 'Units'
    TOXOPID_CANNON: 'Units'
    VANQUISH: 'Units'
    VANQUISH_POINT_WEAPON: 'Units'
    VANQUISH_WEAPON: 'Units'
    VELA: 'Units'
    VELA_WEAPON: 'Units'
    ZENITH: 'Units'
    ZENITH_MISSILES: 'Units'
    _BLADE: 'Units'
    _FIN: 'Units'
    _GLOW: 'Units'
    _SIDE: 'Units'
    _SIDES: 'Units'
    _SINKS: 'Units'
    _SINKS_HEAT: 'Units'
    _SPINE: 'Units'

# ---------------------------------------------------------------------------
# Compiler Core Entry Points
# ---------------------------------------------------------------------------

class CompileResult:
    """Result of compilation containing final mlog text, IR, and label table."""
    mlog: str
    ir: List[Any]
    label_table: Dict[str, int]

def compile_py(source: str, filename: str = '<stdin>', optimize: bool = False, validate: bool = True) -> CompileResult:
    """Compile Python subset source code into canonical vanilla mlog."""
    ...

def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for Python-to-mlog compiler."""
    ...

# ---------------------------------------------------------------------------
# Compiler Intrinsics (Python DSL APIs)
# ---------------------------------------------------------------------------

def control(type: Union[ControlProperty, str], target: Any, p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0) -> None:
    """Control a building property.

    Args:
        type: ControlProperty enum or string (e.g. ControlProperty.ENABLED, 'shoot').
        target: Target building.
        p1, p2, p3, p4: Control parameters (default 0).
    """
    ...

class _DrawCallable:
    """Callable namespace object for Mindustry draw operations.

    Supports both legacy function-call syntax:
        draw("line", x1, y1, x2, y2)
        draw(DrawType.LINE, x1, y1, x2, y2)
    and modern namespace method syntax:
        draw.line(x1, y1, x2, y2)
        draw.clear(r, g, b)
        draw.color(r, g, b, a=255)
    """
    def __call__(self, type: Union[DrawType, str], x: Any = 0, y: Any = 0, p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0) -> None: ...
    def clear(self, r: Any, g: Any, b: Any) -> None: ...
    def color(self, r: Any, g: Any, b: Any, a: Any = 255) -> None: ...
    def col(self, color: Any) -> None: ...
    def stroke(self, width: Any) -> None: ...
    def line(self, x1: Any, y1: Any, x2: Any, y2: Any) -> None: ...
    def rect(self, x: Any, y: Any, width: Any, height: Any) -> None: ...
    def line_rect(self, x: Any, y: Any, width: Any, height: Any) -> None: ...
    def lineRect(self, x: Any, y: Any, width: Any, height: Any) -> None: ...
    def poly(self, x: Any, y: Any, sides: Any, radius: Any, rotation: Any = 0) -> None: ...
    def line_poly(self, x: Any, y: Any, sides: Any, radius: Any, rotation: Any = 0) -> None: ...
    def linePoly(self, x: Any, y: Any, sides: Any, radius: Any, rotation: Any = 0) -> None: ...
    def triangle(self, x1: Any, y1: Any, x2: Any, y2: Any, x3: Any, y3: Any) -> None: ...
    def image(self, x: Any, y: Any, image: Any, size: Any = 32, rotation: Any = 0) -> None: ...
    def print(self, x: Any, y: Any, align: Any = 0) -> None: ...
    def translate(self, x: Any, y: Any) -> None: ...
    def scale(self, x: Any, y: Any) -> None: ...
    def rotate(self, degrees: Any) -> None: ...
    def reset(self) -> None: ...
    def flush(self, display: Any) -> None: ...

draw: _DrawCallable

def drawflush(display: Any) -> None:
    """Flush queued draw operations to a logic display building.

    Args:
        display: Target display block.
    """
    ...

def end() -> None:
    """Jump processor execution back to instruction 0 (restart loop).
    """
    ...

def format(value: Any) -> None:
    """Replace the first placeholder {0}..{9} in the print buffer matching LExecutor.FormatI.

    Args:
        value: Value to replace the placeholder with.
    """
    ...

@overload
def getlink(dest: Any, index: Any) -> Any:
    """Get linked block by index into dest variable (statement form).
    """
    ...

@overload
def getlink(index: Any) -> Any:
    """Get linked block by index and return it (expression form: block = getlink(i)).
    """
    ...

def jump(target: Union[str, int], cond: Union[Condition, str] = "always", a: Any = 0, b: Any = 0) -> None:
    """Jump to a label or instruction address conditionally or unconditionally.

    Args:
        target: Symbolic label name or numeric instruction address.
        cond: Jump condition (Condition enum or string, e.g. Condition.EQUAL, 'lessThan', default 'always').
        a: First comparison operand (default 0).
        b: Second comparison operand (default 0).
    """
    ...

@overload
def lookup(type: Union[LookupType, str], dest: Any, index: Any) -> Any:
    """Look up content and write result to dest variable (statement form).
    """
    ...

@overload
def lookup(type: Union[LookupType, str], index: Any) -> Any:
    """Look up content and return result (expression form: dest = lookup(...)).
    """
    ...

def max(a: Any, b: Any) -> Any:
    """Compute the maximum of two values without compile-time evaluation.

    Args:
        a: First operand.
        b: Second operand.

    Returns:
        The larger of a and b.
    """
    ...

def min(a: Any, b: Any) -> Any:
    """Compute the minimum of two values without compile-time evaluation.

    Args:
        a: First operand.
        b: Second operand.

    Returns:
        The smaller of a and b.
    """
    ...

def noop() -> None:
    """No-operation instruction (occupies 1 instruction slot, executes nothing).
    """
    ...

class _OpCallable:
    """Callable namespace object for Mindustry logic operations.

    Supports both legacy function-call syntax:
        op("add", dest, a, b)
        result = op("add", a, b)
    and modern namespace method syntax:
        result = op.add(a, b)
        op.add(dest, a, b)
        result = op.sin(deg)
        op.sin(dest, deg)
    """
    @overload
    def __call__(self, op_name: Union[LogicOp, str], dest: Any, a: Any, b: Any = 0) -> Any: ...
    @overload
    def __call__(self, op_name: Union[LogicOp, str], a: Any, b: Any = 0) -> Any: ...
    def __call__(self, op_name: Any, *args: Any) -> Any: ...

    # Unary operations (15)
    @overload
    def abs(self, a: Any) -> Any: ...
    @overload
    def abs(self, dest: Any, a: Any) -> Any: ...
    def abs(self, *args: Any) -> Any: ...
    @overload
    def sign(self, a: Any) -> Any: ...
    @overload
    def sign(self, dest: Any, a: Any) -> Any: ...
    def sign(self, *args: Any) -> Any: ...
    @overload
    def log(self, a: Any) -> Any: ...
    @overload
    def log(self, dest: Any, a: Any) -> Any: ...
    def log(self, *args: Any) -> Any: ...
    @overload
    def log10(self, a: Any) -> Any: ...
    @overload
    def log10(self, dest: Any, a: Any) -> Any: ...
    def log10(self, *args: Any) -> Any: ...
    @overload
    def floor(self, a: Any) -> Any: ...
    @overload
    def floor(self, dest: Any, a: Any) -> Any: ...
    def floor(self, *args: Any) -> Any: ...
    @overload
    def ceil(self, a: Any) -> Any: ...
    @overload
    def ceil(self, dest: Any, a: Any) -> Any: ...
    def ceil(self, *args: Any) -> Any: ...
    @overload
    def round(self, a: Any) -> Any: ...
    @overload
    def round(self, dest: Any, a: Any) -> Any: ...
    def round(self, *args: Any) -> Any: ...
    @overload
    def sqrt(self, a: Any) -> Any: ...
    @overload
    def sqrt(self, dest: Any, a: Any) -> Any: ...
    def sqrt(self, *args: Any) -> Any: ...
    @overload
    def rand(self, a: Any) -> Any: ...
    @overload
    def rand(self, dest: Any, a: Any) -> Any: ...
    def rand(self, *args: Any) -> Any: ...
    @overload
    def sin(self, a: Any) -> Any: ...
    @overload
    def sin(self, dest: Any, a: Any) -> Any: ...
    def sin(self, *args: Any) -> Any: ...
    @overload
    def cos(self, a: Any) -> Any: ...
    @overload
    def cos(self, dest: Any, a: Any) -> Any: ...
    def cos(self, *args: Any) -> Any: ...
    @overload
    def tan(self, a: Any) -> Any: ...
    @overload
    def tan(self, dest: Any, a: Any) -> Any: ...
    def tan(self, *args: Any) -> Any: ...
    @overload
    def asin(self, a: Any) -> Any: ...
    @overload
    def asin(self, dest: Any, a: Any) -> Any: ...
    def asin(self, *args: Any) -> Any: ...
    @overload
    def acos(self, a: Any) -> Any: ...
    @overload
    def acos(self, dest: Any, a: Any) -> Any: ...
    def acos(self, *args: Any) -> Any: ...
    @overload
    def atan(self, a: Any) -> Any: ...
    @overload
    def atan(self, dest: Any, a: Any) -> Any: ...
    def atan(self, *args: Any) -> Any: ...
    log_10 = log10

    # Binary operations (27)
    @overload
    def add(self, a: Any, b: Any) -> Any: ...
    @overload
    def add(self, dest: Any, a: Any, b: Any) -> Any: ...
    def add(self, *args: Any) -> Any: ...
    @overload
    def sub(self, a: Any, b: Any) -> Any: ...
    @overload
    def sub(self, dest: Any, a: Any, b: Any) -> Any: ...
    def sub(self, *args: Any) -> Any: ...
    @overload
    def mul(self, a: Any, b: Any) -> Any: ...
    @overload
    def mul(self, dest: Any, a: Any, b: Any) -> Any: ...
    def mul(self, *args: Any) -> Any: ...
    @overload
    def div(self, a: Any, b: Any) -> Any: ...
    @overload
    def div(self, dest: Any, a: Any, b: Any) -> Any: ...
    def div(self, *args: Any) -> Any: ...
    @overload
    def idiv(self, a: Any, b: Any) -> Any: ...
    @overload
    def idiv(self, dest: Any, a: Any, b: Any) -> Any: ...
    def idiv(self, *args: Any) -> Any: ...
    @overload
    def mod(self, a: Any, b: Any) -> Any: ...
    @overload
    def mod(self, dest: Any, a: Any, b: Any) -> Any: ...
    def mod(self, *args: Any) -> Any: ...
    @overload
    def emod(self, a: Any, b: Any) -> Any: ...
    @overload
    def emod(self, dest: Any, a: Any, b: Any) -> Any: ...
    def emod(self, *args: Any) -> Any: ...
    @overload
    def pow(self, a: Any, b: Any) -> Any: ...
    @overload
    def pow(self, dest: Any, a: Any, b: Any) -> Any: ...
    def pow(self, *args: Any) -> Any: ...
    @overload
    def equal(self, a: Any, b: Any) -> Any: ...
    @overload
    def equal(self, dest: Any, a: Any, b: Any) -> Any: ...
    def equal(self, *args: Any) -> Any: ...
    @overload
    def not_equal(self, a: Any, b: Any) -> Any: ...
    @overload
    def not_equal(self, dest: Any, a: Any, b: Any) -> Any: ...
    def not_equal(self, *args: Any) -> Any: ...
    @overload
    def notEqual(self, a: Any, b: Any) -> Any: ...
    @overload
    def notEqual(self, dest: Any, a: Any, b: Any) -> Any: ...
    def notEqual(self, *args: Any) -> Any: ...
    @overload
    def land(self, a: Any, b: Any) -> Any: ...
    @overload
    def land(self, dest: Any, a: Any, b: Any) -> Any: ...
    def land(self, *args: Any) -> Any: ...
    @overload
    def less_than(self, a: Any, b: Any) -> Any: ...
    @overload
    def less_than(self, dest: Any, a: Any, b: Any) -> Any: ...
    def less_than(self, *args: Any) -> Any: ...
    @overload
    def lessThan(self, a: Any, b: Any) -> Any: ...
    @overload
    def lessThan(self, dest: Any, a: Any, b: Any) -> Any: ...
    def lessThan(self, *args: Any) -> Any: ...
    @overload
    def less_than_eq(self, a: Any, b: Any) -> Any: ...
    @overload
    def less_than_eq(self, dest: Any, a: Any, b: Any) -> Any: ...
    def less_than_eq(self, *args: Any) -> Any: ...
    @overload
    def lessThanEq(self, a: Any, b: Any) -> Any: ...
    @overload
    def lessThanEq(self, dest: Any, a: Any, b: Any) -> Any: ...
    def lessThanEq(self, *args: Any) -> Any: ...
    @overload
    def greater_than(self, a: Any, b: Any) -> Any: ...
    @overload
    def greater_than(self, dest: Any, a: Any, b: Any) -> Any: ...
    def greater_than(self, *args: Any) -> Any: ...
    @overload
    def greaterThan(self, a: Any, b: Any) -> Any: ...
    @overload
    def greaterThan(self, dest: Any, a: Any, b: Any) -> Any: ...
    def greaterThan(self, *args: Any) -> Any: ...
    @overload
    def greater_than_eq(self, a: Any, b: Any) -> Any: ...
    @overload
    def greater_than_eq(self, dest: Any, a: Any, b: Any) -> Any: ...
    def greater_than_eq(self, *args: Any) -> Any: ...
    @overload
    def greaterThanEq(self, a: Any, b: Any) -> Any: ...
    @overload
    def greaterThanEq(self, dest: Any, a: Any, b: Any) -> Any: ...
    def greaterThanEq(self, *args: Any) -> Any: ...
    @overload
    def strict_equal(self, a: Any, b: Any) -> Any: ...
    @overload
    def strict_equal(self, dest: Any, a: Any, b: Any) -> Any: ...
    def strict_equal(self, *args: Any) -> Any: ...
    @overload
    def strictEqual(self, a: Any, b: Any) -> Any: ...
    @overload
    def strictEqual(self, dest: Any, a: Any, b: Any) -> Any: ...
    def strictEqual(self, *args: Any) -> Any: ...
    @overload
    def shl(self, a: Any, b: Any) -> Any: ...
    @overload
    def shl(self, dest: Any, a: Any, b: Any) -> Any: ...
    def shl(self, *args: Any) -> Any: ...
    @overload
    def shr(self, a: Any, b: Any) -> Any: ...
    @overload
    def shr(self, dest: Any, a: Any, b: Any) -> Any: ...
    def shr(self, *args: Any) -> Any: ...
    @overload
    def ushr(self, a: Any, b: Any) -> Any: ...
    @overload
    def ushr(self, dest: Any, a: Any, b: Any) -> Any: ...
    def ushr(self, *args: Any) -> Any: ...
    @overload
    def xor(self, a: Any, b: Any) -> Any: ...
    @overload
    def xor(self, dest: Any, a: Any, b: Any) -> Any: ...
    def xor(self, *args: Any) -> Any: ...
    @overload
    def max(self, a: Any, b: Any) -> Any: ...
    @overload
    def max(self, dest: Any, a: Any, b: Any) -> Any: ...
    def max(self, *args: Any) -> Any: ...
    @overload
    def min(self, a: Any, b: Any) -> Any: ...
    @overload
    def min(self, dest: Any, a: Any, b: Any) -> Any: ...
    def min(self, *args: Any) -> Any: ...
    @overload
    def angle(self, a: Any, b: Any) -> Any: ...
    @overload
    def angle(self, dest: Any, a: Any, b: Any) -> Any: ...
    def angle(self, *args: Any) -> Any: ...
    @overload
    def angle_diff(self, a: Any, b: Any) -> Any: ...
    @overload
    def angle_diff(self, dest: Any, a: Any, b: Any) -> Any: ...
    def angle_diff(self, *args: Any) -> Any: ...
    @overload
    def angleDiff(self, a: Any, b: Any) -> Any: ...
    @overload
    def angleDiff(self, dest: Any, a: Any, b: Any) -> Any: ...
    def angleDiff(self, *args: Any) -> Any: ...
    @overload
    def len(self, a: Any, b: Any) -> Any: ...
    @overload
    def len(self, dest: Any, a: Any, b: Any) -> Any: ...
    def len(self, *args: Any) -> Any: ...
    @overload
    def length(self, a: Any, b: Any) -> Any: ...
    @overload
    def length(self, dest: Any, a: Any, b: Any) -> Any: ...
    def length(self, *args: Any) -> Any: ...
    @overload
    def noise(self, a: Any, b: Any) -> Any: ...
    @overload
    def noise(self, dest: Any, a: Any, b: Any) -> Any: ...
    def noise(self, *args: Any) -> Any: ...
    @overload
    def logn(self, a: Any, b: Any) -> Any: ...
    @overload
    def logn(self, dest: Any, a: Any, b: Any) -> Any: ...
    def logn(self, *args: Any) -> Any: ...

op: _OpCallable

@overload
def packcolor(dest: Any, r: Any, g: Any, b: Any, a: Any) -> Any:
    """Pack color components into dest variable (statement form).
    """
    ...

@overload
def packcolor(r: Any, g: Any, b: Any, a: Any) -> Any:
    """Pack color components and return result (expression form: dest = packcolor(...)).
    """
    ...

def print(value: Any) -> None:
    """Append text or a value to the processor print buffer.

    Note: Mindustry Logic's print does NOT append a newline character.
    Multiple consecutive print() calls concatenate directly into a single string.
    To insert a newline, explicitly include '\n' in the text string (e.g. print('Line 1\n')).

    The processor print buffer has a maximum capacity of 400 characters (maxTextBuffer = 400).
    If the buffer is already full (>= 400 characters), subsequent calls are ignored.
    If a string exceeds remaining capacity, it is truncated to fit.
    Numbers within 0.00001 of an integer format as integers; null/NaN/Inf format as 'null'.

    Args:
        value: Text string literal or variable to print.
    """
    ...

def printchar(value: Any) -> None:
    """Append a character to the processor print buffer matching LExecutor.PrintCharI.

    If value is an unlockable content with emoji, appends its emoji character.
    Otherwise, appends chr(floor(value)).

    Args:
        value: Character code (numeric) or content with emoji.
    """
    ...

def printflush(message: Any) -> None:
    """Flush the print buffer to a message block and clear the buffer.

    If target is a valid printable block (e.g. message1), text is displayed on the block.
    The processor print buffer is always cleared unconditionally to length 0.

    Args:
        message: Target message block.
    """
    ...

@overload
def radar(target1: Union[RadarTarget, str], target2: Union[RadarTarget, str], target3: Union[RadarTarget, str], sort: Union[RadarSort, str], turret: Any, sort_order: Any, output: Any) -> Any:
    """Scan radar and write found unit to output (statement form).
    """
    ...

@overload
def radar(target1: Union[RadarTarget, str], target2: Union[RadarTarget, str], target3: Union[RadarTarget, str], sort: Union[RadarSort, str], turret: Any, sort_order: Any) -> Any:
    """Scan radar and return found unit (expression form: target = radar(...)).
    """
    ...

def raw(value: Any) -> str:
    """Explicit escape hatch to bypass registry validation in mlog code.

    Args:
        value: Unverified property string or token (e.g. '@myCustomModProp').

    Returns:
        Raw token string that compiles verbatim into output mlog.
    """
    ...

@overload
def read(dest: Any, cell: Any, address: Any) -> Any:
    """Read number from cell at address into dest variable (statement form).
    """
    ...

@overload
def read(cell: Any, address: Any) -> Any:
    """Read number from cell at address and return it (expression form: dest = read(...)).
    """
    ...

@overload
def select(cond: Any, a: Any, b: Any) -> Any:
    """Select between a and b based on truthiness of cond.
    """
    ...

@overload
def select(dest: Any, cond: Any, a: Any, b: Any) -> None:
    """Select between a and b into dest based on truthiness of cond.
    """
    ...

@overload
def select(cond_op: Union[Condition, str], comp0: Any, comp1: Any, a: Any, b: Any) -> Any:
    """Select between a and b based on cond_op comparison between comp0 and comp1.
    """
    ...

@overload
def select(dest: Any, cond_op: Union[Condition, str], comp0: Any, comp1: Any, a: Any, b: Any) -> None:
    """Select between a and b into dest based on cond_op comparison between comp0 and comp1.
    """
    ...

@overload
def sensor(dest: Any, block: Any, prop: Union[SensorProperty, str]) -> Any:
    """Read property from block into dest variable (statement form).
    """
    ...

@overload
def sensor(block: Any, prop: Union[SensorProperty, str]) -> Any:
    """Read property from block and return result (expression form: dest = sensor(...)).
    """
    ...

def set(to: Any, from_: Any) -> Any:
    """Set a variable to a value.

    Args:
        to: Target variable.
        from_: Source value, variable, or literal.
    """
    ...

def setrate(ipt: Any) -> None:
    """Set processor execution speed in instructions per tick (IPT).

    Args:
        ipt: Target instructions per tick rate (capped by processor max rate, e.g. 1000).
    """
    ...

def stop() -> None:
    """Halt processor execution completely until reset.
    """
    ...

def ubind(unit_type: Union[Units, str]) -> None:
    """Bind a unit of the specified type to this processor.

    Args:
        unit_type: Units enum or string (e.g. Units.FLARE, '@flare', 'mono').
    """
    ...

class _UnitControlCallable:
    """Callable namespace object for Mindustry unit control operations.

    Supports both legacy function-call syntax:
        ucontrol("move", x, y)
        ucontrol(UnitControl.MOVE, x, y)
    and modern namespace method syntax:
        ucontrol.move(x, y)
        ucontrol.approach(x, y, radius)
        ucontrol.mine(x, y)
        ucontrol.boost(True)
        ucontrol.idle()
    """
    def __call__(self, action: Union[UnitControl, str], p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0, p5: Any = 0) -> None: ...
    def idle(self) -> None: ...
    def stop(self) -> None: ...
    def move(self, x: Any, y: Any) -> None: ...
    def approach(self, x: Any, y: Any, radius: Any) -> None: ...
    def pathfind(self, x: Any, y: Any) -> None: ...
    def auto_pathfind(self) -> None: ...
    def autoPathfind(self) -> None: ...
    def boost(self, enable: Any) -> None: ...
    def target(self, x: Any, y: Any, shoot: Any) -> None: ...
    def targetp(self, unit: Any, shoot: Any) -> None: ...
    def item_drop(self, to: Any, amount: Any) -> None: ...
    def itemDrop(self, to: Any, amount: Any) -> None: ...
    def item_take(self, from_: Any, item: Any, amount: Any) -> None: ...
    def itemTake(self, from_: Any, item: Any, amount: Any) -> None: ...
    def pay_drop(self) -> None: ...
    def payDrop(self) -> None: ...
    def pay_take(self, take_units: Any) -> None: ...
    def payTake(self, take_units: Any) -> None: ...
    def pay_enter(self) -> None: ...
    def payEnter(self) -> None: ...
    def mine(self, x: Any, y: Any) -> None: ...
    def flag(self, value: Any) -> None: ...
    def build(self, x: Any, y: Any, block: Any, rotation: Any, config: Any) -> None: ...
    def deconstruct(self, x: Any, y: Any) -> None: ...
    def get_block(self, x: Any, y: Any, out_type: Any, out_building: Any, out_floor: Any) -> None: ...
    def getBlock(self, x: Any, y: Any, out_type: Any, out_building: Any, out_floor: Any) -> None: ...
    def within(self, x: Any, y: Any, radius: Any, out_result: Any) -> None: ...
    def unbind(self) -> None: ...

ucontrol: _UnitControlCallable
unitControl: _UnitControlCallable
unit_control: _UnitControlCallable

class _UnitLocateCallable:
    """Callable namespace object for Mindustry unit locate operations.

    Supports both legacy function-call syntax:
        ulocate("ore", "core", "true", "@copper", outX, outY, found, building)
    and modern namespace method syntax:
        ulocate.ore("@copper", outX, outY, found)
        ulocate.building("core", True, outX, outY, found, building)
        ulocate.spawn(outX, outY, found, building)
        ulocate.damaged(outX, outY, found, building)
    """
    def __call__(self, locate: Any, flag: Any, enemy: Any, ore: Any, out_x: Any, out_y: Any, out_found: Any, out_build: Any) -> None: ...
    def ore(self, ore: Any, out_x: Any, out_y: Any, out_found: Any, out_build: Any = 'building') -> None: ...
    def building(self, group: Any, enemy: Any, out_x: Any, out_y: Any, out_found: Any, out_building: Any) -> None: ...
    def spawn(self, out_x: Any, out_y: Any, out_found: Any, out_build: Any = 'building') -> None: ...
    def damaged(self, out_x: Any, out_y: Any, out_found: Any, out_building: Any) -> None: ...

ulocate: _UnitLocateCallable
unitLocate: _UnitLocateCallable
unit_locate: _UnitLocateCallable

def unpackcolor(r: Any, g: Any, b: Any, a: Any, value: Any) -> None:
    """Unpack a 64-bit double color into 4 target variables r, g, b, a.

    Args:
        r: Target variable for red channel.
        g: Target variable for green channel.
        b: Target variable for blue channel.
        a: Target variable for alpha channel.
        value: 64-bit packed double color operand.
    """
    ...

@overload
def uradar(target1: Union[RadarTarget, str], target2: Union[RadarTarget, str], target3: Union[RadarTarget, str], sort: Union[RadarSort, str], sort_order: Any, output: Any) -> Any:
    """Scan bound unit radar and write found unit to output (statement form).
    """
    ...

@overload
def uradar(target1: Union[RadarTarget, str], target2: Union[RadarTarget, str], target3: Union[RadarTarget, str], sort: Union[RadarSort, str], p1: Any, p2: Any, output: Any) -> Any:
    """Scan bound unit radar with extra parameters (extended statement form).
    """
    ...

@overload
def uradar(target1: Union[RadarTarget, str], target2: Union[RadarTarget, str], target3: Union[RadarTarget, str], sort: Union[RadarSort, str], sort_order: Any) -> Any:
    """Scan bound unit radar and return found unit (expression form: target = uradar(...)).
    """
    ...

def wait(seconds: Any = 0.5) -> None:
    """Pause processor execution for a duration in seconds.

    Args:
        seconds: Duration to wait in seconds (default 0.5).
    """
    ...

def write(input: Any, cell: Any, address: Any) -> None:
    """Write a value to a memory cell or memory bank at the specified index.

    Args:
        input: Value to write.
        cell: Target memory cell or memory bank.
        address: Numeric address index.
    """
    ...

# ---------------------------------------------------------------------------
# Array Class (Memory Cell / Bank Allocator)
# ---------------------------------------------------------------------------

class Array:
    """Fixed-size memory array backed by a Mindustry Memory Cell (max 64) or Memory Bank (max 512)."""
    block: str
    size: int
    dtype: type
    def __init__(self, block: str, size: int, dtype: Union[type, str] = int) -> None: ...
    def __getitem__(self, index: int) -> Any: ...
    def __setitem__(self, index: int, value: Any) -> None: ...
    def __len__(self) -> int: ...

__all__ = [
    "Array",
    "BuiltinVarToken",
    "CompileResult",
    "Condition",
    "ControlProperty",
    "DrawType",
    "Items",
    "Liquids",
    "LogicOp",
    "LookupType",
    "RadarSort",
    "RadarTarget",
    "SensorProperty",
    "Teams",
    "UnitControl",
    "Units",
    "Vars",
    "_DrawCallable",
    "_OpCallable",
    "_UnitControlCallable",
    "_UnitLocateCallable",
    "__version__",
    "compile_py",
    "control",
    "draw",
    "drawflush",
    "end",
    "format",
    "getlink",
    "jump",
    "lookup",
    "main",
    "max",
    "min",
    "noop",
    "null",
    "op",
    "packcolor",
    "print",
    "printchar",
    "printflush",
    "radar",
    "raw",
    "read",
    "select",
    "sensor",
    "set",
    "setrate",
    "stop",
    "ubind",
    "ucontrol",
    "ulocate",
    "unitControl",
    "unitLocate",
    "unit_control",
    "unit_locate",
    "unpackcolor",
    "uradar",
    "wait",
    "write",
]
