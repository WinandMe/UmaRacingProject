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

## 🚀 Version Evolution

### Generation 1 (Archived)
- **UmaRacing.py (Base) → UmaRacingGUI_Original.py → UmaRacingGUI_V2.py**

### Generation 2 (Current Stable - in `/src/`)
- **UmaRacingGUI_V3.py** - Major GUI overhaul of race indicators
- **Most tested and reliable version**
- Used extensively for race simulations

### Generation 3 (Experimental - in `/experimental/`)
- V4 series with completely overhauled racing mechanisms
- New config generator system with skill management

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