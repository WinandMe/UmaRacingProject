# Experimental Features

## 🧪 Active Development Versions

### V4 Racing GUI Series
All V4 versions feature major racing mechanism overhauls:

#### `V4_stable/`
- **UmaRacingGUI_V4.py** - Base V4 implementation
- Major overhaul of the core racing mechanism
- Foundation for all other V4 variants

#### `V4_overhauled/`
- **UmaRacingGUI_V4_overhauled.py** - Enhanced V4
- Further improvements and refinements on the V4 base
- Different approach to the racing mechanics

#### `V4_another_mechanism/`
- **UmaRacingGUI_V4_another_mechanism.py** - Alternative V4
- Completely different implementation approach
- Does NOT overwrite or replace the overhauled version

### New Configuration System
Located in `config_generators/`:

#### `UmaConfigGenerator_V2.py`
- Introduces skill list functionality (lists currently empty)
- Designed for use with V4 GUI versions only
- **Incompatible with V3 and earlier GUI versions**

#### `UmaConfigGenerator_V3.py`
- Improved version of V2 with partial skill lists populated
- Same compatibility as V2 (V4 GUI versions only)
- More features and better organization

#### `UmaSkills.json`
- Required data file for V2/V3 config generators
- Contains skill definitions and data
- Must be in the same directory as the config generators

## ⚠️ Important Notes

- **V4 versions are EXPERIMENTAL** and may be unstable
- **V2/V3 config generators ONLY work with V4 GUI versions**
- **UmaSkills.json is REQUIRED** for the new config system
- These versions are under active development and testing

## 🎯 Usage
```bash
# For V4 experimental versions:
cd experimental/V4_stable/
python UmaRacingGUI_V4.py

# With new config system:
cd experimental/config_generators/
python UmaConfigGenerator_V3.py