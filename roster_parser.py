"""
BattleScribe Roster Parser
Parses .ros (roster) JSON files exported from BattleScribe
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RosterWeapon:
    """A weapon in a roster unit"""
    name: str
    profile_type: str  # 'Ranged Weapons' or 'Melee Weapons'
    range: str
    attacks: str
    bs_ws: str  # BS for ranged, WS for melee
    strength: str
    ap: str
    damage: str
    keywords: List[str] = field(default_factory=list)


@dataclass
class RosterAbility:
    """An ability on a roster unit"""
    name: str
    description: str
    ability_type: str  # 'Abilities', 'Core', 'Faction', etc.


@dataclass
class RosterUnitProfile:
    """Unit stats profile"""
    name: str
    movement: str
    toughness: str
    save: str
    wounds: str
    leadership: str
    oc: str


@dataclass
class RosterUnit:
    """A complete unit from a roster"""
    id: str
    name: str
    type: str  # 'model', 'unit', 'upgrade'
    number: int  # Model count
    points: int

    # Stats
    profile: Optional[RosterUnitProfile] = None

    # Wargear
    ranged_weapons: List[RosterWeapon] = field(default_factory=list)
    melee_weapons: List[RosterWeapon] = field(default_factory=list)

    # Abilities
    abilities: List[RosterAbility] = field(default_factory=list)
    rules: List[RosterAbility] = field(default_factory=list)

    # Keywords
    keywords: List[str] = field(default_factory=list)

    # Metadata
    is_character: bool = False
    is_leader: bool = False
    is_warlord: bool = False

    # Sub-units (for composite units like characters attached to squads)
    selections: List['RosterUnit'] = field(default_factory=list)


@dataclass
class Roster:
    """Complete army roster"""
    name: str = ""
    faction: str = ""
    detachment: str = ""
    points_total: int = 0
    points_limit: int = 2000
    units: List[RosterUnit] = field(default_factory=list)


class RosterParser:
    """Parse BattleScribe .ros JSON files"""

    def __init__(self):
        self.roster = Roster()

    def parse_file(self, file_path: str) -> Roster:
        """Parse a .ros JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return self.parse_json(data)

    def parse_json(self, data: Dict) -> Roster:
        """Parse roster JSON data"""
        roster_data = data.get('roster', {})

        # Extract roster metadata
        costs = roster_data.get('costs', [])
        for cost in costs:
            if cost.get('name') == 'pts':
                self.roster.points_total = int(float(cost.get('value', 0)))

        cost_limits = roster_data.get('costLimits', [])
        for limit in cost_limits:
            if limit.get('name') == 'pts':
                self.roster.points_limit = int(float(limit.get('value', 2000)))

        # Parse forces (army selections)
        forces = roster_data.get('forces', [])
        for force in forces:
            self._parse_force(force)

        return self.roster

    def _parse_force(self, force: Dict):
        """Parse a force (detachment) from the roster"""
        selections = force.get('selections', [])

        for selection in selections:
            # Parse detachment, battle size, etc.
            if selection.get('name') == 'Detachment':
                detachment_selections = selection.get('selections', [])
                if detachment_selections:
                    self.roster.detachment = detachment_selections[0].get('name', '')

            # Parse units
            elif selection.get('type') in ['model', 'unit']:
                unit = self._parse_unit(selection)
                if unit:
                    self.roster.units.append(unit)

    def _parse_unit(self, selection: Dict) -> Optional[RosterUnit]:
        """Parse a unit selection"""
        unit = RosterUnit(
            id=selection.get('id', ''),
            name=selection.get('name', ''),
            type=selection.get('type', ''),
            number=int(selection.get('number', 1)),
            points=0
        )

        # Get points cost
        costs = selection.get('costs', [])
        for cost in costs:
            if cost.get('name') == 'pts':
                unit.points = int(float(cost.get('value', 0)))

        # Get categories to determine unit type
        categories = selection.get('categories', [])
        for cat in categories:
            cat_name = cat.get('name', '')
            unit.keywords.append(cat_name)

            if cat_name == 'Character':
                unit.is_character = True
            if cat.get('primary') == True:
                unit.type = cat_name

        # Parse profiles (stats)
        profiles = selection.get('profiles', [])
        for profile in profiles:
            profile_type = profile.get('typeName', '')

            if profile_type == 'Unit':
                unit.profile = self._parse_unit_profile(profile)

            elif profile_type == 'Ranged Weapons':
                weapon = self._parse_weapon_profile(profile, 'Ranged Weapons')
                unit.ranged_weapons.append(weapon)

            elif profile_type == 'Melee Weapons':
                weapon = self._parse_weapon_profile(profile, 'Melee Weapons')
                unit.melee_weapons.append(weapon)

            elif profile_type == 'Abilities':
                ability = self._parse_ability_profile(profile)
                unit.abilities.append(ability)

        # Parse rules
        rules = selection.get('rules', [])
        for rule in rules:
            ability = RosterAbility(
                name=rule.get('name', ''),
                description=rule.get('description', ''),
                ability_type='Rule'
            )
            unit.rules.append(ability)

        # Check for warlord
        sub_selections = selection.get('selections', [])
        for sub_sel in sub_selections:
            if sub_sel.get('name') == 'Warlord':
                unit.is_warlord = True
            elif sub_sel.get('type') == 'upgrade':
                # Parse wargear/weapons in sub-selections
                self._parse_subselection(unit, sub_sel)

        return unit

    def _parse_unit_profile(self, profile: Dict) -> RosterUnitProfile:
        """Parse unit stat profile"""
        chars = {char.get('name'): char.get('$text', '')
                for char in profile.get('characteristics', [])}

        return RosterUnitProfile(
            name=profile.get('name', ''),
            movement=chars.get('M', ''),
            toughness=chars.get('T', ''),
            save=chars.get('SV', ''),
            wounds=chars.get('W', ''),
            leadership=chars.get('LD', ''),
            oc=chars.get('OC', '')
        )

    def _parse_weapon_profile(self, profile: Dict, profile_type: str) -> RosterWeapon:
        """Parse weapon profile"""
        chars = {char.get('name'): char.get('$text', '')
                for char in profile.get('characteristics', [])}

        keywords_str = chars.get('Keywords', '')
        keywords = [k.strip() for k in keywords_str.split(',') if k.strip() and k.strip() != '-']

        return RosterWeapon(
            name=profile.get('name', ''),
            profile_type=profile_type,
            range=chars.get('Range', ''),
            attacks=chars.get('A', ''),
            bs_ws=chars.get('BS') or chars.get('WS', ''),
            strength=chars.get('S', ''),
            ap=chars.get('AP', ''),
            damage=chars.get('D', ''),
            keywords=keywords
        )

    def _parse_ability_profile(self, profile: Dict) -> RosterAbility:
        """Parse ability profile"""
        chars = {char.get('name'): char.get('$text', '')
                for char in profile.get('characteristics', [])}

        return RosterAbility(
            name=profile.get('name', ''),
            description=chars.get('Description', ''),
            ability_type=profile.get('typeName', 'Abilities')
        )

    def _parse_subselection(self, unit: RosterUnit, sub_sel: Dict):
        """Parse sub-selections (wargear, weapons, etc.)"""
        # Parse weapon profiles in sub-selections
        profiles = sub_sel.get('profiles', [])
        for profile in profiles:
            profile_type = profile.get('typeName', '')

            if profile_type == 'Ranged Weapons':
                weapon = self._parse_weapon_profile(profile, 'Ranged Weapons')
                unit.ranged_weapons.append(weapon)

            elif profile_type == 'Melee Weapons':
                weapon = self._parse_weapon_profile(profile, 'Melee Weapons')
                unit.melee_weapons.append(weapon)


def parse_roster(file_path: str) -> Roster:
    """Convenience function to parse a roster file"""
    parser = RosterParser()
    return parser.parse_file(file_path)


# Example usage
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        roster = parse_roster(sys.argv[1])

        print(f"\n=== {roster.detachment} ===")
        print(f"Points: {roster.points_total}/{roster.points_limit}")
        print(f"\nUnits ({len(roster.units)}):")

        for unit in roster.units:
            warlord_badge = "👑 " if unit.is_warlord else ""
            char_badge = "⚔️ " if unit.is_character else ""

            print(f"\n{warlord_badge}{char_badge}{unit.name} ({unit.points} pts)")

            if unit.profile:
                print(f"  Stats: M:{unit.profile.movement} T:{unit.profile.toughness} "
                      f"SV:{unit.profile.save} W:{unit.profile.wounds} "
                      f"LD:{unit.profile.leadership} OC:{unit.profile.oc}")

            if unit.ranged_weapons:
                print(f"  Ranged Weapons:")
                for w in unit.ranged_weapons:
                    print(f"    - {w.name}: {w.range}\" A:{w.attacks} BS:{w.bs_ws} "
                          f"S:{w.strength} AP:{w.ap} D:{w.damage}")

            if unit.melee_weapons:
                print(f"  Melee Weapons:")
                for w in unit.melee_weapons:
                    print(f"    - {w.name}: A:{w.attacks} WS:{w.bs_ws} "
                          f"S:{w.strength} AP:{w.ap} D:{w.damage}")

            if unit.abilities:
                print(f"  Abilities: {', '.join(a.name for a in unit.abilities)}")
    else:
        print("Usage: python roster_parser.py <roster.ros>")
