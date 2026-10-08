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
    senseable = [name for name, _ in constants if name not in controls and name not in privileged]

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


def extract_builtin_constants() -> List[str]:
    """Core built-in variables and constants defined in GlobalVars and LAssembler."""
    return [
        "@this", "@thisx", "@thisy", "@ipt", "@links",
        "@counter", "@unit",
        "@time", "@tick", "@second", "@minute",
        "@waveNumber", "@waveTime", "@mapw", "@maph",
        "@pi", "@e", "@degToRad", "@radToDeg",
        "@ctrlProcessor", "@ctrlPlayer", "@ctrlCommand",
        "@server", "@client", "@wait",
    ]


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
