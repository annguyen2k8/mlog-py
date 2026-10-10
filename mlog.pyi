"""Auto-generated IDE typing stub for Mindustry Logic (mlog) Python DSL.
Single Source of Truth: src/metadata.py and src/mlog_registry.py.
Do not edit directly; regenerated and verified via test suite.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Union, overload

# Null constant representing null in Mindustry Logic
null: Any = None

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

def draw(type: Union[DrawType, str], x: Any = 0, y: Any = 0, p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0) -> None:
    """Queue a drawing operation to display buffer.
    
    Args:
        type: DrawType enum or string (e.g. DrawType.CLEAR, DrawType.LINE, DrawType.RECT, 'color').
        x, y, p1, p2, p3, p4: Drawing coordinates, dimensions, or color components (default 0).
    """
    ...

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

@overload
def op(op_name: Union[LogicOp, str], dest: Any, a: Any, b: Any = 0) -> Any:
    """Perform operation and write result to dest variable (statement form).
    """
    ...

@overload
def op(op_name: Union[LogicOp, str], a: Any, b: Any = 0) -> Any:
    """Perform operation and return result (expression form: dest = op(...)).
    """
    ...

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

def ucontrol(action: Union[UnitControl, str], p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0, p5: Any = 0) -> None:
    """Issue a command to the currently bound unit.
    
    Args:
        action: UnitControl enum or string (e.g. UnitControl.MOVE, UnitControl.APPROACH, 'target').
        p1, p2, p3, p4, p5: Command parameters (default 0).
    """
    ...

def ulocate(locate: Any, flag: Any, enemy: Any, ore: Any, outX: Any, outY: Any, outFound: Any, outBuild: Any) -> None:
    """Locate positions, buildings, or ores with the bound unit.
    
    Args:
        locate: Finding type ('ore', 'building', 'spawn', 'damaged').
        flag: Finding flag / building type.
        enemy: Enemy filter (1 / true, 0 / false).
        ore: Ore type if locating ore (e.g. '@copper').
        outX, outY: Output coordinates variables.
        outFound: Output boolean found variable.
        outBuild: Output building variable.
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
    def __init__(self, block: str, size: int) -> None: ...
    def __getitem__(self, index: int) -> int: ...
    def __setitem__(self, index: int, value: int) -> None: ...
    def __len__(self) -> int: ...

__all__ = [
    "Array",
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
    "compile_py",
    "control",
    "draw",
    "drawflush",
    "end",
    "getlink",
    "jump",
    "lookup",
    "main",
    "max",
    "min",
    "null",
    "op",
    "packcolor",
    "print",
    "printflush",
    "radar",
    "raw",
    "read",
    "sensor",
    "set",
    "stop",
    "ubind",
    "ucontrol",
    "ulocate",
    "uradar",
    "wait",
    "write",
]
