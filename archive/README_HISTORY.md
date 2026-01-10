# Project History & Version Archive

This directory contains historical versions of the Uma Racing Project for reference and educational purposes.

## 📁 Archive Structure

### `/v1_original/` - The Foundation
- **UmaRacing.py** - The very first base file that started it all (deprecated)
  - Original command-line/text-based racing simulation
  - Foundation for all future GUI versions

- **UmaRacingGUI_Original.py** - First GUI Release
  - Initial graphical interface built on top of UmaRacing.py
  - Basic functionality and layout

### `/v2_improved/` - Early Improvements
- **UmaRacingGUI_V2.py** - Enhanced GUI Release
  - Improvements to the original GUI interface
  - Better user experience and additional features

### `/v3_tkinter/` - last release of tkinter based UI 

- **UmaRacingGUI_V3.py** - last tkinter before switch to PySide6
  - adding better cornering mechanism to the sim
  - track indicator still straight, might implement it later

### `/spec_1_upt/` - Major changes with PySide6

- **UmaRacingGUI_SP1.py** - The Main App
  - curved tracks implemented 
  - commentaries
  - skills
  - live position standing sidebar
  - Python engine overhauls



## 🔄 Compatibility Notes

| Version | Config Generator Compatibility |
|---------|--------------------------------|
| v1_original | Basic configuration only |
| v2_improved | Basic configuration only |
| Current Stable (V3) | **UmaConfigGenerator.py** (from `/src/`) |
| Experimental V4 | **UmaConfigGenerator_V2/V3.py** (from `/experimental/config_generators/`) |

## 📝 Why Archive These Versions?

These files are preserved to:
- Show the project's evolution and development journey
- Provide reference for specific algorithms or approaches
- Demonstrate how the codebase has grown and improved
- Serve as educational examples of iterative development

---

**Note**: For current development, use files in `/src/` (stable) or `/experimental/` (new features).