"""
Converter: BattleScribe Roster → Battle Simulator
Converts parsed roster units into battle-ready units
"""

from roster_parser import RosterUnit, RosterWeapon, Roster
from battle_simulator import (
    BattleUnit, BattleUnitStats, BattleWeapon, Position
)
from typing import List


def parse_stat_value(value: str, default: int = 0) -> int:
    """Parse stat value from string (handles '-', 'N/A', numbers)"""
    value = value.strip().upper()

    if value in ['-', 'N/A', '']:
        return default

    # Handle values like "3+", "2+"
    if '+' in value:
        value = value.replace('+', '')

    # Handle fractions like "4++"
    if value.count('+') > 1:
        value = value.replace('+', '')

    try:
        return int(value)
    except ValueError:
        return default


def parse_range(range_str: str) -> int:
    """Parse weapon range (handles 'Melee', '24"', etc.)"""
    range_str = range_str.strip().upper()

    if range_str == 'MELEE':
        return 1

    # Extract number
    try:
        return int(''.join(c for c in range_str if c.isdigit()))
    except ValueError:
        return 0


def convert_roster_weapon(weapon: RosterWeapon) -> BattleWeapon:
    """Convert RosterWeapon to BattleWeapon"""
    is_ranged = weapon.profile_type == 'Ranged Weapons'

    return BattleWeapon(
        name=weapon.name,
        is_ranged=is_ranged,
        range=parse_range(weapon.range),
        attacks=weapon.attacks,
        bs_ws=parse_stat_value(weapon.bs_ws, default=4),
        strength=parse_stat_value(weapon.strength, default=4),
        ap=parse_stat_value(weapon.ap, default=0),
        damage=weapon.damage,
        keywords=weapon.keywords
    )


def convert_roster_unit(roster_unit: RosterUnit, player_id: int = 0,
                        faction: str = "") -> BattleUnit:
    """Convert RosterUnit to BattleUnit for battle simulation"""

    # Parse stats
    if roster_unit.profile:
        stats = BattleUnitStats(
            movement=parse_stat_value(roster_unit.profile.movement, default=6),
            toughness=parse_stat_value(roster_unit.profile.toughness, default=4),
            save=parse_stat_value(roster_unit.profile.save, default=5),
            invuln_save=None,  # Would need to parse from abilities
            wounds=parse_stat_value(roster_unit.profile.wounds, default=1),
            leadership=parse_stat_value(roster_unit.profile.leadership, default=7),
            oc=parse_stat_value(roster_unit.profile.oc, default=1)
        )
        wounds_per_model = stats.wounds
    else:
        # Default stats for units without profile
        stats = BattleUnitStats(
            movement=6, toughness=4, save=5, invuln_save=None,
            wounds=1, leadership=7, oc=1
        )
        wounds_per_model = 1

    # Convert weapons
    ranged_weapons = [convert_roster_weapon(w) for w in roster_unit.ranged_weapons]
    melee_weapons = [convert_roster_weapon(w) for w in roster_unit.melee_weapons]

    # Extract abilities
    ability_names = [a.name for a in roster_unit.abilities]
    ability_names.extend([r.name for r in roster_unit.rules])

    # Check for invulnerable save in abilities
    for ability in roster_unit.abilities + roster_unit.rules:
        desc = ability.description.lower()
        if 'invulnerable save' in desc or 'invuln' in desc:
            # Try to extract invuln value
            if '4+' in desc or '4+ invulnerable' in desc:
                stats.invuln_save = 4
            elif '5+' in desc or '5+ invulnerable' in desc:
                stats.invuln_save = 5
            elif '3+' in desc or '3+ invulnerable' in desc:
                stats.invuln_save = 3

    battle_unit = BattleUnit(
        id=roster_unit.id,
        name=roster_unit.name,
        player_id=player_id,
        faction=faction,
        stats=stats,
        model_count=roster_unit.number,
        wounds_per_model=wounds_per_model,
        current_wounds=roster_unit.number * wounds_per_model,
        ranged_weapons=ranged_weapons,
        melee_weapons=melee_weapons,
        abilities=ability_names,
        keywords=roster_unit.keywords,
        is_character=roster_unit.is_character,
        points_cost=roster_unit.points
    )

    return battle_unit


def convert_roster_to_battle_units(roster: Roster, player_id: int = 0) -> List[BattleUnit]:
    """
    Convert entire roster to list of battle units

    Args:
        roster: Parsed roster
        player_id: 0 or 1 (which player controls this army)

    Returns:
        List of BattleUnit objects ready for battle
    """
    battle_units = []

    for roster_unit in roster.units:
        # Skip configuration/upgrades
        if roster_unit.type in ['upgrade', 'rule']:
            continue

        # Convert unit
        battle_unit = convert_roster_unit(roster_unit, player_id, roster.faction)
        battle_units.append(battle_unit)

    return battle_units


# Example usage
if __name__ == "__main__":
    import sys
    from roster_parser import parse_roster

    if len(sys.argv) > 1:
        roster = parse_roster(sys.argv[1])
        battle_units = convert_roster_to_battle_units(roster, player_id=0)

        print(f"\n=== Converted {len(battle_units)} units for battle ===\n")

        for unit in battle_units:
            print(f"{unit.name}")
            print(f"  Models: {unit.model_count} | Wounds: {unit.current_wounds}")
            print(f"  M:{unit.stats.movement}\" T:{unit.stats.toughness} "
                  f"SV:{unit.stats.save}+ W:{unit.wounds_per_model}")

            if unit.ranged_weapons:
                print(f"  Ranged: {', '.join(w.name for w in unit.ranged_weapons)}")
            if unit.melee_weapons:
                print(f"  Melee: {', '.join(w.name for w in unit.melee_weapons)}")

            print()
    else:
        print("Usage: python roster_to_battle.py <roster.ros>")
