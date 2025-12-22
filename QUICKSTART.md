# 🚀 Quick Start Guide

## What You Now Have

You have **TWO complete simulation systems**:

### 1. ⚔️ Combat Simulator ([combat_simulator.py](combat_simulator.py))
**Single combat matchup analyzer** - Deep dive into one-on-one unit combat

- Perfect for: "How does X unit perform against Y unit?"
- Statistical analysis with 1,000-40,000 simulations
- Composite squad builder for 10th Edition leader attachments
- META ratings, percentile analysis, kill probability charts
- Matchup matrix for testing one unit against many

**Launch:** `uv run streamlit run combat_simulator.py`

---

### 2. 🗺️ Battle Simulator ([battle_app.py](battle_app.py))
**Full battle simulation** - Complete games with movement, terrain, and strategy

- Perfect for: "Who wins if these two armies fight?"
- 5-phase turn sequence (Command, Movement, Shooting, Charge, Fight)
- AI-driven strategy and target selection
- Battlefield terrain and objectives
- Turn-by-turn battle log with visualization

**Launch:** `uv run streamlit run battle_app.py`

---

## Using Your Death Guard Roster

### Option 1: Test the Roster Parser (CLI)

```bash
# Parse and display your roster
uv run python roster_parser.py /path/to/your/roster.ros

# Convert to battle units
uv run python roster_to_battle.py /path/to/your/roster.ros
```

### Option 2: Upload to Battle Simulator (GUI)

1. Export your army from BattleScribe as `.ros` (JSON format)
2. Launch battle app: `uv run streamlit run battle_app.py`
3. Select "Upload Files" in sidebar
4. Upload Player 1 roster (your Death Guard)
5. Upload Player 2 roster (opponent army)
6. Configure battlefield settings
7. Click "Run Battle Simulation"

---

## Quick Test of Full Battle System

```bash
# Run test battle (Space Marines vs Necrons)
uv run python test_battle_system.py
```

This will simulate a complete 5-turn battle and show:
- Deployment
- Turn-by-turn combat
- Damage dealt
- Units destroyed
- Final victory determination

---

## File Structure

```
wh40k-10e/
│
├── combat_simulator.py          # Original combat simulator (statistical)
├── battle_app.py                 # Full battle simulator (tactical)
├── battle_simulator.py           # Battle engine (movement, phases, AI)
├── roster_parser.py              # BattleScribe .ros parser
├── roster_to_battle.py           # Roster → Battle unit converter
├── test_battle_system.py         # Test script
│
├── README_COMBAT_SIMULATOR.md    # Combat simulator docs
├── README_BATTLE_SIMULATOR.md    # Battle simulator docs
└── QUICKSTART.md                 # This file
```

---

## What Each System Does

### Combat Simulator ⚔️

**Input:** Pick two units from catalogues
**Output:** Statistical combat analysis

```
Intercessors (5 models) vs Necron Warriors (10 models)
↓
Run 10,000 simulations
↓
Average damage: 3.2
Kill probability for 5+ models: 42%
Reliability Grade: B
```

**Best for:**
- Unit comparison
- Weapon loadout optimization
- Points efficiency analysis
- Tournament prep (reliability metrics)

---

### Battle Simulator 🗺️

**Input:** Full army rosters (or manual setup)
**Output:** Complete battle simulation

```
Death Guard (1160 pts) vs Space Marines (1200 pts)
↓
5 turns of gameplay
↓
Player 2 wins 45 VP to 30 VP
8 units destroyed, 3 objectives held
```

**Best for:**
- Army list testing
- Strategic analysis
- Terrain impact assessment
- Full game outcomes

---

## Example Workflows

### Workflow 1: Optimize a Unit Choice

**Goal:** "Should I take Hellblasters or Eradicators?"

1. Open `combat_simulator.py`
2. Test Hellblasters vs various targets (saves to benchmark)
3. Test Eradicators vs same targets
4. Compare META ratings and point efficiency
5. Decision: Pick unit with better avg damage per point

---

### Workflow 2: Test Your Army List

**Goal:** "Will my Death Guard list beat Space Marines?"

1. Export both rosters from BattleScribe as `.ros`
2. Open `battle_app.py`
3. Upload both rosters
4. Run battle simulation 10 times (note win rate)
5. Analyze battle logs to identify weaknesses
6. Adjust army list and re-test

---

### Workflow 3: Understand a Matchup

**Goal:** "How do I use Mortarion effectively?"

1. Open `combat_simulator.py` → Test Mortarion vs common targets
2. Note which weapons are most effective
3. Open `battle_app.py` → Run full battle with Mortarion
4. Watch battle log to see how AI uses him
5. Learn optimal positioning and target priority

---

## Advanced: Programmatic Usage

### Run Combat Simulation Programmatically

```python
from combat_simulator import simulate_attack_sequence

# Define units (simplified example)
attacker_weapon = {...}  # Weapon profile
attacker_unit = {...}    # Unit stats
defender_unit = {...}    # Defender stats

results = simulate_attack_sequence(
    attacker_weapon,
    attacker_unit,
    defender_unit,
    num_simulations=10000,
    attacker_squad_size=5,
    defender_squad_size=10,
    modifiers={}
)

print(f"Average damage: {results['total_damage'] / 10000}")
```

### Run Battle Simulation Programmatically

```python
from battle_simulator import BattleSimulator, Battlefield
from roster_parser import parse_roster
from roster_to_battle import convert_roster_to_battle_units

# Load rosters
p1_roster = parse_roster("death_guard.ros")
p2_roster = parse_roster("space_marines.ros")

# Convert to battle units
p1_units = convert_roster_to_battle_units(p1_roster, player_id=0)
p2_units = convert_roster_to_battle_units(p2_roster, player_id=1)

# Create battle
battlefield = Battlefield(width=44, length=60)
simulator = BattleSimulator(battlefield)

for unit in p1_units + p2_units:
    simulator.add_unit(unit)

# Run battle
results = simulator.simulate_battle(max_turns=5)

print(f"Winner: {results['winner']}")
print(f"VP: {results['player_1_vp']} vs {results['player_2_vp']}")
```

---

## Tips for Your Death Guard Army

### Using the Combat Simulator

1. **Test Mortarion's weapons:**
   - Silence (Strike vs Sweep modes)
   - Lantern
   - Rotwind

2. **Find optimal targets:**
   - Run Mortarion vs 20 different units
   - Check Matchup Matrix tab
   - Identify which units he should prioritize

3. **Test Plague Marine loadouts:**
   - Compare boltgun vs plasma gun vs blight launcher
   - Use Composite Squad mode
   - Mix weapons for optimal damage

### Using the Battle Simulator

1. **Test deployment strategies:**
   - Units deploy randomly in zone
   - Run battle 10 times to see variance

2. **Analyze movement patterns:**
   - Watch how AI moves your units
   - Learn optimal spacing
   - Note when units charge vs shoot

3. **Objective control:**
   - Plague Marines have high OC
   - Battle log shows objective scoring
   - Identify which units to keep on objectives

---

## Troubleshooting

### Roster Won't Parse

**Problem:** "Error parsing roster.ros"

**Solutions:**
1. Ensure exported from BattleScribe as JSON (.ros), not HTML
2. Check file is valid JSON: `cat roster.ros | python -m json.tool`
3. Try exporting roster again from BattleScribe

### Battle Simulator Shows No Damage

**Problem:** "Units don't shoot each other"

**Possible causes:**
- Units out of range (check weapon ranges)
- No line of sight (too much obscuring terrain)
- Units fell back (cannot shoot after falling back)

**Debug:** Check battle log for "movement" events showing fall back

### Streamlit App Won't Start

**Problem:** `ModuleNotFoundError`

**Solution:**
```bash
uv sync  # Re-sync dependencies
uv run streamlit run battle_app.py
```

---

## Next Steps

### Immediate

1. ✅ Test your Death Guard roster with `roster_parser.py`
2. ✅ Run `test_battle_system.py` to see a sample battle
3. ✅ Open `combat_simulator.py` and test some matchups
4. ✅ Open `battle_app.py` and run a full battle

### Short-term

- Export your opponent's armies as `.ros` files
- Run multiple battles to get win rates
- Use combat simulator to optimize unit loadouts
- Test different detachments

### Long-term

- Contribute AI improvements to `BattleStrategy` class
- Add terrain templates for competitive missions
- Build database of common matchups
- Create mission-specific objective rules

---

## Getting Help

- **Combat Simulator Docs:** [README_COMBAT_SIMULATOR.md](README_COMBAT_SIMULATOR.md)
- **Battle Simulator Docs:** [README_BATTLE_SIMULATOR.md](README_BATTLE_SIMULATOR.md)
- **Code Issues:** Check function docstrings in source files

---

## Fun Experiments

1. **Tournament Practice:**
   - Load your tournament list
   - Simulate vs meta armies (Space Marines, Tau, Tyranids)
   - Note win rates

2. **Weapon Math Hammer:**
   - Test all Death Guard weapons vs same target
   - Sort by damage per point
   - Build optimal loadouts

3. **Terrain Impact:**
   - Run same battle with 3, 6, and 10 terrain pieces
   - See how terrain affects results

4. **Detachment Comparison:**
   - Manually apply detachment bonuses as modifiers
   - Compare same list with different detachments

---

Enjoy the simulators! 🎮⚔️
