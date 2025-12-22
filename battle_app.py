"""
Warhammer 40k Battle Simulator - Streamlit UI
Full battle simulation with movement, terrain, and strategy
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import json
from pathlib import Path
from typing import List, Optional

from battle_simulator import (
    BattleSimulator, Battlefield, Position, Objective,
    TerrainFeature, Terrain, BattleUnit, Phase
)
from roster_parser import parse_roster
from roster_to_battle import convert_roster_to_battle_units


# Page config
st.set_page_config(
    page_title="40k Battle Simulator",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)


@st.cache_data
def load_roster_from_file(file_path: str, player_id: int):
    """Load and convert roster file"""
    roster = parse_roster(file_path)
    battle_units = convert_roster_to_battle_units(roster, player_id)
    return roster, battle_units


def create_battlefield_visualization(battlefield: Battlefield,
                                     player_1_units: List[BattleUnit] = None,
                                     player_2_units: List[BattleUnit] = None,
                                     p1_deployment_zone=None,
                                     p2_deployment_zone=None,
                                     show_units: bool = True) -> go.Figure:
    """Create interactive battlefield map with rectangles"""

    fig = go.Figure()

    # Draw battlefield boundary
    fig.add_shape(
        type="rect",
        x0=0, y0=0, x1=battlefield.width, y1=battlefield.length,
        line=dict(color="white", width=2),
        fillcolor="rgba(20,20,20,0.3)"
    )

    # Draw deployment zones from zone objects if provided
    if p1_deployment_zone and p2_deployment_zone:
        # Player 1 zone
        if p1_deployment_zone.shape == 'rectangle':
            bounds = p1_deployment_zone.bounds
            fig.add_shape(
                type="rect",
                x0=bounds['x_min'], y0=bounds['y_min'],
                x1=bounds['x_max'], y1=bounds['y_max'],
                line=dict(color="cyan", width=2, dash="dash"),
                fillcolor="rgba(0,255,255,0.1)",
                layer="below"
            )
            # Add label
            fig.add_annotation(
                x=(bounds['x_min'] + bounds['x_max']) / 2,
                y=(bounds['y_min'] + bounds['y_max']) / 2,
                text="P1 Deployment",
                showarrow=False,
                font=dict(size=14, color="cyan"),
                opacity=0.6
            )

        # Player 2 zone
        if p2_deployment_zone.shape == 'rectangle':
            bounds = p2_deployment_zone.bounds
            fig.add_shape(
                type="rect",
                x0=bounds['x_min'], y0=bounds['y_min'],
                x1=bounds['x_max'], y1=bounds['y_max'],
                line=dict(color="orange", width=2, dash="dash"),
                fillcolor="rgba(255,165,0,0.1)",
                layer="below"
            )
            # Add label
            fig.add_annotation(
                x=(bounds['x_min'] + bounds['x_max']) / 2,
                y=(bounds['y_min'] + bounds['y_max']) / 2,
                text="P2 Deployment",
                showarrow=False,
                font=dict(size=14, color="orange"),
                opacity=0.6
            )

    # Draw terrain as rectangles
    for terrain in battlefield.terrain:
        color = {
            Terrain.LIGHT_COVER: "rgba(100,200,100,0.5)",
            Terrain.HEAVY_COVER: "rgba(150,150,50,0.6)",
            Terrain.OBSCURING: "rgba(80,80,80,0.7)",
            Terrain.IMPASSABLE: "rgba(50,50,50,0.9)"
        }.get(terrain.terrain_type, "rgba(150,150,150,0.5)")

        # Calculate rectangle corners
        half_width = terrain.width / 2
        half_length = terrain.length / 2

        fig.add_shape(
            type="rect",
            x0=terrain.center.x - half_width,
            y0=terrain.center.y - half_length,
            x1=terrain.center.x + half_width,
            y1=terrain.center.y + half_length,
            fillcolor=color,
            line=dict(color="gray" if not terrain.blocks_los else "red", width=2),
            layer="above"
        )

        # Add terrain label with height
        label_text = f"{terrain.name}"
        if terrain.blocks_los:
            label_text += f"\n{terrain.height}\" (LOS)"

        fig.add_annotation(
            x=terrain.center.x,
            y=terrain.center.y,
            text=label_text,
            showarrow=False,
            font=dict(size=9, color="white"),
            bgcolor="rgba(0,0,0,0.6)",
            borderpad=2
        )

    # Draw objectives
    for obj in battlefield.objectives:
        color = "gold"
        if obj.controlled_by == 0:
            color = "blue"
        elif obj.controlled_by == 1:
            color = "red"

        fig.add_scatter(
            x=[obj.position.x],
            y=[obj.position.y],
            mode='markers+text',
            marker=dict(size=20, color=color, symbol='star', line=dict(width=2, color='black')),
            text=[obj.name],
            textposition="top center",
            textfont=dict(size=10, color="white"),
            name=obj.name,
            showlegend=False
        )

    # Draw units only if requested and units exist
    if show_units and player_1_units:
        for unit in player_1_units:
            if unit.is_destroyed():
                continue

            fig.add_scatter(
                x=[unit.position.x],
                y=[unit.position.y],
                mode='markers+text',
                marker=dict(
                    size=15 if unit.is_character else 12,
                    color='blue',
                    symbol='diamond' if unit.is_character else 'circle',
                    line=dict(width=2, color='white' if not unit.in_melee else 'yellow')
                ),
                text=[f"{unit.name[:15]} ({unit.models_remaining()})"],
                textposition="top center",
                textfont=dict(size=8, color="lightblue"),
                name=unit.name,
                hovertext=f"{unit.name}<br>Models: {unit.models_remaining()}/{unit.model_count}<br>"
                          f"Wounds: {unit.current_wounds}/{unit.model_count * unit.wounds_per_model}",
                hoverinfo="text",
                showlegend=False
            )

    if show_units and player_2_units:
        for unit in player_2_units:
            if unit.is_destroyed():
                continue

            fig.add_scatter(
                x=[unit.position.x],
                y=[unit.position.y],
                mode='markers+text',
                marker=dict(
                    size=15 if unit.is_character else 12,
                    color='red',
                    symbol='diamond' if unit.is_character else 'circle',
                    line=dict(width=2, color='white' if not unit.in_melee else 'yellow')
                ),
                text=[f"{unit.name[:15]} ({unit.models_remaining()})"],
                textposition="bottom center",
                textfont=dict(size=8, color="lightcoral"),
                name=unit.name,
                hovertext=f"{unit.name}<br>Models: {unit.models_remaining()}/{unit.model_count}<br>"
                          f"Wounds: {unit.current_wounds}/{unit.model_count * unit.wounds_per_model}",
                hoverinfo="text",
                showlegend=False
            )

    # Layout
    fig.update_layout(
        title="Battlefield Map",
        xaxis=dict(title="Width (inches)", range=[0, battlefield.width], showgrid=True),
        yaxis=dict(title="Length (inches)", range=[0, battlefield.length], showgrid=True),
        plot_bgcolor='#1a1a1a',
        paper_bgcolor='#0e0e0e',
        font=dict(color='white'),
        height=700,
        hovermode='closest'
    )

    return fig


def create_battle_timeline(battle_log: List) -> go.Figure:
    """Create timeline visualization of battle events"""

    df_events = pd.DataFrame([
        {
            'Turn': event.turn,
            'Phase': event.phase.value,
            'Player': f"Player {event.player + 1}",
            'Type': event.event_type,
            'Description': event.description,
            'Damage': event.damage_dealt,
            'Kills': event.models_killed
        }
        for event in battle_log
    ])

    # Damage over time
    fig = go.Figure()

    for player in [0, 1]:
        player_events = [e for e in battle_log if e.player == player and e.damage_dealt > 0]

        if player_events:
            fig.add_scatter(
                x=[f"T{e.turn} {e.phase.value}" for e in player_events],
                y=[e.damage_dealt for e in player_events],
                mode='lines+markers',
                name=f"Player {player + 1} Damage",
                line=dict(color='blue' if player == 0 else 'red')
            )

    fig.update_layout(
        title="Damage Dealt Over Battle",
        xaxis_title="Turn & Phase",
        yaxis_title="Damage Dealt",
        plot_bgcolor='#1a1a1a',
        paper_bgcolor='#0e0e0e',
        font=dict(color='white'),
        height=400
    )

    return fig


def main():
    st.title("⚔️ Warhammer 40k Battle Simulator")
    st.markdown("Full battle simulation with movement, terrain, and AI strategy")

    # Sidebar - battle setup
    with st.sidebar:
        st.header("⚙️ Battle Setup")

        # Upload rosters or use test data
        roster_source = st.radio("Roster Source", ["Upload Files", "Test Battle"])

        if roster_source == "Upload Files":
            st.subheader("Player 1 Army")
            p1_file = st.file_uploader("Upload Player 1 Roster (.ros)", type=['ros', 'json'], key='p1')

            st.subheader("Player 2 Army")
            p2_file = st.file_uploader("Upload Player 2 Roster (.ros)", type=['ros', 'json'], key='p2')

            if p1_file and p2_file:
                # Save uploaded files temporarily
                p1_path = Path("/tmp/p1_roster.ros")
                p2_path = Path("/tmp/p2_roster.ros")

                with open(p1_path, 'wb') as f:
                    f.write(p1_file.getvalue())
                with open(p2_path, 'wb') as f:
                    f.write(p2_file.getvalue())

                p1_roster, p1_units = load_roster_from_file(str(p1_path), 0)
                p2_roster, p2_units = load_roster_from_file(str(p2_path), 1)

                st.success(f"✅ Player 1: {len(p1_units)} units loaded")
                st.success(f"✅ Player 2: {len(p2_units)} units loaded")
            else:
                st.info("Upload both rosters to begin")
                return

        else:
            st.info("Using test battle scenario")
            # Create test units
            from battle_simulator import BattleUnitStats, BattleWeapon

            # Test unit for Player 1
            p1_units = [
                BattleUnit(
                    id="test_p1_1",
                    name="Space Marine Intercessors",
                    player_id=0,
                    faction="Space Marines",
                    stats=BattleUnitStats(movement=6, toughness=4, save=3, wounds=2, leadership=6, oc=2),
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
                )
            ]

            # Test unit for Player 2
            p2_units = [
                BattleUnit(
                    id="test_p2_1",
                    name="Necron Warriors",
                    player_id=1,
                    faction="Necrons",
                    stats=BattleUnitStats(movement=5, toughness=4, save=4, wounds=1, leadership=7, oc=2),
                    model_count=10,
                    wounds_per_model=1,
                    current_wounds=10,
                    ranged_weapons=[
                        BattleWeapon(
                            name="Gauss Flayer",
                            is_ranged=True,
                            range=24,
                            attacks="1",
                            bs_ws=4,
                            strength=4,
                            ap=-1,
                            damage="1",
                            keywords=["Lethal Hits"]
                        )
                    ],
                    melee_weapons=[
                        BattleWeapon(
                            name="Close Combat Weapon",
                            is_ranged=False,
                            range=1,
                            attacks="1",
                            bs_ws=4,
                            strength=4,
                            ap=0,
                            damage="1",
                            keywords=[]
                        )
                    ],
                    points_cost=110
                )
            ]

        st.divider()

        st.subheader("🗺️ Mission Setup")

        # Initialize terrain manager
        from terrain_manager import TerrainManager
        terrain_mgr = TerrainManager()

        # Deployment map selection
        deployment_options = {
            "Hammer and Anvil": "hammer_and_anvil",
            "Dawn of War": "dawn_of_war",
            "Search and Destroy": "search_and_destroy",
            "Sweeping Engagement": "sweeping_engagement",
            "Tipping Point": "tipping_point",
            "Crucible of Battle": "crucible_of_battle"
        }

        selected_deployment_name = st.selectbox(
            "Deployment Map",
            list(deployment_options.keys()),
            help="Official 10th Edition deployment zones"
        )
        selected_deployment = deployment_options[selected_deployment_name]

        # Show deployment description
        st.caption(terrain_mgr.get_deployment_description(selected_deployment))

        # Terrain layout selection
        terrain_layout_options = {
            "GW Tournament Layout 1": "layout_1",
            "GW Tournament Layout 2": "layout_2",
            "GW Tournament Layout 3": "layout_3"
        }

        selected_terrain_name = st.selectbox(
            "Terrain Layout",
            list(terrain_layout_options.keys()),
            help="Official GW terrain configurations"
        )
        selected_terrain = terrain_layout_options[selected_terrain_name]

        # Objective placement selection
        objective_options = {
            "Standard 5 Objectives": "standard_5_objectives",
            "Diagonal 5 Objectives": "diagonal_5_objectives",
            "Spread 6 Objectives": "spread_6_objectives"
        }

        selected_objectives_name = st.selectbox(
            "Objective Placement",
            list(objective_options.keys()),
            help="Official objective marker positions"
        )
        selected_objectives = objective_options[selected_objectives_name]

        # Battlefield size (fixed for now)
        bf_width, bf_length = 44.0, 60.0

        st.divider()

        st.subheader("⚔️ Battle Settings")
        max_turns = st.slider("Maximum Turns", 1, 5, 5)
        run_battle = st.button("🎮 Run Battle Simulation", type="primary", use_container_width=True)

    # Main content - show preview before battle
    st.header("🗺️ Battlefield Preview")

    # Create preview battlefield
    preview_battlefield = Battlefield(width=bf_width, length=bf_length)

    # Load selected terrain and objectives for preview
    terrain_features = terrain_mgr.get_terrain_layout(selected_terrain)
    for feature in terrain_features:
        preview_battlefield.add_terrain(feature)

    objectives = terrain_mgr.get_objectives(selected_objectives)
    for obj in objectives:
        preview_battlefield.add_objective(obj)

    # Get deployment zones for preview
    p1_preview_zone, p2_preview_zone = terrain_mgr.get_deployment_map(selected_deployment)

    # Show preview
    preview_fig = create_battlefield_visualization(
        preview_battlefield,
        player_1_units=None,
        player_2_units=None,
        p1_deployment_zone=p1_preview_zone,
        p2_deployment_zone=p2_preview_zone,
        show_units=False
    )
    preview_fig.update_layout(title=f"Mission: {selected_deployment_name} | Terrain: {selected_terrain_name}")

    st.plotly_chart(preview_fig, use_container_width=True)

    # Show mission details
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Terrain Pieces", len(preview_battlefield.terrain))
        terrain_types = {}
        for t in preview_battlefield.terrain:
            terrain_types[t.terrain_type.value] = terrain_types.get(t.terrain_type.value, 0) + 1
        for ttype, count in terrain_types.items():
            st.caption(f"  {ttype}: {count}")

    with col2:
        st.metric("Objectives", len(preview_battlefield.objectives))
        obscuring_count = sum(1 for t in preview_battlefield.terrain if t.blocks_los)
        st.caption(f"LOS Blocking: {obscuring_count}")

    with col3:
        st.metric("Deployment", selected_deployment_name)
        st.caption(terrain_mgr.get_deployment_description(selected_deployment).split(':')[1].strip())

    st.divider()

    # Main content
    if 'battle_results' not in st.session_state:
        st.session_state.battle_results = None

    if run_battle:
        with st.spinner("⚔️ Simulating battle..."):
            # Create battlefield
            battlefield = Battlefield(width=bf_width, length=bf_length)

            # Load official terrain layout
            terrain_features = terrain_mgr.get_terrain_layout(selected_terrain)
            for feature in terrain_features:
                battlefield.add_terrain(feature)

            # Load official objectives
            objectives = terrain_mgr.get_objectives(selected_objectives)
            for obj in objectives:
                battlefield.add_objective(obj)

            # Get deployment zones
            p1_deployment_zone, p2_deployment_zone = terrain_mgr.get_deployment_map(selected_deployment)

            # Create battle simulator
            simulator = BattleSimulator(battlefield)

            # Add units
            for unit in p1_units:
                simulator.add_unit(unit)
            for unit in p2_units:
                simulator.add_unit(unit)

            # Run battle with deployment zones
            results = simulator.simulate_battle(
                max_turns=max_turns,
                p1_deployment_zone=p1_deployment_zone,
                p2_deployment_zone=p2_deployment_zone
            )
            st.session_state.battle_results = results
            st.session_state.battlefield = battlefield
            st.session_state.p1_units = p1_units
            st.session_state.p2_units = p2_units
            st.session_state.p1_deployment_zone = p1_deployment_zone
            st.session_state.p2_deployment_zone = p2_deployment_zone

            st.success(f"✅ Battle complete! {results['winner']} wins!")
            st.balloons()

    # Display results
    if st.session_state.battle_results:
        results = st.session_state.battle_results

        # Battle summary
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Winner", results['winner'])
        with col2:
            st.metric("Turns Played", results['turns_played'])
        with col3:
            st.metric("Player 1 VP", results['player_1_vp'])
        with col4:
            st.metric("Player 2 VP", results['player_2_vp'])

        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["📍 Battlefield Map", "📊 Battle Analysis", "📜 Battle Log"])

        with tab1:
            st.subheader("Final Battlefield State")
            fig_map = create_battlefield_visualization(
                st.session_state.battlefield,
                st.session_state.p1_units,
                st.session_state.p2_units,
                p1_deployment_zone=st.session_state.get('p1_deployment_zone'),
                p2_deployment_zone=st.session_state.get('p2_deployment_zone'),
                show_units=True
            )
            st.plotly_chart(fig_map, use_container_width=True)

        with tab2:
            st.subheader("Battle Statistics")

            col1, col2 = st.columns(2)

            with col1:
                st.metric("Player 1 Units Surviving",
                         f"{results['player_1_units_alive']} ({results['player_1_points_remaining']} pts)")

            with col2:
                st.metric("Player 2 Units Surviving",
                         f"{results['player_2_units_alive']} ({results['player_2_points_remaining']} pts)")

            # Damage timeline
            st.subheader("Damage Over Time")
            fig_timeline = create_battle_timeline(results['battle_log'])
            st.plotly_chart(fig_timeline, use_container_width=True)

            # Casualty breakdown
            st.subheader("Casualties by Unit")

            p1_casualties = []
            for unit in st.session_state.p1_units:
                models_lost = unit.model_count - unit.models_remaining()
                if models_lost > 0:
                    p1_casualties.append({
                        'Unit': unit.name,
                        'Models Lost': models_lost,
                        'Points Lost': int(unit.points_cost * (models_lost / unit.model_count))
                    })

            p2_casualties = []
            for unit in st.session_state.p2_units:
                models_lost = unit.model_count - unit.models_remaining()
                if models_lost > 0:
                    p2_casualties.append({
                        'Unit': unit.name,
                        'Models Lost': models_lost,
                        'Points Lost': int(unit.points_cost * (models_lost / unit.model_count))
                    })

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Player 1 Casualties:**")
                if p1_casualties:
                    st.dataframe(pd.DataFrame(p1_casualties), use_container_width=True, hide_index=True)
                else:
                    st.info("No casualties")

            with col2:
                st.write("**Player 2 Casualties:**")
                if p2_casualties:
                    st.dataframe(pd.DataFrame(p2_casualties), use_container_width=True, hide_index=True)
                else:
                    st.info("No casualties")

        with tab3:
            st.subheader("Complete Battle Log")

            # Filter options
            filter_phase = st.multiselect(
                "Filter by Phase",
                options=[p.value for p in Phase],
                default=[p.value for p in Phase]
            )

            filter_type = st.multiselect(
                "Filter by Event Type",
                options=list(set(e.event_type for e in results['battle_log'])),
                default=list(set(e.event_type for e in results['battle_log']))
            )

            # Display log
            for event in results['battle_log']:
                if event.phase.value not in filter_phase or event.event_type not in filter_type:
                    continue

                icon = {
                    'deployment': '🎯',
                    'movement': '🏃',
                    'shooting': '🔫',
                    'charge': '⚡',
                    'melee': '⚔️',
                    'objective': '🏆',
                    'battle-shock': '😱'
                }.get(event.event_type, '📝')

                player_color = "blue" if event.player == 0 else "red"

                st.markdown(
                    f"**Turn {event.turn}** | {event.phase.value} | "
                    f":{player_color}[Player {event.player + 1}] | "
                    f"{icon} {event.description}"
                )

                if event.damage_dealt > 0:
                    st.caption(f"   💥 Damage: {event.damage_dealt} | Models Killed: {event.models_killed}")


if __name__ == "__main__":
    main()
