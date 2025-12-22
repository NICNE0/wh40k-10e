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
    """
    Get all units from catalogue including imported units from linked catalogues.

    For Astartes armies, this includes both chapter-specific units and shared Space Marine units.
    """
    units = []
    unit_ids = set()  # Track IDs to avoid duplicates

    # Find the root-level entryLinks element (direct units)
    entry_links_elem = _root.find('cat:entryLinks', _ns)

    if entry_links_elem is not None:
        # Get only direct children of entryLinks
        for entry in entry_links_elem.findall('cat:entryLink', _ns):
            if entry.get('type') == 'selectionEntry' and entry.get('hidden', 'false') == 'false':
                unit_id = entry.get('id')
                if unit_id not in unit_ids:
                    units.append({
                        'name': entry.get('name'),
                        'id': unit_id,
                        'targetId': entry.get('targetId'),
                        'source': 'direct'
                    })
                    unit_ids.add(unit_id)

    # Check for imported catalogue units (e.g., Space Marines importing shared Astartes units)
    # This handles the case where Dark Angels, Blood Angels, etc. import Space Marines catalogue
    for cat_link in _root.findall('cat:catalogueLinks/cat:catalogueLink', _ns):
        import_root = cat_link.get('importRootEntries', 'false')
        if import_root == 'true':
            # This catalogue imports units from another catalogue
            # We need to parse the linked catalogue
            linked_cat_name = cat_link.get('name')
            linked_cat_id = cat_link.get('targetId')

            # Try to find and parse the linked catalogue file
            # Common pattern: "Imperium - Space Marines" -> "Imperium - Space Marines.cat"
            try:
                from pathlib import Path
                base_path = Path(__file__).parent

                # Try exact match first
                linked_file = base_path / f"{linked_cat_name}.cat"

                if linked_file.exists():
                    linked_tree = ET.parse(str(linked_file))
                    linked_root = linked_tree.getroot()

                    # Get units from linked catalogue
                    linked_entry_links = linked_root.find('cat:entryLinks', _ns)
                    if linked_entry_links is not None:
                        for entry in linked_entry_links.findall('cat:entryLink', _ns):
                            if entry.get('type') == 'selectionEntry' and entry.get('hidden', 'false') == 'false':
                                unit_id = entry.get('id')
                                if unit_id not in unit_ids:
                                    units.append({
                                        'name': entry.get('name'),
                                        'id': unit_id,
                                        'targetId': entry.get('targetId'),
                                        'source': f'imported from {linked_cat_name}'
                                    })
                                    unit_ids.add(unit_id)
            except Exception as e:
                # Silently skip if we can't load the linked catalogue
                pass

    return pd.DataFrame(units)

@st.cache_data
def extract_detachments(_root, _ns, catalogue_name: str) -> List[Dict]:
    """
    Extract detachment information and their rules.

    Detachments can be in multiple locations:
    1. Direct selectionEntry with selectionEntryGroup children
    2. sharedSelectionEntryGroups (for Space Marines and chapters)
    3. Imported from linked catalogues
    """
    detachments = []
    detachment_ids = set()  # Track IDs to avoid duplicates

    # Method 1: Find detachments in sharedSelectionEntryGroups (primary method for Space Marines)
    for group in _root.findall('.//cat:sharedSelectionEntryGroups/cat:selectionEntryGroup', _ns):
        group_name = group.get('name', '').lower()
        if 'detachment' in group_name:
            # Found a detachment group
            for detachment in group.findall('cat:selectionEntries/cat:selectionEntry', _ns):
                det_name = detachment.get('name')
                det_id = detachment.get('id')

                if det_name and det_name.lower() != 'none' and det_id not in detachment_ids:
                    det_data = {
                        'name': det_name,
                        'id': det_id,
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
                    detachment_ids.add(det_id)

    # Method 2: Original method - Find the Detachment selectionEntry (fallback)
    for entry in _root.findall('.//cat:selectionEntry[@name="Detachment"]', _ns):
        # Find all detachment options within the selectionEntryGroup
        for group in entry.findall('.//cat:selectionEntryGroup', _ns):
            for detachment in group.findall('.//cat:selectionEntry', _ns):
                det_name = detachment.get('name')
                det_id = detachment.get('id')

                if det_name and det_name.lower() != 'none' and det_id not in detachment_ids:
                    det_data = {
                        'name': det_name,
                        'id': det_id,
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
                    detachment_ids.add(det_id)

    # Method 3: Import detachments from linked catalogues (for chapters importing from Space Marines)
    for cat_link in _root.findall('cat:catalogueLinks/cat:catalogueLink', _ns):
        import_root = cat_link.get('importRootEntries', 'false')
        if import_root == 'true':
            linked_cat_name = cat_link.get('name')

            try:
                from pathlib import Path
                base_path = Path(__file__).parent
                linked_file = base_path / f"{linked_cat_name}.cat"

                if linked_file.exists():
                    linked_tree = ET.parse(str(linked_file))
                    linked_root = linked_tree.getroot()

                    # Get detachments from linked catalogue using both methods
                    # Method 1: sharedSelectionEntryGroups
                    for group in linked_root.findall('.//cat:sharedSelectionEntryGroups/cat:selectionEntryGroup', _ns):
                        group_name = group.get('name', '').lower()
                        if 'detachment' in group_name:
                            for detachment in group.findall('cat:selectionEntries/cat:selectionEntry', _ns):
                                det_name = detachment.get('name')
                                det_id = detachment.get('id')

                                if det_name and det_name.lower() != 'none' and det_id not in detachment_ids:
                                    det_data = {
                                        'name': det_name,
                                        'id': det_id,
                                        'rules': []
                                    }

                                    for rule in detachment.findall('.//cat:rule', _ns):
                                        rule_name = rule.get('name')
                                        desc_elem = rule.find('cat:description', _ns)
                                        description = desc_elem.text if desc_elem is not None and desc_elem.text else ''

                                        det_data['rules'].append({
                                            'name': rule_name,
                                            'description': description
                                        })

                                    detachments.append(det_data)
                                    detachment_ids.add(det_id)
            except Exception:
                # Silently skip if we can't load the linked catalogue
                pass

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

def parse_weapon_abilities(abilities_text: str) -> Dict[str, any]:
    """Parse weapon abilities string and extract special rules"""
    import re

    abilities = {
        'lethal_hits': False,
        'devastating_wounds': False,
        'sustained_hits': 0,  # Number (e.g., Sustained Hits 1, 2, etc.)
        'anti': {},  # e.g., {'infantry': 4} means Anti-Infantry 4+
        'melta': 0,  # Melta X
        'blast': False,
        'torrent': False,
        'twin_linked': False,
        'rapid_fire': 0,
        'assault': False,
        'heavy': False,
        'pistol': False,
        'ignores_cover': False,
        'precision': False,
        'extra_attacks': False,
        'hazardous': False,
        'indirect_fire': False,
        'lance': False,
        'one_shot': False,
        'psychic': False,
        # Re-rolls
        'reroll_hits': '',  # 'all', 'ones', 'failed', or conditional
        'reroll_wounds': '',  # 'all', 'ones', 'failed', or conditional
        'reroll_damage': False,
        # Modifiers
        'hit_modifier': 0,
        'wound_modifier': 0,
        'strength_modifier': 0,
        'ap_modifier': 0,
        'damage_modifier': 0,
        # Conditional modifiers
        'conditional_hit': [],  # List of {condition: str, modifier: int}
        'conditional_wound': [],
        'conditional_strength': [],
        'conditional_ap': [],
        'conditional_damage': [],
        # Other
        'exploding_6s': False,  # Each hit roll of 6 generates additional hit
        'mortal_wounds_on_6': 0,  # Generate X mortal wounds on hit/wound roll of 6
        'auto_wound_on_6': False,
        'raw_text': abilities_text
    }

    if not abilities_text:
        return abilities

    lower_text = abilities_text.lower()

    # Lethal Hits
    if 'lethal hits' in lower_text:
        abilities['lethal_hits'] = True

    # Devastating Wounds
    if 'devastating wounds' in lower_text:
        abilities['devastating_wounds'] = True

    # Sustained Hits (with number)
    if 'sustained hits' in lower_text:
        match = re.search(r'sustained hits\s+(\d+)', lower_text)
        if match:
            abilities['sustained_hits'] = int(match.group(1))
        else:
            abilities['sustained_hits'] = 1  # Default

    # Anti-X
    if 'anti-' in lower_text:
        matches = re.finditer(r'anti-(\w+)\s+(\d+)\+', lower_text)
        for match in matches:
            keyword = match.group(1)
            value = int(match.group(2))
            abilities['anti'][keyword] = value

    # Melta
    if 'melta' in lower_text:
        match = re.search(r'melta\s+(\d+)', lower_text)
        if match:
            abilities['melta'] = int(match.group(1))
        else:
            abilities['melta'] = 2  # Default Melta 2

    # Re-roll hits
    if 're-roll hit' in lower_text or 'reroll hit' in lower_text:
        if 'all hit' in lower_text or 're-roll all hit' in lower_text:
            abilities['reroll_hits'] = 'all'
        elif 'hit rolls of 1' in lower_text or 'hit roll of 1' in lower_text:
            abilities['reroll_hits'] = 'ones'
        elif 'failed hit' in lower_text:
            abilities['reroll_hits'] = 'failed'
        else:
            abilities['reroll_hits'] = 'conditional'

    # Re-roll wounds
    if 're-roll wound' in lower_text or 'reroll wound' in lower_text:
        if 'all wound' in lower_text or 're-roll all wound' in lower_text:
            abilities['reroll_wounds'] = 'all'
        elif 'wound rolls of 1' in lower_text or 'wound roll of 1' in lower_text:
            abilities['reroll_wounds'] = 'ones'
        elif 'failed wound' in lower_text:
            abilities['reroll_wounds'] = 'failed'
        else:
            abilities['reroll_wounds'] = 'conditional'

    # Twin-Linked (re-roll wounds)
    if 'twin-linked' in lower_text or 'twin linked' in lower_text:
        abilities['twin_linked'] = True
        if not abilities['reroll_wounds']:
            abilities['reroll_wounds'] = 'failed'

    # Re-roll damage
    if 're-roll damage' in lower_text or 'reroll damage' in lower_text:
        abilities['reroll_damage'] = True

    # Direct modifiers
    # +1 to hit
    if '+1 to hit' in lower_text or 'add 1 to hit' in lower_text:
        abilities['hit_modifier'] = 1
    elif '-1 to hit' in lower_text or 'subtract 1 from hit' in lower_text:
        abilities['hit_modifier'] = -1

    # +1 to wound
    if '+1 to wound' in lower_text or 'add 1 to wound' in lower_text:
        abilities['wound_modifier'] = 1
    elif '-1 to wound' in lower_text or 'subtract 1 from wound' in lower_text:
        abilities['wound_modifier'] = -1

    # Strength modifiers
    match = re.search(r'strength is (\d+)', lower_text)
    if match:
        # This is an absolute value, handle separately
        pass

    # AP modifiers
    match = re.search(r'improve.*armour penetration.*by (\d+)', lower_text)
    if match:
        abilities['ap_modifier'] = int(match.group(1))
    elif 'ap-' in lower_text:
        # Already in base stats
        pass

    # Damage modifiers
    match = re.search(r'\+(\d+) damage', lower_text)
    if match:
        abilities['damage_modifier'] = int(match.group(1))

    # Auto-wound on 6s
    if 'wound roll of 6' in lower_text and 'automatically wounds' in lower_text:
        abilities['auto_wound_on_6'] = True

    # Mortal wounds on 6
    match = re.search(r'(\d+) mortal wounds?.*(on|in addition)', lower_text)
    if match:
        abilities['mortal_wounds_on_6'] = int(match.group(1))

    # Conditional modifiers - these are complex, store as text for now
    # Example: "+1 to hit against Monster or Vehicle"
    match = re.search(r'\+(\d+) to hit.*against ([\w\s,]+)', lower_text)
    if match:
        abilities['conditional_hit'].append({
            'modifier': int(match.group(1)),
            'condition': match.group(2).strip()
        })

    match = re.search(r'\+(\d+) to wound.*against ([\w\s,]+)', lower_text)
    if match:
        abilities['conditional_wound'].append({
            'modifier': int(match.group(1)),
            'condition': match.group(2).strip()
        })

    # Simple boolean abilities
    if 'blast' in lower_text:
        abilities['blast'] = True
    if 'torrent' in lower_text:
        abilities['torrent'] = True
    if 'ignores cover' in lower_text:
        abilities['ignores_cover'] = True
    if 'precision' in lower_text:
        abilities['precision'] = True
    if 'extra attacks' in lower_text:
        abilities['extra_attacks'] = True
    if 'hazardous' in lower_text:
        abilities['hazardous'] = True
    if 'indirect fire' in lower_text:
        abilities['indirect_fire'] = True
    if 'lance' in lower_text:
        abilities['lance'] = True
    if '[assault]' in lower_text or 'assault' in lower_text:
        abilities['assault'] = True
    if '[heavy]' in lower_text or 'heavy' in lower_text:
        abilities['heavy'] = True
    if '[pistol' in lower_text:
        abilities['pistol'] = True

    # Rapid Fire
    if 'rapid fire' in lower_text:
        match = re.search(r'rapid fire\s+(\d+)', lower_text)
        if match:
            abilities['rapid_fire'] = int(match.group(1))

    return abilities

def parse_unit_abilities(unit_data: Dict) -> Dict[str, any]:
    """Parse unit abilities and extract special rules that affect combat"""
    import re

    abilities = {
        'feel_no_pain': 0,  # 0 = none, otherwise the roll needed
        'invuln_save': '',
        'stealth': False,
        'scouts': False,
        'leader': False,
        'deadly_demise': 0,
        'deep_strike': False,
        'fights_first': False,
        'lone_operative': False,
        'benefits_of_cover': False,
        # Re-rolls
        'reroll_hits': '',  # From unit abilities
        'reroll_wounds': '',
        'reroll_saves': '',  # 'all', 'ones', etc.
        'reroll_charges': False,
        # Modifiers
        'hit_modifier': 0,  # +1/-1 to hit when attacking
        'wound_modifier': 0,
        'save_modifier': 0,  # +1 to saves
        'charge_bonus': 0,
        # Defensive
        'minus_1_to_be_hit': False,  # Different from stealth
        'minus_1_to_be_wounded': False,
        'transhuman': False,  # Can't be wounded on better than 4+
        'halve_damage': False,
        # Offensive
        'extra_hits_on_6': False,
        'auto_wound_on_6': False,
        'mortal_wounds_on_6': 0,
        # Conditionals
        'conditional_modifiers': [],  # List of {type, modifier, condition}
        'raw_abilities': []
    }

    # Check profiles for invuln save
    if unit_data.get('profiles'):
        for profile in unit_data['profiles']:
            if 'Invuln' in profile:
                abilities['invuln_save'] = profile['Invuln']
                break

    # Parse ability descriptions
    for ability in unit_data.get('abilities', []):
        ability_name = ability.get('name', '')
        ability_desc = ability.get('description', '')
        ability_text = (ability_desc + ' ' + ability_name).lower()
        abilities['raw_abilities'].append(ability_name)

        # Feel No Pain
        if 'feel no pain' in ability_text:
            match = re.search(r'(\d+)\+', ability_text)
            if match:
                abilities['feel_no_pain'] = int(match.group(1))

        # Stealth / -1 to be hit
        if 'stealth' in ability_text:
            abilities['stealth'] = True
            abilities['minus_1_to_be_hit'] = True
        if 'subtract 1 from hit' in ability_text or '-1 to hit' in ability_text:
            if 'attack' in ability_text or 'targeting' in ability_text:
                abilities['minus_1_to_be_hit'] = True

        # -1 to be wounded
        if 'subtract 1 from wound' in ability_text or '-1 to wound' in ability_text:
            if 'against' in ability_text:
                abilities['minus_1_to_be_wounded'] = True

        # Transhuman
        if 'wound roll of 1-3' in ability_text or 'wounds on unmodified' in ability_text:
            if 'always fails' in ability_text or 'fail' in ability_text:
                abilities['transhuman'] = True

        # Halve damage
        if 'halve' in ability_text and 'damage' in ability_text:
            abilities['halve_damage'] = True
        if 'half damage' in ability_text or 'half of the damage' in ability_text:
            abilities['halve_damage'] = True

        # Re-roll hits (for attacker unit)
        if 're-roll hit' in ability_text or 'reroll hit' in ability_text:
            if 'all hit' in ability_text:
                abilities['reroll_hits'] = 'all'
            elif 'hit rolls of 1' in ability_text:
                abilities['reroll_hits'] = 'ones'
            elif 'failed hit' in ability_text:
                abilities['reroll_hits'] = 'failed'

        # Re-roll wounds
        if 're-roll wound' in ability_text or 'reroll wound' in ability_text:
            if 'all wound' in ability_text:
                abilities['reroll_wounds'] = 'all'
            elif 'wound rolls of 1' in ability_text:
                abilities['reroll_wounds'] = 'ones'
            elif 'failed wound' in ability_text:
                abilities['reroll_wounds'] = 'failed'

        # Re-roll saves
        if 're-roll sav' in ability_text or 'reroll sav' in ability_text:
            if 'all sav' in ability_text:
                abilities['reroll_saves'] = 'all'
            elif 'saving throw of 1' in ability_text or 'save of 1' in ability_text:
                abilities['reroll_saves'] = 'ones'
            elif 'failed sav' in ability_text:
                abilities['reroll_saves'] = 'failed'

        # Hit modifiers
        if '+1 to hit' in ability_text or 'add 1 to hit' in ability_text:
            if 'made by' in ability_text or 'when' in ability_text:
                abilities['hit_modifier'] = 1

        # Wound modifiers
        if '+1 to wound' in ability_text or 'add 1 to wound' in ability_text:
            if 'made by' in ability_text or 'when' in ability_text:
                abilities['wound_modifier'] = 1

        # Save modifiers
        if '+1 to.*sav' in ability_text or 'add 1.*sav' in ability_text:
            abilities['save_modifier'] = 1

        # Extra hits on 6s
        if 'hit roll of 6' in ability_text and ('additional hit' in ability_text or 'extra hit' in ability_text or '2 hits' in ability_text):
            abilities['extra_hits_on_6'] = True

        # Auto-wound on 6s
        if 'wound roll of 6' in ability_text and 'automatically wounds' in ability_text:
            abilities['auto_wound_on_6'] = True

        # Mortal wounds on 6s
        match = re.search(r'(\d+) mortal wound', ability_text)
        if match and ('6' in ability_text or 'critical' in ability_text):
            abilities['mortal_wounds_on_6'] = int(match.group(1))

        # Scouts
        if 'scouts' in ability_text:
            abilities['scouts'] = True

        # Leader
        if 'leader' in ability_text:
            abilities['leader'] = True

        # Deadly Demise
        if 'deadly demise' in ability_text:
            match = re.search(r'deadly demise\s+d(\d+)', ability_text)
            if match:
                abilities['deadly_demise'] = int(match.group(1))

        # Deep Strike
        if 'deep strike' in ability_text:
            abilities['deep_strike'] = True

        # Fights First
        if 'fights first' in ability_text:
            abilities['fights_first'] = True

        # Lone Operative
        if 'lone operative' in ability_text:
            abilities['lone_operative'] = True

        # Benefits of Cover
        if 'benefit' in ability_text and 'cover' in ability_text:
            abilities['benefits_of_cover'] = True

    return abilities

def parse_dice_value(value: str) -> int:
    """Parse dice notation like 'D6', '2D6', 'D3', etc."""
    if not value or value == '-':
        return 0

    value = value.strip().upper()

    # Handle D3 notation
    if 'D3' in value:
        parts = value.split('+')
        base = parts[0]
        modifier = int(parts[1]) if len(parts) > 1 else 0

        if base == 'D3':
            return np.random.randint(1, 4) + modifier
        else:
            # e.g., "2D3"
            num_dice = int(base.replace('D3', ''))
            return sum(np.random.randint(1, 4) for _ in range(num_dice)) + modifier

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
    Simulate attack sequence following Warhammer 40k 10th Edition rules:
    Hit -> Wound -> Save -> Damage -> Models Destroyed

    Supports:
    - Lethal Hits (critical hits auto-wound)
    - Sustained Hits (critical hits generate extra hits)
    - Devastating Wounds (critical wounds become mortal wounds)
    - Anti-X (improved wound rolls against keywords)
    - Melta (re-roll damage at half range)
    - Twin-Linked (re-roll wound rolls)
    - Torrent (auto-hit)
    - Invulnerable saves
    - Feel No Pain
    - Stealth (-1 to hit)
    - Manual modifiers (hit, wound, save, damage, AP)
    - Squad sizes and model tracking

    Returns statistics and detailed calculation logs
    """

    if modifiers is None:
        modifiers = {}

    results = {
        'total_attacks': 0,
        'hits': 0,
        'critical_hits': 0,
        'sustained_hits_generated': 0,
        'wounds': 0,
        'critical_wounds': 0,
        'failed_saves': 0,
        'mortal_wounds': 0,
        'fnp_saved': 0,
        'total_damage': 0,
        'models_killed': 0,
        'damage_per_simulation': [],
        'models_killed_per_simulation': [],
        'calculation_log': []  # Detailed math breakdown per simulation
    }

    # Parse weapon abilities
    weapon_abilities_text = attacker_weapon.get('Abilities', '')
    weapon_abilities = parse_weapon_abilities(weapon_abilities_text)

    # Parse unit abilities
    attacker_abilities = parse_unit_abilities(attacker_unit)
    defender_abilities = parse_unit_abilities(defender_unit)

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

    invuln = defender_abilities.get('invuln_save', defender_profile.get('Invuln', ''))

    wounds_raw = defender_profile.get('W', '1')
    if wounds_raw in ['N/A', '-', '']:
        wounds_per_model = 1
    else:
        try:
            wounds_per_model = int(wounds_raw)
        except ValueError:
            wounds_per_model = 1

    # Combine abilities with manual modifiers
    has_lethal_hits = weapon_abilities['lethal_hits'] or modifiers.get('lethal_hits', False)
    has_devastating_wounds = weapon_abilities['devastating_wounds'] or modifiers.get('devastating_wounds', False)
    sustained_hits = weapon_abilities['sustained_hits']
    has_twin_linked = weapon_abilities['twin_linked']
    has_torrent = weapon_abilities['torrent']
    has_auto_wound_on_6 = weapon_abilities['auto_wound_on_6'] or attacker_abilities.get('auto_wound_on_6', False)
    mortal_wounds_on_6 = max(weapon_abilities['mortal_wounds_on_6'], attacker_abilities.get('mortal_wounds_on_6', 0))
    extra_hits_on_6 = attacker_abilities.get('extra_hits_on_6', False)

    # Re-rolls - weapon takes priority, then unit ability
    reroll_hits = weapon_abilities['reroll_hits'] or attacker_abilities.get('reroll_hits', '')
    reroll_wounds = weapon_abilities['reroll_wounds'] or attacker_abilities.get('reroll_wounds', '')
    reroll_saves = defender_abilities.get('reroll_saves', '')

    # Feel No Pain - from unit ability or manual modifier
    fnp = defender_abilities.get('feel_no_pain', 0)
    if modifiers.get('feel_no_pain', 0) > 0:
        fnp = modifiers.get('feel_no_pain')

    # Defensive abilities
    minus_1_to_be_hit = defender_abilities.get('minus_1_to_be_hit', False)
    minus_1_to_be_wounded = defender_abilities.get('minus_1_to_be_wounded', False)
    transhuman = defender_abilities.get('transhuman', False)
    halve_damage = defender_abilities.get('halve_damage', False)

    # Stealth gives -1 to hit
    stealth_modifier = -1 if (defender_abilities.get('stealth', False) or minus_1_to_be_hit) else 0

    # Combine all modifiers from weapon, unit, and manual
    hit_modifier = modifiers.get('hit_modifier', 0) + stealth_modifier + weapon_abilities['hit_modifier'] + attacker_abilities.get('hit_modifier', 0)
    wound_modifier = modifiers.get('wound_modifier', 0) + weapon_abilities['wound_modifier'] + attacker_abilities.get('wound_modifier', 0)

    # -1 to be wounded applies to wound rolls against this unit
    if minus_1_to_be_wounded:
        wound_modifier -= 1

    save_modifier = modifiers.get('save_modifier', 0) + defender_abilities.get('save_modifier', 0)
    damage_modifier = modifiers.get('damage_modifier', 0) + weapon_abilities['damage_modifier']
    ap_modifier = modifiers.get('ap_modifier', 0) + weapon_abilities['ap_modifier']

    # Parse hit requirement (e.g., "3+" -> need 3 or higher)
    base_hit_requirement = int(skill_stat.replace('+', ''))
    hit_requirement = max(2, min(6, base_hit_requirement - hit_modifier))

    # Modified AP
    modified_ap = ap + ap_modifier

    # Get defender keywords for Anti-X checking
    defender_keywords = [kw.lower() for kw in defender_unit.get('keywords', [])]

    # Create initial log entry explaining setup
    setup_log = []
    setup_log.append(f"=== COMBAT SIMULATION SETUP ===")
    setup_log.append(f"Attacker: {attacker_unit.get('name', 'Unknown')} ({attacker_squad_size} models)")
    setup_log.append(f"Weapon: {attacker_weapon.get('name', 'Unknown')}")
    setup_log.append(f"  - Attacks: {attacks_stat} per model")
    setup_log.append(f"  - Skill: {skill_stat} (need {hit_requirement}+ to hit after modifiers)")
    setup_log.append(f"  - Strength: {strength}, AP: {ap} (modified: {modified_ap}), Damage: {damage_stat}")

    if weapon_abilities['raw_text']:
        setup_log.append(f"  - Abilities: {weapon_abilities['raw_text']}")

    active_weapon_abilities = []
    if has_lethal_hits:
        active_weapon_abilities.append("Lethal Hits")
    if has_devastating_wounds:
        active_weapon_abilities.append("Devastating Wounds")
    if sustained_hits > 0:
        active_weapon_abilities.append(f"Sustained Hits {sustained_hits}")
    if has_twin_linked:
        active_weapon_abilities.append("Twin-Linked")
    if has_torrent:
        active_weapon_abilities.append("Torrent")
    if has_auto_wound_on_6:
        active_weapon_abilities.append("Auto-wound on 6s")
    if mortal_wounds_on_6 > 0:
        active_weapon_abilities.append(f"{mortal_wounds_on_6} Mortal Wounds on 6s")
    if extra_hits_on_6:
        active_weapon_abilities.append("Extra Hits on 6s")
    if weapon_abilities['anti']:
        for keyword, value in weapon_abilities['anti'].items():
            active_weapon_abilities.append(f"Anti-{keyword.title()} {value}+")
    if reroll_hits:
        active_weapon_abilities.append(f"Re-roll {reroll_hits} hits")
    if reroll_wounds:
        active_weapon_abilities.append(f"Re-roll {reroll_wounds} wounds")
    if active_weapon_abilities:
        setup_log.append(f"  - Active Abilities: {', '.join(active_weapon_abilities)}")

    setup_log.append(f"\nDefender: {defender_unit.get('name', 'Unknown')} ({defender_squad_size} models)")
    setup_log.append(f"  - Toughness: {toughness}, Save: {save}+, Wounds: {wounds_per_model} per model")
    if invuln:
        setup_log.append(f"  - Invulnerable Save: {invuln}")
    if fnp > 0:
        setup_log.append(f"  - Feel No Pain: {fnp}+")
    if defender_abilities.get('stealth') or minus_1_to_be_hit:
        setup_log.append(f"  - Stealth/Cover (enemies get -1 to hit)")
    if transhuman:
        setup_log.append(f"  - Transhuman (cannot be wounded on better than 4+)")
    if halve_damage:
        setup_log.append(f"  - Halve Damage")
    if minus_1_to_be_wounded:
        setup_log.append(f"  - -1 to be wounded")
    if reroll_saves:
        setup_log.append(f"  - Re-roll {reroll_saves} saves")

    setup_log.append(f"\nModifiers Applied:")
    setup_log.append(f"  - Hit: {hit_modifier:+d}")
    setup_log.append(f"  - Wound: {wound_modifier:+d}")
    setup_log.append(f"  - Save: {save_modifier:+d}")
    setup_log.append(f"  - Damage: {damage_modifier:+d}")
    setup_log.append(f"  - AP: {ap_modifier:+d}")

    results['calculation_log'].append('\n'.join(setup_log))

    # Check if weapon has Anti-X that applies to this defender
    anti_wound_bonus = 0
    active_anti = None
    for keyword, value in weapon_abilities['anti'].items():
        if keyword in defender_keywords:
            anti_wound_bonus = value
            active_anti = keyword
            break

    # Run simulations
    for sim in range(num_simulations):
        sim_damage = 0
        models_killed_this_sim = 0
        sim_log = []

        # Log only first 3 simulations in detail
        log_this_sim = (sim < 3)

        if log_this_sim:
            sim_log.append(f"\n=== SIMULATION {sim + 1} ===")

        # Track defender's remaining wounds
        remaining_defender_wounds = [wounds_per_model] * defender_squad_size

        # 1. Determine number of attacks (total from all attacking models)
        num_attacks = 0
        for _ in range(attacker_squad_size):
            num_attacks += parse_dice_value(attacks_stat)
        results['total_attacks'] += num_attacks

        if log_this_sim:
            sim_log.append(f"ATTACKS: {attacker_squad_size} models × {attacks_stat} attacks = {num_attacks} total attacks")

        # 2. Roll to hit
        hits = 0
        critical_hits = 0
        extra_hits_generated = 0

        if has_torrent:
            # Torrent auto-hits
            hits = num_attacks
            if log_this_sim:
                sim_log.append(f"HIT PHASE: Torrent - all {num_attacks} attacks auto-hit")
        else:
            # Roll to hit with re-rolls if applicable
            for _ in range(num_attacks):
                roll = roll_d6()

                # Check if we should re-roll
                should_reroll = False
                if reroll_hits == 'all':
                    should_reroll = True
                elif reroll_hits == 'ones' and roll == 1:
                    should_reroll = True
                elif reroll_hits == 'failed' and roll < hit_requirement:
                    should_reroll = True

                if should_reroll:
                    roll = roll_d6()  # Re-roll

                # Check result
                if roll == 6:  # Critical hit
                    critical_hits += 1
                    hits += 1
                    results['critical_hits'] += 1

                    # Extra hits on 6s (e.g., some abilities generate additional hits)
                    if extra_hits_on_6:
                        hits += 1
                        extra_hits_generated += 1
                elif roll >= hit_requirement:
                    hits += 1

            if log_this_sim:
                sim_log.append(f"HIT PHASE: Need {hit_requirement}+ to hit")
                if reroll_hits:
                    sim_log.append(f"  Re-rolling {reroll_hits} hit rolls")
                sim_log.append(f"  Result: {hits} hits ({critical_hits} critical)")
                if extra_hits_generated > 0:
                    sim_log.append(f"  Extra hits on 6s: {extra_hits_generated}")

        results['hits'] += hits

        # Sustained Hits: Critical hits generate extra hits
        if sustained_hits > 0 and critical_hits > 0:
            extra_hits = critical_hits * sustained_hits
            hits += extra_hits
            results['sustained_hits_generated'] += extra_hits
            if log_this_sim:
                sim_log.append(f"  Sustained Hits {sustained_hits}: {critical_hits} crits generate {extra_hits} extra hits")
                sim_log.append(f"  Total hits after Sustained: {hits}")

        if hits == 0:
            results['damage_per_simulation'].append(0)
            results['models_killed_per_simulation'].append(0)
            if log_this_sim:
                sim_log.append(f"  No hits - simulation ends")
                results['calculation_log'].append('\n'.join(sim_log))
            continue

        # 3. Roll to wound (S vs T comparison)
        base_wound_requirement = calculate_wound_requirement(strength, toughness)

        # Anti-X: If active, improve wound requirement
        wound_requirement = base_wound_requirement
        if active_anti and anti_wound_bonus > 0:
            wound_requirement = min(wound_requirement, anti_wound_bonus)
            if log_this_sim:
                sim_log.append(f"WOUND PHASE: Anti-{active_anti.title()} {anti_wound_bonus}+ improves wound requirement from {base_wound_requirement}+ to {wound_requirement}+")

        wound_requirement = max(2, min(6, wound_requirement - wound_modifier))

        if log_this_sim:
            sim_log.append(f"WOUND PHASE: S{strength} vs T{toughness} = need {base_wound_requirement}+ (modified to {wound_requirement}+)")

        wounds = 0
        critical_wounds = 0
        mortal_wounds_this_phase = 0
        mw_from_6s = 0

        # Transhuman: Cannot wound on better than 4+ (unmodified)
        effective_wound_requirement = wound_requirement
        if transhuman:
            effective_wound_requirement = max(4, base_wound_requirement)
            if log_this_sim:
                sim_log.append(f"  Transhuman: Minimum wound roll is 4+ (unmodified)")

        # Lethal Hits: Critical hits auto-wound
        if has_lethal_hits:
            lethal_wounds = critical_hits
            wounds += lethal_wounds
            critical_wounds += lethal_wounds
            results['critical_wounds'] += lethal_wounds

            if log_this_sim:
                sim_log.append(f"  Lethal Hits: {critical_hits} critical hits auto-wound")

            # Roll to wound for non-critical hits
            normal_hits = hits - critical_hits
            for _ in range(normal_hits):
                roll = roll_d6()

                # Check for re-rolls
                should_reroll_wound = False
                if reroll_wounds == 'all':
                    should_reroll_wound = True
                elif reroll_wounds == 'ones' and roll == 1:
                    should_reroll_wound = True
                elif reroll_wounds == 'failed' and roll < effective_wound_requirement:
                    should_reroll_wound = True

                if should_reroll_wound:
                    roll = roll_d6()

                # Check result
                if roll == 6:
                    critical_wounds += 1
                    wounds += 1
                    results['critical_wounds'] += 1

                    # Auto-wound on 6s
                    if has_auto_wound_on_6:
                        # Already wounds, no need to check requirement
                        pass

                    # Mortal wounds on 6s
                    if mortal_wounds_on_6 > 0:
                        mw_from_6s += mortal_wounds_on_6
                elif roll >= effective_wound_requirement:
                    wounds += 1

            if log_this_sim:
                sim_log.append(f"  Non-critical hits ({normal_hits}): {wounds - lethal_wounds} wounds ({critical_wounds - lethal_wounds} critical)")
                if reroll_wounds:
                    sim_log.append(f"  Re-rolling {reroll_wounds} wound rolls")
                if mw_from_6s > 0:
                    sim_log.append(f"  Generated {mw_from_6s} mortal wounds from 6s")
        else:
            # Standard wound rolls with re-rolls
            for _ in range(hits):
                roll = roll_d6()

                # Check for re-rolls (twin-linked or other abilities)
                should_reroll_wound = False
                if has_twin_linked or reroll_wounds == 'all':
                    should_reroll_wound = True
                elif reroll_wounds == 'ones' and roll == 1:
                    should_reroll_wound = True
                elif reroll_wounds == 'failed' and roll < effective_wound_requirement:
                    should_reroll_wound = True

                if should_reroll_wound:
                    roll = roll_d6()

                # Check result
                if roll == 6:
                    critical_wounds += 1
                    wounds += 1
                    results['critical_wounds'] += 1

                    # Auto-wound on 6s always wounds
                    if has_auto_wound_on_6:
                        # Already counted
                        pass

                    # Mortal wounds on 6s
                    if mortal_wounds_on_6 > 0:
                        mw_from_6s += mortal_wounds_on_6
                elif roll >= effective_wound_requirement or (has_auto_wound_on_6 and roll == 6):
                    wounds += 1

            if log_this_sim:
                if has_twin_linked or reroll_wounds:
                    sim_log.append(f"  Re-rolling {reroll_wounds if reroll_wounds else 'failed (Twin-Linked)'} wound rolls")
                if mw_from_6s > 0:
                    sim_log.append(f"  Generated {mw_from_6s} mortal wounds from 6s")

        # Add mortal wounds from 6s to phase total
        mortal_wounds_this_phase += mw_from_6s

        if log_this_sim:
            sim_log.append(f"  Result: {wounds} wounds ({critical_wounds} critical)")

        results['wounds'] += wounds

        if wounds == 0:
            results['damage_per_simulation'].append(0)
            results['models_killed_per_simulation'].append(0)
            if log_this_sim:
                sim_log.append(f"  No wounds - simulation ends")
                results['calculation_log'].append('\n'.join(sim_log))
            continue

        # Devastating Wounds: Critical wounds become mortal wounds (skip saves)
        normal_wounds = wounds
        if has_devastating_wounds and critical_wounds > 0:
            mortal_wounds_this_phase = critical_wounds
            normal_wounds = wounds - critical_wounds
            results['mortal_wounds'] += mortal_wounds_this_phase

            if log_this_sim:
                sim_log.append(f"  Devastating Wounds: {critical_wounds} critical wounds become mortal wounds (skip saves)")

        # 4. Roll saves for normal wounds
        failed_saves = 0
        if normal_wounds > 0:
            modified_save = save - modified_ap + save_modifier

            # Check if invuln is better
            save_used = "armor"
            if invuln:
                invuln_val = int(invuln.replace('+', ''))
                if invuln_val < modified_save:
                    save_requirement = invuln_val
                    save_used = "invuln"
                else:
                    save_requirement = modified_save
            else:
                save_requirement = modified_save

            if log_this_sim:
                if save_used == "invuln":
                    sim_log.append(f"SAVE PHASE: Using {invuln} invuln (better than {modified_save}+ armor)")
                else:
                    sim_log.append(f"SAVE PHASE: Using {modified_save}+ armor save (base {save}+ - {modified_ap} AP + {save_modifier} modifier)")

            # Cannot save on 7+, auto-save on 1 or less
            if save_requirement > 6:
                failed_saves = normal_wounds
                if log_this_sim:
                    sim_log.append(f"  All saves fail (need {save_requirement}+, impossible)")
            elif save_requirement <= 1:
                failed_saves = 0
                if log_this_sim:
                    sim_log.append(f"  All saves succeed (need {save_requirement}+ or less)")
            else:
                # Roll saves with re-rolls if applicable
                failed_saves = 0
                for _ in range(normal_wounds):
                    roll = roll_d6()

                    # Check for save re-rolls
                    should_reroll_save = False
                    if reroll_saves == 'all':
                        should_reroll_save = True
                    elif reroll_saves == 'ones' and roll == 1:
                        should_reroll_save = True
                    elif reroll_saves == 'failed' and roll < save_requirement:
                        should_reroll_save = True

                    if should_reroll_save:
                        roll = roll_d6()

                    if roll < save_requirement:
                        failed_saves += 1

                if log_this_sim:
                    sim_log.append(f"  {normal_wounds} wounds → {failed_saves} failed saves (need {save_requirement}+)")
                    if reroll_saves:
                        sim_log.append(f"  Re-rolling {reroll_saves} save rolls")

        results['failed_saves'] += failed_saves

        # 5. Deal damage
        all_damage_instances = []

        # Damage from normal wounds
        for _ in range(failed_saves):
            dmg = parse_dice_value(damage_stat) + damage_modifier
            dmg = max(1, dmg)  # Minimum 1 damage

            # Halve damage if ability is active
            if halve_damage:
                dmg = max(1, dmg // 2)  # Round down, minimum 1

            all_damage_instances.append(dmg)

        # Mortal wounds bypass saves and deal damage
        for _ in range(mortal_wounds_this_phase):
            dmg = parse_dice_value(damage_stat) + damage_modifier
            dmg = max(1, dmg)

            # Halve damage applies to mortal wounds too
            if halve_damage:
                dmg = max(1, dmg // 2)

            all_damage_instances.append(dmg)

        if log_this_sim:
            total_damage_instances = len(all_damage_instances)
            sim_log.append(f"DAMAGE PHASE: {total_damage_instances} damage instances ({failed_saves} from failed saves + {mortal_wounds_this_phase} mortal wounds)")
            if halve_damage:
                sim_log.append(f"  Halve Damage: All damage halved (round down, min 1)")

        # 6. Apply Feel No Pain to all damage
        if fnp > 0:
            damage_after_fnp = []
            fnp_saved_this_sim = 0
            for dmg in all_damage_instances:
                for _ in range(dmg):
                    if roll_d6() >= fnp:
                        # FNP failed, damage goes through
                        damage_after_fnp.append(1)
                    else:
                        # FNP succeeded
                        fnp_saved_this_sim += 1
            results['fnp_saved'] += fnp_saved_this_sim
            all_damage_instances = damage_after_fnp

            if log_this_sim:
                sim_log.append(f"FEEL NO PAIN: Prevented {fnp_saved_this_sim} damage (need {fnp}+), {len(all_damage_instances)} damage remaining")

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
                        if log_this_sim:
                            sim_log.append(f"  Model {i+1} destroyed (took {dmg} damage)")
                    break

        if log_this_sim:
            sim_log.append(f"\nRESULT: {sim_damage} total damage, {models_killed_this_sim} models killed")
            results['calculation_log'].append('\n'.join(sim_log))

        results['damage_per_simulation'].append(sim_damage)
        results['models_killed_per_simulation'].append(models_killed_this_sim)

    return results

def calculate_advanced_statistics(results: Dict, attacker_points: int = 0, defender_points: int = 0,
                                  defender_squad_size: int = 1, num_simulations: int = 100) -> Dict:
    """
    Calculate advanced statistical metrics for META analysis

    Args:
        results: Raw simulation results
        attacker_points: Points cost of attacking unit (optional)
        defender_points: Points cost of defending unit (optional)
        defender_squad_size: Number of models in defender squad
        num_simulations: Number of simulations run

    Returns:
        Dictionary with advanced statistical metrics
    """
    damage_array = np.array(results['damage_per_simulation'])
    models_array = np.array(results['models_killed_per_simulation'])

    avg_damage = damage_array.mean()
    avg_models_killed = models_array.mean()
    avg_attacks = results['total_attacks'] / num_simulations
    avg_hits = results['hits'] / num_simulations
    avg_wounds = results['wounds'] / num_simulations

    stats = {}

    # === PERCENTILE ANALYSIS ===
    stats['percentiles'] = {
        'damage': {
            'p10': np.percentile(damage_array, 10),
            'p25': np.percentile(damage_array, 25),
            'p50': np.percentile(damage_array, 50),  # Median
            'p75': np.percentile(damage_array, 75),
            'p90': np.percentile(damage_array, 90),
        },
        'models_killed': {
            'p10': np.percentile(models_array, 10),
            'p25': np.percentile(models_array, 25),
            'p50': np.percentile(models_array, 50),
            'p75': np.percentile(models_array, 75),
            'p90': np.percentile(models_array, 90),
        }
    }

    # === CONSISTENCY METRICS ===
    # Coefficient of Variation (lower = more consistent)
    damage_std = damage_array.std()
    damage_cv = (damage_std / avg_damage * 100) if avg_damage > 0 else 0

    models_std = models_array.std()
    models_cv = (models_std / avg_models_killed * 100) if avg_models_killed > 0 else 0

    # Reliability Score (0-100): How often you get at least 75% of average damage
    threshold_75 = avg_damage * 0.75
    reliability_75 = np.sum(damage_array >= threshold_75) / len(damage_array) * 100

    # Consistency Score (0-100): Inverse of CV, normalized
    consistency_score = max(0, 100 - damage_cv)

    stats['consistency'] = {
        'damage_std': damage_std,
        'damage_cv': damage_cv,
        'models_std': models_std,
        'models_cv': models_cv,
        'reliability_75': reliability_75,  # % of time you get 75%+ of average
        'consistency_score': consistency_score
    }

    # === EFFICIENCY METRICS ===
    # Damage per point (if points provided)
    damage_per_point = (avg_damage / attacker_points) if attacker_points > 0 else 0

    # Damage per attack
    damage_per_attack = avg_damage / avg_attacks if avg_attacks > 0 else 0

    # Hit efficiency
    hit_rate = (avg_hits / avg_attacks * 100) if avg_attacks > 0 else 0

    # Wound efficiency
    wound_rate = (avg_wounds / avg_hits * 100) if avg_hits > 0 else 0

    # Overall conversion rate (attacks -> damage)
    conversion_rate = (avg_damage / avg_attacks) if avg_attacks > 0 else 0

    stats['efficiency'] = {
        'damage_per_point': damage_per_point,
        'damage_per_attack': damage_per_attack,
        'hit_rate': hit_rate,
        'wound_rate': wound_rate,
        'conversion_rate': conversion_rate,
        'expected_value': avg_damage  # Expected damage output
    }

    # === PROBABILITY ANALYSIS ===
    # Chance to kill exactly N models
    kill_probabilities = {}
    for n in range(0, min(defender_squad_size + 1, 21)):
        prob = np.sum(models_array == n) / len(models_array) * 100
        if prob > 0:
            kill_probabilities[n] = prob

    # Chance to kill AT LEAST N models
    cumulative_kill_probs = {}
    for n in range(1, min(defender_squad_size + 1, 21)):
        prob = np.sum(models_array >= n) / len(models_array) * 100
        cumulative_kill_probs[n] = prob

    # Overkill analysis
    squad_wipe_rate = np.sum(models_array >= defender_squad_size) / len(models_array) * 100
    overkill_damage = damage_array[models_array >= defender_squad_size]
    avg_overkill = overkill_damage.mean() if len(overkill_damage) > 0 else 0

    # "Clutch" probability - chance to kill at least 1 model even in bad roll (P10)
    clutch_prob = np.sum(models_array >= 1) / len(models_array) * 100

    stats['probability'] = {
        'kill_probabilities': kill_probabilities,  # Exactly N models
        'cumulative_kill_probs': cumulative_kill_probs,  # At least N models
        'squad_wipe_rate': squad_wipe_rate,
        'avg_overkill_damage': avg_overkill,
        'clutch_probability': clutch_prob,
        'zero_damage_rate': np.sum(damage_array == 0) / len(damage_array) * 100
    }

    # === META SCORING ===
    # Threat Level (0-100): Based on average damage and consistency
    # Higher damage + higher consistency = higher threat
    damage_score = min(100, (avg_damage / (defender_squad_size * 2)) * 100) if defender_squad_size > 0 else 0
    threat_level = (damage_score * 0.7) + (consistency_score * 0.3)

    # Reliability Rating (S/A/B/C/D/F)
    if reliability_75 >= 90:
        reliability_grade = 'S'
    elif reliability_75 >= 75:
        reliability_grade = 'A'
    elif reliability_75 >= 60:
        reliability_grade = 'B'
    elif reliability_75 >= 45:
        reliability_grade = 'C'
    elif reliability_75 >= 30:
        reliability_grade = 'D'
    else:
        reliability_grade = 'F'

    # Point Efficiency Grade (if points available)
    if attacker_points > 0 and defender_points > 0:
        # Expected points destroyed per attacker point spent
        expected_defender_points_destroyed = (avg_models_killed / defender_squad_size) * defender_points
        points_trade_ratio = expected_defender_points_destroyed / attacker_points

        if points_trade_ratio >= 2.0:
            efficiency_grade = 'S'  # Exceptional
        elif points_trade_ratio >= 1.5:
            efficiency_grade = 'A'  # Excellent
        elif points_trade_ratio >= 1.0:
            efficiency_grade = 'B'  # Good
        elif points_trade_ratio >= 0.75:
            efficiency_grade = 'C'  # Fair
        elif points_trade_ratio >= 0.5:
            efficiency_grade = 'D'  # Poor
        else:
            efficiency_grade = 'F'  # Very Poor
    else:
        points_trade_ratio = 0
        efficiency_grade = 'N/A'

    stats['meta_scoring'] = {
        'threat_level': threat_level,
        'reliability_grade': reliability_grade,
        'efficiency_grade': efficiency_grade,
        'points_trade_ratio': points_trade_ratio,
        'overall_score': (threat_level + reliability_75 + (points_trade_ratio * 50)) / 3 if points_trade_ratio > 0 else (threat_level + reliability_75) / 2
    }

    # === COMPARATIVE ANALYSIS ===
    # Z-scores for cross-unit comparison (requires multiple benchmarks, calculated later)
    stats['comparative'] = {
        'damage_range': (damage_array.min(), damage_array.max()),
        'interquartile_range': stats['percentiles']['damage']['p75'] - stats['percentiles']['damage']['p25'],
        'variance': damage_array.var(),
    }

    return stats

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
        # Sort army names alphabetically for better UX
        army1_names = sorted([cat['display_name'] for cat in available_catalogues])
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
        # Sort detachment names alphabetically
        army1_detachment_names = ["None"] + sorted([d['name'] for d in army1_detachments])
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
        # Sort detachment names alphabetically
        army2_detachment_names = ["None"] + sorted([d['name'] for d in army2_detachments])
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
                    # Sort units alphabetically
                    options=sorted(army1_units_sim['name'].tolist()),
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
                    # Sort units alphabetically
                    options=sorted(army2_units_sim['name'].tolist()),
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
            # Sort weapons alphabetically
            weapon_names = sorted([w['name'] for w in attacker_data['weapons']])
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

                    # Show Sustained Hits if applicable
                    if results.get('sustained_hits_generated', 0) > 0:
                        avg_sustained = results['sustained_hits_generated'] / num_simulations
                        st.info(f"**Sustained Hits Generated:** {avg_sustained:.2f} extra hits per simulation on average")

                    # === ADVANCED STATISTICAL ANALYSIS ===
                    st.divider()
                    st.header("🎯 Advanced META Analysis")

                    # Calculate advanced statistics
                    # Extract points from unit costs if available
                    attacker_points = 0
                    defender_points = 0
                    if attacker_data.get('costs'):
                        attacker_points = int(float(attacker_data['costs'].get('pts', 0)))
                    if defender_data.get('costs'):
                        defender_points = int(float(defender_data['costs'].get('pts', 0)))

                    advanced_stats = calculate_advanced_statistics(
                        results,
                        attacker_points=attacker_points,
                        defender_points=defender_points,
                        defender_squad_size=defender_squad_size,
                        num_simulations=num_simulations
                    )

                    # META Scoring Display
                    st.subheader("⭐ META Rating")
                    meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)

                    with meta_col1:
                        threat = advanced_stats['meta_scoring']['threat_level']
                        st.metric("Threat Level", f"{threat:.1f}/100",
                                 help="Combined score of damage output and consistency")

                    with meta_col2:
                        reliability = advanced_stats['meta_scoring']['reliability_grade']
                        reliability_pct = advanced_stats['consistency']['reliability_75']
                        st.metric("Reliability", reliability,
                                 f"{reliability_pct:.1f}% ≥75% avg",
                                 help="How often you get at least 75% of average damage")

                    with meta_col3:
                        efficiency = advanced_stats['meta_scoring']['efficiency_grade']
                        if efficiency != 'N/A':
                            points_ratio = advanced_stats['meta_scoring']['points_trade_ratio']
                            st.metric("Point Efficiency", efficiency,
                                     f"{points_ratio:.2f}:1 ratio",
                                     help="Expected points destroyed per point spent")
                        else:
                            st.metric("Point Efficiency", "N/A",
                                     help="Add unit costs for efficiency analysis")

                    with meta_col4:
                        overall = advanced_stats['meta_scoring']['overall_score']
                        st.metric("Overall Score", f"{overall:.1f}/100",
                                 help="Combined META rating across all factors")

                    # Percentile Analysis
                    st.subheader("📊 Damage Percentiles")
                    st.markdown("**Damage output probability distribution**")

                    perc_col1, perc_col2, perc_col3, perc_col4, perc_col5 = st.columns(5)

                    damage_perc = advanced_stats['percentiles']['damage']
                    with perc_col1:
                        st.metric("P10 (Bad Roll)", f"{damage_perc['p10']:.1f}",
                                 help="10% of attacks do this damage or less")
                    with perc_col2:
                        st.metric("P25 (Low)", f"{damage_perc['p25']:.1f}",
                                 help="25% of attacks do this damage or less")
                    with perc_col3:
                        st.metric("P50 (Median)", f"{damage_perc['p50']:.1f}",
                                 help="50% of attacks do this damage or less")
                    with perc_col4:
                        st.metric("P75 (High)", f"{damage_perc['p75']:.1f}",
                                 help="75% of attacks do this damage or less")
                    with perc_col5:
                        st.metric("P90 (Hot Roll)", f"{damage_perc['p90']:.1f}",
                                 help="90% of attacks do this damage or less")

                    # Consistency & Efficiency Metrics
                    cons_col1, cons_col2 = st.columns(2)

                    with cons_col1:
                        st.subheader("🎲 Consistency Metrics")

                        cons_inner1, cons_inner2 = st.columns(2)
                        with cons_inner1:
                            consistency_score = advanced_stats['consistency']['consistency_score']
                            st.metric("Consistency Score", f"{consistency_score:.1f}/100",
                                     help="Higher = more predictable damage")

                            damage_cv = advanced_stats['consistency']['damage_cv']
                            st.metric("Variability (CV)", f"{damage_cv:.1f}%",
                                     help="Coefficient of variation - lower is better")

                        with cons_inner2:
                            iqr = advanced_stats['comparative']['interquartile_range']
                            st.metric("IQR (Spread)", f"{iqr:.1f}",
                                     help="Interquartile range - middle 50% spread")

                            clutch = advanced_stats['probability']['clutch_probability']
                            st.metric("Clutch %", f"{clutch:.1f}%",
                                     help="Chance to kill at least 1 model")

                    with cons_col2:
                        st.subheader("⚡ Efficiency Metrics")

                        eff_inner1, eff_inner2 = st.columns(2)
                        with eff_inner1:
                            dpa = advanced_stats['efficiency']['damage_per_attack']
                            st.metric("Damage/Attack", f"{dpa:.2f}",
                                     help="Average damage per attack")

                            hit_rate = advanced_stats['efficiency']['hit_rate']
                            st.metric("Hit Rate", f"{hit_rate:.1f}%",
                                     help="Percentage of attacks that hit")

                        with eff_inner2:
                            wound_rate = advanced_stats['efficiency']['wound_rate']
                            st.metric("Wound Rate", f"{wound_rate:.1f}%",
                                     help="Percentage of hits that wound")

                            if attacker_points > 0:
                                dpp = advanced_stats['efficiency']['damage_per_point']
                                st.metric("Damage/Point", f"{dpp:.2f}",
                                         help="Damage per points cost")

                    # Kill Probability Analysis
                    st.subheader("🎯 Kill Probability Analysis")

                    # Cumulative probability chart
                    if advanced_stats['probability']['cumulative_kill_probs']:
                        prob_data = []
                        for n, prob in advanced_stats['probability']['cumulative_kill_probs'].items():
                            prob_data.append({'Models': f"≥{n}", 'Models_num': n, 'Probability': prob})

                        if prob_data:
                            prob_df = pd.DataFrame(prob_data)

                            fig_prob = px.bar(
                                prob_df,
                                x='Models',
                                y='Probability',
                                title=f"Probability to Kill At Least N Models",
                                labels={'Probability': 'Probability (%)', 'Models': 'Models Killed'},
                                color='Probability',
                                color_continuous_scale='RdYlGn'
                            )
                            fig_prob.update_layout(showlegend=False)
                            st.plotly_chart(fig_prob, use_container_width=True)

                            # Key probability thresholds
                            prob_metrics_col1, prob_metrics_col2, prob_metrics_col3 = st.columns(3)

                            with prob_metrics_col1:
                                zero_dmg = advanced_stats['probability']['zero_damage_rate']
                                st.metric("Whiff Rate", f"{zero_dmg:.1f}%",
                                         help="Chance to deal 0 damage")

                            with prob_metrics_col2:
                                wipe_rate = advanced_stats['probability']['squad_wipe_rate']
                                st.metric("Squad Wipe", f"{wipe_rate:.1f}%",
                                         help="Chance to kill entire squad")

                            with prob_metrics_col3:
                                if wipe_rate > 0:
                                    overkill = advanced_stats['probability']['avg_overkill_damage']
                                    st.metric("Avg Overkill", f"{overkill:.1f}",
                                             help="Average excess damage when wiping squad")

                    # Interpretation Guide
                    with st.expander("📖 How to Read These Stats"):
                        st.markdown("""
                        ### META Rating Guide

                        **Threat Level (0-100):** How dangerous this unit is against the target
                        - 80-100: Extremely lethal
                        - 60-80: Very effective
                        - 40-60: Moderately effective
                        - 20-40: Limited threat
                        - 0-20: Minimal threat

                        **Reliability Grade:** How consistent the damage output is
                        - S: Elite tier (90%+ reliability)
                        - A: Tournament viable (75-90%)
                        - B: Competitive (60-75%)
                        - C: Inconsistent (45-60%)
                        - D/F: Unreliable (<45%)

                        **Point Efficiency Grade:** Value for points spent
                        - S: 2.0+ points destroyed per point (exceptional value)
                        - A: 1.5-2.0 (excellent value)
                        - B: 1.0-1.5 (good trade)
                        - C: 0.75-1.0 (fair trade)
                        - D/F: <0.75 (poor trade)

                        ### Percentiles
                        - **P10:** Your worst-case scenario (bad luck)
                        - **P50 (Median):** Your typical result
                        - **P90:** Your best-case scenario (hot dice)

                        ### Consistency Metrics
                        - **Consistency Score:** Higher = more reliable damage
                        - **Variability (CV):** Lower = more predictable
                        - **IQR:** Smaller = tighter damage clustering
                        - **Clutch %:** Reliability of getting at least 1 kill

                        ### Strategic Insights
                        - High damage + high consistency = META threat
                        - High damage + low consistency = risky glass cannon
                        - Low damage + high consistency = reliable chip damage
                        - Low damage + low consistency = avoid this matchup
                        """)

                    # Display calculation log
                    st.divider()
                    st.subheader("📋 Detailed Calculation Log")
                    st.markdown("See how modifiers and special rules affect the simulation")

                    with st.expander("📖 View Calculation Details", expanded=False):
                        if results.get('calculation_log'):
                            for log_entry in results['calculation_log']:
                                st.text(log_entry)
                        else:
                            st.info("No calculation log available")

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
                        'results': results,
                        'advanced_stats': advanced_stats,  # Include advanced statistics
                        'attacker_points': attacker_points,
                        'defender_points': defender_points
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
                    # Sort units alphabetically
                    options=sorted(filtered_army1_browse['name'].tolist()),
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
                    # Sort units alphabetically
                    options=sorted(filtered_army2_browse['name'].tolist()),
                    key="browser_army2"
                )

                if selected_unit_army2_browse:
                    unit_details = extract_unit_details(army2_root, army2_ns, selected_unit_army2_browse)
                    display_unit_panel(unit_details, selected_unit_army2_browse)
            else:
                st.error(f"No {selected_army2} units found in catalogue")

    with tab3:
        st.header("📊 Benchmark Results")
        st.markdown("Compare multiple simulation results across matchups")

        if 'benchmark_results' in st.session_state and st.session_state.benchmark_results:
            # Add filters and sort options
            filter_col1, filter_col2, filter_col3 = st.columns(3)

            with filter_col1:
                # Filter by attacker army
                all_attacker_armies = sorted(set(r.get('attacker_army', 'Unknown') for r in st.session_state.benchmark_results))
                filter_attacker = st.multiselect(
                    "Filter by Attacker Army",
                    options=all_attacker_armies,
                    default=all_attacker_armies,
                    key="benchmark_filter_attacker"
                )

            with filter_col2:
                # Filter by defender army
                all_defender_armies = sorted(set(r.get('defender_army', 'Unknown') for r in st.session_state.benchmark_results))
                filter_defender = st.multiselect(
                    "Filter by Defender Army",
                    options=all_defender_armies,
                    default=all_defender_armies,
                    key="benchmark_filter_defender"
                )

            with filter_col3:
                # Sort by option
                sort_by = st.selectbox(
                    "Sort by",
                    options=[
                        "Overall Score (High to Low)",
                        "Avg Damage (High to Low)",
                        "Threat Level (High to Low)",
                        "Reliability Grade (Best to Worst)",
                        "Point Efficiency (Best to Worst)",
                        "Consistency (High to Low)",
                        "Most Recent First"
                    ],
                    key="benchmark_sort"
                )

            # Filter results
            filtered_results = [
                r for r in st.session_state.benchmark_results
                if r.get('attacker_army', 'Unknown') in filter_attacker
                and r.get('defender_army', 'Unknown') in filter_defender
            ]

            # Sort results
            if sort_by == "Overall Score (High to Low)":
                filtered_results = sorted(filtered_results,
                    key=lambda r: r.get('advanced_stats', {}).get('meta_scoring', {}).get('overall_score', 0),
                    reverse=True)
            elif sort_by == "Avg Damage (High to Low)":
                filtered_results = sorted(filtered_results, key=lambda r: r['avg_damage'], reverse=True)
            elif sort_by == "Threat Level (High to Low)":
                filtered_results = sorted(filtered_results,
                    key=lambda r: r.get('advanced_stats', {}).get('meta_scoring', {}).get('threat_level', 0),
                    reverse=True)
            elif sort_by == "Reliability Grade (Best to Worst)":
                grade_order = {'S': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4, 'F': 5, 'N/A': 6}
                filtered_results = sorted(filtered_results,
                    key=lambda r: grade_order.get(r.get('advanced_stats', {}).get('meta_scoring', {}).get('reliability_grade', 'N/A'), 6))
            elif sort_by == "Point Efficiency (Best to Worst)":
                grade_order = {'S': 0, 'A': 1, 'B': 2, 'C': 3, 'D': 4, 'F': 5, 'N/A': 6}
                filtered_results = sorted(filtered_results,
                    key=lambda r: grade_order.get(r.get('advanced_stats', {}).get('meta_scoring', {}).get('efficiency_grade', 'N/A'), 6))
            elif sort_by == "Consistency (High to Low)":
                filtered_results = sorted(filtered_results,
                    key=lambda r: r.get('advanced_stats', {}).get('consistency', {}).get('consistency_score', 0),
                    reverse=True)
            # else: Most Recent First (default order)

            st.caption(f"Showing {len(filtered_results)} of {len(st.session_state.benchmark_results)} results")

            # Create comparison dataframe with advanced stats
            comparison_data = []
            for result in filtered_results:
                adv_stats = result.get('advanced_stats', {})
                meta_scoring = adv_stats.get('meta_scoring', {})

                comparison_data.append({
                    'Attacker Army': result.get('attacker_army', 'Unknown'),
                    'Attacker': result['attacker'],
                    'Weapon': result['weapon'],
                    'Defender Army': result.get('defender_army', 'Unknown'),
                    'Defender': result['defender'],
                    'Avg Damage': f"{result['avg_damage']:.2f}",
                    'Models Killed': f"{result['avg_models_killed']:.2f}",
                    'Wipe %': f"{result['squad_wipe_chance']:.1f}%",
                    'Threat': f"{meta_scoring.get('threat_level', 0):.1f}",
                    'Reliability': meta_scoring.get('reliability_grade', 'N/A'),
                    'Efficiency': meta_scoring.get('efficiency_grade', 'N/A'),
                    'Score': f"{meta_scoring.get('overall_score', 0):.1f}",
                    'Sims': result['simulations']
                })

            comparison_df = pd.DataFrame(comparison_data)
            st.dataframe(comparison_df, use_container_width=True, hide_index=True)

            # Comparison charts
            if len(filtered_results) > 1:
                st.subheader("📈 Comparative Analysis")

                # Create matchup labels
                matchup_labels = [
                    f"{r['attacker'][:15]} vs {r['defender'][:15]}"
                    for r in filtered_results
                ]

                chart_col1, chart_col2 = st.columns(2)

                with chart_col1:
                    # Damage comparison
                    chart_data = pd.DataFrame({
                        'Matchup': matchup_labels,
                        'Average Damage': [r['avg_damage'] for r in filtered_results]
                    })

                    fig = px.bar(
                        chart_data,
                        x='Matchup',
                        y='Average Damage',
                        title='Average Damage by Matchup',
                        color='Average Damage',
                        color_continuous_scale='Reds'
                    )
                    fig.update_xaxes(tickangle=-45)
                    st.plotly_chart(fig, use_container_width=True)

                with chart_col2:
                    # Threat level comparison
                    threat_data = pd.DataFrame({
                        'Matchup': matchup_labels,
                        'Threat Level': [r.get('advanced_stats', {}).get('meta_scoring', {}).get('threat_level', 0)
                                        for r in filtered_results]
                    })

                    fig2 = px.bar(
                        threat_data,
                        x='Matchup',
                        y='Threat Level',
                        title='Threat Level by Matchup',
                        color='Threat Level',
                        color_continuous_scale='RdYlGn'
                    )
                    fig2.update_xaxes(tickangle=-45)
                    st.plotly_chart(fig2, use_container_width=True)

                # Multi-metric comparison
                st.subheader("🎯 META Ratings Comparison")

                meta_comparison_data = []
                for i, result in enumerate(filtered_results):
                    adv_stats = result.get('advanced_stats', {})
                    meta_comparison_data.append({
                        'Matchup': matchup_labels[i],
                        'Threat': adv_stats.get('meta_scoring', {}).get('threat_level', 0),
                        'Reliability %': adv_stats.get('consistency', {}).get('reliability_75', 0),
                        'Consistency': adv_stats.get('consistency', {}).get('consistency_score', 0),
                        'Damage/Attack': adv_stats.get('efficiency', {}).get('damage_per_attack', 0)
                    })

                meta_df = pd.DataFrame(meta_comparison_data)

                # Radar/Spider chart alternative - grouped bar chart
                fig_meta = px.bar(
                    meta_df,
                    x='Matchup',
                    y=['Threat', 'Reliability %', 'Consistency'],
                    title='META Metrics Comparison (0-100 scale)',
                    barmode='group',
                    labels={'value': 'Score', 'variable': 'Metric'}
                )
                fig_meta.update_xaxes(tickangle=-45)
                st.plotly_chart(fig_meta, use_container_width=True)

                # Point efficiency comparison (if available)
                has_points = any(r.get('attacker_points', 0) > 0 and r.get('defender_points', 0) > 0
                                for r in filtered_results)

                if has_points:
                    st.subheader("💰 Point Efficiency Analysis")

                    efficiency_data = []
                    for i, result in enumerate(filtered_results):
                        adv_stats = result.get('advanced_stats', {})
                        points_ratio = adv_stats.get('meta_scoring', {}).get('points_trade_ratio', 0)
                        if points_ratio > 0:
                            efficiency_data.append({
                                'Matchup': matchup_labels[i],
                                'Points Trade Ratio': points_ratio,
                                'Grade': adv_stats.get('meta_scoring', {}).get('efficiency_grade', 'N/A')
                            })

                    if efficiency_data:
                        eff_df = pd.DataFrame(efficiency_data)

                        fig_eff = px.bar(
                            eff_df,
                            x='Matchup',
                            y='Points Trade Ratio',
                            title='Points Destroyed per Point Spent',
                            color='Points Trade Ratio',
                            color_continuous_scale='RdYlGn',
                            text='Grade'
                        )
                        fig_eff.update_traces(textposition='outside')
                        fig_eff.update_xaxes(tickangle=-45)
                        fig_eff.add_hline(y=1.0, line_dash="dash", line_color="yellow",
                                         annotation_text="Break Even (1:1)", annotation_position="right")
                        st.plotly_chart(fig_eff, use_container_width=True)

                # Best/Worst matchups summary
                st.subheader("🏆 META Summary")

                summary_col1, summary_col2, summary_col3 = st.columns(3)

                # Find best damage output
                best_damage_idx = max(range(len(filtered_results)),
                                     key=lambda i: filtered_results[i]['avg_damage'])
                best_damage = filtered_results[best_damage_idx]

                with summary_col1:
                    st.metric(
                        "🔥 Highest Damage",
                        f"{best_damage['avg_damage']:.2f}",
                        f"{best_damage['attacker']} vs {best_damage['defender']}"
                    )

                # Find most consistent
                best_consistency_idx = max(range(len(filtered_results)),
                                          key=lambda i: filtered_results[i].get('advanced_stats', {}).get('consistency', {}).get('consistency_score', 0))
                best_consistency = filtered_results[best_consistency_idx]

                with summary_col2:
                    consistency_score = best_consistency.get('advanced_stats', {}).get('consistency', {}).get('consistency_score', 0)
                    st.metric(
                        "🎯 Most Consistent",
                        f"{consistency_score:.1f}/100",
                        f"{best_consistency['attacker']} vs {best_consistency['defender']}"
                    )

                # Find best value (if points available)
                if has_points:
                    best_value_idx = max(range(len(filtered_results)),
                                        key=lambda i: filtered_results[i].get('advanced_stats', {}).get('meta_scoring', {}).get('points_trade_ratio', 0))
                    best_value = filtered_results[best_value_idx]
                    points_ratio = best_value.get('advanced_stats', {}).get('meta_scoring', {}).get('points_trade_ratio', 0)

                    with summary_col3:
                        st.metric(
                            "💎 Best Value",
                            f"{points_ratio:.2f}:1",
                            f"{best_value['attacker']} vs {best_value['defender']}"
                        )

            if st.button("Clear Benchmark History"):
                st.session_state.benchmark_results = []
                st.rerun()
        else:
            st.info("No benchmark results yet. Run simulations in the Combat Simulator tab to see results here.")

if __name__ == "__main__":
    main()
