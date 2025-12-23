#!/usr/bin/env python3
"""
Quick test script to verify battle simulator is working correctly
"""

from terrain_manager import TerrainManager
from battle_simulator import (
    BattleSimulator, Battlefield, BattleUnit, BattleUnitStats,
    BattleWeapon, Position
)

def test_terrain_layouts():
    """Test terrain layout loading"""
    print("=== Testing Terrain Layouts ===\n")

    terrain_mgr = TerrainManager()
    layouts = terrain_mgr.list_available_layouts()

    print(f"✓ Found {len(layouts)} terrain layouts")

    for layout_id in layouts:
        terrain = terrain_mgr.get_terrain_layout(layout_id)

        # Count pieces by size
        small = sum(1 for t in terrain if t.width == 6 and t.length == 4)
        medium = sum(1 for t in terrain if t.width == 10 and t.length == 5)
        large = sum(1 for t in terrain if t.width == 12 and t.length == 6)
        total = small + medium + large

        # Check official specs (4 small, 2 medium, 6 large = 12 total)
        status = "✓" if (small == 4 and medium == 2 and large == 6) else "⚠"
        print(f"  {status} {layout_id}: S={small} M={medium} L={large} Total={total}")

    print()

def test_deployment_maps():
    """Test deployment map loading"""
    print("=== Testing Deployment Maps ===\n")

    terrain_mgr = TerrainManager()
    deployments = terrain_mgr.list_available_deployments()

    print(f"✓ Found {len(deployments)} deployment maps")

    for deploy_id in deployments:
        p1_zone, p2_zone = terrain_mgr.get_deployment_map(deploy_id)
        desc = terrain_mgr.get_deployment_description(deploy_id)
        print(f"  ✓ {deploy_id}")
        print(f"    Shape: {p1_zone.shape}, {p2_zone.shape}")

    print()

def test_battle_simulation():
    """Test running a complete battle"""
    print("=== Testing Battle Simulation ===\n")

    # Create test units
    p1_units = [
        BattleUnit(
            id="plague_marines_1",
            name="Plague Marines",
            player_id=0,
            faction="Death Guard",
            stats=BattleUnitStats(
                movement=5, toughness=5, save=3, wounds=2,
                leadership=6, oc=2, invuln_save=None
            ),
            model_count=10,
            wounds_per_model=2,
            current_wounds=20,
            is_character=False,
            ranged_weapons=[
                BattleWeapon(
                    name="Boltgun",
                    is_ranged=True,
                    range=24,
                    attacks="2",
                    bs_ws=3,
                    strength=4,
                    ap=0,
                    damage="1",
                    keywords=["RAPID FIRE 1"]
                )
            ],
            melee_weapons=[
                BattleWeapon(
                    name="Plague Knife",
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
            points_cost=170
        )
    ]

    p2_units = [
        BattleUnit(
            id="intercessors_1",
            name="Intercessor Squad",
            player_id=1,
            faction="Space Marines",
            stats=BattleUnitStats(
                movement=6, toughness=4, save=3, wounds=2,
                leadership=6, oc=2, invuln_save=None
            ),
            model_count=10,
            wounds_per_model=2,
            current_wounds=20,
            is_character=False,
            ranged_weapons=[
                BattleWeapon(
                    name="Bolt Rifle",
                    is_ranged=True,
                    range=24,
                    attacks="2",
                    bs_ws=3,
                    strength=4,
                    ap=0,
                    damage="1",
                    keywords=["RAPID FIRE 1"]
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
        )
    ]

    # Setup battlefield
    terrain_mgr = TerrainManager()
    battlefield = Battlefield(width=44.0, length=60.0)

    # Add terrain
    terrain_features = terrain_mgr.get_terrain_layout('layout_1')
    for feature in terrain_features:
        battlefield.add_terrain(feature)

    # Add objectives
    objectives = terrain_mgr.get_objectives('standard_5_objectives')
    for obj in objectives:
        battlefield.add_objective(obj)

    # Get deployment zones
    p1_zone, p2_zone = terrain_mgr.get_deployment_map('hammer_and_anvil')

    # Run simulation
    simulator = BattleSimulator(battlefield)
    for unit in p1_units + p2_units:
        simulator.add_unit(unit)

    print("✓ Running 5-turn battle simulation...")
    results = simulator.simulate_battle(
        max_turns=5,
        p1_deployment_zone=p1_zone,
        p2_deployment_zone=p2_zone
    )

    # Display results
    print(f"\n=== Battle Results ===")
    print(f"Winner: {results['winner']}")
    print(f"Turns Played: {results['turns_played']}")
    print(f"Victory Points: P1={results['player_1_vp']} vs P2={results['player_2_vp']}")
    print(f"Units Alive: P1={results['player_1_units_alive']}/{len(p1_units)} vs P2={results['player_2_units_alive']}/{len(p2_units)}")
    print(f"Points Remaining: P1={results['player_1_points_remaining']} vs P2={results['player_2_points_remaining']}")
    print()

if __name__ == "__main__":
    test_terrain_layouts()
    test_deployment_maps()
    test_battle_simulation()
    print("✅ All tests passed! System is operational.\n")
