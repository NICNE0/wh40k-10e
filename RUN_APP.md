# How to Run the Warhammer 40k Battle Simulator

## ✅ System Status

All tests passing! The simulator is fully operational with:
- ✓ 8 official GW terrain layouts (Chapter Approved 2025-26)
- ✓ 6 deployment maps
- ✓ Full battle simulation engine
- ✓ Batch simulation (up to 40,000 battles)
- ✓ Comprehensive analytics dashboard

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install streamlit plotly pandas numpy
```

### 2. Run the App

```bash
streamlit run battle_app.py
```

This will:
- Open your browser automatically to `http://localhost:8501`
- Start the interactive battle simulator
- Show the dynamic battlefield preview

### 3. Using the App

#### Single Battle Mode
1. Configure armies in the sidebar
   - Enter army names (e.g., "Death Guard", "Space Marines")
   - Load `.ros` roster files OR use default test army
2. Select mission setup:
   - Deployment map (Hammer and Anvil, Dawn of War, etc.)
   - Terrain layout (8 official layouts)
   - Objective placement
3. **Watch the battlefield update in real-time** as you change selections
4. Click "Run Battle" to simulate
5. View results with:
   - Final battlefield state with unit positions
   - Battle statistics
   - Complete battle log

#### Batch Simulation Mode (Analytics)
1. Switch to "Batch Simulation (Analytics)" in sidebar
2. **Both armies must use .ros roster files** for batch mode
3. Select number of battles (10 to 40,000)
4. Click "Run X Battles"
5. View comprehensive analytics:
   - Win/loss distribution pie chart
   - Victory points analysis with histograms
   - Casualty statistics
   - Unit performance tables (survival rates)
   - Battle length distribution

## 📊 Features

### Dynamic Battlefield
- **Single map** that updates instantly when you change:
  - Deployment zones
  - Terrain layouts
  - Objectives
- Preview mode (before battle) shows setup
- Results mode (after battle) shows final positions

### Official GW Specifications
All terrain layouts follow **Chapter Approved 2025-26** standards:
- 6 large pieces (12" × 6")
- 2 medium pieces (10" × 5")
- 4 small pieces (6" × 4")
- Total: 12 pieces per layout

### Army Name Mapping
- Custom army names throughout the app
- Deployment zones labeled with army names (not "Player 1/2")
- All statistics and charts use your army names

### Batch Analytics
Run thousands of simulations to get:
- Statistical win rates
- Average VP scores with standard deviation
- Unit survival rates
- Battle dynamics (average length, etc.)

## 🧪 Testing

Run the test script to verify everything works:

```bash
python3 test_simulator.py
```

This checks:
- All 8 terrain layouts are correct (4 small, 2 medium, 6 large)
- All 6 deployment maps load properly
- Battle simulation runs successfully

## 📁 File Structure

- `battle_app.py` - Main Streamlit application
- `battle_simulator.py` - Core battle engine
- `terrain_manager.py` - Terrain and deployment loader
- `terrain_layouts.json` - 8 official GW layouts
- `deployment_maps.json` - 6 official deployment zones
- `roster_parser.py` - BattleScribe .ros file parser
- `roster_to_battle.py` - Convert rosters to battle units
- `test_simulator.py` - Test script

## 🎮 Keyboard Shortcuts (Streamlit)

- `R` - Rerun the app
- `C` - Clear cache
- `?` - Show keyboard shortcuts

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'streamlit'"
```bash
pip install streamlit plotly pandas numpy
```

### Streamlit app won't start
- Make sure you're in the correct directory
- Check Python version (3.8+):
  ```bash
  python3 --version
  ```

### Can't load roster files
- Ensure `.ros` files exist at the specified path
- Use default test army if you don't have roster files

## 📚 Official Sources

Terrain and deployment specifications from:
- [Wahapedia - Chapter Approved 2025-26](https://wahapedia.ru/wh40k10ed/the-rules/chapter-approved-2025-26/)
- [Goonhammer - GW Terrain Layout Guide](https://www.goonhammer.com/40k-start-competing-gw-terrain-layout-1/)

---

**Ready to simulate some battles! 🎲⚔️**
