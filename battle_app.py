"""
Warhammer 40k Battle Simulator - Streamlit UI
Full battle simulation with movement, terrain, and strategy
Includes batch simulation and comprehensive analytics
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass
from collections import defaultdict

from battle_simulator import (
    BattleSimulator, Battlefield, Position, Objective,
    TerrainFeature, Terrain, BattleUnit
)
from roster_parser import parse_roster, Roster
from roster_to_battle import convert_roster_to_battle_units
from terrain_manager import TerrainManager


# Page config
st.set_page_config(
    page_title="40k Battle Simulator",
    page_icon="⚔️",
    layout="wide",
    initial_sidebar_state="expanded"
)


@dataclass
class ArmyConfig:
    """Configuration for an army"""
    name: str
    roster_file: Optional[str] = None
    roster: Optional[Roster] = None
    units: List[BattleUnit] = None
    player_id: int = 0


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
                                     p1_army_name: str = "Player 1",
                                     p2_army_name: str = "Player 2",
                                     show_units: bool = True) -> go.Figure:
    """Create interactive battlefield map"""

    fig = go.Figure()

    # Draw battlefield boundary
    fig.add_shape(
        type="rect",
        x0=0, y0=0, x1=battlefield.width, y1=battlefield.length,
        line=dict(color="white", width=2),
        fillcolor="rgba(20,20,20,0.3)"
    )

    # Deployment zones
    if p1_deployment_zone and p2_deployment_zone:
        def _get_rectangles(zone):
            b = getattr(zone, "bounds", None) or {}
            if isinstance(b, dict) and isinstance(b.get("rectangles"), list):
                return b["rectangles"]
            if isinstance(b, dict) and isinstance(b.get("bounds"), dict):
                inner = b["bounds"]
                if isinstance(inner.get("rectangles"), list):
                    return inner["rectangles"]
            return []

        def _get_vertices(zone):
            verts = getattr(zone, "vertices", None)
            if verts:
                return verts
            b = getattr(zone, "bounds", None) or {}
            if isinstance(b, dict) and b.get("vertices"):
                return b["vertices"]
            return None

        def _get_center_radius(zone):
            b = getattr(zone, "bounds", None) or {}
            if not isinstance(b, dict):
                return None, None
            center = b.get("center")
            radius = b.get("radius")
            if center is None or radius is None:
                return None, None
            return center, radius

        def _get_cutout_circle(zone):
            cutout = getattr(zone, "cutout_circle", None)
            if cutout:
                return cutout
            b = getattr(zone, "bounds", None) or {}
            if isinstance(b, dict):
                return b.get("cutout_circle")
            return None

        def draw_zone(zone, line_color, fill_rgba, label):
            if not zone:
                return

            shape = getattr(zone, "shape", None)
            bounds = getattr(zone, "bounds", None) or {}

            if shape == "rectangle":
                if not isinstance(bounds, dict):
                    return
                fig.add_shape(
                    type="rect",
                    x0=bounds["x_min"], y0=bounds["y_min"],
                    x1=bounds["x_max"], y1=bounds["y_max"],
                    line=dict(color=line_color, width=2, dash="dash"),
                    fillcolor=fill_rgba,
                    layer="below"
                )
                fig.add_annotation(
                    x=(bounds["x_min"] + bounds["x_max"]) / 2,
                    y=(bounds["y_min"] + bounds["y_max"]) / 2,
                    text=label,
                    showarrow=False,
                    font=dict(size=14, color=line_color),
                    opacity=0.6
                )
                return

            if shape == "compound":
                rects = _get_rectangles(zone)
                if not rects:
                    return
                for r in rects:
                    fig.add_shape(
                        type="rect",
                        x0=r["x_min"], y0=r["y_min"],
                        x1=r["x_max"], y1=r["y_max"],
                        line=dict(color=line_color, width=2, dash="dash"),
                        fillcolor=fill_rgba,
                        layer="below"
                    )
                x_min = min(r["x_min"] for r in rects)
                x_max = max(r["x_max"] for r in rects)
                y_min = min(r["y_min"] for r in rects)
                y_max = max(r["y_max"] for r in rects)
                fig.add_annotation(
                    x=(x_min + x_max) / 2,
                    y=(y_min + y_max) / 2,
                    text=label,
                    showarrow=False,
                    font=dict(size=14, color=line_color),
                    opacity=0.6
                )
                return

            if shape in ("triangle", "polygon"):
                verts = _get_vertices(zone)
                if verts and len(verts) >= 3:
                    xs = [v[0] for v in verts] + [verts[0][0]]
                    ys = [v[1] for v in verts] + [verts[0][1]]
                    fig.add_trace(go.Scatter(
                        x=xs, y=ys,
                        mode="lines",
                        fill="toself",
                        fillcolor=fill_rgba,
                        line=dict(color=line_color, width=2, dash="dash"),
                        name=label,
                        showlegend=False,
                        hoverinfo="skip"
                    ))
                    fig.add_annotation(
                        x=sum(v[0] for v in verts) / len(verts),
                        y=sum(v[1] for v in verts) / len(verts),
                        text=label,
                        showarrow=False,
                        font=dict(size=14, color=line_color),
                        opacity=0.6
                    )
                    return

                center, radius = _get_center_radius(zone)
                if center is not None and radius is not None:
                    cx, cy = center[0], center[1]
                    fig.add_shape(
                        type="circle",
                        x0=cx - radius, y0=cy - radius,
                        x1=cx + radius, y1=cy + radius,
                        line=dict(color=line_color, width=2, dash="dash"),
                        fillcolor=fill_rgba,
                        layer="below"
                    )
                    fig.add_annotation(
                        x=cx, y=cy,
                        text=label,
                        showarrow=False,
                        font=dict(size=14, color=line_color),
                        opacity=0.6
                    )
                    return

        draw_zone(p1_deployment_zone, "cyan", "rgba(0,255,255,0.1)", p1_army_name)
        draw_zone(p2_deployment_zone, "orange", "rgba(255,165,0,0.1)", p2_army_name)

        # Draw center cutout circle if any
        cutout = _get_cutout_circle(p1_deployment_zone) or _get_cutout_circle(p2_deployment_zone)
        if cutout and isinstance(cutout, dict) and "center" in cutout and "radius" in cutout:
            cx, cy = cutout["center"]
            r = cutout["radius"]
            fig.add_shape(
                type="circle",
                x0=cx - r, y0=cy - r,
                x1=cx + r, y1=cy + r,
                line=dict(color="white", width=2, dash="dot"),
                fillcolor="rgba(20,20,20,0.95)",
                layer="above"
            )
            fig.add_annotation(
                x=cx, y=cy,
                text="No Man's Land (9\")",
                showarrow=False,
                font=dict(size=12, color="white"),
                opacity=0.7
            )

    # Draw terrain
    for terrain in battlefield.terrain:
        color = {
            Terrain.LIGHT_COVER: "rgba(100,200,100,0.5)",
            Terrain.HEAVY_COVER: "rgba(150,150,50,0.6)",
            Terrain.OBSCURING: "rgba(80,80,80,0.7)",
            Terrain.IMPASSABLE: "rgba(50,50,50,0.9)"
        }.get(terrain.terrain_type, "rgba(150,150,150,0.5)")

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
            mode="markers+text",
            marker=dict(size=20, color=color, symbol="star", line=dict(width=2, color="black")),
            text=[obj.name],
            textposition="top center",
            textfont=dict(size=10, color="white"),
            name=obj.name,
            showlegend=False
        )

    # Draw units
    if show_units and player_1_units:
        for unit in player_1_units:
            if unit.is_destroyed():
                continue
            fig.add_scatter(
                x=[unit.position.x],
                y=[unit.position.y],
                mode="markers+text",
                marker=dict(
                    size=15 if unit.is_character else 12,
                    color="blue",
                    symbol="diamond" if unit.is_character else "circle",
                    line=dict(width=2, color="white" if not unit.in_melee else "yellow")
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
                mode="markers+text",
                marker=dict(
                    size=15 if unit.is_character else 12,
                    color="red",
                    symbol="diamond" if unit.is_character else "circle",
                    line=dict(width=2, color="white" if not unit.in_melee else "yellow")
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

    # Layout - maintain proper aspect ratio (44" × 60" battlefield)
    # Calculate height based on aspect ratio to prevent stretching
    aspect_ratio = battlefield.length / battlefield.width  # 60/44 = 1.36
    fig_width = 700
    fig_height = int(fig_width * aspect_ratio)

    fig.update_layout(
        title="Battlefield Map",
        xaxis=dict(
            title="Width (inches)",
            range=[0, battlefield.width],
            showgrid=True,
            scaleanchor="y",
            scaleratio=1
        ),
        yaxis=dict(
            title="Length (inches)",
            range=[0, battlefield.length],
            showgrid=True,
            constrain="domain"
        ),
        plot_bgcolor="#1a1a1a",
        paper_bgcolor="#0e0e0e",
        font=dict(color="white"),
        width=fig_width,
        height=fig_height,
        hovermode="closest"
    )

    return fig


def run_single_battle(p1_units, p2_units, p1_army_name, p2_army_name,
                      selected_terrain, selected_deployment, selected_objectives, max_turns=5):
    """Run a single battle simulation"""
    # Create battlefield
    battlefield = Battlefield(width=44.0, length=60.0)

    # Initialize terrain manager
    terrain_mgr = TerrainManager()

    # Load terrain layout
    terrain_features = terrain_mgr.get_terrain_layout(selected_terrain)
    for feature in terrain_features:
        battlefield.add_terrain(feature)

    # Load objectives
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

    # Run battle
    results = simulator.simulate_battle(
        max_turns=max_turns,
        p1_deployment_zone=p1_deployment_zone,
        p2_deployment_zone=p2_deployment_zone,
        p1_army_name=p1_army_name,
        p2_army_name=p2_army_name
    )

    # Calculate total army costs for analytics
    p1_total_cost = sum(u.points_cost for u in p1_units)
    p2_total_cost = sum(u.points_cost for u in p2_units)

    # Add costs to results for batch analytics
    results['player_1_points_cost'] = p1_total_cost
    results['player_2_points_cost'] = p2_total_cost

    return {
        'results': results,
        'battlefield': battlefield,
        'p1_units': p1_units,
        'p2_units': p2_units,
        'p1_deployment_zone': p1_deployment_zone,
        'p2_deployment_zone': p2_deployment_zone,
        'p1_army_name': p1_army_name,
        'p2_army_name': p2_army_name
    }


def run_batch_simulations(p1_roster_file, p2_roster_file, p1_army_name, p2_army_name,
                          selected_terrain, selected_deployment, selected_objectives,
                          num_battles, max_turns=5):
    """Run multiple battle simulations and collect statistics"""

    all_results = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i in range(num_battles):
        status_text.text(f"Running battle {i+1} of {num_battles}...")
        progress_bar.progress((i + 1) / num_battles)

        # Load fresh units for each battle
        _, p1_units = load_roster_from_file(p1_roster_file, player_id=0)
        _, p2_units = load_roster_from_file(p2_roster_file, player_id=1)

        # Run battle
        battle_data = run_single_battle(
            p1_units, p2_units, p1_army_name, p2_army_name,
            selected_terrain, selected_deployment, selected_objectives, max_turns
        )

        all_results.append(battle_data)

    progress_bar.empty()
    status_text.empty()

    return all_results


def create_analytics_dashboard(batch_results, p1_army_name, p2_army_name):
    """Create comprehensive analytics from batch simulation results"""

    st.header("📊 Batch Simulation Analytics")

    # Overall statistics
    st.subheader("Overall Results")

    # Determine wins and draws.  The battle simulator sets the
    # ``winner`` field to the name of the winning army or the literal
    # string ``"Draw"``.  Count a win when the ``winner`` matches
    # the corresponding army name and count draws explicitly.  This avoids
    # mismatching against strings like ``"<army> wins!"`` which never occur.
    p1_wins = sum(1 for r in batch_results if r['results']['winner'] == p1_army_name)
    p2_wins = sum(1 for r in batch_results if r['results']['winner'] == p2_army_name)
    draws = sum(1 for r in batch_results if r['results']['winner'] == "Draw")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Battles", len(batch_results))
    with col2:
        st.metric(f"{p1_army_name} Wins", p1_wins, f"{100*p1_wins/len(batch_results):.1f}%")
    with col3:
        st.metric(f"{p2_army_name} Wins", p2_wins, f"{100*p2_wins/len(batch_results):.1f}%")
    with col4:
        st.metric("Draws", draws, f"{100*draws/len(batch_results):.1f}%")

    # Win rate pie chart
    fig_winrate = go.Figure(data=[go.Pie(
        labels=[p1_army_name, p2_army_name, "Draw"],
        values=[p1_wins, p2_wins, draws],
        marker=dict(colors=["#636EFA", "#EF553B", "#00CC96"])
    )])
    fig_winrate.update_layout(title="Win Distribution", height=400)
    st.plotly_chart(fig_winrate, use_container_width=True)

    # Victory Points Analysis
    st.subheader("Victory Points Analysis")

    p1_vps = [r['results']['player_1_vp'] for r in batch_results]
    p2_vps = [r['results']['player_2_vp'] for r in batch_results]

    col1, col2 = st.columns(2)
    with col1:
        st.metric(f"{p1_army_name} Avg VP", f"{np.mean(p1_vps):.1f}",
                  f"± {np.std(p1_vps):.1f}")
    with col2:
        st.metric(f"{p2_army_name} Avg VP", f"{np.mean(p2_vps):.1f}",
                  f"± {np.std(p2_vps):.1f}")

    # VP distribution histogram
    fig_vp = go.Figure()
    fig_vp.add_trace(go.Histogram(
        x=p1_vps,
        name=p1_army_name,
        opacity=0.7,
        marker_color='blue'
    ))
    fig_vp.add_trace(go.Histogram(
        x=p2_vps,
        name=p2_army_name,
        opacity=0.7,
        marker_color='red'
    ))
    fig_vp.update_layout(
        title="Victory Points Distribution",
        xaxis_title="Victory Points",
        yaxis_title="Frequency",
        barmode='overlay',
        height=400
    )
    st.plotly_chart(fig_vp, use_container_width=True)

    # Casualty Analysis
    st.subheader("Casualty Analysis")

    # Calculate points lost (now always available since we add it in run_single_battle)
    p1_points_lost: List[float] = []
    p2_points_lost: List[float] = []
    p1_total_costs: List[float] = []
    p2_total_costs: List[float] = []

    for battle in batch_results:
        res = battle['results']
        p1_total = res['player_1_points_cost']
        p2_total = res['player_2_points_cost']

        p1_total_costs.append(p1_total)
        p2_total_costs.append(p2_total)

        p1_lost = p1_total - res['player_1_points_remaining']
        p2_lost = p2_total - res['player_2_points_remaining']

        p1_points_lost.append(p1_lost)
        p2_points_lost.append(p2_lost)

    col1, col2 = st.columns(2)
    with col1:
        avg_lost = np.mean(p1_points_lost)
        avg_total = np.mean(p1_total_costs)
        st.metric(
            f"{p1_army_name} Avg Points Lost",
            f"{avg_lost:.0f}",
            f"{100 * avg_lost / avg_total:.1f}% of army"
        )
    with col2:
        avg_lost = np.mean(p2_points_lost)
        avg_total = np.mean(p2_total_costs)
        st.metric(
            f"{p2_army_name} Avg Points Lost",
            f"{avg_lost:.0f}",
            f"{100 * avg_lost / avg_total:.1f}% of army"
        )

    # Unit Performance Analysis
    st.subheader("Unit Performance")

    # Collect unit statistics
    p1_unit_stats = defaultdict(lambda: {'total_battles': 0, 'survived': 0, 'kills': 0})
    p2_unit_stats = defaultdict(lambda: {'total_battles': 0, 'survived': 0, 'kills': 0})

    for battle in batch_results:
        for unit in battle['p1_units']:
            p1_unit_stats[unit.name]['total_battles'] += 1
            if not unit.is_destroyed():
                p1_unit_stats[unit.name]['survived'] += 1

        for unit in battle['p2_units']:
            p2_unit_stats[unit.name]['total_battles'] += 1
            if not unit.is_destroyed():
                p2_unit_stats[unit.name]['survived'] += 1

    # Create unit performance dataframes
    p1_unit_df = pd.DataFrame([
        {
            'Unit': name,
            'Survival Rate': f"{100*stats['survived']/stats['total_battles']:.1f}%",
            'Battles': stats['total_battles']
        }
        for name, stats in p1_unit_stats.items()
    ])

    p2_unit_df = pd.DataFrame([
        {
            'Unit': name,
            'Survival Rate': f"{100*stats['survived']/stats['total_battles']:.1f}%",
            'Battles': stats['total_battles']
        }
        for name, stats in p2_unit_stats.items()
    ])

    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**{p1_army_name} Unit Performance**")
        st.dataframe(p1_unit_df, use_container_width=True)
    with col2:
        st.write(f"**{p2_army_name} Unit Performance**")
        st.dataframe(p2_unit_df, use_container_width=True)

    # Battle Length Analysis
    st.subheader("Battle Dynamics")

    turns_played = [r['results']['turns_played'] for r in batch_results]

    col1, col2 = st.columns(2)
    with col1:
        fig_turns = go.Figure(data=[go.Histogram(
            x=turns_played,
            nbinsx=5,
            marker_color='purple'
        )])
        fig_turns.update_layout(
            title="Battle Length Distribution",
            xaxis_title="Turns Played",
            yaxis_title="Number of Battles",
            height=300
        )
        st.plotly_chart(fig_turns, use_container_width=True)

    with col2:
        st.metric("Average Battle Length", f"{np.mean(turns_played):.1f} turns")
        st.metric("Shortest Battle", f"{min(turns_played)} turns")
        st.metric("Longest Battle", f"{max(turns_played)} turns")
        st.metric("Std Deviation", f"{np.std(turns_played):.2f} turns")

    # Victory Margin Analysis
    st.subheader("Victory Margin Analysis")

    vp_margins = []
    for r in batch_results:
        margin = r['results']['player_1_vp'] - r['results']['player_2_vp']
        vp_margins.append(margin)

    fig_margin = go.Figure()
    fig_margin.add_trace(go.Histogram(
        x=vp_margins,
        nbinsx=20,
        marker_color='teal',
        name='VP Margin'
    ))
    fig_margin.add_vline(x=0, line_dash="dash", line_color="white", annotation_text="Even")
    fig_margin.update_layout(
        title=f"Victory Point Margin Distribution ({p1_army_name} perspective)",
        xaxis_title=f"VP Margin (Positive = {p1_army_name} ahead)",
        yaxis_title="Number of Battles",
        height=350
    )
    st.plotly_chart(fig_margin, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average VP Margin", f"{np.mean(vp_margins):.1f} VP")
    with col2:
        close_games = sum(1 for m in vp_margins if abs(m) <= 10)
        st.metric("Close Games (≤10 VP)", f"{close_games} ({100*close_games/len(batch_results):.1f}%)")
    with col3:
        blowouts = sum(1 for m in vp_margins if abs(m) >= 30)
        st.metric("Decisive Victories (≥30 VP)", f"{blowouts} ({100*blowouts/len(batch_results):.1f}%)")

    # Wins by Battle Length
    st.subheader("Performance Over Time")

    # Group battles by turn length and calculate win rates
    turn_win_data = defaultdict(lambda: {'p1': 0, 'p2': 0, 'draw': 0})
    for r in batch_results:
        turn = r['results']['turns_played']
        winner = r['results']['winner']
        if winner == p1_army_name:
            turn_win_data[turn]['p1'] += 1
        elif winner == p2_army_name:
            turn_win_data[turn]['p2'] += 1
        else:
            turn_win_data[turn]['draw'] += 1

    turns_sorted = sorted(turn_win_data.keys())
    p1_wins_by_turn = [turn_win_data[t]['p1'] for t in turns_sorted]
    p2_wins_by_turn = [turn_win_data[t]['p2'] for t in turns_sorted]
    draws_by_turn = [turn_win_data[t]['draw'] for t in turns_sorted]

    fig_turn_wins = go.Figure()
    fig_turn_wins.add_trace(go.Bar(name=p1_army_name, x=turns_sorted, y=p1_wins_by_turn, marker_color='blue'))
    fig_turn_wins.add_trace(go.Bar(name=p2_army_name, x=turns_sorted, y=p2_wins_by_turn, marker_color='red'))
    fig_turn_wins.add_trace(go.Bar(name='Draw', x=turns_sorted, y=draws_by_turn, marker_color='gray'))

    fig_turn_wins.update_layout(
        title="Wins by Battle Length",
        xaxis_title="Turns Played",
        yaxis_title="Number of Wins",
        barmode='stack',
        height=350
    )
    st.plotly_chart(fig_turn_wins, use_container_width=True)

    # Casualty Rate Analysis
    st.subheader("Casualty Rate Comparison")

    p1_casualty_rates = [100 * loss / total for loss, total in zip(p1_points_lost, p1_total_costs)]
    p2_casualty_rates = [100 * loss / total for loss, total in zip(p2_points_lost, p2_total_costs)]

    fig_casualties = go.Figure()
    fig_casualties.add_trace(go.Box(
        y=p1_casualty_rates,
        name=p1_army_name,
        marker_color='blue',
        boxmean='sd'
    ))
    fig_casualties.add_trace(go.Box(
        y=p2_casualty_rates,
        name=p2_army_name,
        marker_color='red',
        boxmean='sd'
    ))

    fig_casualties.update_layout(
        title="Casualty Rate Distribution (% of Army Lost)",
        yaxis_title="Casualty Rate (%)",
        height=400
    )
    st.plotly_chart(fig_casualties, use_container_width=True)

    # Head-to-Head Performance Metrics
    st.subheader("Head-to-Head Comparison")

    comparison_data = {
        'Metric': [
            'Win Rate',
            'Avg Victory Points',
            'Avg Points Lost',
            'Avg Casualty Rate',
            'Avg Surviving Units'
        ],
        p1_army_name: [
            f"{100*p1_wins/len(batch_results):.1f}%",
            f"{np.mean([r['results']['player_1_vp'] for r in batch_results]):.1f}",
            f"{np.mean(p1_points_lost):.0f}",
            f"{np.mean(p1_casualty_rates):.1f}%",
            f"{np.mean([r['results']['player_1_units_alive'] for r in batch_results]):.1f}"
        ],
        p2_army_name: [
            f"{100*p2_wins/len(batch_results):.1f}%",
            f"{np.mean([r['results']['player_2_vp'] for r in batch_results]):.1f}",
            f"{np.mean(p2_points_lost):.0f}",
            f"{np.mean(p2_casualty_rates):.1f}%",
            f"{np.mean([r['results']['player_2_units_alive'] for r in batch_results]):.1f}"
        ]
    }

    df_comparison = pd.DataFrame(comparison_data)
    st.dataframe(df_comparison, use_container_width=True, hide_index=True)


def main():
    st.title("⚔️ Warhammer 40k Battle Simulator")
    st.markdown("*Full battle simulation with official GW terrain layouts and deployment maps*")

    # Initialize session state
    if 'battle_results' not in st.session_state:
        st.session_state.battle_results = None
    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = None

    # Initialize terrain manager
    terrain_mgr = TerrainManager()

    # Sidebar - Army Configuration
    with st.sidebar:
        st.header("⚔️ Army Setup")

        # Simulation mode
        sim_mode = st.radio(
            "Simulation Mode",
            ["Single Battle", "Batch Simulation (Analytics)"],
            help="Single battle for detailed results, batch for statistical analysis"
        )

        st.divider()

        # Army 1
        st.subheader("Army 1")

        # Initialize session state for army name if not exists
        if 'p1_army_name' not in st.session_state:
            st.session_state.p1_army_name = "Player 1"

        p1_roster_file = st.file_uploader("Upload Roster (JSON)", type=["json"], key="p1_file")

        # Load roster and auto-populate army name
        if p1_roster_file is not None:
            # Save uploaded file temporarily and load it
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp_file:
                tmp_file.write(p1_roster_file.getvalue())
                tmp_path = tmp_file.name

            p1_roster, p1_units = load_roster_from_file(tmp_path, player_id=0)

            # Auto-populate army name from roster faction
            faction_name = p1_roster.faction if p1_roster.faction else "Player 1"
            st.session_state.p1_army_name = faction_name

            st.success(f"✓ Loaded {len(p1_units)} units from {faction_name}")

            # Clean up temp file
            Path(tmp_path).unlink()
        else:
            p1_units = []

        # Display the current army name
        st.info(f"Army: **{st.session_state.p1_army_name}**")
        p1_army_name = st.session_state.p1_army_name

        st.divider()

        # Army 2
        st.subheader("Army 2")

        # Initialize session state for army name if not exists
        if 'p2_army_name' not in st.session_state:
            st.session_state.p2_army_name = "Player 2"

        p2_roster_file = st.file_uploader("Upload Roster (JSON)", type=["json"], key="p2_file")

        # Load roster and auto-populate army name
        if p2_roster_file is not None:
            # Save uploaded file temporarily and load it
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp_file:
                tmp_file.write(p2_roster_file.getvalue())
                tmp_path = tmp_file.name

            p2_roster, p2_units = load_roster_from_file(tmp_path, player_id=1)

            # Auto-populate army name from roster faction
            faction_name = p2_roster.faction if p2_roster.faction else "Player 2"
            st.session_state.p2_army_name = faction_name

            st.success(f"✓ Loaded {len(p2_units)} units from {faction_name}")

            # Clean up temp file
            Path(tmp_path).unlink()
        else:
            p2_units = []

        # Display the current army name
        st.info(f"Army: **{st.session_state.p2_army_name}**")
        p2_army_name = st.session_state.p2_army_name

        st.divider()

        # Mission Setup
        st.subheader("🗺️ Mission Setup")

        # Deployment map
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
        st.caption(terrain_mgr.get_deployment_description(selected_deployment))

        # Terrain layout
        terrain_layout_options = {
            "Layout 1 - L-Shaped Center": "layout_1",
            "Layout 2 - Central Corridor": "layout_2",
            "Layout 3 - Diagonal Cross": "layout_3",
            "Layout 4 - Fortress Center": "layout_4",
            "Layout 5 - Flanking Ruins": "layout_5",
            "Layout 6 - Symmetrical Spread": "layout_6",
            "Layout 7 - Urban Ruins": "layout_7",
            "Layout 8 - Open Battlefield": "layout_8"
        }

        selected_terrain_name = st.selectbox(
            "Terrain Layout",
            list(terrain_layout_options.keys()),
            help="Official GW Chapter Approved 2025-26 layouts"
        )
        selected_terrain = terrain_layout_options[selected_terrain_name]

        # Objective placement
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

        st.divider()

        # Battle Settings
        st.subheader("⚔️ Battle Settings")
        max_turns = st.slider("Maximum Turns", 1, 5, 5)

        if sim_mode == "Batch Simulation (Analytics)":
            num_battles = st.slider("Number of Battles", 10, 40000, 1000, step=10,
                                    help="Run multiple simulations for statistical analysis")

        # Run button
        if sim_mode == "Single Battle":
            run_battle = st.button("🎮 Run Battle", type="primary", use_container_width=True)
        else:
            run_batch = st.button(f"🎲 Run {num_battles} Battles", type="primary", use_container_width=True)

    # Main content area
    st.header("🗺️ Battlefield")

    # Create battlefield for visualization
    if st.session_state.battle_results:
        # Show battle results on map
        battle_data = st.session_state.battle_results
        battlefield_fig = create_battlefield_visualization(
            battle_data['battlefield'],
            battle_data['p1_units'],
            battle_data['p2_units'],
            p1_deployment_zone=battle_data['p1_deployment_zone'],
            p2_deployment_zone=battle_data['p2_deployment_zone'],
            p1_army_name=p1_army_name,
            p2_army_name=p2_army_name,
            show_units=True
        )
        battlefield_fig.update_layout(
            title=f"Battle Results: {battle_data['results']['winner']}"
        )
    else:
        # Preview mode - no units
        preview_battlefield = Battlefield(width=44.0, length=60.0)
        terrain_features = terrain_mgr.get_terrain_layout(selected_terrain)
        for feature in terrain_features:
            preview_battlefield.add_terrain(feature)
        objectives = terrain_mgr.get_objectives(selected_objectives)
        for obj in objectives:
            preview_battlefield.add_objective(obj)
        p1_preview_zone, p2_preview_zone = terrain_mgr.get_deployment_map(selected_deployment)

        battlefield_fig = create_battlefield_visualization(
            preview_battlefield,
            player_1_units=None,
            player_2_units=None,
            p1_deployment_zone=p1_preview_zone,
            p2_deployment_zone=p2_preview_zone,
            p1_army_name=p1_army_name,
            p2_army_name=p2_army_name,
            show_units=False
        )
        battlefield_fig.update_layout(
            title=f"Mission: {selected_deployment_name} | Terrain: {selected_terrain_name}"
        )

    # Display the single battlefield map
    st.plotly_chart(battlefield_fig, use_container_width=True)

    # Show mission details (only in preview mode)
    if st.session_state.battle_results is None:
        col1, col2, col3 = st.columns(3)
        with col1:
            terrain_count = len(terrain_features)
            st.metric("Terrain Pieces", terrain_count)
            obscuring_count = sum(1 for t in terrain_features if t.blocks_los)
            st.caption(f"LOS Blocking: {obscuring_count}")
        with col2:
            objectives = terrain_mgr.get_objectives(selected_objectives)
            st.metric("Objectives", len(objectives))
        with col3:
            st.metric("Deployment", selected_deployment_name)

    # Handle single battle
    if sim_mode == "Single Battle" and 'run_battle' in locals() and run_battle:
        with st.spinner("⚔️ Simulating battle..."):
            battle_data = run_single_battle(
                p1_units, p2_units, p1_army_name, p2_army_name,
                selected_terrain, selected_deployment, selected_objectives, max_turns
            )
            st.session_state.battle_results = battle_data
            st.success(f"✅ {battle_data['results']['winner']}")
            st.balloons()

    # Handle batch simulation
    if sim_mode == "Batch Simulation (Analytics)" and 'run_batch' in locals() and run_batch:
        if p1_roster_file is None:
            st.error("Army 1 must have a roster file for batch simulation")
        elif p2_roster_file is None:
            st.error("Army 2 must have a roster file for batch simulation")
        else:
            # Save uploaded files temporarily for batch processing
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp1:
                tmp1.write(p1_roster_file.getvalue())
                p1_tmp_path = tmp1.name
            with tempfile.NamedTemporaryFile(delete=False, suffix='.json') as tmp2:
                tmp2.write(p2_roster_file.getvalue())
                p2_tmp_path = tmp2.name

            with st.spinner(f"⚔️ Running {num_battles} battles..."):
                batch_results = run_batch_simulations(
                    p1_tmp_path, p2_tmp_path, p1_army_name, p2_army_name,
                    selected_terrain, selected_deployment, selected_objectives,
                    num_battles, max_turns
                )
                st.session_state.batch_results = batch_results
                st.success(f"✅ Completed {num_battles} battles!")

            # Clean up temp files
            Path(p1_tmp_path).unlink()
            Path(p2_tmp_path).unlink()

    # Display single battle results
    if st.session_state.battle_results:
        st.divider()
        battle_data = st.session_state.battle_results
        results = battle_data['results']

        st.header("📊 Battle Results")

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Winner", results['winner'])
        with col2:
            st.metric(f"{p1_army_name} VP", results['player_1_vp'])
        with col3:
            st.metric(f"{p2_army_name} VP", results['player_2_vp'])

        # Tabs
        tab1, tab2 = st.tabs(["📊 Statistics", "📜 Battle Log"])

        with tab1:
            st.subheader("Army Statistics")
            col1, col2 = st.columns(2)
            with col1:
                st.metric(f"{p1_army_name} Units Surviving",
                         f"{results['player_1_units_alive']} ({results['player_1_points_remaining']} pts)")
            with col2:
                st.metric(f"{p2_army_name} Units Surviving",
                         f"{results['player_2_units_alive']} ({results['player_2_points_remaining']} pts)")

        with tab2:
            st.subheader("Battle Log")

            # Display battle log with nice formatting
            log_entries = results['battle_log'][-50:]  # Show last 50 entries

            if log_entries:
                # Group by turn
                from collections import defaultdict
                by_turn = defaultdict(list)
                for event in log_entries:
                    by_turn[event.turn].append(event)

                for turn in sorted(by_turn.keys()):
                    st.markdown(f"### Turn {turn}")
                    for event in by_turn[turn]:
                        # Format the event with icon and color
                        icon = {
                            'deployment': '🎯',
                            'movement': '🏃',
                            'shooting': '🔫',
                            'charge': '⚔️',
                            'melee': '⚔️',
                            'objective_scored': '🏆',
                            'morale': '😰'
                        }.get(event.event_type, '•')

                        player_name = p1_army_name if event.player == 0 else p2_army_name
                        phase_name = event.phase.name.title() if hasattr(event.phase, 'name') else str(event.phase)

                        # Color code by event type
                        if event.damage_dealt > 0 or event.models_killed > 0:
                            damage_text = f" **({event.damage_dealt} dmg, {event.models_killed} casualties)**" if event.models_killed > 0 else f" **({event.damage_dealt} dmg)**"
                        else:
                            damage_text = ""

                        st.markdown(f"{icon} **{player_name}** [{phase_name}]: {event.description}{damage_text}")
            else:
                st.info("No battle log entries")

    # Display batch results
    if st.session_state.batch_results:
        st.divider()
        create_analytics_dashboard(st.session_state.batch_results, p1_army_name, p2_army_name)


if __name__ == "__main__":
    main()
