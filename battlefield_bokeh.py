"""
Bokeh-based battlefield visualization for Warhammer 40k Battle Simulator
Much better rendering than Plotly for tactical wargame maps
"""

from typing import List
from bokeh.plotting import figure
from bokeh.models import HoverTool, Label
from battle_simulator import Battlefield, BattleUnit, Terrain
import math


def create_battlefield_bokeh(battlefield: Battlefield,
                             player_1_units: List[BattleUnit] = None,
                             player_2_units: List[BattleUnit] = None,
                             p1_deployment_zone=None,
                             p2_deployment_zone=None,
                             p1_army_name: str = "Player 1",
                             p2_army_name: str = "Player 2",
                             show_units: bool = True):
    """Create interactive battlefield map using Bokeh - much better than Plotly"""

    # Calculate proper dimensions maintaining 1:1 aspect ratio for data units
    # IMPORTANT: For HORIZONTAL/LANDSCAPE display, put the LONGER dimension on X-axis
    # Original: width=44", length=60"
    # Horizontal display: X-axis=60" (length), Y-axis=44" (width)

    fig_width = 1200   # For the 60" range on X-axis
    fig_height = int(fig_width * (battlefield.width / battlefield.length))  # 1200 * 0.733 = 880px

    # Now fig is 1200px wide × 880px tall = LANDSCAPE!

    # Create figure with proper 1:1 data unit aspect ratio
    p = figure(
        width=fig_width,
        height=fig_height,
        title="Battlefield Map (60\" × 44\")",
        tools="pan,wheel_zoom,box_zoom,reset,save,hover",
        match_aspect=True,
        aspect_scale=1.0,  # Enforce 1:1 data unit scaling
        x_range=(0, battlefield.length),  # 60" on X axis (HORIZONTAL)
        y_range=(0, battlefield.width),   # 44" on Y axis (VERTICAL)
        background_fill_color="#1a1a1a",
        border_fill_color="#0e0e0e"
    )

    # Explicitly set aspect ratio to ensure 1:1 unit scaling
    p.x_range.bounds = (0, battlefield.length)
    p.y_range.bounds = (0, battlefield.width)

    # Style the axes
    p.xaxis.axis_label = "Length (inches)"  # 60" on horizontal axis
    p.yaxis.axis_label = "Width (inches)"   # 44" on vertical axis
    p.xgrid.grid_line_color = "#333333"
    p.ygrid.grid_line_color = "#333333"
    p.xaxis.axis_label_text_color = "white"
    p.yaxis.axis_label_text_color = "white"
    p.xaxis.major_label_text_color = "white"
    p.yaxis.major_label_text_color = "white"

    # Draw battlefield boundary (swapped for horizontal layout)
    p.rect(x=[battlefield.length/2], y=[battlefield.width/2],
           width=[battlefield.length], height=[battlefield.width],
           fill_alpha=0.1, fill_color="white",
           line_color="white", line_width=2)

    # Helper functions for deployment zones
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

    # Collect labels to draw last (so they appear on top)
    zone_labels = []

    def draw_zone_bokeh(zone, line_color, fill_color, label_text):
        if not zone:
            return

        shape = getattr(zone, "shape", None)
        bounds = getattr(zone, "bounds", None) or {}

        # Rectangle deployment zone (swap X/Y for horizontal display)
        if shape == "rectangle" and isinstance(bounds, dict):
            # Bounds in original coords: x=width(0-44), y=length(0-60)
            # Display coords: X=length(0-60), Y=width(0-44)
            # So swap the bounds interpretation
            x_center = (bounds["y_min"] + bounds["y_max"]) / 2  # Use Y bounds for display X
            y_center = (bounds["x_min"] + bounds["x_max"]) / 2  # Use X bounds for display Y
            width = bounds["y_max"] - bounds["y_min"]           # Use Y range for display width
            height = bounds["x_max"] - bounds["x_min"]          # Use X range for display height

            p.rect(x=[x_center], y=[y_center],
                   width=[width], height=[height],
                   fill_alpha=0.15, fill_color=fill_color,
                   line_color=line_color, line_width=2, line_dash="dashed")

            # Store label for later (draw on top of terrain)
            zone_labels.append((x_center, y_center, label_text, line_color))

        # Compound deployment zone (multiple rectangles, swap X/Y)
        elif shape == "compound":
            rects = _get_rectangles(zone)
            if rects:
                for r in rects:
                    # Swap bounds interpretation
                    x_center = (r["y_min"] + r["y_max"]) / 2
                    y_center = (r["x_min"] + r["x_max"]) / 2
                    width = r["y_max"] - r["y_min"]
                    height = r["x_max"] - r["x_min"]

                    p.rect(x=[x_center], y=[y_center],
                           width=[width], height=[height],
                           fill_alpha=0.15, fill_color=fill_color,
                           line_color=line_color, line_width=2, line_dash="dashed")

                # Store label at center (swap bounds)
                x_center = sum((r["y_min"] + r["y_max"]) / 2 for r in rects) / len(rects)
                y_center = sum((r["x_min"] + r["x_max"]) / 2 for r in rects) / len(rects)
                zone_labels.append((x_center, y_center, label_text, line_color))

        # Triangle/polygon deployment zone (swap X/Y)
        elif shape in ("triangle", "polygon"):
            verts = _get_vertices(zone)
            if verts and len(verts) >= 3:
                # Swap vertices: original (x,y) -> display (y,x)
                xs = [v[1] for v in verts]  # Use original Y for display X
                ys = [v[0] for v in verts]  # Use original X for display Y

                p.patch(xs, ys, fill_alpha=0.15, fill_color=fill_color,
                        line_color=line_color, line_width=2, line_dash="dashed")

                # Store label at centroid
                x_center = sum(xs) / len(xs)
                y_center = sum(ys) / len(ys)
                zone_labels.append((x_center, y_center, label_text, line_color))

    # Draw deployment zones
    if p1_deployment_zone and p2_deployment_zone:
        draw_zone_bokeh(p1_deployment_zone, "cyan", "cyan", p1_army_name)
        draw_zone_bokeh(p2_deployment_zone, "orange", "orange", p2_army_name)

        # Draw no-man's land circle if present
        def _get_cutout_circle(zone):
            cutout = getattr(zone, "cutout_circle", None)
            if cutout:
                return cutout
            b = getattr(zone, "bounds", None) or {}
            if isinstance(b, dict):
                return b.get("cutout_circle")
            return None

        cutout = _get_cutout_circle(p1_deployment_zone) or _get_cutout_circle(p2_deployment_zone)
        if cutout and isinstance(cutout, dict) and "center" in cutout and "radius" in cutout:
            cx, cy = cutout["center"]
            r = cutout["radius"]

            # Draw circle (swap X/Y for horizontal display)
            p.circle(x=[cy], y=[cx], radius=r,
                    fill_alpha=0.3, fill_color="black",
                    line_color="white", line_width=2, line_dash="dotted")

            label = Label(x=cy, y=cx, text="No Man's Land (9\")",
                         text_color="white", text_alpha=0.7,
                         text_align="center", text_baseline="middle",
                         text_font_size="11pt")
            p.add_layout(label)

    # Draw terrain
    for terrain in battlefield.terrain:
        color_map = {
            Terrain.LIGHT_COVER: "#64c864",
            Terrain.HEAVY_COVER: "#969632",
            Terrain.OBSCURING: "#505050",
            Terrain.IMPASSABLE: "#323232"
        }
        color = color_map.get(terrain.terrain_type, "#969696")

        half_width = terrain.width / 2
        half_length = terrain.length / 2

        # Draw terrain rectangle (swap X/Y for horizontal display)
        p.rect(x=[terrain.center.y], y=[terrain.center.x],
               width=[terrain.length], height=[terrain.width],
               fill_alpha=0.6, fill_color=color,
               line_color="red" if terrain.blocks_los else "gray",
               line_width=2)

        # Add terrain label (swap X/Y)
        label_text = terrain.name
        if terrain.blocks_los:
            label_text += f"\n{terrain.height}\" (LOS)"

        label = Label(x=terrain.center.y, y=terrain.center.x, text=label_text,
                     text_color="white", text_alpha=0.9,
                     text_align="center", text_baseline="middle",
                     text_font_size="9pt",
                     background_fill_color="black", background_fill_alpha=0.6)
        p.add_layout(label)

    # Draw objectives
    obj_xs, obj_ys, obj_colors, obj_names = [], [], [], []
    for obj in battlefield.objectives:
        obj_xs.append(obj.position.x)
        obj_ys.append(obj.position.y)

        if obj.controlled_by == 0:
            obj_colors.append("blue")
        elif obj.controlled_by == 1:
            obj_colors.append("red")
        else:
            obj_colors.append("gold")

        obj_names.append(obj.name)

        # Add objective label
        label = Label(x=obj.position.x, y=obj.position.y + 2, text=obj.name,
                     text_color="white", text_alpha=0.9,
                     text_align="center", text_baseline="bottom",
                     text_font_size="10pt")
        p.add_layout(label)

    if obj_xs:
        p.star(x=obj_xs, y=obj_ys, size=20, color=obj_colors,
               line_color="black", line_width=2)

    # Draw units
    if show_units:
        if player_1_units:
            p1_xs, p1_ys, p1_sizes, p1_colors, p1_labels = [], [], [], [], []
            for unit in player_1_units:
                if not unit.is_destroyed():
                    p1_xs.append(unit.position.x)
                    p1_ys.append(unit.position.y)
                    p1_sizes.append(15 if unit.is_character else 12)
                    p1_colors.append("yellow" if unit.in_melee else "white")
                    p1_labels.append(f"{unit.name[:15]} ({unit.models_remaining()})")

                    # Add unit label
                    label = Label(x=unit.position.x, y=unit.position.y + 1.5,
                                 text=f"{unit.name[:15]}\n({unit.models_remaining()})",
                                 text_color="lightblue", text_alpha=0.9,
                                 text_align="center", text_baseline="bottom",
                                 text_font_size="8pt")
                    p.add_layout(label)

            if p1_xs:
                p.circle(x=p1_xs, y=p1_ys, size=p1_sizes, color="blue",
                        line_color=p1_colors, line_width=2, alpha=0.8)

        if player_2_units:
            p2_xs, p2_ys, p2_sizes, p2_colors, p2_labels = [], [], [], [], []
            for unit in player_2_units:
                if not unit.is_destroyed():
                    p2_xs.append(unit.position.x)
                    p2_ys.append(unit.position.y)
                    p2_sizes.append(15 if unit.is_character else 12)
                    p2_colors.append("yellow" if unit.in_melee else "white")
                    p2_labels.append(f"{unit.name[:15]} ({unit.models_remaining()})")

                    # Add unit label
                    label = Label(x=unit.position.x, y=unit.position.y - 1.5,
                                 text=f"{unit.name[:15]}\n({unit.models_remaining()})",
                                 text_color="lightcoral", text_alpha=0.9,
                                 text_align="center", text_baseline="top",
                                 text_font_size="8pt")
                    p.add_layout(label)

            if p2_xs:
                p.circle(x=p2_xs, y=p2_ys, size=p2_sizes, color="red",
                        line_color=p2_colors, line_width=2, alpha=0.8)

    # Draw all zone labels last (on top of terrain)
    for x, y, text, color in zone_labels:
        label = Label(x=x, y=y, text=text,
                     text_color=color, text_alpha=0.9,
                     text_align="center", text_baseline="middle",
                     text_font_size="16pt", text_font_style="bold",
                     background_fill_color="black", background_fill_alpha=0.7,
                     border_line_color=color, border_line_width=2)
        p.add_layout(label)

    # Configure hover tool
    hover = p.select_one(HoverTool)
    if hover:
        hover.tooltips = [("Position", "($x, $y)")]

    return p
