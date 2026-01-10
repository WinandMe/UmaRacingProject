"""
Hybrid Race Engine - Supports both Uma Musume Flat Racing and Harness Racing

This module extends the flat racing engine to support harness racing mechanics
while maintaining backward compatibility with existing Uma Musume simulations.

RacingMode:
    - FLAT_RACING: Traditional Uma Musume horse racing
    - HARNESS_RACING: European harness racing with trotters/pacers and sulkies
"""

from enum import Enum
from typing import Union, Optional
from harness_engine import HarnessRaceEngine, SulkyConfiguration
from harness_races import HarnessRace, HarnessStatCategory


class RacingMode(Enum):
    """Type of racing to simulate"""
    FLAT_RACING = "flat"          # Uma Musume style
    HARNESS_RACING = "harness"    # European harness


class HybridRaceEngine:
    """
    Manages both flat and harness racing simulations
    
    This is a factory/adapter that routes to appropriate engine based on race type
    """
    
    def __init__(self, mode: RacingMode = RacingMode.FLAT_RACING):
        self.mode = mode
        self.flat_engine = None
        self.harness_engine = None
    
    def setup_flat_race(self, race, horses, participation_requirement=None):
        """Setup a flat racing simulation (Uma Musume)"""
        self.mode = RacingMode.FLAT_RACING
        # Import here to avoid circular imports
        from race_engine import RaceEngine
        self.flat_engine = RaceEngine(race, horses, participation_requirement)
        return self.flat_engine
    
    def setup_harness_race(self, race: HarnessRace, horses, 
                          sulky_config: Optional[SulkyConfiguration] = None):
        """Setup a harness racing simulation"""
        self.mode = RacingMode.HARNESS_RACING
        self.harness_engine = HarnessRaceEngine(race, horses, sulky_config)
        return self.harness_engine
    
    def run_race(self):
        """Run the current race simulation"""
        if self.mode == RacingMode.FLAT_RACING:
            if not self.flat_engine:
                raise ValueError("Flat racing engine not initialized")
            return self.flat_engine.run_race()
        else:
            if not self.harness_engine:
                raise ValueError("Harness racing engine not initialized")
            return self.harness_engine.run_race()
    
    def get_summary(self):
        """Get race summary for current mode"""
        if self.mode == RacingMode.FLAT_RACING:
            return self.flat_engine.get_race_summary()
        else:
            return self.harness_engine.get_race_summary()


def convert_flat_stats_to_harness(flat_stats):
    """
    Convert Uma Musume stats to Harness Racing stats
    
    Mapping:
        Speed → Pulling Power (primary stat for acceleration)
        Stamina → Endurance (ability to sustain effort)
        Power → Sulky Tolerance (ability to pull heavy weight)
        Guts → Heat Recovery (mental toughness across multiple rounds)
        Wisdom → Gait Consistency (smooth, efficient movement)
        
    Note: Harness racing doesn't have direct equivalents, so this is approximate
    """
    from harness_races import HarnessStatCategory
    
    if not hasattr(flat_stats, '__dict__'):
        return None
    
    stats_dict = flat_stats.__dict__ if hasattr(flat_stats, '__dict__') else flat_stats
    
    return {
        'pulling_power': int(stats_dict.get('speed', 50) * 1.1),      # Speed → Pulling Power
        'endurance': int(stats_dict.get('stamina', 50)),               # Stamina → Endurance
        'gait_consistency': int(stats_dict.get('wisdom', 50) * 1.2),   # Wisdom → Gait Consistency
        'heat_recovery': int(stats_dict.get('guts', 50)),              # Guts → Heat Recovery
        'start_acceleration': int(stats_dict.get('speed', 50) * 0.8),  # Speed → Start Acceleration
        'temperament': int(stats_dict.get('guts', 50) * 0.9),          # Guts → Temperament
        'sulky_tolerance': int(stats_dict.get('power', 50) * 1.3),     # Power → Sulky Tolerance
    }


def convert_harness_stats_to_flat(harness_stats):
    """
    Convert Harness Racing stats to Uma Musume stats
    
    Reverse mapping for cross-compatibility
    """
    if not hasattr(harness_stats, '__dict__'):
        return None
    
    stats_dict = harness_stats.__dict__ if hasattr(harness_stats, '__dict__') else harness_stats
    
    return {
        'speed': int(stats_dict.get('pulling_power', 50) / 1.1),
        'stamina': int(stats_dict.get('endurance', 50)),
        'power': int(stats_dict.get('sulky_tolerance', 50) / 1.3),
        'guts': max(
            int(stats_dict.get('heat_recovery', 50)),
            int(stats_dict.get('temperament', 50) / 0.9)
        ),
        'wisdom': int(stats_dict.get('gait_consistency', 50) / 1.2),
    }


if __name__ == "__main__":
    print("Hybrid Race Engine loaded")
    print(f"Available racing modes: {[m.value for m in RacingMode]}")
    
    # Example stat conversion
    class FlatStats:
        def __init__(self):
            self.speed = 60
            self.stamina = 70
            self.power = 50
            self.guts = 65
            self.wisdom = 55
    
    flat = FlatStats()
    harness = convert_flat_stats_to_harness(flat)
    print(f"\nFlat stats: Speed={flat.speed}, Stamina={flat.stamina}, Power={flat.power}")
    print(f"Harness stats: {harness}")
    
    back = convert_harness_stats_to_flat(harness)
    print(f"Converted back: {back}")
