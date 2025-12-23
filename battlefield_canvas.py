"""
HTML5 Canvas-based battlefield visualization for Warhammer 40k Battle Simulator
Pixel-perfect rendering with exact proportions - NO plotting library distortion
"""

from typing import List, Optional
from battle_simulator import Battlefield, BattleUnit, Terrain
import json


def create_battlefield_canvas(battlefield: Battlefield,
                              player_1_units: List[BattleUnit] = None,
                              player_2_units: List[BattleUnit] = None,
                              p1_deployment_zone=None,
                              p2_deployment_zone=None,
                              p1_army_name: str = "Player 1",
                              p2_army_name: str = "Player 2",
                              show_units: bool = True) -> str:
    """
    Create interactive battlefield map using HTML5 Canvas
    Returns HTML string for embedding in Streamlit

    Coordinate convention (refactored)
    - data_x: 0–60" (long edge)  -> horizontal axis
    - data_y: 0–44" (short edge) -> vertical axis

    Rendering is now a direct mapping (no axis swapping / board rotation).
    """

    # Perfect 1:1 pixel scaling: 20 pixels per inch
    PIXELS_PER_INCH = 20

    # Canvas dimensions follow the battlefield axes directly.
    # 60" -> 1200px (at 20 px/in), 44" -> 880px.
    canvas_width = int(battlefield.width * PIXELS_PER_INCH)
    canvas_height = int(battlefield.length * PIXELS_PER_INCH)

    def to_canvas(data_x: float, data_y: float) -> tuple:
        """
        Convert battlefield (data) coordinates to canvas coordinates.

        Direct mapping with inverted vertical axis.

        - data_x (0–battlefield.width)   maps to canvas_x (left->right)
        - data_y (0–battlefield.length)  maps to canvas_y (bottom->top)

        Parameters
        ----------
        data_x : float
            The width coordinate (0–battlefield.width).
        data_y : float
            The length coordinate (0–battlefield.length).

        Returns
        -------
        tuple
            (canvas_x, canvas_y) in pixel coordinates.
        """
        canvas_x = data_x * PIXELS_PER_INCH
        canvas_y = canvas_height - (data_y * PIXELS_PER_INCH)
        return (canvas_x, canvas_y)

    # -------------------------------------------------------------------------
    # Backwards compatibility helpers
    #
    # Some earlier code referred to ``to_canvas_x`` and ``to_canvas_y``.  Define
    # these here as thin wrappers around ``to_canvas`` so that stale references
    # don't raise NameError.  They simply return one component of the mapping.
    def to_canvas_x(data_x: float, data_y: float) -> float:
        return to_canvas(data_x, data_y)[0]

    def to_canvas_y(data_x: float, data_y: float) -> float:
        return to_canvas(data_x, data_y)[1]

    # Prepare data structures for JavaScript rendering
    terrain_data = []
    for terrain in battlefield.terrain:
        color_map = {
            Terrain.LIGHT_COVER: "#64c864",
            Terrain.HEAVY_COVER: "#969632",
            Terrain.OBSCURING: "#505050",
            Terrain.IMPASSABLE: "#323232"
        }
        color = color_map.get(terrain.terrain_type, "#969696")

        # Convert terrain position
        cx, cy = to_canvas(terrain.center.x, terrain.center.y)

        terrain_data.append({
            'name': terrain.name,
            'x': cx,
            'y': cy,
            'width': terrain.width * PIXELS_PER_INCH,
            'height': terrain.length * PIXELS_PER_INCH,
            'color': color,
            'border': 'red' if terrain.blocks_los else 'gray',
            'blocks_los': terrain.blocks_los,
            'terrain_height': terrain.height,
            'rotation': terrain.rotation
        })

    objectives_data = []
    for obj in battlefield.objectives:
        if obj.controlled_by == 0:
            color = "blue"
        elif obj.controlled_by == 1:
            color = "red"
        else:
            color = "gold"

        # Convert objective position
        ox, oy = to_canvas(obj.position.x, obj.position.y)

        objectives_data.append({
            'name': obj.name,
            'x': ox,
            'y': oy,
            'color': color
        })

    # Deployment zones
    def process_zone(zone, color, label):
        if not zone:
            return None

        shape = getattr(zone, "shape", None)
        bounds = getattr(zone, "bounds", None) or {}

        if shape == "rectangle" and isinstance(bounds, dict):
            """Convert a rectangular deployment zone from data bounds -> canvas rect."""
            # Calculate center in data coordinates
            data_center_x = (bounds["x_min"] + bounds["x_max"]) / 2
            data_center_y = (bounds["y_min"] + bounds["y_max"]) / 2

            # Convert center to canvas coordinates
            canvas_center_x, canvas_center_y = to_canvas(data_center_x, data_center_y)

            # Extents map directly: x-range -> width, y-range -> height
            data_x_extent = bounds["x_max"] - bounds["x_min"]
            data_y_extent = bounds["y_max"] - bounds["y_min"]
            canvas_width_px = data_x_extent * PIXELS_PER_INCH
            canvas_height_px = data_y_extent * PIXELS_PER_INCH

            return {
                'type': 'rectangle',
                'x': canvas_center_x,
                'y': canvas_center_y,
                'width': canvas_width_px,
                'height': canvas_height_px,
                'color': color,
                'label': label
            }

        elif shape == "compound":
            rectangles = []
            rects = bounds.get("rectangles", [])
            if isinstance(bounds.get("bounds"), dict):
                rects = bounds["bounds"].get("rectangles", [])

            for r in rects:
                # Same logic as single rectangle
                data_center_x = (r["x_min"] + r["x_max"]) / 2
                data_center_y = (r["y_min"] + r["y_max"]) / 2
                canvas_center_x, canvas_center_y = to_canvas(data_center_x, data_center_y)

                data_x_extent = r["x_max"] - r["x_min"]
                data_y_extent = r["y_max"] - r["y_min"]

                canvas_width_px = data_x_extent * PIXELS_PER_INCH
                canvas_height_px = data_y_extent * PIXELS_PER_INCH

                rectangles.append({
                    'x': canvas_center_x,
                    'y': canvas_center_y,
                    'width': canvas_width_px,
                    'height': canvas_height_px,
                })

            if rectangles:
                label_x = sum(r['x'] for r in rectangles) / len(rectangles)
                label_y = sum(r['y'] for r in rectangles) / len(rectangles)
                return {
                    'type': 'compound',
                    'rectangles': rectangles,
                    'color': color,
                    'label': label,
                    'label_x': label_x,
                    'label_y': label_y
                }

        elif shape in ("triangle", "polygon"):
            verts = getattr(zone, "vertices", None)
            if not verts and isinstance(bounds, dict):
                verts = bounds.get("vertices")

            if verts and len(verts) >= 3:
                # Convert vertices - vertices are (x, y) where x=width, y=length
                points = []
                for v in verts:
                    vx, vy = to_canvas(v[0], v[1])
                    points.append({'x': vx, 'y': vy})

                # Calculate centroid for label
                label_x = sum(p['x'] for p in points) / len(points)
                label_y = sum(p['y'] for p in points) / len(points)

                return {
                    'type': 'polygon',
                    'points': points,
                    'color': color,
                    'label': label,
                    'label_x': label_x,
                    'label_y': label_y
                }

        return None

    p1_zone_data = process_zone(p1_deployment_zone, "cyan", p1_army_name)
    p2_zone_data = process_zone(p2_deployment_zone, "orange", p2_army_name)

    # Units
    p1_units_data = []
    p2_units_data = []

    if show_units:
        if player_1_units:
            for unit in player_1_units:
                if not unit.is_destroyed():
                    ux, uy = to_canvas(unit.position.x, unit.position.y)
                    p1_units_data.append({
                        'name': unit.name[:15],
                        'x': ux,
                        'y': uy,
                        'models': unit.models_remaining(),
                        'is_character': unit.is_character,
                        'in_melee': unit.in_melee
                    })

        if player_2_units:
            for unit in player_2_units:
                if not unit.is_destroyed():
                    ux, uy = to_canvas(unit.position.x, unit.position.y)
                    p2_units_data.append({
                        'name': unit.name[:15],
                        'x': ux,
                        'y': uy,
                        'models': unit.models_remaining(),
                        'is_character': unit.is_character,
                        'in_melee': unit.in_melee
                    })

    # Calculate display size (90% of actual canvas size for easier viewing on small displays)
    display_width = int(canvas_width * 0.9)   # 1080px instead of 1200px
    display_height = int(canvas_height * 0.9)  # 792px instead of 880px

    # Generate HTML with embedded JavaScript
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                margin: 0;
                padding: 0;
                background-color: #0e0e0e;
                overflow: hidden;
            }}
            #battlefield {{
                display: block;
                margin: 0 auto;
                background-color: #1a1a1a;
                cursor: crosshair;
                width: {display_width}px;
                height: {display_height}px;
            }}
        </style>
    </head>
    <body>
        <canvas id="battlefield" width="{canvas_width}" height="{canvas_height}"></canvas>

        <script>
            const canvas = document.getElementById('battlefield');
            const ctx = canvas.getContext('2d');

            // Data from Python
            const terrain = {json.dumps(terrain_data)};
            const objectives = {json.dumps(objectives_data)};
            const p1_zone = {json.dumps(p1_zone_data)};
            const p2_zone = {json.dumps(p2_zone_data)};
            const p1_units = {json.dumps(p1_units_data)};
            const p2_units = {json.dumps(p2_units_data)};

            const CANVAS_WIDTH = {canvas_width};
            const CANVAS_HEIGHT = {canvas_height};
            const PIXELS_PER_INCH = {PIXELS_PER_INCH};

            function drawBattlefield() {{
                // Clear canvas
                ctx.fillStyle = '#1a1a1a';
                ctx.fillRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

                // Draw battlefield border
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 2;
                ctx.strokeRect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT);

                // Draw deployment zones
                function drawZone(zone) {{
                    if (!zone) return;

                    ctx.save();
                    ctx.globalAlpha = 0.15;
                    ctx.fillStyle = zone.color;
                    ctx.strokeStyle = zone.color;
                    ctx.lineWidth = 2;
                    ctx.setLineDash([10, 5]);

                    if (zone.type === 'rectangle') {{
                        ctx.fillRect(zone.x - zone.width/2, zone.y - zone.height/2, zone.width, zone.height);
                        ctx.strokeRect(zone.x - zone.width/2, zone.y - zone.height/2, zone.width, zone.height);
                    }} else if (zone.type === 'compound') {{
                        zone.rectangles.forEach(r => {{
                            ctx.fillRect(r.x - r.width/2, r.y - r.height/2, r.width, r.height);
                            ctx.strokeRect(r.x - r.width/2, r.y - r.height/2, r.width, r.height);
                        }});
                    }} else if (zone.type === 'polygon') {{
                        ctx.beginPath();
                        ctx.moveTo(zone.points[0].x, zone.points[0].y);
                        for (let i = 1; i < zone.points.length; i++) {{
                            ctx.lineTo(zone.points[i].x, zone.points[i].y);
                        }}
                        ctx.closePath();
                        ctx.fill();
                        ctx.stroke();
                    }}

                    ctx.restore();
                }}

                drawZone(p1_zone);
                drawZone(p2_zone);

                // Draw terrain
                terrain.forEach(t => {{
                    ctx.save();

                    // Draw rectangle
                    ctx.fillStyle = t.color;
                    ctx.globalAlpha = 0.6;
                    ctx.fillRect(t.x - t.width/2, t.y - t.height/2, t.width, t.height);

                    ctx.globalAlpha = 1.0;
                    ctx.strokeStyle = t.border;
                    ctx.lineWidth = 2;
                    ctx.strokeRect(t.x - t.width/2, t.y - t.height/2, t.width, t.height);

                    // Label
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
                    ctx.fillRect(t.x - 50, t.y - 20, 100, 40);

                    ctx.fillStyle = 'white';
                    ctx.font = '12px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(t.name, t.x, t.y - 5);
                    if (t.blocks_los) {{
                        ctx.font = '10px Arial';
                        ctx.fillText(t.terrain_height + '" (LOS)', t.x, t.y + 8);
                    }}

                    ctx.restore();
                }});

                // Draw objectives
                objectives.forEach(obj => {{
                    ctx.save();

                    // Star shape
                    const spikes = 5;
                    const outerRadius = 10;
                    const innerRadius = 5;

                    ctx.beginPath();
                    for (let i = 0; i < spikes * 2; i++) {{
                        const radius = i % 2 === 0 ? outerRadius : innerRadius;
                        const angle = (Math.PI / spikes) * i - Math.PI / 2;
                        const x = obj.x + Math.cos(angle) * radius;
                        const y = obj.y + Math.sin(angle) * radius;
                        if (i === 0) {{
                            ctx.moveTo(x, y);
                        }} else {{
                            ctx.lineTo(x, y);
                        }}
                    }}
                    ctx.closePath();

                    ctx.fillStyle = obj.color;
                    ctx.fill();
                    ctx.strokeStyle = 'black';
                    ctx.lineWidth = 2;
                    ctx.stroke();

                    // Label
                    ctx.fillStyle = 'white';
                    ctx.font = '12px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'bottom';
                    ctx.fillText(obj.name, obj.x, obj.y - 15);

                    ctx.restore();
                }});

                // Draw units
                function drawUnits(units, fillColor, borderColor, labelColor, labelOffset) {{
                    units.forEach(unit => {{
                        ctx.save();

                        // Circle
                        const radius = unit.is_character ? 7.5 : 6;
                        ctx.beginPath();
                        ctx.arc(unit.x, unit.y, radius, 0, Math.PI * 2);
                        ctx.fillStyle = fillColor;
                        ctx.globalAlpha = 0.8;
                        ctx.fill();

                        ctx.globalAlpha = 1.0;
                        ctx.strokeStyle = unit.in_melee ? 'yellow' : borderColor;
                        ctx.lineWidth = 2;
                        ctx.stroke();

                        // Label
                        ctx.fillStyle = labelColor;
                        ctx.font = '10px Arial';
                        ctx.textAlign = 'center';
                        ctx.textBaseline = labelOffset > 0 ? 'top' : 'bottom';
                        ctx.fillText(unit.name, unit.x, unit.y + labelOffset);
                        ctx.fillText('(' + unit.models + ')', unit.x, unit.y + labelOffset + 12 * (labelOffset > 0 ? 1 : -1));

                        ctx.restore();
                    }});
                }}

                drawUnits(p1_units, 'blue', 'white', 'lightblue', -10);
                drawUnits(p2_units, 'red', 'white', 'lightcoral', 10);

                // Draw zone labels LAST (on top of everything)
                function drawZoneLabel(zone) {{
                    if (!zone) return;

                    const labelX = zone.label_x || zone.x;
                    const labelY = zone.label_y || zone.y;

                    ctx.save();

                    // Background
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
                    ctx.fillRect(labelX - 80, labelY - 20, 160, 40);

                    // Border
                    ctx.strokeStyle = zone.color;
                    ctx.lineWidth = 2;
                    ctx.setLineDash([]);
                    ctx.strokeRect(labelX - 80, labelY - 20, 160, 40);

                    // Text
                    ctx.fillStyle = zone.color;
                    ctx.font = 'bold 16px Arial';
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(zone.label, labelX, labelY);

                    ctx.restore();
                }}

                drawZoneLabel(p1_zone);
                drawZoneLabel(p2_zone);

                // Grid lines (optional)
                ctx.save();
                ctx.strokeStyle = '#333333';
                ctx.lineWidth = 0.5;
                ctx.globalAlpha = 0.3;

                // Vertical lines every 6" (120px)
                for (let x = PIXELS_PER_INCH * 6; x < CANVAS_WIDTH; x += PIXELS_PER_INCH * 6) {{
                    ctx.beginPath();
                    ctx.moveTo(x, 0);
                    ctx.lineTo(x, CANVAS_HEIGHT);
                    ctx.stroke();
                }}

                // Horizontal lines every 6" (120px)
                for (let y = PIXELS_PER_INCH * 6; y < CANVAS_HEIGHT; y += PIXELS_PER_INCH * 6) {{
                    ctx.beginPath();
                    ctx.moveTo(0, y);
                    ctx.lineTo(CANVAS_WIDTH, y);
                    ctx.stroke();
                }}

                ctx.restore();
            }}

            // Draw on load
            drawBattlefield();

            // Mouse interaction (show coordinates on hover)
            canvas.addEventListener('mousemove', (e) => {{
                const rect = canvas.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;

                // Convert to battlefield inches (swap back)
                const bf_y = (x / PIXELS_PER_INCH).toFixed(1);
                const bf_x = ((CANVAS_HEIGHT - y) / PIXELS_PER_INCH).toFixed(1);

                canvas.title = `Position: (x=${{bf_x}}\\", y=${{bf_y}}\\")`;
            }});
        </script>
    </body>
    </html>
    """

    return html
