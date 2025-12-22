# ⚔️ Warhammer 40k Combat Simulator

A statistical combat simulator for Warhammer 40k 10th Edition. Compare units from **any army** with detailed dice roll simulations and statistical analysis. Supports all factions with .cat files in the repository!

## Features

### 🎖️ Multi-Army Support
- **Select any two armies** from available .cat files
- Automatically discovers all catalogues in the repository
- Supports all factions:
  - Imperium (Space Marines, Astra Militarum, Custodes, Sisters, Knights, etc.)
  - Chaos (Death Guard, World Eaters, Thousand Sons, Daemons, Knights, etc.)
  - Xenos (Necrons, Orks, Tyranids, T'au, Craftworlds, Drukhari, etc.)
  - Leagues of Votann, Genestealer Cults, and more!

### 🎯 Unit Browser
- Browse all units from both selected armies side-by-side
- Complete unit profiles with stats (M, T, SV, W, LD, OC)
- All weapon profiles (Ranged and Melee)
- Special abilities and rules
- Keywords and faction tags
- Points costs

### ⚔️ Combat Simulator
- Select attacking and defending units from **any two armies**
- Choose specific weapons to attack with
- Simulates complete attack sequence:
  1. **Hit rolls** - Based on BS/WS characteristic
  2. **Wound rolls** - Strength vs Toughness comparison
  3. **Save rolls** - Applies AP and invulnerable saves
  4. **Damage** - Calculates total damage dealt
- Run 1-40,000 simulations for statistical accuracy
- Handles dice notation (D6, 2D6, D6+2, etc.)
- Squad sizes from 1-20 models
- Tracks individual model kills

### 📊 Statistical Analysis
- Average damage output
- Hit/Wound/Save success rates
- Damage distribution histogram
- Min/Max/Median damage
- Standard deviation
- Benchmark comparison across multiple matchups

## Installation

```bash
# Sync dependencies with UV
uv sync
```

## Usage

```bash
# Run the combat simulator
uv run streamlit run combat_simulator.py
```

## How It Works

### Combat Mechanics

The simulator follows Warhammer 40k 10th Edition combat rules:

1. **Hit Roll**: Roll D6 for each attack. Success if roll ≥ BS/WS value
2. **Wound Roll**: Compare Strength vs Toughness:
   - S ≥ 2×T: Wound on 2+
   - S > T: Wound on 3+
   - S = T: Wound on 4+
   - S < T (but S×2 > T): Wound on 5+
   - S×2 ≤ T: Wound on 6+
3. **Save Roll**: Defender rolls save
   - Modified Save = Base Save - AP
   - Use Invulnerable save if better
   - Cannot save on 7+
4. **Damage**: Apply weapon damage for each failed save

### Dice Notation

The simulator supports:
- Fixed values: `3`, `5`, etc.
- Single die: `D6`
- Multiple dice: `2D6`, `3D6`
- Modified rolls: `D6+2`, `2D6+3`

### Workflow

1. **Select Armies** - Choose Army 1 (attacker) and Army 2 (defender) from the sidebar
2. **Browse Units** - Explore unit stats in the Unit Browser tab
3. **Select Combatants** - Choose specific units from each army
4. **Pick Weapon** - Select which weapon the attacker uses
5. **Configure Settings** - Set squad sizes, detachments, and modifiers
6. **Configure Simulation** - Set number of simulations (1-40,000)
7. **Run Simulation** - Click "Run Combat Simulation"
8. **Analyze Results** - View statistics and damage distribution
9. **Compare Benchmarks** - Results are saved for cross-army comparison

## Example Use Cases

### Cross-Faction Analysis
Compare units from different armies:
- Space Marine Intercessors vs Necron Warriors
- T'au Fire Warriors vs Ork Boyz
- Custodes Guard vs World Eaters Berzerkers
- Test any matchup you're curious about!

### Unit Performance Analysis
Compare how different units from the same army perform:
- Test multiple Death Guard units against the same target
- Find the most efficient anti-tank/anti-infantry options
- Optimize your army composition

### Weapon Effectiveness
Test different weapons from the same unit:
- Bolter vs Plasma Gun vs Melta
- Against different targets with varying toughness/saves
- Determine optimal loadouts for specific matchups

### Detachment Comparison
See how different detachment bonuses affect outcomes:
- Run same matchup with different detachments
- Quantify the impact of army-wide rules
- Make informed detachment choices

### Matchup Matrix
Run multiple matchups to create a comprehensive damage matrix:
- Test your army against multiple opponents
- Identify advantageous/disadvantageous matchups
- Plan your target priority and tactics

## Limitations

Current version does not include:
- Stratagems
- Command points
- Re-rolls (except those built into weapon profiles)
- Special abilities that modify rolls
- Mortal wounds
- Feel No Pain saves
- Multi-model unit targeting

These features may be added in future versions.

## Tips

- Run at least 100 simulations for reliable averages
- Use 500-1000 simulations for precise statistics
- Compare multiple weapons against the same target
- Save benchmark results to track performance
- Higher variance (std dev) = less predictable outcomes

## Technical Details

- Built with Streamlit for interactive UI
- Uses Plotly for interactive charts
- NumPy for random number generation
- Pandas for data management
- Parses BattleScribe .cat XML files directly

## Supported Armies

The simulator automatically detects all .cat files in the repository. Currently supported factions include:

**Imperium:**
- Space Marines (and all chapters: Blood Angels, Dark Angels, Space Wolves, etc.)
- Astra Militarum, Adeptus Custodes, Adepta Sororitas
- Adeptus Mechanicus, Grey Knights, Deathwatch
- Imperial Knights, Agents of the Imperium

**Chaos:**
- Death Guard, Thousand Sons, World Eaters, Emperor's Children
- Chaos Space Marines, Chaos Daemons, Chaos Knights

**Xenos:**
- Necrons, Orks, Tyranids, Genestealer Cults
- T'au Empire, Craftworlds, Drukhari, Ynnari
- Leagues of Votann

Simply add new .cat files to the repository and they'll be automatically available!

## Future Enhancements

Planned features:
- Support for re-rolls from abilities
- Automatic detachment modifier application
- Reverse simulation (defender attacks back)
- Full battle simulation (multi-turn)
- Custom unit builder
- Export simulation results to CSV/Excel
- Probability charts (damage ranges)
