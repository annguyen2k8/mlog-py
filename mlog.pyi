"""Auto-generated IDE typing stub for Mindustry Logic (mlog) Python DSL.
Single Source of Truth: src/metadata.py and src/mlog_registry.py.
Do not edit directly; regenerated and verified via test suite.
"""

from enum import Enum, IntEnum
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union, overload

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

class Align(Enum):
    """Mindustry Logic Align registry enum."""
    BOTTOM: 'Align'
    BOTTOMLEFT: 'Align'
    BOTTOMRIGHT: 'Align'
    BOTTOM_LEFT: 'Align'
    BOTTOM_RIGHT: 'Align'
    CENTER: 'Align'
    LEFT: 'Align'
    RIGHT: 'Align'
    TOP: 'Align'
    TOPLEFT: 'Align'
    TOPRIGHT: 'Align'
    TOP_LEFT: 'Align'
    TOP_RIGHT: 'Align'

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

class CutsceneAction(Enum):
    """Mindustry Logic CutsceneAction registry enum."""
    ACTIVE: 'CutsceneAction'
    GET_HUD: 'CutsceneAction'
    PAN: 'CutsceneAction'
    SET_HUD: 'CutsceneAction'
    SHAKE: 'CutsceneAction'
    STOP: 'CutsceneAction'
    ZOOM: 'CutsceneAction'

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

class FetchType(Enum):
    """Mindustry Logic FetchType registry enum."""
    BUILD: 'FetchType'
    BUILDCOUNT: 'FetchType'
    BUILD_COUNT: 'FetchType'
    CORE: 'FetchType'
    CORECOUNT: 'FetchType'
    CORE_COUNT: 'FetchType'
    PLAYER: 'FetchType'
    PLAYERCOUNT: 'FetchType'
    PLAYER_COUNT: 'FetchType'
    UNIT: 'FetchType'
    UNITCOUNT: 'FetchType'
    UNIT_COUNT: 'FetchType'

class Fx(Enum):
    """Mindustry Logic Fx registry enum."""
    BLOCK_FALL: 'Fx'
    BREAK_BLOCK: 'Fx'
    BREAK_PROP: 'Fx'
    BUBBLE: 'Fx'
    CROSS: 'Fx'
    CROSS_EXPLOSION: 'Fx'
    DRILL: 'Fx'
    DRILL_BIG: 'Fx'
    EXPLOSION: 'Fx'
    HIT: 'Fx'
    HIT_SQUARE: 'Fx'
    LIGHT_BLOCK: 'Fx'
    PLACE_BLOCK: 'Fx'
    PLACE_BLOCK_SPARK: 'Fx'
    SHOOT_BIG: 'Fx'
    SHOOT_SMALL: 'Fx'
    SMOKE_BIG: 'Fx'
    SMOKE_CLOUD: 'Fx'
    SMOKE_COLOR: 'Fx'
    SMOKE_PUFF: 'Fx'
    SMOKE_SMALL: 'Fx'
    SMOKE_SQUARE: 'Fx'
    SMOKE_SQUARE_BIG: 'Fx'
    SPARK: 'Fx'
    SPARK_BIG: 'Fx'
    SPARK_EXPLOSION: 'Fx'
    SPARK_SHOOT: 'Fx'
    SPARK_SHOOT_BIG: 'Fx'
    SPAWN: 'Fx'
    TRAIL: 'Fx'
    VAPOR: 'Fx'
    WARN: 'Fx'
    WAVE: 'Fx'

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

class LogicRules(Enum):
    """Mindustry Logic LogicRules registry enum."""
    AMBIENTLIGHT: 'LogicRules'
    AMBIENT_LIGHT: 'LogicRules'
    ATTACKMODE: 'LogicRules'
    ATTACK_MODE: 'LogicRules'
    BAN: 'LogicRules'
    BLOCKDAMAGE: 'LogicRules'
    BLOCKHEALTH: 'LogicRules'
    BLOCK_DAMAGE: 'LogicRules'
    BLOCK_HEALTH: 'LogicRules'
    BUILDSPEED: 'LogicRules'
    BUILD_SPEED: 'LogicRules'
    CANGAMEOVER: 'LogicRules'
    CAN_GAME_OVER: 'LogicRules'
    CURRENTWAVETIME: 'LogicRules'
    CURRENT_WAVE_TIME: 'LogicRules'
    DRAGMULTIPLIER: 'LogicRules'
    DRAG_MULTIPLIER: 'LogicRules'
    DROPZONERADIUS: 'LogicRules'
    DROP_ZONE_RADIUS: 'LogicRules'
    ENEMYCOREBUILDRADIUS: 'LogicRules'
    ENEMY_CORE_BUILD_RADIUS: 'LogicRules'
    LIGHTING: 'LogicRules'
    MAPAREA: 'LogicRules'
    MAP_AREA: 'LogicRules'
    MUSICVOLUME: 'LogicRules'
    MUSIC_VOLUME: 'LogicRules'
    PAUSEDISABLED: 'LogicRules'
    PAUSE_DISABLED: 'LogicRules'
    RTSMINSQUAD: 'LogicRules'
    RTSMINWEIGHT: 'LogicRules'
    RTS_MIN_SQUAD: 'LogicRules'
    RTS_MIN_WEIGHT: 'LogicRules'
    SOLARMULTIPLIER: 'LogicRules'
    SOLAR_MULTIPLIER: 'LogicRules'
    UNBAN: 'LogicRules'
    UNITBUILDSPEED: 'LogicRules'
    UNITCAP: 'LogicRules'
    UNITCOST: 'LogicRules'
    UNITDAMAGE: 'LogicRules'
    UNITHEALTH: 'LogicRules'
    UNITLIGHT: 'LogicRules'
    UNITMINESPEED: 'LogicRules'
    UNIT_BUILD_SPEED: 'LogicRules'
    UNIT_CAP: 'LogicRules'
    UNIT_COST: 'LogicRules'
    UNIT_DAMAGE: 'LogicRules'
    UNIT_HEALTH: 'LogicRules'
    UNIT_LIGHT: 'LogicRules'
    UNIT_MINE_SPEED: 'LogicRules'
    WAVE: 'LogicRules'
    WAVES: 'LogicRules'
    WAVESENDING: 'LogicRules'
    WAVESPACING: 'LogicRules'
    WAVETIMER: 'LogicRules'
    WAVE_SENDING: 'LogicRules'
    WAVE_SPACING: 'LogicRules'
    WAVE_TIMER: 'LogicRules'

class LookupType(Enum):
    """Mindustry Logic LookupType registry enum."""
    BLOCK: 'LookupType'
    ITEM: 'LookupType'
    LIQUID: 'LookupType'
    TEAM: 'LookupType'
    UNIT: 'LookupType'

class MarkerControl(Enum):
    """Mindustry Logic MarkerControl registry enum."""
    ARC: 'MarkerControl'
    AUTOSCALE: 'MarkerControl'
    COLOR: 'MarkerControl'
    COLORI: 'MarkerControl'
    DRAW_LAYER: 'MarkerControl'
    END_POS: 'MarkerControl'
    FLUSH_TEXT: 'MarkerControl'
    FONT_SIZE: 'MarkerControl'
    LABEL_FLAGS: 'MarkerControl'
    LIGHT: 'MarkerControl'
    LINE_ALIGN: 'MarkerControl'
    MINIMAP: 'MarkerControl'
    OUTLINE: 'MarkerControl'
    POS: 'MarkerControl'
    POSI: 'MarkerControl'
    RADIUS: 'MarkerControl'
    REMOVE: 'MarkerControl'
    ROTATION: 'MarkerControl'
    SHAPE: 'MarkerControl'
    STROKE: 'MarkerControl'
    TEXTURE: 'MarkerControl'
    TEXTURE_SIZE: 'MarkerControl'
    TEXT_ALIGN: 'MarkerControl'
    TEXT_HEIGHT: 'MarkerControl'
    UVI: 'MarkerControl'
    WORLD: 'MarkerControl'

class MarkerType(Enum):
    """Mindustry Logic MarkerType registry enum."""
    LIGHT: 'MarkerType'
    LINE: 'MarkerType'
    POINT: 'MarkerType'
    QUAD: 'MarkerType'
    SHAPE: 'MarkerType'
    SHAPE_TEXT: 'MarkerType'
    TEXT: 'MarkerType'
    TEXTURE: 'MarkerType'

class MessageType(Enum):
    """Mindustry Logic MessageType registry enum."""
    ANNOUNCE: 'MessageType'
    MISSION: 'MessageType'
    NOTIFY: 'MessageType'
    TOAST: 'MessageType'

class QueryShape(Enum):
    """Mindustry Logic QueryShape registry enum."""
    CIRCLE: 'QueryShape'
    RECT: 'QueryShape'

class QueryType(Enum):
    """Mindustry Logic QueryType registry enum."""
    BUILDING: 'QueryType'
    UNIT: 'QueryType'

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
    BLASTED: 'SensorProperty'
    BLAST_COMPOUND: 'SensorProperty'
    BOOSTING: 'SensorProperty'
    BOSS: 'SensorProperty'
    BREAKING: 'SensorProperty'
    BUFFER_SIZE: 'SensorProperty'
    BUILDING: 'SensorProperty'
    BUILD_X: 'SensorProperty'
    BUILD_Y: 'SensorProperty'
    BULLET_LIFETIME: 'SensorProperty'
    BULLET_TIME: 'SensorProperty'
    BURNING: 'SensorProperty'
    CARBIDE: 'SensorProperty'
    COAL: 'SensorProperty'
    COLOR: 'SensorProperty'
    CONFIG: 'SensorProperty'
    CONTROLLED: 'SensorProperty'
    CONTROLLER: 'SensorProperty'
    COPPER: 'SensorProperty'
    CORRODED: 'SensorProperty'
    CRYOFLUID: 'SensorProperty'
    CURRENT_AMMO_TYPE: 'SensorProperty'
    CYANOGEN: 'SensorProperty'
    DEAD: 'SensorProperty'
    DISARMED: 'SensorProperty'
    DISPLAY_HEIGHT: 'SensorProperty'
    DISPLAY_WIDTH: 'SensorProperty'
    DORMANT_CYST: 'SensorProperty'
    DYNAMIC: 'SensorProperty'
    EFFICIENCY: 'SensorProperty'
    ELECTRIFIED: 'SensorProperty'
    ENABLED: 'SensorProperty'
    FAST: 'SensorProperty'
    FIRST_ITEM: 'SensorProperty'
    FISSILE_MATTER: 'SensorProperty'
    FLAG: 'SensorProperty'
    FLYING: 'SensorProperty'
    FREEZING: 'SensorProperty'
    GALLIUM: 'SensorProperty'
    GRAPHITE: 'SensorProperty'
    HEALTH: 'SensorProperty'
    HEAT: 'SensorProperty'
    HYDROGEN: 'SensorProperty'
    ID: 'SensorProperty'
    INVINCIBLE: 'SensorProperty'
    ITEM_CAPACITY: 'SensorProperty'
    LEAD: 'SensorProperty'
    LIQUID_CAPACITY: 'SensorProperty'
    MAX_HEALTH: 'SensorProperty'
    MAX_UNITS: 'SensorProperty'
    MELTING: 'SensorProperty'
    MEMORY_CAPACITY: 'SensorProperty'
    METAGLASS: 'SensorProperty'
    MINE_X: 'SensorProperty'
    MINE_Y: 'SensorProperty'
    MINING: 'SensorProperty'
    MUDDY: 'SensorProperty'
    NAME: 'SensorProperty'
    NITROGEN: 'SensorProperty'
    NONE: 'SensorProperty'
    OIL: 'SensorProperty'
    OPERATIONS: 'SensorProperty'
    OVERCLOCK: 'SensorProperty'
    OVERDRIVE: 'SensorProperty'
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
    SAPPED: 'SensorProperty'
    SCRAP: 'SensorProperty'
    SELECTED_BLOCK: 'SensorProperty'
    SELECTED_ROTATION: 'SensorProperty'
    SHIELD: 'SensorProperty'
    SHIELDED: 'SensorProperty'
    SHOCKED: 'SensorProperty'
    SHOOTING: 'SensorProperty'
    SHOOT_X: 'SensorProperty'
    SHOOT_Y: 'SensorProperty'
    SILICON: 'SensorProperty'
    SIZE: 'SensorProperty'
    SLAG: 'SensorProperty'
    SLOW: 'SensorProperty'
    SOLID: 'SensorProperty'
    SPEED: 'SensorProperty'
    SPORE_POD: 'SensorProperty'
    SPORE_SLOWED: 'SensorProperty'
    SURGE_ALLOY: 'SensorProperty'
    TARRED: 'SensorProperty'
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
    UNMOVING: 'SensorProperty'
    VELOCITY_X: 'SensorProperty'
    VELOCITY_Y: 'SensorProperty'
    WATER: 'SensorProperty'
    WET: 'SensorProperty'
    X: 'SensorProperty'
    Y: 'SensorProperty'

class StatusEffects(Enum):
    """Mindustry Logic StatusEffects registry enum."""
    BLASTED: 'StatusEffects'
    BOSS: 'StatusEffects'
    BURNING: 'StatusEffects'
    CORRODED: 'StatusEffects'
    DISARMED: 'StatusEffects'
    DYNAMIC: 'StatusEffects'
    ELECTRIFIED: 'StatusEffects'
    FAST: 'StatusEffects'
    FREEZING: 'StatusEffects'
    INVINCIBLE: 'StatusEffects'
    MELTING: 'StatusEffects'
    MUDDY: 'StatusEffects'
    NONE: 'StatusEffects'
    OVERCLOCK: 'StatusEffects'
    OVERDRIVE: 'StatusEffects'
    SAPPED: 'StatusEffects'
    SHIELDED: 'StatusEffects'
    SHOCKED: 'StatusEffects'
    SLOW: 'StatusEffects'
    SPORE_SLOWED: 'StatusEffects'
    TARRED: 'StatusEffects'
    UNMOVING: 'StatusEffects'
    WET: 'StatusEffects'

class Teams(Enum):
    """Mindustry Logic Teams registry enum."""
    BLUE: 'Teams'
    CRUX: 'Teams'
    DERELICT: 'Teams'
    GREEN: 'Teams'
    MALIS: 'Teams'
    NEOPLASTIC: 'Teams'
    SHARDED: 'Teams'

class TileLayer(Enum):
    """Mindustry Logic TileLayer registry enum."""
    BLOCK: 'TileLayer'
    BUILDING: 'TileLayer'
    FLOOR: 'TileLayer'
    ORE: 'TileLayer'

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

class Weathers(Enum):
    """Mindustry Logic Weathers registry enum."""
    FOG: 'Weathers'
    RAIN: 'Weathers'
    SANDSTORM: 'Weathers'
    SNOW: 'Weathers'
    SNOWING: 'Weathers'
    SPORESTORM: 'Weathers'
    SUSPEND_PARTICLES: 'Weathers'

# ---------------------------------------------------------------------------
# Compiler Core Entry Points
# ---------------------------------------------------------------------------

class CompileResult:
    """Result of compilation containing final mlog text, IR, and label table."""
    mlog: str
    ir: List[Any]
    label_table: Dict[str, int]

def compile_py(source: str, filename: str = '<stdin>', optimize: bool = False, validate: bool = True, allow_functions: bool = False, fold_constants: bool = True, comments_to_print: bool = False) -> CompileResult:
    """Compile Python subset source code into canonical vanilla mlog."""
    ...

def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for Python-to-mlog compiler."""
    ...

# ---------------------------------------------------------------------------
# Compiler Intrinsics (Python DSL APIs)
# ---------------------------------------------------------------------------

@overload
def bullet(from_: Any, index: Any, x: Any, y: Any, rotation: Any, team: Union[Teams, str], owner: Any = "null", damage: Any = -1, velocityScl: Any = 1, lifeScl: Any = 1, aimX: Any = -1, aimY: Any = -1) -> Any:
    """Create a bullet and assign to variable.
    """
    ...

@overload
def bullet(result: Any, from_: Any, index: Any, x: Any, y: Any, rotation: Any, team: Union[Teams, str], owner: Any = "null", damage: Any = -1, velocityScl: Any = 1, lifeScl: Any = 1, aimX: Any = -1, aimY: Any = -1) -> None:
    """Create a bullet into specified result variable.
    """
    ...

def clientdata(channel: Any, value: Any, reliable: Any = False) -> None:
    """Send custom network logic data on a channel.
    """
    ...

class _ControlCallable:
    """Callable namespace object for Mindustry building control operations.

    Supports both legacy function-call syntax:
        control("enabled", target, 1)
        control(ControlProperty.ENABLED, target, 1)
    and modern namespace method syntax:
        control.enabled(target, 1)
        control.shoot(target, x, y, shoot)
        control.shootp(target, unit, shoot)
        control.config(target, "@copper")
        control.color(target, color_value)
    """
    def __call__(self, type: Union[ControlProperty, str], target: Any, p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0) -> None: ...
    def enabled(self, target: Any, value: Any) -> None: ...
    def shoot(self, target: Any, x: Any, y: Any, shoot: Any) -> None: ...
    def shootp(self, target: Any, unit: Any, shoot: Any) -> None: ...
    def config(self, target: Any, value: Any) -> None: ...
    def color(self, target: Any, value: Any) -> None: ...

control: _ControlCallable

class _CutsceneCallable:
    """Callable namespace object for Mindustry cutscene operations.

    Supports both direct function-call syntax:
        cutscene("pan", x, y, speed)
        cutscene(CutsceneAction.PAN, x, y, speed)
        result = cutscene(CutsceneAction.ACTIVE)
    and modern namespace method syntax:
        cutscene.pan(x, y, speed=0.06)
        cutscene.zoom(level)
        cutscene.stop()
        cutscene.shake(amount, duration)
        result = cutscene.active()
        result = cutscene.get_hud()
        cutscene.set_hud(shown)
    """
    def __call__(self, action: Union[CutsceneAction, str], p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0) -> Any: ...
    @overload
    def active(self) -> Any: ...
    @overload
    def active(self, out_result: Any) -> None: ...
    def active(self, *args: Any) -> Any: ...
    def pan(self, x: Any, y: Any, speed: Any = 0.06) -> None: ...
    def zoom(self, level: Any) -> None: ...
    def stop(self) -> None: ...
    def shake(self, amount: Any, duration: Any) -> None: ...
    @overload
    def get_hud(self) -> Any: ...
    @overload
    def get_hud(self, out_result: Any) -> None: ...
    def get_hud(self, *args: Any) -> Any: ...
    @overload
    def getHud(self) -> Any: ...
    @overload
    def getHud(self, out_result: Any) -> None: ...
    def getHud(self, *args: Any) -> Any: ...
    def set_hud(self, shown: Any) -> None: ...
    def setHud(self, shown: Any) -> None: ...

cutscene: _CutsceneCallable

class _DrawCallable:
    """Callable namespace object for Mindustry draw operations.

    Supports both legacy function-call syntax:
        draw("line", x1, y1, x2, y2)
        draw(DrawType.LINE, x1, y1, x2, y2)
    and modern namespace method syntax:
        draw.line(x1, y1, x2, y2)
        draw.clear(r=0, g=0, b=0, a=0)
        draw.color(r, g, b, a=255)
    """
    def __call__(self, type: Union[DrawType, str], x: Any = 0, y: Any = 0, p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0) -> None: ...
    def clear(self, r: Any = 0, g: Any = 0, b: Any = 0, a: Any = 0) -> None: ...
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

def effect(type: Union[Fx, str], x: Any, y: Any, sizerot: Any = 0, color: Any = 0, data: Any = 0) -> None:
    """Creates a visual effect at world coordinates in World Processor.

    Args:
        type: Effect name (Fx enum or string, e.g. Fx.WARN, Fx.EXPLOSION, 'spark').
        x: World tile X coordinate.
        y: World tile Y coordinate.
        sizerot: Effect size or rotation angle (default 0).
        color: Packed color integer or color literal (default 0).
        data: Associated entity or block data (default 0).
    """
    ...

def end() -> None:
    """Jump processor execution back to instruction 0 (restart loop).
    """
    ...

def explosion(team: Union[Teams, str], x: Any, y: Any, radius: Any, damage: Any, air: Any = 1, ground: Any = 1, pierce: Any = 0, effect: Any = 1) -> None:
    """Creates an explosion dealing damage to enemy entities within radius.

    Args:
        team: Team initiating explosion (friendly units/buildings take no damage).
        x: Map tile X coordinate.
        y: Map tile Y coordinate.
        radius: Blast radius in tiles (max 100).
        damage: Maximum blast damage at epicenter (damage < 0 ignored).
        air: Damage flying targets (1 or 0, default 1).
        ground: Damage ground targets (1 or 0, default 1).
        pierce: Damage pierces armor/shields (1 or 0, default 0).
        effect: Trigger explosion visual effect (1 or 0, default 1).
    """
    ...

@overload
def fetch(type: Union[FetchType, str], team: Union[Teams, str], index: Any = 0, extra: Any = 0) -> Any:
    """Fetch entity or count and return result (expression form).
    """
    ...

@overload
def fetch(type: Union[FetchType, str], result: Any, team: Union[Teams, str], index: Any = 0, extra: Any = 0) -> None:
    """Fetch entity or count into result variable (statement form).
    """
    ...

def format(value: Any, *values: Any) -> None:
    """Replace placeholders {0}..{9} in the print buffer matching LExecutor.FormatI.

    Supports single or multiple arguments:
        format(value)
        format(wScr, hScr)

    Args:
        value: First value to replace the next placeholder with.
        values: Additional values to replace subsequent placeholders.
    """
    ...

@overload
def getblock(layer: Union[TileLayer, str], x: Any, y: Any) -> Any:
    """Get block/tile at coordinates into target variable.
    """
    ...

@overload
def getblock(layer: Union[TileLayer, str], result: Any, x: Any, y: Any) -> None:
    """Get block/tile at coordinates into specified result variable.
    """
    ...

@overload
def getflag(flag: Any) -> Any:
    """Check if objective flag is set and return 1 or 0 (expression form: res = getflag(flag)).
    """
    ...

@overload
def getflag(result: Any, flag: Any) -> None:
    """Check if objective flag is set into result variable (statement form: getflag(result, flag)).
    """
    ...

@overload
def getlink(index: Any) -> Any:
    """Get linked block by index and return it (expression form: block = getlink(i)).
    """
    ...

@overload
def getlink(dest: Any, index: Any) -> Any:
    """Get linked block by index into dest variable (statement form: getlink(dest, i)).
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

def localeprint(value: Any) -> None:
    """Append a localized bundle string to the print buffer.
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

def makemarker(type: Any, id: Any, x: Any, y: Any, replace: Any = True) -> None:
    """Create an objective map marker at tile coordinates.
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

def message(type: Any, duration: Any = 3, out_success: Any = "@wait") -> Any:
    """Display an on-screen message or set mission text in World Processor.

    Args:
        type: Message display type (MessageType enum or string, e.g. MessageType.ANNOUNCE, 'notify', 'toast', 'mission').
        duration: Display duration in seconds (default 3).
        out_success: Variable receiving success status (1 or 0) or @wait (default '@wait').
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

def playmusic(name: Any, interrupt: Any = True) -> None:
    """Play a background music track.
    """
    ...

def playsound(positional: Any, id: Any, volume: Any = 1, pitch: Any = 1, pan: Any = 0, x: Any = 0, y: Any = 0, limit: Any = True) -> None:
    """Play a sound effect globally or at world coordinates.
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

def query(shape: Union[QueryShape, str], type_: Union[QueryType, str], team: Any, x: Any, y: Any, w: Any, h: Any) -> None:
    """Queries units or buildings in a specified spatial area.
    Results are outputted into @queries (can be read via read instruction or measured via sensor @size).

    Args:
        shape: Spatial shape ('circle' or 'rect', or QueryShape enum).
        type_: Target type ('unit' or 'building', or QueryType enum).
        team: Target team (Teams enum, team string, or 'null' for all teams).
        x: Center X coordinate in world/tile units.
        y: Center Y coordinate in world/tile units.
        w: Radius (circle) or Width (rect).
        h: Height (rect) or unused (circle).
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

def setblock(layer: Union[TileLayer, str], block: Any, x: Any, y: Any, team: Any = "@derelict", rotation: Any = 0) -> None:
    """Sets the block, floor, or ore at specified map tile coordinates.

    Args:
        layer: Target layer ('floor', 'ore', or 'block', or TileLayer enum).
        block: Target block/floor content (e.g. '@copper-wall', '@dirt', '@air').
        x: Map tile X coordinate.
        y: Map tile Y coordinate.
        team: Target team (optional, defaults to @derelict).
        rotation: Block rotation 0..3 (optional, defaults to 0).
    """
    ...

def setflag(flag: Any, value: Any) -> None:
    """Adds or removes an objective flag from world rules.
    If value evaluates to true (1), the flag is added; if false (0), the flag is removed.

    Args:
        flag: Flag name string (e.g. 'flag1' or 'sector_complete').
        value: Boolean truth value (1/True to add, 0/False to remove).
    """
    ...

def setmarker(type: Any, id: Any, p1: Any = 0, p2: Any = 0, p3: Any = 0) -> None:
    """Control properties or remove an existing map marker.
    """
    ...

def setprop(type: Any, of: Any, value: Any) -> None:
    """Directly modifies a property on a target Settable entity (Unit or Building).
    The property can be an LAccess property (e.g. '@health', '@team', '@shield', '@rotation')
    or an item/liquid UnlockableContent token (e.g. '@copper', '@water').

    Args:
        type: Property token (SensorProperty enum, Item, Liquid, or string token).
        of: Target unit or building entity.
        value: New value to set.
    """
    ...

def setrate(ipt: Any) -> None:
    """Set processor execution speed in instructions per tick (IPT).

    Args:
        ipt: Target instructions per tick rate (capped by processor max rate, e.g. 1000).
    """
    ...

def setrule(rule: Union[LogicRules, str], value: Any, p1: Any = 0, p2: Any = 0, p3: Any = 0, p4: Any = 0) -> None:
    """Modifies world rules or team-specific rules.
    For global rules (e.g. waveTimer, waves, waveSpacing), modifies rule using value.
    For team rules (e.g. unitHealth, buildSpeed, unitDamage), p1 is team and value is multiplier.
    For mapArea, p1=x, p2=y, p3=w, p4=h.
    For ban/unban, value is block or unit content to ban/unban.

    Args:
        rule: LogicRules enum or string (e.g. LogicRules.WAVE_TIMER, LogicRules.UNIT_HEALTH).
        value: Value or multiplier for rule.
        p1, p2, p3, p4: Additional parameters (team, coordinate, dimension; default 0).
    """
    ...

@overload
def spawn(type: Union[Units, str], x: Any, y: Any, rotation: Any, team: Union[Teams, str], effect: Any = 0) -> Any:
    """Spawn a unit and assign to variable.
    """
    ...

@overload
def spawn(type: Union[Units, str], x: Any, y: Any, rotation: Any, team: Union[Teams, str], result: Any, effect: Any = 0) -> None:
    """Spawn a unit into specified result variable.
    """
    ...

def spawnwave(x: Any, y: Any, natural: Any = 0) -> None:
    """Spawns an enemy wave in World Processor.

    If natural is True (1), triggers the natural wave progression (advancing @waveNumber).
    If natural is False (0), spawns enemy wave units from map spawn rules at (x, y).

    Args:
        x: World tile X coordinate (default 0).
        y: World tile Y coordinate (default 0).
        natural: 1/True to advance natural wave, 0/False to spawn at coords (default 0).
    """
    ...

def status(clear: Any, effect: Union[StatusEffects, str], unit: Any, duration: Any = 0) -> None:
    """Applies or clears a status effect on the target unit.

    Args:
        clear: 1/True to unapply/clear, 0/False to apply.
        effect: Status effect token (StatusEffects enum or string, e.g. StatusEffects.BURNING).
        unit: Target unit variable.
        duration: Effect duration in seconds (default 0).
    """
    ...

def stop() -> None:
    """Halt processor execution completely until reset.
    """
    ...

def sync(variable: Any) -> None:
    """Broadcasts a processor variable value to multiplayer clients.
    Rate-limited by Mindustry engine to 20 syncs per second.

    Args:
        variable: Variable name to synchronize.
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

class LocateResult(NamedTuple):
    """Runtime mock result for ulocate building/spawn/damaged queries (4-tuple: x, y, found, building)."""
    x: float
    y: float
    found: int
    building: Any

class OreLocateResult(NamedTuple):
    """Runtime mock result for ulocate ore queries (3-tuple: x, y, found)."""
    x: float
    y: float
    found: int

class _UnitLocateCallable:
    """Callable namespace object for Mindustry unit locate operations.

    NOTE: These runtime methods are local static stubs/mocks for AST validation
    and IDE autocompletion. They do not connect to or query a live Mindustry game.

    Supports both Pythonic tuple unpacking:
        core_x, core_y, found_core, core_build = ulocate.building("core", False)
        ore_x, ore_y, found_ore = ulocate.ore("@copper")
        spawn_x, spawn_y, found_spawn, spawn_build = ulocate.spawn()
        dmg_x, dmg_y, found_dmg, dmg_build = ulocate.damaged()
    and positional argument syntax.
    """
    def __call__(self, locate: Any, *params: Any) -> Any: ...
    @overload
    def ore(self, ore: Any) -> OreLocateResult: ...
    @overload
    def ore(self, ore: Any, out_x: Any, out_y: Any, out_found: Any, out_build: Any = None) -> None: ...
    @overload
    def building(self, group: Any, enemy: Any) -> LocateResult: ...
    @overload
    def building(self, group: Any, enemy: Any, out_x: Any, out_y: Any, out_found: Any, out_building: Any = None) -> None: ...
    @overload
    def spawn(self) -> LocateResult: ...
    @overload
    def spawn(self, out_x: Any, out_y: Any, out_found: Any, out_build: Any = None) -> None: ...
    @overload
    def damaged(self) -> LocateResult: ...
    @overload
    def damaged(self, out_x: Any, out_y: Any, out_found: Any, out_building: Any = None) -> None: ...

ulocate: _UnitLocateCallable

class ColorChannels(NamedTuple):
    """Runtime mock result for unpackcolor queries (4-tuple: r, g, b, a)."""
    r: float
    g: float
    b: float
    a: float

@overload
def unpackcolor(value: Any) -> ColorChannels:
    """Unpack a packed color value and return its RGBA channels (tuple unpacking form).
    """
    ...

@overload
def unpackcolor(r: Any, g: Any, b: Any, a: Any, value: Any) -> None:
    """Unpack packed color value into r, g, b, a variables (statement form).
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

@overload
def weathersense(weather: Union[Weathers, str]) -> Any:
    """Query whether weather event is active.
    """
    ...

@overload
def weathersense(to: Any, weather: Union[Weathers, str]) -> None:
    """Query whether weather event is active into destination variable.
    """
    ...

def weatherset(weather: Union[Weathers, str], state: Any = 1) -> None:
    """Activates or deactivates a weather event.

    Args:
        weather: Weather type (Weathers enum or token, e.g. Weathers.RAIN, '@snowing').
        state: Target state (1/True to activate, 0/False to deactivate, default 1).
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

class _SoundCallable:
    """Callable namespace object for Mindustry sound operations."""
    def __call__(self, positional: Any, id: Any, volume: Any = 1, pitch: Any = 1, pan: Any = 0, x: Any = 0, y: Any = 0, limit: Any = True) -> None: ...
    def play(self, id: Any, volume: Any = 1, pitch: Any = 1, pan: Any = 0, limit: Any = True) -> None: ...
    def play_at(self, id: Any, x: Any, y: Any, volume: Any = 1, pitch: Any = 1, limit: Any = True) -> None: ...
    def playAt(self, id: Any, x: Any, y: Any, volume: Any = 1, pitch: Any = 1, limit: Any = True) -> None: ...

sound: _SoundCallable

class _MusicCallable:
    """Callable namespace object for Mindustry music operations."""
    def __call__(self, name: Any, interrupt: Any = True) -> None: ...
    def play(self, name: Any, interrupt: Any = True) -> None: ...
    def stop(self) -> None: ...

music: _MusicCallable

class _MarkerCallable:
    """Callable namespace object for Mindustry map marker operations."""
    def make(self, type: Union[MarkerType, str], id: Any, x: Any, y: Any, replace: Any = True) -> None: ...
    def remove(self, id: Any) -> None: ...
    def world(self, id: Any, enabled: Any = True) -> None: ...
    def minimap(self, id: Any, enabled: Any = True) -> None: ...
    def light(self, id: Any, enabled: Any = True) -> None: ...
    def autoscale(self, id: Any, enabled: Any = True) -> None: ...
    def pos(self, id: Any, x: Any, y: Any) -> None: ...
    def end_pos(self, id: Any, x: Any, y: Any) -> None: ...
    def endPos(self, id: Any, x: Any, y: Any) -> None: ...
    def draw_layer(self, id: Any, layer: Any) -> None: ...
    def drawLayer(self, id: Any, layer: Any) -> None: ...
    def color(self, id: Any, color: Any) -> None: ...
    def radius(self, id: Any, radius: Any) -> None: ...
    def stroke(self, id: Any, stroke: Any) -> None: ...
    def outline(self, id: Any, outline: Any = True) -> None: ...
    def rotation(self, id: Any, rotation: Any) -> None: ...
    def shape(self, id: Any, sides: Any, fill: Any = 1, outline: Any = 1) -> None: ...
    def arc(self, id: Any, start: Any, end: Any) -> None: ...
    def flush_text(self, id: Any, fetch: Any = False) -> None: ...
    def flushText(self, id: Any, fetch: Any = False) -> None: ...
    def font_size(self, id: Any, size: Any) -> None: ...
    def fontSize(self, id: Any, size: Any) -> None: ...
    def text_height(self, id: Any, height: Any) -> None: ...
    def textHeight(self, id: Any, height: Any) -> None: ...
    def text_align(self, id: Any, align: Any) -> None: ...
    def textAlign(self, id: Any, align: Any) -> None: ...
    def line_align(self, id: Any, align: Any) -> None: ...
    def lineAlign(self, id: Any, align: Any) -> None: ...
    def label_flags(self, id: Any, background: Any = 1, outline: Any = 1) -> None: ...
    def labelFlags(self, id: Any, background: Any = 1, outline: Any = 1) -> None: ...
    def texture(self, id: Any, name: Any, print_flush: Any = False) -> None: ...
    def texture_size(self, id: Any, width: Any, height: Any) -> None: ...
    def textureSize(self, id: Any, width: Any, height: Any) -> None: ...
    def posi(self, id: Any, index: Any, x: Any, y: Any) -> None: ...
    def uvi(self, id: Any, index: Any, x: Any, y: Any) -> None: ...
    def colori(self, id: Any, index: Any, color: Any) -> None: ...

marker: _MarkerCallable

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
    "Align",
    "Array",
    "BuiltinVarToken",
    "ColorChannels",
    "CompileResult",
    "Condition",
    "ControlProperty",
    "CutsceneAction",
    "DrawType",
    "FetchType",
    "Fx",
    "IntEnum",
    "Items",
    "Liquids",
    "LocateResult",
    "LogicOp",
    "LogicRules",
    "LookupType",
    "MarkerControl",
    "MarkerType",
    "MessageType",
    "OreLocateResult",
    "QueryShape",
    "QueryType",
    "RadarSort",
    "RadarTarget",
    "SensorProperty",
    "StatusEffects",
    "Teams",
    "TileLayer",
    "UnitControl",
    "Units",
    "Vars",
    "Weathers",
    "_ControlCallable",
    "_CutsceneCallable",
    "_DrawCallable",
    "_MarkerCallable",
    "_MusicCallable",
    "_OpCallable",
    "_SoundCallable",
    "_UnitControlCallable",
    "_UnitLocateCallable",
    "__version__",
    "bullet",
    "clientdata",
    "compile_py",
    "control",
    "cutscene",
    "draw",
    "drawflush",
    "effect",
    "end",
    "explosion",
    "fetch",
    "format",
    "getblock",
    "getflag",
    "getlink",
    "jump",
    "localeprint",
    "lookup",
    "main",
    "makemarker",
    "marker",
    "max",
    "message",
    "min",
    "music",
    "noop",
    "null",
    "op",
    "packcolor",
    "playmusic",
    "playsound",
    "print",
    "printchar",
    "printflush",
    "query",
    "radar",
    "raw",
    "read",
    "select",
    "sensor",
    "set",
    "setblock",
    "setflag",
    "setmarker",
    "setprop",
    "setrate",
    "setrule",
    "sound",
    "spawn",
    "spawnwave",
    "status",
    "stop",
    "sync",
    "ubind",
    "ucontrol",
    "ulocate",
    "unpackcolor",
    "uradar",
    "wait",
    "weathersense",
    "weatherset",
    "write",
]
