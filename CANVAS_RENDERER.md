# HTML5 Canvas Battlefield Renderer

## ✅ Problem Solved

**Previous Issue**: Plotting libraries (Plotly, Bokeh) were distorting terrain proportions and deployment zones due to inherent limitations in how they handle aspect ratios and coordinate systems.

**Solution**: Replaced plotting libraries with **HTML5 Canvas** for pixel-perfect, custom map rendering with no distortion.

## 🎯 Key Features

### 1. Perfect 1:1 Aspect Ratio
- **20 pixels per inch** for both horizontal and vertical dimensions
- No stretching or compression of terrain pieces
- Exact proportions maintained:
  - 12" × 6" terrain → 240px × 120px (ratio: 2.0)
  - 10" × 5" terrain → 200px × 100px (ratio: 2.0)
  - 6" × 4" terrain → 120px × 80px (ratio: 1.5)

### 2. Horizontal/Landscape Layout (HIGHEST PRIORITY ✓)
- **Canvas Dimensions**: 1200px wide × 880px tall
- **Battlefield**: 60" (horizontal) × 44" (vertical)
- **Aspect Ratio**: 1.364:1 (exactly 60/44)
- Display is WIDER than it is TALL

### 3. Coordinate System
```
Battlefield coordinates: (x=width 0-44", y=length 0-60")
Canvas coordinates:      (x=length 0-1200px, y=width 0-880px)

Transformation:
  canvas_x = battlefield_y × 20  (swap to horizontal)
  canvas_y = (44 - battlefield_x) × 20  (swap + invert for canvas origin)
```

### 4. Rendering Layers (Z-order)
1. **Background**: Dark battlefield with grid lines
2. **Deployment Zones**: Semi-transparent rectangles/polygons with dashed borders
3. **Terrain**: Colored rectangles with labels
4. **Objectives**: Star markers with labels
5. **Units**: Circles with text labels
6. **Zone Labels**: Bold labels with backgrounds (drawn LAST, on top)

## 📁 Files Modified

### New Files
- **battlefield_canvas.py**: Complete HTML5 Canvas renderer
  - Generates standalone HTML with embedded JavaScript
  - Perfect pixel-level control
  - Interactive (shows coordinates on hover)

### Modified Files
- **battle_app.py**:
  - Changed import from `battlefield_bokeh` to `battlefield_canvas`
  - Updated `create_battlefield_visualization()` to return HTML string
  - Modified display code to use `components.html()` directly

### Removed Dependencies
- ❌ `bokeh` - No longer needed
- ❌ `streamlit-bokeh` - No longer needed

## 🧪 Verification

All tests passing:
```bash
✓ Canvas HTML generated successfully
✓ Canvas dimensions: 1200px wide × 880px tall (HORIZONTAL LANDSCAPE)
✓ Aspect ratio: 1.364 (matches 60/44 perfectly)
✓ Pixels per inch: 20 (1:1 scaling)
✓ All deployment maps render correctly
✓ Terrain proportions exact
```

### Test Files Generated
- `test_canvas_battlefield.html` - Main verification
- `test_canvas_hammer_and_anvil.html` - Rectangle zones (left/right)
- `test_canvas_dawn_of_war.html` - Rectangle zones (different positions)
- `test_canvas_search_and_destroy.html` - Triangle zones

Open these files in a browser to verify:
1. ✅ Canvas is horizontal (wider than tall)
2. ✅ Deployment zones correctly oriented
3. ✅ Terrain maintains exact proportions
4. ✅ No distortion anywhere

## 🎨 Visual Features

### Interactive Elements
- **Mouse Hover**: Shows battlefield coordinates in tooltip
- **Grid Lines**: Every 6" (120px) for easy measurement
- **Color Coding**:
  - Player 1 deployment: Cyan
  - Player 2 deployment: Orange
  - Light Cover: Green (#64c864)
  - Heavy Cover: Yellow-green (#969632)
  - Obscuring: Gray (#505050)
  - Impassable: Dark gray (#323232)

### Labels
- **Terrain**: Name + height (if LOS blocking)
- **Objectives**: Name above star marker
- **Units**: Name + model count
- **Deployment Zones**: Army names with colored borders

## 🚀 Running the App

```bash
# No new dependencies needed! Just run:
streamlit run battle_app.py
```

The battlefield will now render with:
- ✅ Perfect proportions (no plotting library distortion)
- ✅ Horizontal layout (wider than tall)
- ✅ Exact 1:1 aspect ratio
- ✅ Correct deployment zone orientation

## 📊 Technical Details

### Canvas Setup
```javascript
const canvas = document.getElementById('battlefield');
const ctx = canvas.getContext('2d');
canvas.width = 1200;   // 60" × 20px/inch
canvas.height = 880;   // 44" × 20px/inch
```

### Coordinate Transformation
```python
PIXELS_PER_INCH = 20

def to_canvas_x(battlefield_y: float) -> float:
    """Convert battlefield Y (length, 0-60") to canvas X (horizontal)"""
    return battlefield_y * PIXELS_PER_INCH

def to_canvas_y(battlefield_x: float) -> float:
    """Convert battlefield X (width, 0-44") to canvas Y (vertical)"""
    return (44 - battlefield_x) * PIXELS_PER_INCH  # Invert for canvas
```

### Why This Works
1. **Direct Pixel Control**: No library interpretation of aspect ratios
2. **Fixed Canvas Size**: 1200×880 never changes
3. **Explicit Coordinate Mapping**: We control every transformation
4. **No Auto-Scaling**: Canvas doesn't try to "help" with proportions

## 🎯 Success Criteria Met

- ✅ **HIGHEST PRIORITY**: Horizontal/landscape layout maintained
- ✅ **No distortion**: Terrain pieces maintain exact proportions
- ✅ **Correct orientation**: Deployment zones appear left/right (not top/bottom)
- ✅ **1:1 aspect ratio**: 20 pixels per inch for both dimensions
- ✅ **Clean rendering**: No plotting artifacts or strange scaling

---

**This is the correct approach for tactical wargame maps** - using a canvas/graphics library instead of plotting libraries that are designed for data visualization, not precise spatial rendering.
