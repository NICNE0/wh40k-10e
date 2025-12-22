

 # ⚔️ Warhammer 40k Full Battle Simulator

A complete battle simulation system for Warhammer 40k 10th Edition with **movement, positioning, terrain, objectives, and AI strategy**.

## Features

### 🎮 Complete Battle Simulation
- **All 5 Phases**: Command, Movement, Shooting, Charge, Fight
- **Full Turn Sequence**: Both players alternate turns with complete phase execution
- **Victory Conditions**: Victory points from objectives + tabling opponent
- **Battle Length**: 1-5 turns (configurable)

### 🗺️ Battlefield System
- **Standard Sizes**: Strike Force (44"×60"), Incursion (44"×30"), Onslaught (44"×90")
- **Deployment Zones**: Standard deployment (24" from each edge)
- **Objective Markers**: 3-6 objectives with victory point values
- **Terrain Features**:
  - Light Cover (+1 to saves)
  - Heavy Cover (+2 to saves, -1 to hit)
  - Obscuring (blocks line of sight)
  - Impassable (blocks movement)

### 🎯 Positioning & Movement
- **2D Coordinate System**: Units positioned in inches (X, Y)
- **Movement Types**:
  - Normal Move (up to Movement characteristic)
  - Advance (Move + D6", cannot shoot heavy weapons)
  - Fall Back (move away from engagement range, cannot shoot/charge)
- **Engagement Range**: 1" horizontal distance
- **Distance Calculations**: Accurate Euclidean distance for all interactions

### 🔫 Combat Mechanics
- **Line of Sight**: Checks for obscuring terrain between attacker and target
- **Range Calculations**: Weapons must be in range to fire
- **Cover System**: Units in terrain get cover bonuses
- **Full Attack Sequence**:
  1. Hit rolls (BS for shooting, WS for melee)
  2. Wound rolls (Strength vs Toughness)
  3. Save rolls (modified by AP, with cover and invulnerable saves)
  4. Damage allocation (tracks individual model wounds)

### 🤖 AI Strategy Engine
- **Deployment**: Intelligent unit placement in deployment zones
- **Movement Priority**:
  1. Engage/disengage based on unit role (melee vs ranged)
  2. Maintain optimal weapon ranges
  3. Move toward objectives when no targets
  4. Fall back when overwhelmed
- **Target Selection**:
  - Prioritize damaged units (finish kills)
  - Focus on high-value targets (characters, heavy weapons)
  - Choose closest valid targets when priorities equal
- **Charge Logic**: Assess charge viability and target priority

### 📊 Battle Analytics
- **Real-time Battle Log**: Every action tracked with turn, phase, and details
- **Damage Tracking**: Total damage and models killed per attack
- **Objective Scoring**: VP scored each turn based on control
- **Casualty Reports**: Breakdown by unit with points values
- **Victory Determination**:
  - Primary: Victory Points
  - Tie-breaker: Points value of surviving units

## Installation

```bash
# Already installed with combat_simulator dependencies
uv sync
```

## Usage

### 1. Run the Battle Simulator App

```bash
uv run streamlit run battle_app.py
```

### 2. Load Armies

**Option A: Upload Rosters**
- Export army lists from BattleScribe as `.ros` files
- Upload both Player 1 and Player 2 rosters in the app
- Units are automatically converted for battle

**Option B: Test Battle**
- Use built-in test scenario with Space Marines vs Necrons
- Quick start for testing the system

### 3. Configure Battlefield

- **Battlefield Size**: Strike Force (standard), Incursion (small), Onslaught (large)
- **Objectives**: 3-6 objective markers (auto-placed)
- **Terrain**: 3-10 terrain pieces (random types and positions)

### 4. Run Simulation

- Set maximum turns (1-5)
- Click "Run Battle Simulation"
- Watch the AI play out the entire battle

### 5. Analyze Results

**Battlefield Map Tab:**
- Visual representation of final positions
- Unit status (models remaining, wounds)
- Objective control
- Terrain features
- Color-coded by player (Blue = Player 1, Red = Player 2)
- Yellow outline = in melee combat

**Battle Analysis Tab:**
- VP scores
- Surviving units and points
- Damage timeline chart
- Casualty breakdown by unit

**Battle Log Tab:**
- Complete turn-by-turn event log
- Filter by phase or event type
- Shows all movements, attacks, charges, and objective scoring

## Roster Import System

### Supported Formats

The simulator can import BattleScribe rosters in `.ros` (JSON) format.

### Roster Parser Features

- **Unit Stats**: M, T, SV, W, LD, OC
- **Weapons**: All ranged and melee weapons with full profiles
- **Abilities**: Special rules, army rules, detachment rules
- **Keywords**: Faction keywords, unit types, special abilities
- **Warlords**: Automatically detects warlord trait
- **Characters**: Identifies character units
- **Points Costs**: Used for victory tie-breakers

### Conversion Process

```python
from roster_parser import parse_roster
from roster_to_battle import convert_roster_to_battle_units

# Parse roster file
roster = parse_roster("my_army.ros")

# Convert to battle units
battle_units = convert_roster_to_battle_units(roster, player_id=0)

# Add to battle
for unit in battle_units:
    simulator.add_unit(unit)
```

## Architecture

### Core Components

1. **`roster_parser.py`**: Parses BattleScribe .ros JSON files
   - Extracts units, weapons, abilities, stats
   - Handles complex nested structures
   - Returns structured `Roster` objects

2. **`roster_to_battle.py`**: Converts roster units to battle units
   - Maps roster stats to battle stats
   - Parses string values ("6\"", "3+", etc.)
   - Extracts invulnerable saves from abilities
   - Creates fully-equipped battle-ready units

3. **`battle_simulator.py`**: Core battle engine
   - **`Battlefield`**: Map with terrain and objectives
   - **`BattleUnit`**: Units with position, state, weapons
   - **`BattleSimulator`**: Main battle loop
   - **`BattleStrategy`**: AI decision-making
   - **`BattleState`**: Current turn, phase, scores

4. **`battle_app.py`**: Streamlit UI
   - Roster upload interface
   - Battle configuration
   - Real-time visualization
   - Results analysis

### Data Flow

```
BattleScribe .ros file
         ↓
    roster_parser.py  →  Roster object
         ↓
  roster_to_battle.py  →  List[BattleUnit]
         ↓
  battle_simulator.py  →  Battle results
         ↓
     battle_app.py  →  Visualization & analysis
```

## Example: Running a Battle Programmatically

```python
from battle_simulator import (
    BattleSimulator, Battlefield, Position, Objective, BattleUnit, BattleUnitStats, BattleWeapon
)
from roster_parser import parse_roster
from roster_to_battle import convert_roster_to_battle_units

# Create battlefield
battlefield = Battlefield(width=44, length=60)

# Add objectives
battlefield.add_objective(Objective("Center", Position(22, 30), value=5))
battlefield.add_objective(Objective("Left", Position(11, 30), value=5))
battlefield.add_objective(Objective("Right", Position(33, 30), value=5))

# Load armies from rosters
p1_roster = parse_roster("death_guard.ros")
p2_roster = parse_roster("space_marines.ros")

p1_units = convert_roster_to_battle_units(p1_roster, player_id=0)
p2_units = convert_roster_to_battle_units(p2_roster, player_id=1)

# Create battle
simulator = BattleSimulator(battlefield)

for unit in p1_units:
    simulator.add_unit(unit)

for unit in p2_units:
    simulator.add_unit(unit)

# Run battle
results = simulator.simulate_battle(max_turns=5)

# Print results
print(f"Winner: {results['winner']}")
print(f"Player 1 VP: {results['player_1_vp']}")
print(f"Player 2 VP: {results['player_2_vp']}")

# Print battle log
for event in results['battle_log']:
    print(f"T{event.turn} {event.phase.value}: {event.description}")
```

## Advanced Features

### Custom Battle Scenarios

```python
# Create custom terrain
from battle_simulator import TerrainFeature, Terrain

ruins = TerrainFeature(
    name="Ancient Ruins",
    terrain_type=Terrain.HEAVY_COVER,
    center=Position(22, 30),
    radius=5.0,
    provides_cover=True,
    blocks_los=False
)
battlefield.add_terrain(ruins)

# Create high-value objective
battlefield.add_objective(
    Objective("Relic", Position(22, 30), value=10)
)
```

### Battle Statistics

The simulator tracks:
- Total damage dealt per unit
- Models killed per unit
- Objectives held per turn
- Phases where damage occurred
- Movement distances
- Successful charges

All data is available in the `battle_log` for analysis.

## Current Limitations

### Not Yet Implemented
- **Stratagems**: Command point spending
- **Detachment Abilities**: Army-wide special rules (manual for now)
- **Psychic Phase**: Separate from shooting
- **Overwatch**: Shooting during charge phase
- **Heroic Interventions**: Counter-charge moves
- **Multi-model Coherency**: Units treated as single position
- **Flying Units**: Treated same as ground units
- **Transports**: Embarking/disembarking

### Simplified Mechanics
- **Dice Rolling**: Uses average values for attack counts (e.g., D6 = 3.5)
- **Unit Positioning**: Single point per unit (no model spacing)
- **Terrain Interaction**: Simplified LOS and cover checks
- **AI Strategy**: Rule-based heuristics (not deep learning)

## Future Enhancements

### Planned Features
1. **Advanced AI**: Machine learning for strategy optimization
2. **Replay System**: Step-by-step battle replay with visualization
3. **Custom Scenarios**: Mission builder with special objectives
4. **Tournament Mode**: Best-of-3 with variable missions
5. **Unit Grouping**: Combine multiple units into formations
6. **Detachment Rules**: Automatic application of army bonuses
7. **Stratagems**: CP management and stratagem selection
8. **Balance Analysis**: Identify overpowered combos
9. **3D Visualization**: Three.js or Babylon.js battlefield view
10. **Multiplayer**: Two human players making decisions

### Performance Optimizations
- Batch simulations (run 100 battles, aggregate results)
- Parallel processing for multiple battle scenarios
- Database caching of common unit matchups

## Tips for Best Results

1. **Roster Quality**: Ensure BattleScribe rosters are valid and up-to-date
2. **Unit Balance**: Test balanced point values for fair battles
3. **Terrain Placement**: More terrain = more tactical complexity
4. **Objective Count**: 5 objectives standard for Strike Force
5. **Turn Length**: 3-5 turns gives decisive results
6. **Analyze Logs**: Study battle logs to understand AI decisions

## Technical Details

- **Language**: Python 3.8+
- **Dependencies**: NumPy, Streamlit, Plotly, Pandas
- **Battle Resolution**: Monte Carlo simulation with realistic dice rolls
- **AI Decision-Making**: Heuristic-based strategy with priority scoring
- **Visualization**: Plotly for interactive 2D maps
- **State Management**: Dataclasses for type-safe battle state

## Contributing

The battle simulator is modular and extensible:

- **Add Terrain Types**: Extend `Terrain` enum and update LOS/cover logic
- **Improve AI**: Enhance `BattleStrategy` class methods
- **Add Abilities**: Parse more complex abilities from rosters
- **Custom Missions**: Create mission-specific objective scoring
- **Balance Tuning**: Adjust AI priorities and movement heuristics

## License

Part of the wh40k-10e project. See main repository for license.

---

**For combat-only simulation (no movement/positioning)**, use the original `combat_simulator.py`.

**For full tactical battles**, use this battle simulator system.
