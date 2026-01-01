# Uma Racing Simulator

A Python-based racing simulator inspired by Uma Musume, featuring a graphical interface, customizable race parameters, detailed commentary generation, and aptitude-based race calculations.

> ⚠️ This project is source-available, not open-source.
> Usage requires explicit permission from the author.
> Forking does not grant permission to use, run, or distribute the simulator without explicit authorization from the author.

## Overview

The Uma Racing Simulator provides a complete toolset for creating and running simulated races for roleplay or community events, including:

* Customizable race settings
* Automated commentary output
* Aptitude and performance calculations
* Human-readable result formatting
* A graphical user interface
* A configuration generator for runners

This project was originally created for community hobby purposes and remains open for future extension.

# Uma Racing Simulator

A polished and community-focused Python racing simulator inspired by
**Uma Musume**, designed for roleplay, events, and hobby
experimentation.\
This project provides a stable GUI race simulator, a configuration
generator, and experimental prototypes for future expansions.

> **Note:** Parts of this project were developed with AI-assisted coding
> as the author continues to learn.\
> feedbacks are always welcome.

------------------------------------------------------------------------

## ⭐ Features

The Uma Racing Simulator includes:

-   **Customizable race parameters**
-   **Aptitude- and stat-based performance calculations**
-   **Dynamic commentary generation**
-   **Readable race result formatting**
-   **Graphical user interface (GUI)**
-   **A configuration generator for runners**
-   **A modular, extensible project structure**
-   **Harness Racing System** - European harness racing simulator with live visualization
-   **Live Race Animation** - 30 FPS curved track rendering with real-time positions
-   **Dynamic Commentary** - 200+ commentary lines with race events and incidents
-   **17 European Tracks** - Authentic harness racing track layouts
-   **154+ Races** - G1, G2, G3 flat racing + 67 international races + 16 harness races
-   **559 Skills** - Complete skill database with unique and JP-exclusive skills

Perfect for: - RP communities\
- Organized events\
- Hobby simulations\
- Cross-genre racing experimentation\
- Casual fun & storytelling

------------------------------------------------------------------------

Project Structure

---

```txt

UmaRacingProject/

├── src/ # Stable, production-ready versions

│ ├── UmaRacingGUI.py # Primary GUI simulator

│ └── UmaConfigGenerator.py # Compatible configuration generator

│

├── experimental/ # In-development versions (V4+ prototypes)

│ └── ... # Mechanism overhauls, new skill systems, rewrites

│

├── archive/ # Older versions and historical snapshots

│

└── docs/ # Documentation

```

------------------------------------------------------------------------

## 🏇 Racing Systems

### Flat Racing (Uma Musume)
Traditional flat horse racing with 5 core stats: Speed, Stamina, Power, Guts, Wisdom.
- **Races**: 154 total (25 G1, 29 G2, 33 G3, 67 international)
- **Tracks**: 53 racecourses (17 JRA, 7 NAR Japan, 29 international)
- **Skills**: 559 total (63 unique character skills, 15 JP-exclusive)
- **Interface**: UmaRacingGUI.py, UmaConfigGenerator.py

### Harness Racing (European Trotters)
European harness racing with specialized 7-stat system for sulky-pulling mechanics.
- **Races**: 16 major European harness races (Prix d'Amérique, Elitloppet, Oslo Grand Prix, etc.)
- **Tracks**: 13 European harness tracks (Paris-Vincennes, Solvalla, Bjerke, etc.)
- **Stats**: Pulling Power, Endurance, Gait Consistency, Heat Recovery, Start Acceleration, Temperament, Sulky Tolerance
- **Horse Age**: 2-3 years (young trotters)
- **Sulky Weight**: 700-850kg realistic equipment
- **Interface**: HarnessRacingGUI.py, HarnessConfigGenerator.py
- **Documentation**: See [HARNESS_RACING_README.md](src/HARNESS_RACING_README.md)

------------------------------------------------------------------------

## 🚀 Quick Start

For the **recommended stable experience**, use:

-   `src/UmaRacingGUI.py`
-   `src/UmaConfigGenerator.py`

These versions are fully compatible and represent the most polished
implementation.

------------------------------------------------------------------------

## 🧪 Experimental Versions (V4+)

The `experimental/` directory includes ongoing prototypes featuring:

-   Overhauled calculation logic
-   Expanded systems and skill mechanics
-   Architectural redesigns for future features

These versions may include breaking changes or untested features.\
Use only if you're comfortable with experimentation.

------------------------------------------------------------------------

## 🏇 Harness Racing System (v2.0)

The harness racing system now features live race visualization matching the flat racing GUI:

### New Features
- **Live Race Animation** - 30 FPS smooth animation with curved tracks
- **F1-Style Positions** - Real-time standings sidebar with gate colors
- **Dynamic Commentary** - 200+ commentary lines for harness-specific events
- **17 European Tracks** - Authentic layouts (Paris-Vincennes, Solvalla, Milan, etc.)
- **Visual Indicators** - Gait breaks (red pulse), sulky carts, finish markers
- **Dual Race Modes** - Live animated or instant simulation

### Quick Start
```bash
cd src
python HarnessRacingGUI.py
```

1. **Tab 1**: Generate 3-10 harness horses with 7-stat system
2. **Tab 2**: Select from 16 major European harness races
3. **Tab 3**: Click "Run Race (Live)" for animated race
4. **Tab 4**: View results and save with commentary

### Documentation
- [HARNESS_GUI_ENHANCEMENTS.md](docs/HARNESS_GUI_ENHANCEMENTS.md) - Complete feature guide
- [HARNESS_QUICK_START.md](docs/HARNESS_QUICK_START.md) - Quick reference
- [VISUAL_ENHANCEMENTS.txt](docs/VISUAL_ENHANCEMENTS.txt) - Visual diagrams

------------------------------------------------------------------------

## 📦 Requirements

-   **Python 3.6+**
-   **PySide6** in order to wrk for the newest update

Everything runs with the Python standard library.

------------------------------------------------------------------------

## ⚖️ License

**Copyright © WinandMe**

This project is **source-available**, not open-source.

You may view the source code for educational and review purposes.

❌ You may NOT:
- Modify the code
- Redistribute the code
- Use the simulator in other projects
- Fork or rehost the project
- Use it in public communities or events

…unless you have **explicit permission from the author**.

### Approved Contributors
The following individuals are permitted to modify and use this project:
- Ilfaust-Rembrandt

Any other usage requires direct consent from the author.

See the `LICENSE` file for full terms.


------------------------------------------------------------------------

## 🤝 Contributions

This project accepts contributions **by invitation or prior discussion only**.

If you wish to contribute:
1. Open an Issue to discuss the idea first
2. Wait for explicit approval before submitting changes

Unauthorized pull requests may be declined.

------------------------------------------------------------------------

## 📬 Contact

For licensing, permissions, or usage requests, please contact the author via GitHub Issues.


------------------------------------------------------------------------
