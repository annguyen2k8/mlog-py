"""Mindustry source code extractor for Logic Enums, Properties, and Constants.

Inspects the official Mindustry source tree to extract exact definitions for:
- LAccess (Senseable and Controllable properties)
- LUnitControl (Unit control commands)
- LogicOp (Mathematical and logical operations)
- ConditionOp (Jump condition operations)
- GraphicsType (Draw operations)
- RadarTarget and RadarSort
- Content items, liquids, unit types, and teams
- Global built-in variables and constants
"""

import os
import re
from typing import Dict, List, Optional, Tuple


def strip_java_comments(text: str) -> str:
    """Strip comments from Java source while preserving string literals."""
    pattern = r'("(?:\\.|[^"\\])*")|(/\*.*?\*/)|(//[^\n]*)'
    def replace(m):
        if m.group(1):
            return m.group(1)
        return ''
    return re.sub(pattern, replace, text, flags=re.DOTALL)


def parse_enum_constants(text: str, enum_name: str) -> List[Tuple[str, Optional[str]]]:
    """Parse enum constants before the first ';' honoring nested parentheses."""
    text = strip_java_comments(text)
    pattern = rf'enum\s+{enum_name}\s*\{{'
    m = re.search(pattern, text)
    if not m:
        return []
    body = text[m.end():]

    constants = []
    current_token = []
    depth = 0
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == '(':
            depth += 1
            current_token.append(ch)
        elif ch == ')':
            depth -= 1
            current_token.append(ch)
        elif ch == ';' and depth == 0:
            token_str = ''.join(current_token).strip()
            if token_str:
                constants.append(token_str)
            break
        elif ch == ',' and depth == 0:
            token_str = ''.join(current_token).strip()
            if token_str:
                constants.append(token_str)
            current_token = []
        else:
            current_token.append(ch)
        i += 1

    results = []
    for c in constants:
        c = c.strip()
        m = re.match(r'^([a-zA-Z0-9_]+)(?:\((.*)\))?$', c, flags=re.DOTALL)
        if m:
            name = m.group(1)
            params = m.group(2)
            results.append((name, params))
    return results


def extract_laccess(java_dir: str) -> Tuple[List[str], List[str], List[str]]:
    """Extract senseable, controllable, and all LAccess properties."""
    path = os.path.join(java_dir, "logic", "LAccess.java")
    with open(path, "r", encoding="utf-8") as f:
        constants = parse_enum_constants(f.read(), "LAccess")

    privileged = {"cameraX", "cameraY", "cameraWidth", "cameraHeight"}
    controls = [name for name, params in constants if params is not None and len(params.strip()) > 0]
    all_props = [name for name, _ in constants]
    # In Mindustry LAccess.java, senseable properties are all entries where
    # params.length <= 1 and not privileged.
    # Entries with 1 parameter (enabled, config, color) are BOTH controllable and senseable.
    senseable = []
    for name, params in constants:
        if name in privileged:
            continue
        if params is None or len(params.strip()) == 0:
            senseable.append(name)
        else:
            args = [a.strip() for a in params.split(",")]
            if args and args[0] in ("true", "false"):
                args = args[1:]
            if len(args) <= 1:
                senseable.append(name)

    return all_props, senseable, controls


def extract_unit_control(java_dir: str) -> List[str]:
    """Extract LUnitControl action names."""
    path = os.path.join(java_dir, "logic", "LUnitControl.java")
    with open(path, "r", encoding="utf-8") as f:
        constants = parse_enum_constants(f.read(), "LUnitControl")
    return [name for name, _ in constants]


def extract_logic_ops(java_dir: str) -> List[str]:
    """Extract LogicOp operation names."""
    path = os.path.join(java_dir, "logic", "LogicOp.java")
    with open(path, "r", encoding="utf-8") as f:
        constants = parse_enum_constants(f.read(), "LogicOp")
    return [name for name, _ in constants]


def extract_condition_ops(java_dir: str) -> List[str]:
    """Extract ConditionOp condition names."""
    path = os.path.join(java_dir, "logic", "ConditionOp.java")
    with open(path, "r", encoding="utf-8") as f:
        constants = parse_enum_constants(f.read(), "ConditionOp")
    return [name for name, _ in constants]


def extract_graphics_types(java_dir: str) -> List[str]:
    """Extract GraphicsType draw commands from LogicDisplay.java."""
    path = os.path.join(java_dir, "world", "blocks", "logic", "LogicDisplay.java")
    with open(path, "r", encoding="utf-8") as f:
        constants = parse_enum_constants(f.read(), "GraphicsType")
    return [name for name, _ in constants]


def extract_radar_enums(java_dir: str) -> Tuple[List[str], List[str]]:
    """Extract RadarTarget and RadarSort enums."""
    with open(os.path.join(java_dir, "logic", "RadarTarget.java"), "r", encoding="utf-8") as f:
        target_constants = parse_enum_constants(f.read(), "RadarTarget")
    targets = [name for name, _ in target_constants]

    with open(os.path.join(java_dir, "logic", "RadarSort.java"), "r", encoding="utf-8") as f:
        sort_constants = parse_enum_constants(f.read(), "RadarSort")
    sorts = [name for name, _ in sort_constants]

    return targets, sorts


def extract_items(java_dir: str) -> List[str]:
    """Extract item names from Items.java."""
    path = os.path.join(java_dir, "content", "Items.java")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    items = re.findall(r'new\s+Item\s*\(\s*"([a-zA-Z0-9_\-]+)"', content)
    return sorted(set(items))


def extract_liquids(java_dir: str) -> List[str]:
    """Extract liquid names from Liquids.java."""
    path = os.path.join(java_dir, "content", "Liquids.java")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    liquids = re.findall(r'new\s+Liquid\s*\(\s*"([a-zA-Z0-9_\-]+)"', content)
    return sorted(set(liquids))


def extract_units(java_dir: str) -> List[str]:
    """Extract unit names from UnitTypes.java."""
    path = os.path.join(java_dir, "content", "UnitTypes.java")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    units = re.findall(r'new\s+[A-Za-z0-9_]+\s*\(\s*"([a-zA-Z0-9_\-]+)"', content)
    valid_units = [u for u in units if not u.endswith("-missile") and u != "block"]
    return sorted(set(valid_units))


def extract_teams() -> List[str]:
    """Base teams supported in Mindustry."""
    return ["derelict", "sharded", "crux", "malis", "green", "blue", "neoplastic"]


BUILTIN_VARS_SPEC: List[Dict[str, object]] = [
    # Processor (7)
    {"name": "this", "token": "@this", "readonly": True, "category": "Processor", "type": "Any", "doc": "The logic block executing the code"},
    {"name": "thisx", "token": "@thisx", "readonly": True, "category": "Processor", "type": "float", "doc": "X coordinate of block executing the code"},
    {"name": "thisy", "token": "@thisy", "readonly": True, "category": "Processor", "type": "float", "doc": "Y coordinate of block executing the code"},
    {"name": "links", "token": "@links", "readonly": True, "category": "Processor", "type": "int", "doc": "Total number of blocks linked to this processor"},
    {"name": "ipt", "token": "@ipt", "readonly": True, "category": "Processor", "type": "float", "doc": "Execution speed of the processor in instructions per tick"},
    {"name": "counter", "token": "@counter", "readonly": False, "category": "Processor", "type": "int", "doc": "Current instruction counter register"},
    {"name": "unit", "token": "@unit", "readonly": True, "category": "Processor", "type": "Any", "doc": "Currently bound unit"},
    # General (7)
    {"name": "pi", "token": "@pi", "readonly": True, "category": "General", "type": "float", "doc": "The mathematical constant pi (3.141592653589793)"},
    {"name": "e", "token": "@e", "readonly": True, "category": "General", "type": "float", "doc": "The mathematical constant e (2.718281828459045)"},
    {"name": "degToRad", "token": "@degToRad", "readonly": True, "category": "General", "type": "float", "doc": "Multiply by this number to convert degrees to radians"},
    {"name": "radToDeg", "token": "@radToDeg", "readonly": True, "category": "General", "type": "float", "doc": "Multiply by this number to convert radians to degrees"},
    {"name": "ctrlProcessor", "token": "@ctrlProcessor", "readonly": True, "category": "General", "type": "int", "doc": "Unit controller type: processor (1)"},
    {"name": "ctrlPlayer", "token": "@ctrlPlayer", "readonly": True, "category": "General", "type": "int", "doc": "Unit controller type: player (2)"},
    {"name": "ctrlCommand", "token": "@ctrlCommand", "readonly": True, "category": "General", "type": "int", "doc": "Unit controller type: command (3)"},
    # Map (9)
    {"name": "time", "token": "@time", "readonly": True, "category": "Map", "type": "float", "doc": "Playtime of current save, in milliseconds"},
    {"name": "tick", "token": "@tick", "readonly": True, "category": "Map", "type": "int", "doc": "Playtime of current save, in ticks (1 second = 60 ticks)"},
    {"name": "second", "token": "@second", "readonly": True, "category": "Map", "type": "float", "doc": "Playtime of current save, in seconds"},
    {"name": "minute", "token": "@minute", "readonly": True, "category": "Map", "type": "float", "doc": "Playtime of current save, in minutes"},
    {"name": "waveNumber", "token": "@waveNumber", "readonly": True, "category": "Map", "type": "int", "doc": "Current wave number, if waves are enabled"},
    {"name": "waveTime", "token": "@waveTime", "readonly": True, "category": "Map", "type": "float", "doc": "Countdown timer for waves, in seconds"},
    {"name": "mapw", "token": "@mapw", "readonly": True, "category": "Map", "type": "int", "doc": "Map width in tiles"},
    {"name": "maph", "token": "@maph", "readonly": True, "category": "Map", "type": "int", "doc": "Map height in tiles"},
    {"name": "wait", "token": "@wait", "readonly": True, "category": "Map", "type": "Any", "doc": "Internal message wait sentinel (World Processor; null on regular processors)"},
    # Network / Clientside (9)
    {"name": "server", "token": "@server", "readonly": True, "category": "Network", "type": "int", "doc": "True if running on a server or in singleplayer, false otherwise"},
    {"name": "client", "token": "@client", "readonly": True, "category": "Network", "type": "int", "doc": "True if running on a client connected to a server"},
    {"name": "clientLocale", "token": "@clientLocale", "readonly": True, "category": "Network", "type": "str", "doc": "Locale of the client running the code"},
    {"name": "clientUnit", "token": "@clientUnit", "readonly": True, "category": "Network", "type": "Any", "doc": "Unit of client running the code"},
    {"name": "clientName", "token": "@clientName", "readonly": True, "category": "Network", "type": "str", "doc": "Player name of client running the code"},
    {"name": "clientTeam", "token": "@clientTeam", "readonly": True, "category": "Network", "type": "int", "doc": "Team ID of client running the code"},
    {"name": "clientMobile", "token": "@clientMobile", "readonly": True, "category": "Network", "type": "int", "doc": "True if client is on mobile, false otherwise"},
    {"name": "clientMusicPlaying", "token": "@clientMusicPlaying", "readonly": True, "category": "Network", "type": "int", "doc": "True if music is currently playing"},
    {"name": "clientCurrentMusic", "token": "@clientCurrentMusic", "readonly": True, "category": "Network", "type": "str", "doc": "Name of current track being played, or null"},
    # Lookup (4)
    {"name": "blockCount", "token": "@blockCount", "readonly": True, "category": "Lookup", "type": "int", "doc": "Total number of types of block content in the game"},
    {"name": "unitCount", "token": "@unitCount", "readonly": True, "category": "Lookup", "type": "int", "doc": "Total number of types of unit content in the game"},
    {"name": "itemCount", "token": "@itemCount", "readonly": True, "category": "Lookup", "type": "int", "doc": "Total number of types of item content in the game"},
    {"name": "liquidCount", "token": "@liquidCount", "readonly": True, "category": "Lookup", "type": "int", "doc": "Total number of types of liquid content in the game"},
]


def extract_builtin_constants() -> List[str]:
    """Core built-in variables and constants defined in GlobalVars and LAssembler."""
    return [str(spec["token"]) for spec in BUILTIN_VARS_SPEC]


def extract_all(mindustry_root: str) -> Dict[str, object]:
    """Extract all Mindustry Logic constants and enums into a dictionary."""
    java_dir = os.path.join(mindustry_root, "core", "src", "mindustry")
    all_access, senseable, controls = extract_laccess(java_dir)
    ucontrol = extract_unit_control(java_dir)
    logic_ops = extract_logic_ops(java_dir)
    cond_ops = extract_condition_ops(java_dir)
    graphics = extract_graphics_types(java_dir)
    targets, sorts = extract_radar_enums(java_dir)
    items = extract_items(java_dir)
    liquids = extract_liquids(java_dir)
    units = extract_units(java_dir)
    teams = extract_teams()
    builtins = extract_builtin_constants()

    return {
        "laccess_all": all_access,
        "senseable_properties": senseable,
        "control_properties": controls,
        "unit_control_actions": ucontrol,
        "logic_operations": logic_ops,
        "condition_operations": cond_ops,
        "graphics_types": graphics,
        "radar_targets": targets,
        "radar_sorts": sorts,
        "items": items,
        "liquids": liquids,
        "units": units,
        "teams": teams,
        "builtin_constants": builtins,
        "builtin_vars_spec": BUILTIN_VARS_SPEC,
    }


def generate_registry_data_file(data: Dict[str, object], output_file: str):
    """Write extracted data to a standalone Python module."""
    with open(output_file, "w", encoding="utf-8") as f:
        f.write('"""Auto-generated registry data extracted from Mindustry source code."""\n\n')
        for key, val in data.items():
            f.write(f"{key.upper()} = {repr(val)}\n\n")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    mindustry_dir = os.path.join(project_root, "Mindustry")
    data = extract_all(mindustry_dir)
    output_path = os.path.join(script_dir, "mlog_registry_data.py")
    generate_registry_data_file(data, output_path)
    print(f"Generated {output_path} with:")
    for k, v in data.items():
        print(f"  {k}: {len(v)} items")
