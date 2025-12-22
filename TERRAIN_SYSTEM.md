# 🗺️ Official Terrain & Deployment System

The battle simulator now uses **official Warhammer 40k 10th Edition terrain layouts and deployment maps** from Chapter Approved 2025-26.

## What's New

### ✅ Official Terrain Layouts

The simulator includes 3 official GW tournament terrain layouts:

- **Layout 1**: Balanced spread with center LOS blocker
- **Layout 2**: Diagonal coverage
- **Layout 3**: Four-corner setup

Each layout uses official terrain piece dimensions:
- **Small** (6" × 4"): Craters, small ruins
- **Medium** (10" × 5"): Medium ruins
- **Large** (12" × 6"): Large ruins, obscuring terrain

### ✅ Official Deployment Maps

6 official deployment configurations:

1. **Hammer and Anvil**: Long edges, 12" deployment zones
2. **Dawn of War**: Short edges, 12" deployment zones
3. **Search and Destroy**: Diagonal corners
4. **Sweeping Engagement**: Opposite diagonal corners
5. **Tipping Point**: Mirrored L-shaped zones
6. **Crucible of Battle**: Narrow 9" deployment zones

### ✅ Official Objective Placements

3 standard objective configurations:

- **Standard 5 Objectives**: Most common tournament setup
- **Diagonal 5 Objectives**: For diagonal deployments
- **Spread 6 Objectives**: Maximum objective count

---

## How to Use

### In Battle Simulator App

1. Launch battle app: `uv run streamlit run battle_app.py`

2. In the sidebar under "Mission Setup":
   - Select **Deployment Map** (e.g., "Hammer and Anvil")
   - Select **Terrain Layout** (e.g., "GW Tournament Layout 1")
   - Select **Objective Placement** (e.g., "Standard 5 Objectives")

3. Run battle as normal

The simulator will:
- ✅ Place terrain exactly as per official layout
- ✅ Deploy units in correct deployment zones
- ✅ Position objectives per official rules
- ✅ Apply correct LOS blocking and cover rules

---

## Programmatic Usage

### Using Terrain Manager

```python
from terrain_manager import TerrainManager
from battle_simulator import Battlefield, BattleSimulator

# Initialize manager
terrain_mgr = TerrainManager()

# Create battlefield
battlefield = Battlefield(width=44, length=60)

# Load official terrain (Layout 1)
terrain_features = terrain_mgr.get_terrain_layout('layout_1')
for feature in terrain_features:
    battlefield.add_terrain(feature)

# Load official objectives
objectives = terrain_mgr.get_objectives('standard_5_objectives')
for obj in objectives:
    battlefield.add_objective(obj)

# Get deployment zones (Hammer and Anvil)
p1_zone, p2_zone = terrain_mgr.get_deployment_map('hammer_and_anvil')

# Create simulator
simulator = BattleSimulator(battlefield)

# Add units
for unit in my_units:
    simulator.add_unit(unit)

# Run battle with official deployment zones
results = simulator.simulate_battle(
    max_turns=5,
    p1_deployment_zone=p1_zone,
    p2_deployment_zone=p2_zone
)
```

---

## Terrain Rules

### Cover

**Light Cover** (Craters, Woods):
- +1 to armor save
- No LOS blocking

**Heavy Cover** (Ruins <5" tall):
- +1 to armor save
- No LOS blocking

**Obscuring** (Ruins >5" tall):
- +1 to armor save
- **Blocks line of sight** completely

### Line of Sight

The simulator checks:
1. Is there obscuring terrain between attacker and target?
2. If yes → No LOS, cannot shoot
3. If no → LOS clear, can shoot (apply cover if in terrain)

---

## Configuration Files

### terrain_layouts.json

Defines official terrain piece positions:

```json
{
  "layouts": {
    "layout_1": {
      "name": "GW Tournament Layout 1",
      "pieces": [
        {
          "type": "large",
          "position": [22, 30],
          "terrain_type": "ruins",
          "height": 5,
          "obscuring": true
        },
        ...
      ]
    }
  }
}
```

### deployment_maps.json

Defines deployment zones and objectives:

```json
{
  "deployment_maps": {
    "hammer_and_anvil": {
      "name": "Hammer and Anvil",
      "player_1_zone": {
        "bounds": {
          "x_min": 0,
          "x_max": 12,
          "y_min": 0,
          "y_max": 60
        }
      },
      ...
    }
  }
}
```

---

## Terrain Manager API

### List Available Options

```python
from terrain_manager import TerrainManager
mgr = TerrainManager()

# List terrain layouts
layouts = mgr.list_available_layouts()
# ['layout_1', 'layout_2', 'layout_3']

# List deployment maps
deployments = mgr.list_available_deployments()
# ['hammer_and_anvil', 'dawn_of_war', ...]

# List objective sets
objectives = mgr.list_available_objectives()
# ['standard_5_objectives', 'diagonal_5_objectives', ...]
```

### Get Descriptions

```python
# Get human-readable descriptions
desc = mgr.get_deployment_description('hammer_and_anvil')
# "Hammer and Anvil: Long table edges. Deployment zones are 12\" deep..."

layout_desc = mgr.get_layout_description('layout_1')
# "GW Tournament Layout 1"
```

### Validate Deployment

```python
from battle_simulator import Position

p1_zone, p2_zone = mgr.get_deployment_map('dawn_of_war')

# Check if position is valid
pos = Position(22, 6)  # Center of P1 deployment
is_valid = p1_zone.is_valid_deployment(pos)  # True
```

---

## Adding Custom Layouts

### 1. Add to terrain_layouts.json

```json
{
  "layouts": {
    "my_custom_layout": {
      "name": "My Custom Layout",
      "battlefield_size": [44, 60],
      "pieces": [
        {
          "type": "large",
          "position": [22, 30],
          "rotation": 0,
          "terrain_type": "ruins",
          "height": 5,
          "obscuring": true,
          "note": "Center blocker"
        }
      ]
    }
  }
}
```

### 2. Use in Code

```python
terrain = terrain_mgr.get_terrain_layout('my_custom_layout')
```

### 3. Add to UI

Edit `battle_app.py`:

```python
terrain_layout_options = {
    "GW Tournament Layout 1": "layout_1",
    "GW Tournament Layout 2": "layout_2",
    "GW Tournament Layout 3": "layout_3",
    "My Custom Layout": "my_custom_layout"  # Add this
}
```

---

## Official Sources

Terrain layouts and deployment maps are based on:

- [**Wahapedia - Chapter Approved 2025-26**](https://wahapedia.ru/wh40k10ed/the-rules/chapter-approved-2025-26/)
- **GW Tournament Companion** (official PDF)
- **Goonhammer Tournament Map Analysis**

---

## Differences from Random Terrain

### Old System (Random):
- Terrain placed randomly
- No standardization
- Inconsistent cover
- Variable LOS blocking

### New System (Official):
- ✅ Exact GW tournament layouts
- ✅ Standardized piece dimensions
- ✅ Balanced cover distribution
- ✅ Consistent LOS blocking
- ✅ Tournament-legal setups

---

## Testing

Test the terrain system:

```bash
# Test terrain manager
uv run python terrain_manager.py

# Test battle with official layout
uv run streamlit run battle_app.py
```

Select any deployment map + terrain layout combination to see official tournament-style battles.

---

## Future Enhancements

Planned additions:

- [ ] More GW layouts (Layouts 4-8)
- [ ] Custom layout builder UI
- [ ] Mission-specific secondary objectives
- [ ] Terrain feature special rules (e.g., woods = Dense Cover)
- [ ] Tournament pack selector (WTC, LGT, etc.)

---

## Questions?

**Q: Can I still use custom terrain?**
A: Yes! The system supports both official layouts and custom configurations. Just create your own entry in `terrain_layouts.json`.

**Q: Do I need to use official layouts?**
A: No, the simulator still works with the test mode which has simplified terrain. Official layouts are optional but recommended for tournament practice.

**Q: Which deployment should I use?**
A: Hammer and Anvil or Dawn of War are most common. Search and Destroy/Sweeping Engagement are for diagonal deployment missions.

**Q: Why 3 layouts instead of 8?**
A: Currently included 3 most common layouts. Layouts 4-8 will be added in future updates. You can add them yourself to the JSON file.

---

**Now your battles use the same terrain as real tournaments!** 🎯
