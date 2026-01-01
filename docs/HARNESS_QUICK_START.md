# Harness Racing GUI - Quick Start Guide

## Installation

```bash
# Ensure PySide6 is installed
pip install PySide6

# Navigate to source directory
cd "d:\Personal Project\UmaRacingProject\src"

# Run the GUI
python HarnessRacingGUI.py
```

## Quick Start (5 Steps)

### Step 1: Generate Horses
- Go to **Tab 1: Horse Configuration**
- Set number of horses (3-10 recommended)
- Click **"Generate Random Stable"**
- View generated horses with their 7 stats

### Step 2: Select Race
- Go to **Tab 2: Race Selection**
- Choose a race from dropdown (e.g., "Prix d'Amérique")
- View race information (distance, track, prize money)

### Step 3: Watch Live Race
- Go to **Tab 3: Simulation**
- Click **"Run Race (Live)"** for animated race
- OR click **"Run Race (Instant)"** for immediate results

### Step 4: Observe Live Features
- **Left Panel**: Curved track with moving horses and sulkies
- **Right Top**: Live positions (F1-style)
- **Right Bottom**: Race commentary with timestamps

### Step 5: Save Results
- Go to **Tab 4: Results**
- View final standings
- Click **"Save Results"** to export to JSON

## Visual Guide

### Gate Colors (Horse Identification)
| Gate | Color  | RGB         |
|------|--------|-------------|
| 1    | Red    | 255, 0, 0   |
| 2    | Blue   | 0, 0, 255   |
| 3    | Yellow | 255, 255, 0 |
| 4    | Green  | 0, 255, 0   |
| 5    | Orange | 255, 165, 0 |
| 6    | Purple | 128, 0, 128 |
| 7    | Cyan   | 0, 255, 255 |
| 8    | Pink   | 255, 192, 203|

### Status Indicators
- ✓ = Horse finished
- [BREAK!] = Horse breaking gait
- Red pulse on canvas = Gait break in progress

### Track Features
- **Brown oval**: Dirt racing surface
- **Green interior**: Infield grass
- **White line**: Finish line
- **Gray ovals behind horses**: Sulky carts

## Commentary Examples

### Start
```
[0.5s] And they're off from the auto-start gate!
```

### Distance Markers
```
[45.8s] 1000m to go! Nordic Pride leads the charge!
[78.2s] Only 400m left! Nordic Pride is sprinting!
```

### Incidents
```
[58.3s] Storm Sprint breaks stride! Losing valuable momentum!
```

### Dueling
```
[65.1s] Nordic Pride and Valor Elite are locked together!
```

### Finish
```
[120.7s] Nordic Pride crosses the line! Victory in the harness!
[121.2s] Valor Elite claims second place!
```

## Race Recommendations

### Beginner Races (Shorter)
- **Critérium des 3 ans** - 2100m at Paris-Vincennes
- **Copenhagen Cup** - 2140m at Charlottenlund

### Classic Races (Medium)
- **Prix d'Amérique** - 2700m at Paris-Vincennes
- **Elitloppet** - 2140m at Solvalla
- **Åby Stora Pris** - 2140m at Åby

### Championship Races (Longer)
- **Oslo Grand Prix** - 2100m at Bjerke
- **Derby Italiano** - 2000m at Rome

## Understanding Stats

### The 7-Stat System
1. **Pulling Power** (PP): Raw speed with sulky
2. **Endurance** (END): Stamina over distance
3. **Gait Consistency** (GC): Ability to maintain trot/pace
4. **Heat Recovery** (HR): Recovery between heats
5. **Start Acceleration** (SA): Speed from auto-start
6. **Temperament** (TMP): Mental stability
7. **Sulky Tolerance** (ST): Equipment handling

### Optimal Values
- **Speed-focused**: High PP, SA
- **Distance-focused**: High END, GC
- **All-rounder**: Balanced 60-70 across all stats

## Keyboard Shortcuts

None currently implemented (future enhancement).

## Troubleshooting

### GUI Won't Start
```bash
# Check PySide6 installation
pip show PySide6

# If not installed
pip install PySide6
```

### No Commentary Appearing
- Check that horses are generated
- Ensure race is selected
- Try "Run Race (Instant)" first to verify setup
- Commentary only appears during "Run Race (Live)"

### Track Not Visible
- Resize window to minimum 800x600
- Check Tab 2 that race is properly selected
- Track auto-generates when race is selected

### Horses Not Moving
- Verify "Run Race (Live)" was clicked (not "Instant")
- Check progress bar is updating
- If frozen, close and restart GUI

## Performance Tips

### Smooth Animation
- Close other heavy applications
- Use 3-5 horses for best performance
- 8+ horses may cause slight lag on slower systems

### Faster Results
- Use "Run Race (Instant)" for quick testing
- "Run Race (Live)" takes 90-150 seconds per race
- Multiple instant races can be run in quick succession

## Advanced Features

### Save File Location
- Results saved to: `results/harness_race_results_YYYYMMDD_HHMMSS.json`
- Includes horse stats, race details, and last 30 commentary lines

### JSON Structure
```json
{
  "race_name": "Prix d'Amérique",
  "timestamp": "2024-01-15T14:30:00",
  "horses": {
    "horse_1": {
      "name": "Nordic Pride",
      "stats": { "pulling_power": 75, ... }
    }
  },
  "results": ["horse_1", "horse_3", "horse_2"],
  "commentary": ["[0.5s] And they're off...", ...]
}
```

## Tips & Tricks

### Winning Strategy
- High Gait Consistency (70+) is crucial for harness racing
- Balance Pulling Power and Endurance for different distances
- Start Acceleration matters most in short races (<2140m)

### Watch For
- Gait breaks usually occur when stamina depletes
- Leaders often vulnerable in final 400m
- Horses with higher Temperament handle pressure better

### Commentary Timing
- Distance markers trigger at specific points
- Gait breaks immediately announced
- Position changes noted every 4 seconds
- Phase commentary every 8 seconds

## Related Documentation

- **HARNESS_RACING_README.md** - Complete system overview
- **HARNESS_RACING_IMPLEMENTATION.md** - Technical details
- **HARNESS_GUI_ENHANCEMENTS.md** - Feature documentation
- **USAGE_EXAMPLES.py** - Code examples

## Support

For issues or questions, refer to:
- Test suite: `python test_harness_gui.py`
- Test racing: `python test_harness_racing.py`
- Main documentation in `docs/` folder

## Version History

- **v1.0** (Original): Basic GUI with horse generation, race selection, instant simulation
- **v2.0** (Current): Added live visualization, curved tracks, commentary, F1-style positions

## Quick Commands Reference

```bash
# Run GUI
python HarnessRacingGUI.py

# Run tests
python test_harness_gui.py
python test_harness_racing.py

# Generate config only
python HarnessConfigGenerator.py

# Test commentary
python harness_commentary.py
```

---

**Enjoy realistic European harness racing simulation!** 🐴🏁
