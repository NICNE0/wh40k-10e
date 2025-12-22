"""
Test script for the complete battle system
Demonstrates roster import and battle simulation
"""

from battle_simulator import (
    BattleSimulator, Battlefield, Position, Objective,
    TerrainFeature, Terrain, BattleUnit, BattleUnitStats, BattleWeapon
)
import numpy as np


def create_test_battle():
    """Create a test battle with hardcoded units"""

    print("⚔️ Warhammer 40k Battle Simulator - Test Run\n")

    # Create battlefield
    print("🗺️ Creating battlefield...")
    battlefield = Battlefield(width=44.0, length=60.0)

    # Add objectives
    print("🎯 Placing objectives...")
    battlefield.add_objective(Objective("Center Objective", Position(22, 30), value=5))
    battlefield.add_objective(Objective("Left Flank", Position(11, 30), value=5))
    battlefield.add_objective(Objective("Right Flank", Position(33, 30), value=5))

    # Add terrain
    print("🌳 Generating terrain...")
    np.random.seed(42)  # For reproducibility
    for i in range(6):
        x = np.random.uniform(8, 36)
        y = np.random.uniform(8, 52)
        radius = np.random.uniform(3, 6)
        terrain_type = np.random.choice([Terrain.LIGHT_COVER, Terrain.HEAVY_COVER, Terrain.OBSCURING])

        battlefield.add_terrain(TerrainFeature(
            name=f"Ruins-{i+1}",
            terrain_type=terrain_type,
            center=Position(x, y),
            radius=radius,
            provides_cover=terrain_type != Terrain.OBSCURING,
            blocks_los=terrain_type == Terrain.OBSCURING
        ))

    # Create Player 1 army (Space Marines)
    print("\n🔵 Creating Player 1 army (Space Marines)...")
    p1_units = []

    # Intercessor Squad 1
    p1_units.append(BattleUnit(
        id="sm_intercessors_1",
        name="Intercessor Squad Alpha",
        player_id=0,
        faction="Space Marines",
        stats=BattleUnitStats(
            movement=6,
            toughness=4,
            save=3,
            invuln_save=None,
            wounds=2,
            leadership=6,
            oc=2
        ),
        model_count=5,
        wounds_per_model=2,
        current_wounds=10,
        ranged_weapons=[
            BattleWeapon(
                name="Bolt Rifle",
                is_ranged=True,
                range=24,
                attacks="2",
                bs_ws=3,
                strength=4,
                ap=-1,
                damage="1",
                keywords=[]
            )
        ],
        melee_weapons=[
            BattleWeapon(
                name="Close Combat Weapon",
                is_ranged=False,
                range=1,
                attacks="2",
                bs_ws=3,
                strength=4,
                ap=0,
                damage="1",
                keywords=[]
            )
        ],
        points_cost=100
    ))

    # Intercessor Squad 2
    p1_units.append(BattleUnit(
        id="sm_intercessors_2",
        name="Intercessor Squad Beta",
        player_id=0,
        faction="Space Marines",
        stats=BattleUnitStats(movement=6, toughness=4, save=3, wounds=2, leadership=6, oc=2),
        model_count=5,
        wounds_per_model=2,
        current_wounds=10,
        ranged_weapons=[
            BattleWeapon("Bolt Rifle", True, 24, "2", 3, 4, -1, "1", [])
        ],
        melee_weapons=[
            BattleWeapon("Close Combat Weapon", False, 1, "2", 3, 4, 0, "1", [])
        ],
        points_cost=100
    ))

    # Hellblasters (anti-tank)
    p1_units.append(BattleUnit(
        id="sm_hellblasters",
        name="Hellblaster Squad",
        player_id=0,
        faction="Space Marines",
        stats=BattleUnitStats(movement=6, toughness=4, save=3, wounds=2, leadership=6, oc=2),
        model_count=5,
        wounds_per_model=2,
        current_wounds=10,
        ranged_weapons=[
            BattleWeapon(
                name="Plasma Incinerator",
                is_ranged=True,
                range=24,
                attacks="1",
                bs_ws=3,
                strength=8,
                ap=-3,
                damage="2",
                keywords=["Hazardous"]
            )
        ],
        melee_weapons=[
            BattleWeapon("Close Combat Weapon", False, 1, "2", 3, 4, 0, "1", [])
        ],
        points_cost=150
    ))

    print(f"   Added {len(p1_units)} units")

    # Create Player 2 army (Necrons)
    print("\n🔴 Creating Player 2 army (Necrons)...")
    p2_units = []

    # Necron Warriors 1
    p2_units.append(BattleUnit(
        id="nec_warriors_1",
        name="Necron Warriors Squad Alpha",
        player_id=1,
        faction="Necrons",
        stats=BattleUnitStats(movement=5, toughness=4, save=4, wounds=1, leadership=7, oc=2),
        model_count=10,
        wounds_per_model=1,
        current_wounds=10,
        ranged_weapons=[
            BattleWeapon("Gauss Flayer", True, 24, "1", 4, 4, -1, "1", ["Lethal Hits"])
        ],
        melee_weapons=[
            BattleWeapon("Close Combat Weapon", False, 1, "1", 4, 4, 0, "1", [])
        ],
        points_cost=110
    ))

    # Necron Warriors 2
    p2_units.append(BattleUnit(
        id="nec_warriors_2",
        name="Necron Warriors Squad Beta",
        player_id=1,
        faction="Necrons",
        stats=BattleUnitStats(movement=5, toughness=4, save=4, wounds=1, leadership=7, oc=2),
        model_count=10,
        wounds_per_model=1,
        current_wounds=10,
        ranged_weapons=[
            BattleWeapon("Gauss Flayer", True, 24, "1", 4, 4, -1, "1", ["Lethal Hits"])
        ],
        melee_weapons=[
            BattleWeapon("Close Combat Weapon", False, 1, "1", 4, 4, 0, "1", [])
        ],
        points_cost=110
    ))

    # Lychguard (elite melee)
    p2_units.append(BattleUnit(
        id="nec_lychguard",
        name="Lychguard",
        player_id=1,
        faction="Necrons",
        stats=BattleUnitStats(movement=5, toughness=5, save=3, invuln_save=4, wounds=2, leadership=6, oc=1),
        model_count=5,
        wounds_per_model=2,
        current_wounds=10,
        ranged_weapons=[],
        melee_weapons=[
            BattleWeapon(
                name="Warscythe",
                is_ranged=False,
                range=1,
                attacks="3",
                bs_ws=3,
                strength=7,
                ap=-2,
                damage="2",
                keywords=[]
            )
        ],
        points_cost=130
    ))

    print(f"   Added {len(p2_units)} units")

    # Create battle simulator
    print("\n🎮 Initializing battle simulator...")
    simulator = BattleSimulator(battlefield)

    for unit in p1_units:
        simulator.add_unit(unit)

    for unit in p2_units:
        simulator.add_unit(unit)

    # Run battle
    print("\n⚔️ BATTLE START!\n")
    print("=" * 60)

    results = simulator.simulate_battle(max_turns=5)

    # Display results
    print("\n" + "=" * 60)
    print("🏆 BATTLE COMPLETE!")
    print("=" * 60)

    print(f"\n📊 Final Scores:")
    print(f"   Winner: {results['winner']}")
    print(f"   Turns Played: {results['turns_played']}")
    print(f"   Player 1 VP: {results['player_1_vp']}")
    print(f"   Player 2 VP: {results['player_2_vp']}")

    print(f"\n💀 Casualties:")
    print(f"   Player 1 Units Alive: {results['player_1_units_alive']} ({results['player_1_points_remaining']} pts)")
    print(f"   Player 2 Units Alive: {results['player_2_units_alive']} ({results['player_2_points_remaining']} pts)")

    # Show key events
    print(f"\n📜 Key Battle Events:")
    print("-" * 60)

    key_events = [e for e in results['battle_log'] if e.damage_dealt > 0 or e.event_type in ['charge', 'objective']]

    for event in key_events[:20]:  # First 20 key events
        icon = {
            'shooting': '🔫',
            'charge': '⚡',
            'melee': '⚔️',
            'objective': '🏆'
        }.get(event.event_type, '📝')

        player_name = "Space Marines" if event.player == 0 else "Necrons"

        print(f"Turn {event.turn} | {event.phase.value:10} | {player_name:15} | {icon} {event.description}")

    print("\n✅ Battle simulation complete!")

    return results


if __name__ == "__main__":
    results = create_test_battle()
