"""
Warhammer 40k Combat Simulator
Simulate combat between units with statistical analysis
"""

import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import plotly.graph_objects as go
import plotly.express as px
from dataclasses import dataclass

# Set page config
st.set_page_config(
    page_title="WH40k Combat Simulator",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)

@dataclass
class WeaponProfile:
    """Weapon statistics"""
    name: str
    range_val: str
    attacks: str
    skill: str  # BS or WS
    strength: str
    ap: str
    damage: str
    abilities: str = ""

@dataclass
class UnitProfile:
    """Unit statistics"""
    name: str
    movement: str
    toughness: str
    save: str
    wounds: str
    leadership: str
    oc: str
    invuln_save: str = ""
    abilities: List[str] = None

@st.cache_data
def discover_catalogues() -> List[Dict]:
    """Discover all available .cat files in the repository"""
    cat_files = []
    base_path = Path(__file__).parent

    for cat_file in base_path.glob("*.cat"):
        # Skip Library files (they're dependencies, not playable armies)
        if "Library" in cat_file.stem:
            continue

        # Extract a clean display name
        display_name = cat_file.stem

        cat_files.append({
            'display_name': display_name,
            'file_path': str(cat_file),
            'file_name': cat_file.name
        })

    # Sort by display name for better UX
    cat_files.sort(key=lambda x: x['display_name'])

    return cat_files

@st.cache_data
def parse_catalogue(file_path: str) -> Tuple:
    """Parse a catalogue XML file"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    ns = {'cat': 'http://www.battlescribe.net/schema/catalogueSchema'}

    catalogue_info = {
        'name': root.get('name'),
        'revision': root.get('revision'),
        'file_path': file_path
    }

    return root, ns, catalogue_info

@st.cache_data
def get_all_units(_root, _ns, catalogue_name: str) -> pd.DataFrame:
    """Get all units from catalogue (root-level entryLinks only)"""
    units = []

    # Find the root-level entryLinks element
    entry_links_elem = _root.find('cat:entryLinks', _ns)

    if entry_links_elem is not None:
        # Get only direct children of entryLinks
        for entry in entry_links_elem.findall('cat:entryLink', _ns):
            if entry.get('type') == 'selectionEntry' and entry.get('hidden', 'false') == 'false':
                units.append({
                    'name': entry.get('name'),
                    'id': entry.get('id'),
                    'targetId': entry.get('targetId')
                })

    return pd.DataFrame(units)

@st.cache_data
def extract_detachments(_root, _ns, catalogue_name: str) -> List[Dict]:
    """Extract detachment information and their rules"""
    detachments = []

    # Find the Detachment selectionEntry
    for entry in _root.findall('.//cat:selectionEntry[@name="Detachment"]', _ns):
        # Find all detachment options within the selectionEntryGroup
        for group in entry.findall('.//cat:selectionEntryGroup', _ns):
            for detachment in group.findall('.//cat:selectionEntry', _ns):
                det_name = detachment.get('name')
                if det_name and det_name != 'none':
                    det_data = {
                        'name': det_name,
                        'id': detachment.get('id'),
                        'rules': []
                    }

                    # Extract rules for this detachment
                    for rule in detachment.findall('.//cat:rule', _ns):
                        rule_name = rule.get('name')
                        desc_elem = rule.find('cat:description', _ns)
                        description = desc_elem.text if desc_elem is not None and desc_elem.text else ''

                        det_data['rules'].append({
                            'name': rule_name,
                            'description': description
                        })

                    detachments.append(det_data)

    return detachments

@st.cache_data
def extract_unit_details(_root, _ns, unit_name: str) -> Dict:
    """Extract complete details for a specific unit"""
    unit_data = {
        'name': unit_name,
        'profiles': [],
        'weapons': [],
        'abilities': [],
        'keywords': [],
        'costs': {}
    }

    # Find the unit entry
    for entry in _root.findall('.//cat:sharedSelectionEntries/cat:selectionEntry', _ns):
        if entry.get('name') == unit_name:
            # Get costs
            for cost in entry.findall('.//cat:cost', _ns):
                cost_name = cost.get('name')
                cost_value = cost.get('value', '0')
                unit_data['costs'][cost_name] = cost_value

            # Get profiles (unit stats)
            for profile in entry.findall('.//cat:profile[@typeName="Unit"]', _ns):
                profile_dict = {'name': profile.get('name')}
                for char in profile.findall('.//cat:characteristic', _ns):
                    profile_dict[char.get('name')] = char.text or ''
                unit_data['profiles'].append(profile_dict)

            # Get weapon profiles
            for profile in entry.findall('.//cat:profile[@typeName="Ranged Weapons"]', _ns):
                weapon = {'name': profile.get('name')}
                for char in profile.findall('.//cat:characteristic', _ns):
                    weapon[char.get('name')] = char.text or ''
                unit_data['weapons'].append(weapon)

            for profile in entry.findall('.//cat:profile[@typeName="Melee Weapons"]', _ns):
                weapon = {'name': profile.get('name'), 'type': 'Melee'}
                for char in profile.findall('.//cat:characteristic', _ns):
                    weapon[char.get('name')] = char.text or ''
                unit_data['weapons'].append(weapon)

            # Get abilities
            for rule in entry.findall('.//cat:rule', _ns):
                ability = {
                    'name': rule.get('name'),
                    'description': ''
                }
                desc = rule.find('cat:description', _ns)
                if desc is not None and desc.text:
                    ability['description'] = desc.text
                unit_data['abilities'].append(ability)

            # Get keywords
            for category in entry.findall('.//cat:categoryLink', _ns):
                cat_name = category.get('name')
                if cat_name:
                    unit_data['keywords'].append(cat_name)

            break

    return unit_data

def parse_dice_value(value: str) -> int:
    """Parse dice notation like 'D6', '2D6', etc."""
    if not value or value == '-':
        return 0

    value = value.strip().upper()

    # Handle D6+X notation
    if 'D6' in value:
        parts = value.split('+')
        base = parts[0]
        modifier = int(parts[1]) if len(parts) > 1 else 0

        if base == 'D6':
            return np.random.randint(1, 7) + modifier
        elif base.startswith('D'):
            return np.random.randint(1, 7) + modifier
        else:
            # e.g., "2D6"
            num_dice = int(base.replace('D6', ''))
            return sum(np.random.randint(1, 7) for _ in range(num_dice)) + modifier

    # Handle fixed values
    try:
        return int(value)
    except ValueError:
        return 1  # Default

def roll_d6() -> int:
    """Roll a single D6"""
    return np.random.randint(1, 7)

def simulate_attack_sequence(
    attacker_weapon: Dict,
    attacker_unit: Dict,
    defender_unit: Dict,
    num_simulations: int = 100,
    attacker_squad_size: int = 1,
    defender_squad_size: int = 1,
    modifiers: Dict = None
) -> Dict:
    """
    Simulate attack sequence: Hit -> Wound -> Save -> Damage -> Models Destroyed

    Supports:
    - Invulnerable saves
    - Devastating Wounds
    - Lethal Hits
    - Feel No Pain
    - Manual modifiers (hit, wound, save, damage)
    - Squad sizes and model tracking

    Returns statistics about the attack outcomes
    """

    if modifiers is None:
        modifiers = {}

    results = {
        'total_attacks': 0,
        'hits': 0,
        'critical_hits': 0,
        'wounds': 0,
        'critical_wounds': 0,
        'failed_saves': 0,
        'mortal_wounds': 0,
        'fnp_saved': 0,
        'total_damage': 0,
        'models_killed': 0,
        'damage_per_simulation': [],
        'models_killed_per_simulation': [],
        'calculation_log': []  # Detailed math breakdown
    }

    # Get weapon stats with N/A handling
    attacks_stat = attacker_weapon.get('A', '1')
    if attacks_stat in ['N/A', '-', '']:
        attacks_stat = '0'

    skill_stat = attacker_weapon.get('BS', attacker_weapon.get('WS', '4+'))
    if skill_stat in ['N/A', '-', '']:
        skill_stat = '4+'

    strength_raw = attacker_weapon.get('S', '4')
    if strength_raw in ['N/A', '-', '', 'User']:
        strength = 4
    else:
        try:
            strength = int(strength_raw)
        except ValueError:
            strength = 4

    ap_raw = attacker_weapon.get('AP', '0')
    if ap_raw in ['N/A', '-', '']:
        ap = 0
    else:
        try:
            ap = int(ap_raw)
        except ValueError:
            ap = 0

    damage_stat = attacker_weapon.get('D', '1')
    if damage_stat in ['N/A', '-', '']:
        damage_stat = '1'

    # Check for special abilities
    weapon_abilities = attacker_weapon.get('Abilities', '').lower()
    has_lethal_hits = 'lethal hits' in weapon_abilities or modifiers.get('lethal_hits', False)
    has_devastating_wounds = 'devastating wounds' in weapon_abilities or modifiers.get('devastating_wounds', False)

    # Get defender stats with N/A handling
    defender_profile = defender_unit['profiles'][0] if defender_unit['profiles'] else {}

    toughness_raw = defender_profile.get('T', '4')
    if toughness_raw in ['N/A', '-', '']:
        toughness = 4
    else:
        try:
            toughness = int(toughness_raw)
        except ValueError:
            toughness = 4

    save_raw = defender_profile.get('SV', '3+')
    if save_raw in ['N/A', '-', '']:
        save = 7  # No save
    else:
        try:
            save = int(save_raw.replace('+', ''))
        except ValueError:
            save = 7

    invuln = defender_profile.get('Invuln', '')

    wounds_raw = defender_profile.get('W', '1')
    if wounds_raw in ['N/A', '-', '']:
        wounds_per_model = 1
    else:
        try:
            wounds_per_model = int(wounds_raw)
        except ValueError:
            wounds_per_model = 1

    # Feel No Pain
    fnp = modifiers.get('feel_no_pain', 0)  # 0 means none, otherwise the roll needed (e.g., 5 for 5+)

    # Apply modifiers
    hit_modifier = modifiers.get('hit_modifier', 0)
    wound_modifier = modifiers.get('wound_modifier', 0)
    save_modifier = modifiers.get('save_modifier', 0)
    damage_modifier = modifiers.get('damage_modifier', 0)
    ap_modifier = modifiers.get('ap_modifier', 0)

    # Parse hit requirement (e.g., "3+" -> need 3 or higher)
    base_hit_requirement = int(skill_stat.replace('+', ''))
    hit_requirement = max(2, min(6, base_hit_requirement - hit_modifier))

    # Modified AP
    modified_ap = ap + ap_modifier

    for sim in range(num_simulations):
        sim_damage = 0
        models_killed_this_sim = 0

        # Track defender's remaining wounds
        remaining_defender_wounds = [wounds_per_model] * defender_squad_size

        # 1. Determine number of attacks (total from all attacking models)
        num_attacks = 0
        for _ in range(attacker_squad_size):
            num_attacks += parse_dice_value(attacks_stat)
        results['total_attacks'] += num_attacks

        # 2. Roll to hit
        hits = 0
        critical_hits = 0
        for _ in range(num_attacks):
            roll = roll_d6()
            if roll == 6:  # Critical hit
                critical_hits += 1
                hits += 1
                results['critical_hits'] += 1
            elif roll >= hit_requirement:
                hits += 1
        results['hits'] += hits

        if hits == 0:
            results['damage_per_simulation'].append(0)
            results['models_killed_per_simulation'].append(0)
            continue

        # 3. Roll to wound (S vs T comparison)
        base_wound_requirement = calculate_wound_requirement(strength, toughness)
        wound_requirement = max(2, min(6, base_wound_requirement - wound_modifier))

        wounds = 0
        critical_wounds = 0
        mortal_wounds_this_phase = 0

        # Lethal Hits: Critical hits auto-wound
        if has_lethal_hits:
            for _ in range(critical_hits):
                wounds += 1
                critical_wounds += 1
                results['critical_wounds'] += 1
            # Roll to wound for non-critical hits
            for _ in range(hits - critical_hits):
                roll = roll_d6()
                if roll == 6:
                    critical_wounds += 1
                    wounds += 1
                    results['critical_wounds'] += 1
                elif roll >= wound_requirement:
                    wounds += 1
        else:
            for _ in range(hits):
                roll = roll_d6()
                if roll == 6:
                    critical_wounds += 1
                    wounds += 1
                    results['critical_wounds'] += 1
                elif roll >= wound_requirement:
                    wounds += 1

        results['wounds'] += wounds

        if wounds == 0:
            results['damage_per_simulation'].append(0)
            results['models_killed_per_simulation'].append(0)
            continue

        # Devastating Wounds: Critical wounds become mortal wounds (skip saves)
        normal_wounds = wounds
        if has_devastating_wounds and critical_wounds > 0:
            mortal_wounds_this_phase = critical_wounds
            normal_wounds = wounds - critical_wounds
            results['mortal_wounds'] += mortal_wounds_this_phase

        # 4. Roll saves for normal wounds
        failed_saves = 0
        if normal_wounds > 0:
            modified_save = save - modified_ap + save_modifier

            # Check if invuln is better
            if invuln:
                invuln_val = int(invuln.replace('+', ''))
                save_requirement = min(modified_save, invuln_val)
            else:
                save_requirement = modified_save

            # Cannot save on 7+, auto-save on 1 or less
            if save_requirement > 6:
                failed_saves = normal_wounds
            elif save_requirement <= 1:
                failed_saves = 0
            else:
                failed_saves = sum(1 for _ in range(normal_wounds) if roll_d6() < save_requirement)

        results['failed_saves'] += failed_saves

        # 5. Deal damage
        all_damage_instances = []

        # Damage from normal wounds
        for _ in range(failed_saves):
            dmg = parse_dice_value(damage_stat) + damage_modifier
            dmg = max(1, dmg)  # Minimum 1 damage
            all_damage_instances.append(dmg)

        # Mortal wounds (typically D3 or 1 damage each)
        for _ in range(mortal_wounds_this_phase):
            dmg = parse_dice_value(damage_stat) + damage_modifier
            dmg = max(1, dmg)
            all_damage_instances.append(dmg)

        # 6. Apply Feel No Pain to all damage
        if fnp > 0:
            damage_after_fnp = []
            for dmg in all_damage_instances:
                damage_prevented = 0
                for _ in range(dmg):
                    if roll_d6() >= fnp:
                        # FNP failed, damage goes through
                        damage_after_fnp.append(1)
                    else:
                        # FNP succeeded
                        damage_prevented += 1
                results['fnp_saved'] += damage_prevented
            all_damage_instances = damage_after_fnp

        # 7. Allocate damage to models and track kills
        for dmg in all_damage_instances:
            sim_damage += dmg
            results['total_damage'] += dmg

            # Allocate to first alive model
            for i, model_wounds in enumerate(remaining_defender_wounds):
                if model_wounds > 0:
                    remaining_defender_wounds[i] -= dmg
                    if remaining_defender_wounds[i] <= 0:
                        models_killed_this_sim += 1
                        results['models_killed'] += 1
                    break

        results['damage_per_simulation'].append(sim_damage)
        results['models_killed_per_simulation'].append(models_killed_this_sim)

    return results

def calculate_wound_requirement(strength: int, toughness: int) -> int:
    """Calculate the dice roll required to wound based on S vs T"""
    if strength >= toughness * 2:
        return 2
    elif strength > toughness:
        return 3
    elif strength == toughness:
        return 4
    elif strength < toughness and strength * 2 > toughness:
        return 5
    else:  # strength * 2 <= toughness
        return 6

def display_unit_panel(unit_data: Dict, title: str):
    """Display detailed unit information panel"""
    st.subheader(f"📋 {title}")

    if not unit_data or not unit_data.get('profiles'):
        st.warning("No unit data available")
        return

    # Display unit profile
    profile = unit_data['profiles'][0]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Movement", profile.get('M', '-'))
        st.metric("Toughness", profile.get('T', '-'))
    with col2:
        st.metric("Save", profile.get('SV', '-'))
        st.metric("Wounds", profile.get('W', '-'))
    with col3:
        st.metric("Leadership", profile.get('LD', '-'))
        st.metric("OC", profile.get('OC', '-'))
    with col4:
        if profile.get('Invuln'):
            st.metric("Invuln Save", profile.get('Invuln', '-'))

    # Display weapons
    if unit_data['weapons']:
        st.write("**Weapons:**")
        weapons_df = pd.DataFrame(unit_data['weapons'])
        st.dataframe(weapons_df, use_container_width=True, hide_index=True)

    # Display abilities
    if unit_data['abilities']:
        with st.expander("🎯 Abilities"):
            for ability in unit_data['abilities']:
                st.write(f"**{ability['name']}**")
                if ability['description']:
                    st.caption(ability['description'])

    # Display keywords
    if unit_data['keywords']:
        with st.expander("🏷️ Keywords"):
            st.write(", ".join(unit_data['keywords']))

    # Display costs
    if unit_data['costs']:
        st.write("**Costs:**", " | ".join([f"{k}: {v}" for k, v in unit_data['costs'].items()]))

def main():
    st.title("⚔️ Warhammer 40k Combat Simulator")
    st.markdown("Select any armies and simulate combat with statistical analysis")

    # Discover all available catalogues
    available_catalogues = discover_catalogues()

    if not available_catalogues:
        st.error("No catalogue files (.cat) found in the repository!")
        return

    # Sidebar - Army selection FIRST
    with st.sidebar:
        st.header("🎖️ Army Selection")

        # Army 1 selection
        army1_names = [cat['display_name'] for cat in available_catalogues]
        default_army1 = "Chaos - Death Guard" if "Chaos - Death Guard" in army1_names else army1_names[0]
        selected_army1 = st.selectbox(
            "Army 1 (Attacker)",
            options=army1_names,
            index=army1_names.index(default_army1) if default_army1 in army1_names else 0,
            key="army1_selector"
        )

        # Army 2 selection
        default_army2 = "Necrons" if "Necrons" in army1_names else army1_names[1] if len(army1_names) > 1 else army1_names[0]
        selected_army2 = st.selectbox(
            "Army 2 (Defender)",
            options=army1_names,
            index=army1_names.index(default_army2) if default_army2 in army1_names else 0,
            key="army2_selector"
        )

        st.divider()

    # Get file paths for selected armies
    army1_cat = next(cat for cat in available_catalogues if cat['display_name'] == selected_army1)
    army2_cat = next(cat for cat in available_catalogues if cat['display_name'] == selected_army2)

    # Parse catalogues
    try:
        army1_root, army1_ns, army1_info = parse_catalogue(army1_cat['file_path'])
        army2_root, army2_ns, army2_info = parse_catalogue(army2_cat['file_path'])
    except Exception as e:
        st.error(f"Error loading catalogues: {e}")
        st.exception(e)
        return

    # Extract detachments
    army1_detachments = extract_detachments(army1_root, army1_ns, selected_army1)
    army2_detachments = extract_detachments(army2_root, army2_ns, selected_army2)

    # Sidebar continued - Settings
    with st.sidebar:
        st.header("⚙️ Simulation Settings")
        num_simulations = st.slider("Number of Simulations", 1, 40000, 1000, 100)

        st.divider()
        st.subheader("📊 Squad Sizes")
        attacker_squad_size = st.number_input("Attacker Squad Size", min_value=1, max_value=20, value=1, step=1)
        defender_squad_size = st.number_input("Defender Squad Size", min_value=1, max_value=20, value=1, step=1)

        st.divider()
        st.subheader("🎖️ Detachments")

        # Army 1 (Attacker) detachment
        army1_detachment_names = ["None"] + [d['name'] for d in army1_detachments]
        selected_army1_detachment = st.selectbox(
            f"{selected_army1} Detachment",
            options=army1_detachment_names,
            help="Select detachment for attacker army-wide bonuses",
            key="army1_detachment"
        )

        if selected_army1_detachment != "None":
            det = next(d for d in army1_detachments if d['name'] == selected_army1_detachment)
            with st.expander(f"📜 {selected_army1_detachment} Rules"):
                for rule in det['rules']:
                    st.write(f"**{rule['name']}**")
                    st.caption(rule['description'][:200] + "..." if len(rule['description']) > 200 else rule['description'])

        # Army 2 (Defender) detachment
        army2_detachment_names = ["None"] + [d['name'] for d in army2_detachments]
        selected_army2_detachment = st.selectbox(
            f"{selected_army2} Detachment",
            options=army2_detachment_names,
            help="Select detachment for defender army-wide bonuses",
            key="army2_detachment"
        )

        if selected_army2_detachment != "None":
            det = next(d for d in army2_detachments if d['name'] == selected_army2_detachment)
            with st.expander(f"📜 {selected_army2_detachment} Rules"):
                for rule in det['rules']:
                    st.write(f"**{rule['name']}**")
                    st.caption(rule['description'][:200] + "..." if len(rule['description']) > 200 else rule['description'])

        st.divider()
        st.subheader("🎯 Manual Combat Modifiers")
        st.caption("These stack with detachment bonuses")

        with st.expander("Hit Roll Modifiers"):
            hit_modifier = st.slider("Hit Modifier", -3, 3, 0, help="+1 = easier to hit, -1 = harder to hit")
            lethal_hits = st.checkbox("Lethal Hits", help="Critical hits auto-wound")

        with st.expander("Wound Roll Modifiers"):
            wound_modifier = st.slider("Wound Modifier", -3, 3, 0, help="+1 = easier to wound, -1 = harder to wound")
            devastating_wounds = st.checkbox("Devastating Wounds", help="Critical wounds ignore saves")

        with st.expander("Save Roll Modifiers"):
            save_modifier = st.slider("Save Modifier", -3, 3, 0, help="+1 = better save, -1 = worse save")

        with st.expander("Damage & AP Modifiers"):
            damage_modifier = st.slider("Damage Modifier", -3, 3, 0, help="+1 damage per hit")
            ap_modifier = st.slider("AP Modifier", -3, 3, 0, help="+1 = more AP, -1 = less AP")

        with st.expander("Defensive Abilities"):
            fnp_enabled = st.checkbox("Feel No Pain")
            fnp_value = st.selectbox("FNP Roll", [6, 5, 4, 3, 2], index=1, disabled=not fnp_enabled)

        st.divider()
        st.caption(f"{selected_army1}: Rev {army1_info['revision']}")
        st.caption(f"{selected_army2}: Rev {army2_info['revision']}")

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["⚔️ Combat Simulator", "🎯 Unit Comparison", "📊 Benchmark Results"])

    with tab1:
        st.header("Combat Simulator")
        st.markdown(f"Simulate attacks from **{selected_army1}** units against **{selected_army2}** units")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"⚔️ Attacker ({selected_army1})")
            army1_units_sim = get_all_units(army1_root, army1_ns, selected_army1)
            st.caption(f"Available units: {len(army1_units_sim)}")

            if len(army1_units_sim) > 0:
                attacker_name = st.selectbox(
                    "Select attacking unit",
                    options=army1_units_sim['name'].tolist(),
                    key="attacker"
                )

                attacker_data = extract_unit_details(army1_root, army1_ns, attacker_name)
                display_unit_panel(attacker_data, attacker_name)
            else:
                st.error(f"No {selected_army1} units loaded")

        with col2:
            st.subheader(f"🛡️ Defender ({selected_army2})")
            army2_units_sim = get_all_units(army2_root, army2_ns, selected_army2)
            st.caption(f"Available units: {len(army2_units_sim)}")

            if len(army2_units_sim) > 0:
                defender_name = st.selectbox(
                    "Select defending unit",
                    options=army2_units_sim['name'].tolist(),
                    key="defender"
                )

                defender_data = extract_unit_details(army2_root, army2_ns, defender_name)
                display_unit_panel(defender_data, defender_name)
            else:
                st.error(f"No {selected_army2} units loaded")

        st.divider()

        # Weapon selection
        if attacker_data['weapons']:
            st.subheader("⚔️ Select Weapon")
            weapon_names = [w['name'] for w in attacker_data['weapons']]
            selected_weapon_name = st.selectbox("Attacker's weapon", weapon_names)

            selected_weapon = next(w for w in attacker_data['weapons'] if w['name'] == selected_weapon_name)

            # Display weapon stats
            wcol1, wcol2, wcol3, wcol4, wcol5, wcol6 = st.columns(6)
            with wcol1:
                st.metric("Range", selected_weapon.get('Range', '-'))
            with wcol2:
                st.metric("Attacks", selected_weapon.get('A', '-'))
            with wcol3:
                st.metric("Skill", selected_weapon.get('BS', selected_weapon.get('WS', '-')))
            with wcol4:
                st.metric("Strength", selected_weapon.get('S', '-'))
            with wcol5:
                st.metric("AP", selected_weapon.get('AP', '-'))
            with wcol6:
                st.metric("Damage", selected_weapon.get('D', '-'))

            st.divider()

            # Run simulation
            if st.button("🎲 Run Combat Simulation", type="primary", use_container_width=True):
                # Build modifiers dictionary
                modifiers = {
                    'hit_modifier': hit_modifier,
                    'wound_modifier': wound_modifier,
                    'save_modifier': save_modifier,
                    'damage_modifier': damage_modifier,
                    'ap_modifier': ap_modifier,
                    'lethal_hits': lethal_hits,
                    'devastating_wounds': devastating_wounds,
                    'feel_no_pain': fnp_value if fnp_enabled else 0
                }

                with st.spinner(f"Running {num_simulations:,} simulations..."):
                    results = simulate_attack_sequence(
                        selected_weapon,
                        attacker_data,
                        defender_data,
                        num_simulations,
                        attacker_squad_size,
                        defender_squad_size,
                        modifiers
                    )

                    st.success("Simulation complete!")

                    # Display results
                    st.header("📊 Simulation Results")

                    # Show configuration
                    config_col1, config_col2 = st.columns(2)
                    with config_col1:
                        st.info(f"**Attacker:** {attacker_name} ({attacker_squad_size} models)\n\n**Army:** {selected_army1}\n\n**Detachment:** {selected_army1_detachment}")
                    with config_col2:
                        st.info(f"**Defender:** {defender_name} ({defender_squad_size} models)\n\n**Army:** {selected_army2}\n\n**Detachment:** {selected_army2_detachment}")

                    # Summary metrics - First row
                    col1, col2, col3, col4 = st.columns(4)

                    avg_attacks = results['total_attacks'] / num_simulations
                    avg_hits = results['hits'] / num_simulations
                    avg_crit_hits = results['critical_hits'] / num_simulations
                    avg_wounds = results['wounds'] / num_simulations

                    with col1:
                        st.metric("Avg Attacks", f"{avg_attacks:.2f}")
                    with col2:
                        st.metric("Avg Hits", f"{avg_hits:.2f}",
                                 f"{(avg_hits/avg_attacks*100) if avg_attacks > 0 else 0:.1f}%")
                    with col3:
                        st.metric("Critical Hits", f"{avg_crit_hits:.2f}",
                                 f"{(avg_crit_hits/avg_hits*100) if avg_hits > 0 else 0:.1f}%")
                    with col4:
                        st.metric("Avg Wounds", f"{avg_wounds:.2f}",
                                 f"{(avg_wounds/avg_hits*100) if avg_hits > 0 else 0:.1f}%")

                    # Second row
                    col1, col2, col3, col4 = st.columns(4)

                    avg_crit_wounds = results['critical_wounds'] / num_simulations
                    avg_failed_saves = results['failed_saves'] / num_simulations
                    avg_mortal_wounds = results['mortal_wounds'] / num_simulations
                    avg_damage = results['total_damage'] / num_simulations

                    with col1:
                        st.metric("Critical Wounds", f"{avg_crit_wounds:.2f}",
                                 f"{(avg_crit_wounds/avg_wounds*100) if avg_wounds > 0 else 0:.1f}%")
                    with col2:
                        st.metric("Failed Saves", f"{avg_failed_saves:.2f}")
                    with col3:
                        st.metric("Mortal Wounds", f"{avg_mortal_wounds:.2f}")
                    with col4:
                        st.metric("Avg Total Damage", f"{avg_damage:.2f}")

                    # Third row - Models killed
                    col1, col2, col3 = st.columns(3)

                    avg_models_killed = results['models_killed'] / num_simulations
                    avg_fnp_saved = results['fnp_saved'] / num_simulations if fnp_enabled else 0
                    kill_percentage = (avg_models_killed / defender_squad_size * 100) if defender_squad_size > 0 else 0

                    with col1:
                        st.metric("⚰️ Avg Models Killed", f"{avg_models_killed:.2f}",
                                 f"{kill_percentage:.1f}% of squad")
                    with col2:
                        st.metric("Squad Wiped", f"{sum(1 for k in results['models_killed_per_simulation'] if k >= defender_squad_size) / num_simulations * 100:.1f}%")
                    with col3:
                        if fnp_enabled:
                            st.metric("FNP Damage Prevented", f"{avg_fnp_saved:.2f}")

                    # Distribution charts
                    chart_col1, chart_col2 = st.columns(2)

                    with chart_col1:
                        st.subheader("Damage Distribution")
                        damage_df = pd.DataFrame({
                            'Damage': results['damage_per_simulation']
                        })

                        fig_damage = px.histogram(
                            damage_df,
                            x='Damage',
                            nbins=min(50, max(results['damage_per_simulation']) + 1) if results['damage_per_simulation'] else 10,
                            title=f"Damage across {num_simulations:,} simulations",
                            labels={'Damage': 'Damage Dealt', 'count': 'Frequency'}
                        )
                        st.plotly_chart(fig_damage, use_container_width=True)

                    with chart_col2:
                        st.subheader("Models Killed Distribution")
                        models_df = pd.DataFrame({
                            'Models Killed': results['models_killed_per_simulation']
                        })

                        fig_models = px.histogram(
                            models_df,
                            x='Models Killed',
                            nbins=min(defender_squad_size + 1, 30),
                            title=f"Models killed across {num_simulations:,} simulations",
                            labels={'Models Killed': 'Models Killed', 'count': 'Frequency'}
                        )
                        # Add vertical line at defender_squad_size
                        fig_models.add_vline(x=defender_squad_size, line_dash="dash", line_color="red",
                                           annotation_text="Full Squad", annotation_position="top right")
                        st.plotly_chart(fig_models, use_container_width=True)

                    # Statistical summary
                    st.subheader("Statistical Analysis")

                    stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)

                    damage_array = np.array(results['damage_per_simulation'])
                    models_array = np.array(results['models_killed_per_simulation'])

                    with stats_col1:
                        st.metric("Damage Range", f"{int(damage_array.min())}-{int(damage_array.max())}")
                    with stats_col2:
                        st.metric("Median Damage", f"{np.median(damage_array):.2f}")
                    with stats_col3:
                        st.metric("Models Range", f"{int(models_array.min())}-{int(models_array.max())}")
                    with stats_col4:
                        st.metric("Median Models Killed", f"{np.median(models_array):.2f}")

                    # Store results in session state for benchmark tab
                    if 'benchmark_results' not in st.session_state:
                        st.session_state.benchmark_results = []

                    st.session_state.benchmark_results.append({
                        'attacker': attacker_name,
                        'attacker_army': selected_army1,
                        'attacker_size': attacker_squad_size,
                        'attacker_detachment': selected_army1_detachment,
                        'defender': defender_name,
                        'defender_army': selected_army2,
                        'defender_size': defender_squad_size,
                        'defender_detachment': selected_army2_detachment,
                        'weapon': selected_weapon_name,
                        'simulations': num_simulations,
                        'avg_damage': avg_damage,
                        'avg_models_killed': avg_models_killed,
                        'squad_wipe_chance': sum(1 for k in results['models_killed_per_simulation'] if k >= defender_squad_size) / num_simulations * 100,
                        'modifiers': modifiers,
                        'results': results
                    })
        else:
            st.warning("Selected unit has no weapons")

    with tab2:
        st.header("Unit Comparison")
        st.markdown(f"Compare units from **{selected_army1}** and **{selected_army2}** side-by-side")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader(f"{selected_army1} Units")
            army1_units_browse = get_all_units(army1_root, army1_ns, selected_army1)

            if len(army1_units_browse) > 0:
                search_army1_browse = st.text_input(f"Search {selected_army1} units", key="search_army1_browse")
                filtered_army1_browse = army1_units_browse[army1_units_browse['name'].str.contains(search_army1_browse, case=False, na=False)] if search_army1_browse else army1_units_browse

                selected_unit_army1_browse = st.selectbox(
                    f"Select {selected_army1} Unit",
                    options=filtered_army1_browse['name'].tolist(),
                    key="browser_army1"
                )

                if selected_unit_army1_browse:
                    unit_details = extract_unit_details(army1_root, army1_ns, selected_unit_army1_browse)
                    display_unit_panel(unit_details, selected_unit_army1_browse)
            else:
                st.error(f"No {selected_army1} units found in catalogue")

        with col2:
            st.subheader(f"{selected_army2} Units")
            army2_units_browse = get_all_units(army2_root, army2_ns, selected_army2)

            if len(army2_units_browse) > 0:
                search_army2_browse = st.text_input(f"Search {selected_army2} units", key="search_army2_browse")
                filtered_army2_browse = army2_units_browse[army2_units_browse['name'].str.contains(search_army2_browse, case=False, na=False)] if search_army2_browse else army2_units_browse

                selected_unit_army2_browse = st.selectbox(
                    f"Select {selected_army2} Unit",
                    options=filtered_army2_browse['name'].tolist(),
                    key="browser_army2"
                )

                if selected_unit_army2_browse:
                    unit_details = extract_unit_details(army2_root, army2_ns, selected_unit_army2_browse)
                    display_unit_panel(unit_details, selected_unit_army2_browse)
            else:
                st.error(f"No {selected_army2} units found in catalogue")

    with tab3:
        st.header("📊 Benchmark Results")
        st.markdown("Compare multiple simulation results")

        if 'benchmark_results' in st.session_state and st.session_state.benchmark_results:
            # Create comparison dataframe
            comparison_data = []
            for result in st.session_state.benchmark_results:
                comparison_data.append({
                    'Attacker Army': result.get('attacker_army', 'Unknown'),
                    'Attacker': result['attacker'],
                    'Weapon': result['weapon'],
                    'Defender Army': result.get('defender_army', 'Unknown'),
                    'Defender': result['defender'],
                    'Avg Damage': f"{result['avg_damage']:.2f}",
                    'Avg Models Killed': f"{result['avg_models_killed']:.2f}",
                    'Squad Wipe %': f"{result['squad_wipe_chance']:.1f}%",
                    'Simulations': result['simulations']
                })

            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)

            # Comparison chart
            if len(st.session_state.benchmark_results) > 1:
                st.subheader("Damage Comparison")

                chart_data = pd.DataFrame({
                    'Matchup': [f"{r['attacker']} ({r.get('attacker_army', 'Unknown')}) vs {r['defender']} ({r.get('defender_army', 'Unknown')})" for r in st.session_state.benchmark_results],
                    'Average Damage': [r['avg_damage'] for r in st.session_state.benchmark_results]
                })

                fig = px.bar(
                    chart_data,
                    x='Matchup',
                    y='Average Damage',
                    title='Average Damage by Matchup'
                )
                st.plotly_chart(fig, use_container_width=True)

            if st.button("Clear Benchmark History"):
                st.session_state.benchmark_results = []
                st.rerun()
        else:
            st.info("No benchmark results yet. Run simulations in the Combat Simulator tab to see results here.")

if __name__ == "__main__":
    main()
