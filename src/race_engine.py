"""
Uma Musume Race Simulation Engine
=================================
Combines authentic mechanics from:
- umamusu.wiki/Game:Mechanics (exact formulas)
- gametora.com/umamusume/race-mechanics (detailed mechanics descriptions)

CORE FORMULAS (from Wiki):
--------------------------
Base Speed:
    BaseSpeed = 20.0 - (CourseDistance - 2000m) / 1000 [m/s]
    Example: 1200m = 20.8 m/s, 2000m = 20.0 m/s, 2500m = 19.5 m/s

Base Target Speed (Opening/Middle Leg):
    BaseTargetSpeed = BaseSpeed × StrategyPhaseCoef
    NOTE: Speed stat does NOT affect this!

Base Target Speed (Final Leg/Last Spurt):
    BaseTargetSpeed = BaseSpeed × StrategyPhaseCoef + sqrt(500 × SpeedStat) × DistProf × 0.002

Acceleration:
    Accel = BaseAccel × sqrt(500.0 × PowerStat) × StrategyPhaseCoef × GroundProf × DistProf
    BaseAccel = 0.0006 m/s² (normal), 0.0004 m/s² (uphill)
    Start Dash: +24.0 m/s² additional acceleration until speed reaches 0.85 × BaseSpeed

HP (Stamina):
    MaxHP = 0.8 × StrategyCoef × StaminaStat + CourseDistance[m]
    HPConsumption = 20.0 × (CurrentSpeed - BaseSpeed + 12.0)² / 144.0 × Modifiers

Guts (Final Leg):
    GutsModifier = 1.0 + (200 / sqrt(600.0 × GutsStat))
    HP consumption multiplied by GutsModifier in final leg/last spurt

Minimum Speed:
    MinSpeed = 0.85 × BaseSpeed + sqrt(200.0 × GutsStat) × 0.001 [m/s]

Stats Soft Cap:
    Stats past 1200 are halved before calculations

ADDITIONAL MECHANICS (from GameTora):
-------------------------------------
Terrain Conditions:
    - Heavy terrain: Speed stat -50
    - Turf (non-firm): Power stat -50
    - Dirt (non-good): Power stat -100 (or -50 for good)
    - Soft/Heavy: HP consumption +2%

Stat Thresholds:
    - Exceeding course threshold by 300+: Speed +5% (up to +20% at 900+)

Position Keep (until mid-Mid-Race):
    - Front Runners: Speed Up / Overtake modes
    - Others: Pace Up / Pace Down modes based on pacemaker distance

Rushing:
    - Random trigger between mid-Early to mid-Mid-Race
    - HP consumption 1.6x while active
    - Duration: 3-12 seconds

Dueling:
    - Triggers on Final Straight when within 3m for 2+ seconds
    - Requires 15%+ HP
    - Both gain Target Speed + Acceleration from Guts

Spot Struggle:
    - Front Runners within 3.75m trigger contest
    - HP consumption 1.4x during struggle

Start Delay:
    - Random 0-0.1s delay
    - 0.066s+ = Late Start (loses start dash bonus)
"""

import random
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple, Set

# Import skills system
try:
    from skills import (
        Skill, SkillEffect, SkillCondition, ActiveSkill, 
        SkillRarity, SkillTriggerPhase, SkillTriggerPosition,
        SkillTriggerTerrain, SkillEffectType,
        RunningStyleRequirement, RaceTypeRequirement,
        SKILLS_DATABASE, get_skill_by_id
    )
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False


class RacePhase(Enum):
    """
    Race phases based on authentic Uma Musume mechanics.
    Phases are defined by sixths of the race distance.
    """
    START = auto()      # 0-1/6 (0-16.67%): Initial acceleration from gates
    MIDDLE = auto()     # 1/6-4/6 (16.67-66.67%): Stable cruising
    LATE = auto()       # 4/6-5/6 (66.67-83.33%): Speed stat starts affecting target speed
    FINAL_SPURT = auto() # 5/6-6/6 (83.33-100%): Maximum output, Speed stat fully active


class RunningStyle(Enum):
    """Running style archetypes affecting pacing AI"""
    FR = "Front Runner"   # High early speed, front position
    PC = "Pace Chaser"    # Near-front, balanced approach
    LS = "Late Surger"    # Mid-pack, strong late push
    EC = "End Closer"     # Backline, extreme final push


@dataclass
class PhaseConfig:
    """Configuration for a race phase based on authentic game mechanics"""
    progress_start: float      # Phase start (0.0 to 1.0) - using sixths
    progress_end: float        # Phase end (0.0 to 1.0)
    target_speed: float        # Base target speed in m/s (from GameTora)
    speed_stat_affects: bool   # Whether Speed stat modifies target speed this phase
    accel_modifier: float      # Multiplier for base acceleration
    stamina_drain_mult: float  # Multiplier for stamina consumption


@dataclass
class RunningStyleConfig:
    """
    Configuration for running style behavior.
    Stamina efficiency values from GameTora:
    - EC: ~111% HP efficiency (best)
    - LS: ~111% HP efficiency
    - PC: Lowest efficiency
    - FR: Medium efficiency
    """
    target_position_ratio: float  # Preferred position (0.0=front, 1.0=back)
    early_accel_bonus: float      # Acceleration modifier in START phase
    mid_accel_bonus: float        # Acceleration modifier in MIDDLE phase
    late_accel_bonus: float       # Acceleration modifier in LATE phase
    final_accel_bonus: float      # Acceleration modifier in FINAL_SPURT
    stamina_efficiency: float     # HP efficiency multiplier (higher = more HP from stamina)
    hp_recovery_bonus: float      # Bonus to HP recovery (EC/LS get more)


@dataclass
class UmaState:
    """Runtime state for a single Uma during race"""
    name: str
    distance: float = 0.0
    current_speed: float = 3.0    # Start at 3 m/s (authentic starting speed)
    hp: float = 100.0             # HP (converted from stamina stat)
    max_hp: float = 100.0         # Max HP for this Uma
    fatigue: float = 0.0
    lane: int = 0
    is_blocked: bool = False
    in_final_spurt: bool = False
    is_finished: bool = False
    is_dnf: bool = False
    dnf_reason: str = ""
    finish_time: float = 0.0
    position: int = 0
    # Per-Uma random factor for speed variation (set at race start)
    speed_variance_seed: float = 0.0  # -0.01 to +0.01 base modifier
    # GameTora mechanics state
    start_delay: float = 0.0          # Random 0-0.1s start delay
    is_late_start: bool = False       # True if start_delay >= 0.066s
    is_rushing: bool = False          # Rushing state (increased HP consumption)
    rushing_timer: float = 0.0        # Time remaining in rushing state
    is_in_duel: bool = False          # Dueling state
    duel_partner: str = ""            # Name of dueling partner
    duel_proximity_timer: float = 0.0 # Time spent near potential duel partner
    is_in_spot_struggle: bool = False # Spot Struggle state (FR only)
    position_keep_mode: str = "normal"  # normal/pace_up/pace_down/speed_up/overtake
    position_keep_active: bool = True   # Active until mid-Mid-Race
    # Skills system state
    equipped_skills: List[str] = field(default_factory=list)  # List of skill IDs
    active_skills: List['ActiveSkillState'] = field(default_factory=list)  # Currently active skills
    skill_cooldowns: Dict[str, float] = field(default_factory=dict)  # Skill ID -> remaining cooldown
    skills_activated_once: set = field(default_factory=set)  # Skills that have been activated (can only proc once)
    skills_activated_log: List[str] = field(default_factory=list)  # Log of activated skill names (for UI)
    # Terrain state (for skill triggers)
    current_terrain: str = "straight"  # straight, corner, uphill, downhill
    
    # For compatibility with old code
    @property
    def stamina(self) -> float:
        return (self.hp / self.max_hp) * 100.0


# =============================================================================
# TERRAIN & TRACK CONDITIONS (from GameTora)
# =============================================================================

class TerrainType(Enum):
    TURF = "turf"
    DIRT = "dirt"


class TrackCondition(Enum):
    FIRM = "firm"      # Best condition
    GOOD = "good"      # Slightly heavy
    SOFT = "soft"      # Heavy
    HEAVY = "heavy"    # Worst condition


# Stat penalties from terrain condition (GameTora)
TERRAIN_STAT_PENALTIES = {
    # (terrain_type, condition): {'speed': penalty, 'power': penalty, 'hp_mult': multiplier}
    (TerrainType.TURF, TrackCondition.FIRM): {'speed': 0, 'power': 0, 'hp_mult': 1.0},
    (TerrainType.TURF, TrackCondition.GOOD): {'speed': 0, 'power': 50, 'hp_mult': 1.0},
    (TerrainType.TURF, TrackCondition.SOFT): {'speed': 0, 'power': 50, 'hp_mult': 1.02},
    (TerrainType.TURF, TrackCondition.HEAVY): {'speed': 50, 'power': 50, 'hp_mult': 1.02},
    (TerrainType.DIRT, TrackCondition.FIRM): {'speed': 0, 'power': 100, 'hp_mult': 1.0},
    (TerrainType.DIRT, TrackCondition.GOOD): {'speed': 0, 'power': 50, 'hp_mult': 1.0},
    (TerrainType.DIRT, TrackCondition.SOFT): {'speed': 0, 'power': 100, 'hp_mult': 1.02},
    (TerrainType.DIRT, TrackCondition.HEAVY): {'speed': 50, 'power': 100, 'hp_mult': 1.02},
}


@dataclass
class ActiveSkillState:
    """Runtime state for an active skill effect"""
    skill_id: str
    skill_name: str
    remaining_duration: float
    speed_bonus: float = 0.0
    accel_bonus: float = 0.0
    stamina_save: float = 0.0  # Percentage reduction in HP consumption


@dataclass
class UmaStats:
    """Static stats for a single Uma"""
    name: str
    speed: int = 100
    stamina: int = 100
    power: int = 100
    guts: int = 100
    wisdom: int = 100
    running_style: RunningStyle = RunningStyle.PC
    distance_aptitude: str = "B"  # S/A/B/C/D/E/F/G
    surface_aptitude: str = "B"
    skills: List[str] = field(default_factory=list)  # List of equipped skill IDs


# =============================================================================
# PHASE CONFIGURATIONS (from umamusu.wiki)
# =============================================================================
# Race is divided into 4 phases (sections 1-24):
# Opening Leg (0): Section 1-4 (0-1/6)
# Middle Leg (1): Section 5-16 (1/6-4/6)
# Final Leg (2): Section 17-20 (4/6-5/6)
# Last Spurt (3): Section 21-24 (5/6-6/6)


SIXTH = 1.0 / 6.0

# Strategy Phase Coefficients from wiki (for target speed calculation)
# | Strategy     | Opening | Middle | Final/Spurt |
# | Front Runner |   1.0   |  0.98  |    0.962    |
# | Pace Chaser  |  0.978  |  0.991 |    0.975    |
# | Late Surger  |  0.93   |  0.998 |    0.994    |
# | End Closer   |  0.931  |  1.0   |    1.02     |

STRATEGY_SPEED_COEF = {
    RunningStyle.FR: {'opening': 1.0, 'middle': 0.98, 'final': 0.962},
    RunningStyle.PC: {'opening': 0.978, 'middle': 0.991, 'final': 0.975},
    RunningStyle.LS: {'opening': 0.93, 'middle': 0.998, 'final': 0.994},
    RunningStyle.EC: {'opening': 0.931, 'middle': 1.0, 'final': 1.02},
}

# Strategy Phase Coefficients for Acceleration from wiki
# | Strategy     | Opening | Middle | Final/Spurt |
# | Front Runner |   1.0   |  1.0   |    0.996    |
# | Pace Chaser  |  0.985  |  1.0   |    0.996    |
# | Late Surger  |  0.975  |  1.0   |    1.0      |
# | End Closer   |  0.945  |  1.0   |    0.967    |

STRATEGY_ACCEL_COEF = {
    RunningStyle.FR: {'opening': 1.0, 'middle': 1.0, 'final': 0.996},
    RunningStyle.PC: {'opening': 0.985, 'middle': 1.0, 'final': 0.996},
    RunningStyle.LS: {'opening': 0.975, 'middle': 1.0, 'final': 1.0},
    RunningStyle.EC: {'opening': 0.945, 'middle': 1.0, 'final': 0.967},
}

# HP (Stamina) Conversion Coefficients from wiki
# | Front Runner | Pace Chaser | Late Surger | End Closer |
# |    0.95      |    0.89     |    1.0      |   0.995    |

STRATEGY_HP_COEF = {
    RunningStyle.FR: 0.95,
    RunningStyle.PC: 0.89,
    RunningStyle.LS: 1.0,
    RunningStyle.EC: 0.995,
}

# Phase boundaries (using sections mapped to progress)
PHASE_CONFIGS = {
    RacePhase.START: {'start': 0.0, 'end': SIXTH},           # Sections 1-4
    RacePhase.MIDDLE: {'start': SIXTH, 'end': 4 * SIXTH},    # Sections 5-16
    RacePhase.LATE: {'start': 4 * SIXTH, 'end': 5 * SIXTH},  # Sections 17-20
    RacePhase.FINAL_SPURT: {'start': 5 * SIXTH, 'end': 1.0}, # Sections 21-24
}


# =============================================================================
# RUNNING STYLE CONFIGURATIONS (simplified for simulation)
# =============================================================================
# Target position ratios for AI positioning behavior

STYLE_CONFIGS = {
    RunningStyle.FR: RunningStyleConfig(
        target_position_ratio=0.15,
        early_accel_bonus=1.0,
        mid_accel_bonus=1.0,
        late_accel_bonus=0.996,
        final_accel_bonus=0.996,
        stamina_efficiency=0.95,
        hp_recovery_bonus=1.0,
    ),
    RunningStyle.PC: RunningStyleConfig(
        target_position_ratio=0.30,
        early_accel_bonus=0.985,
        mid_accel_bonus=1.0,
        late_accel_bonus=0.996,
        final_accel_bonus=0.996,
        stamina_efficiency=0.89,
        hp_recovery_bonus=0.9,
    ),
    RunningStyle.LS: RunningStyleConfig(
        target_position_ratio=0.50,
        early_accel_bonus=0.975,
        mid_accel_bonus=1.0,
        late_accel_bonus=1.0,
        final_accel_bonus=1.0,
        stamina_efficiency=1.0,
        hp_recovery_bonus=1.0,
    ),
    RunningStyle.EC: RunningStyleConfig(
        target_position_ratio=0.75,
        early_accel_bonus=0.945,
        mid_accel_bonus=1.0,
        late_accel_bonus=0.967,
        final_accel_bonus=0.967,
        stamina_efficiency=0.995,
        hp_recovery_bonus=1.0,
    ),
}


# =============================================================================
# APTITUDE MULTIPLIERS (from wiki - for target speed in final leg)
# =============================================================================
# | S   | A   | B   | C   | D   | E   | F   | G   |
# | 1.05| 1.0 | 0.9 | 0.8 | 0.6 | 0.4 | 0.2 | 0.1 |

DISTANCE_APTITUDE_SPEED = {
    'S': 1.05, 'A': 1.0, 'B': 0.9, 'C': 0.8, 
    'D': 0.6, 'E': 0.4, 'F': 0.2, 'G': 0.1,
}

# Acceleration aptitude (different from speed!)
# | S   | A   | B   | C   | D   | E   | F   | G   |
# | 1.05| 1.0 | 0.9 | 0.8 | 0.7 | 0.5 | 0.3 | 0.1 |

DISTANCE_APTITUDE_ACCEL = {
    'S': 1.05, 'A': 1.0, 'B': 0.9, 'C': 0.8, 
    'D': 0.7, 'E': 0.5, 'F': 0.3, 'G': 0.1,
}

# Ground type (surface) proficiency for acceleration
# | S   | A   | B   | C   | D   | E   | F   | G   |
# | 1.0 | 1.0 | 1.0 | 1.0 | 1.0 | 0.6 | 0.5 | 0.4 |

SURFACE_APTITUDE_ACCEL = {
    'S': 1.0, 'A': 1.0, 'B': 1.0, 'C': 1.0, 
    'D': 1.0, 'E': 0.6, 'F': 0.5, 'G': 0.4,
}

# Surface aptitude for race course modifier (affects speed)
SURFACE_APTITUDE_SPEED = {
    'S': 1.1, 'A': 1.0, 'B': 0.85, 'C': 0.75,
    'D': 0.6, 'E': 0.4, 'F': 0.2, 'G': 0.1,
}


# =============================================================================
# RACE ENGINE
# =============================================================================

class RaceEngine:
    """
    Core race simulation engine using tick-based updates.
    Implements authentic Uma Musume mechanics from umamusu.wiki.
    
    Key formulas:
    - BaseSpeed = 20.0 - (distance - 2000) / 1000
    - Accel = 0.0006 × sqrt(500 × Power) × coefficients
    - Start Dash: +24.0 m/s² until speed reaches 0.85 × BaseSpeed
    - MaxHP = 0.8 × StrategyCoef × Stamina + Distance
    - HPConsumption = 20.0 × (Speed - BaseSpeed + 12)² / 144
    """
    
    # Base acceleration constant from wiki
    BASE_ACCEL = 0.0006  # m/s² (0.0004 for uphill)
    
    # Start dash acceleration bonus
    START_DASH_ACCEL = 24.0  # m/s²
    
    # Starting speed from wiki
    STARTING_SPEED = 3.0  # m/s
    
    # Stats soft cap (values past this are halved)
    STAT_SOFT_CAP = 1200
    
    # LOW STAT PENALTIES - Punish umas with lacking stats
    LOW_STAT_THRESHOLD = 400          # Stats below this get penalties
    CRITICAL_STAT_THRESHOLD = 100     # Stats below this get severe penalties (DNF risk)
    LOW_SPEED_PENALTY = 0.95          # 5% speed reduction per 100 below threshold
    LOW_STAMINA_HP_MULT = 1.3         # 30% more HP consumption if low stamina
    LOW_GUTS_DECEL_MULT = 1.5         # 50% faster deceleration when HP depleted
    LOW_POWER_ACCEL_PENALTY = 0.8     # 20% slower acceleration
    DNF_CHANCE_PER_TICK = 0.00005     # Very low base DNF chance per tick (only for <100 stats)
    
    # Blocking/lane constants
    LANE_BLOCK_SPEED_PENALTY = 0.988  # At 0m distance
    LANE_PROXIMITY_THRESHOLD = 2.0    # Meters for front blocking
    
    # HP thresholds
    HP_THRESHOLD_COMPETITION = 0.15   # 15% HP needed for competition fight
    HP_THRESHOLD_COMPETITION_END = 0.05  # 5% HP ends competition
    
    # GameTora constants
    RUSHING_HP_MULT = 1.6             # HP consumption multiplier while rushing
    SPOT_STRUGGLE_HP_MULT = 1.4       # HP consumption for FR spot struggle
    LATE_START_THRESHOLD = 0.066     # 0.066s+ = late start
    DUEL_DISTANCE_THRESHOLD = 3.0    # 3m proximity for dueling
    DUEL_SPEED_THRESHOLD = 0.6       # Must be within 0.6 m/s
    DUEL_HP_THRESHOLD = 0.15         # Need 15% HP to duel
    
    def __init__(self, race_distance: float, race_type: str = 'Medium', 
                 terrain: TerrainType = TerrainType.TURF,
                 track_condition: TrackCondition = TrackCondition.GOOD,
                 stat_threshold: int = 0,
                 seed: Optional[int] = None):
        """
        Initialize the race engine.
        
        Args:
            race_distance: Total race distance in meters
            race_type: One of 'Sprint', 'Mile', 'Medium', 'Long' (for categorization)
            terrain: TerrainType.TURF or TerrainType.DIRT
            track_condition: TrackCondition (FIRM/GOOD/SOFT/HEAVY)
            stat_threshold: Course stat threshold for speed bonus (0 = none)
            seed: Optional random seed for reproducibility
        """
        self.race_distance = race_distance
        self.race_type = race_type
        self.terrain = terrain
        self.track_condition = track_condition
        self.stat_threshold = stat_threshold
        
        # Calculate base speed from wiki formula
        # BaseSpeed = 20.0 - (CourseDistance - 2000) / 1000
        self.base_speed = 20.0 - (race_distance - 2000) / 1000.0
        
        # Get terrain penalties (from GameTora)
        terrain_key = (terrain, track_condition)
        self.terrain_penalties = TERRAIN_STAT_PENALTIES.get(
            terrain_key, 
            {'speed': 0, 'power': 0, 'hp_mult': 1.0}
        )
        
        self.uma_states: Dict[str, UmaState] = {}
        self.uma_stats: Dict[str, UmaStats] = {}
        self.current_time: float = 0.0
        self.is_finished: bool = False
        
        # Position keep ends at mid-Mid-Race (0.5 * 4/6 = 2/6 = 1/3 of race)
        self.position_keep_end = (1/6 + 0.5 * 3/6) * race_distance  # ~41.67% of race
        
        # Controlled RNG
        if seed is not None:
            random.seed(seed)
        self._rng_seed = seed
    
    def get_effective_stat(self, stat_value: int, stat_type: str = 'other') -> float:
        """
        Apply soft cap to stats (values past 1200 are halved).
        Also applies terrain penalties from GameTora.
        
        Args:
            stat_value: Raw stat value
            stat_type: 'speed', 'power', or 'other' for terrain penalties
        """
        # Apply terrain penalty first
        penalty = 0
        if stat_type == 'speed':
            penalty = self.terrain_penalties.get('speed', 0)
        elif stat_type == 'power':
            penalty = self.terrain_penalties.get('power', 0)
        
        adjusted_value = max(1, stat_value - penalty)
        
        # Then apply soft cap
        if adjusted_value <= self.STAT_SOFT_CAP:
            return float(adjusted_value)
        excess = adjusted_value - self.STAT_SOFT_CAP
        return self.STAT_SOFT_CAP + (excess / 2.0)
    
    def get_stat_threshold_bonus(self, stat_value: int) -> float:
        """
        Calculate speed bonus from exceeding course stat threshold (GameTora).
        +5% per 300 above threshold, max +20% at 900+
        """
        if self.stat_threshold <= 0 or stat_value <= self.stat_threshold:
            return 1.0
        
        excess = stat_value - self.stat_threshold
        bonus_tiers = min(excess // 300, 4)  # Max 4 tiers (20%)
        return 1.0 + (bonus_tiers * 0.05)
    
    def calculate_max_hp(self, stats: UmaStats) -> float:
        """
        Calculate max HP from wiki formula:
        MaxHP = 0.8 × StrategyCoefficient × StaminaStat + CourseDistance[m]
        """
        effective_stamina = self.get_effective_stat(stats.stamina)
        strategy_coef = STRATEGY_HP_COEF.get(stats.running_style, 1.0)
        
        max_hp = 0.8 * strategy_coef * effective_stamina + self.race_distance
        return max_hp
    
    def calculate_minimum_speed(self, uma_name: str) -> float:
        """
        Calculate minimum speed from wiki formula:
        MinSpeed = 0.85 × BaseSpeed + sqrt(200.0 × GutsStat) × 0.001 [m/s]
        """
        stats = self.uma_stats[uma_name]
        effective_guts = self.get_effective_stat(stats.guts)
        min_speed = 0.85 * self.base_speed + math.sqrt(200.0 * effective_guts) * 0.001
        return min_speed
    
    def generate_start_delay(self, stats: UmaStats) -> Tuple[float, bool]:
        """
        Generate random start delay (GameTora).
        Returns (delay_seconds, is_late_start)
        
        - Random 0-0.1s delay
        - 0.066s+ = Late Start (loses start dash bonus)
        - Wisdom does NOT affect this (contrary to popular belief)
        """
        delay = random.random() * 0.1  # 0 to 0.1 seconds
        is_late_start = delay >= self.LATE_START_THRESHOLD
        return delay, is_late_start
        
    def add_uma(self, stats: UmaStats) -> None:
        """Add an Uma to the race with initial state including start delay."""
        self.uma_stats[stats.name] = stats
        max_hp = self.calculate_max_hp(stats)
        
        # Generate start delay (GameTora mechanic)
        start_delay, is_late_start = self.generate_start_delay(stats)
        
        # Generate per-Uma speed variance seed (-1% to +1%)
        # This creates consistent individual variation throughout the race
        speed_variance_seed = (random.random() - 0.5) * 0.02
        
        state = UmaState(
            name=stats.name,
            lane=len(self.uma_states),
            current_speed=self.STARTING_SPEED,  # 3 m/s from wiki
            hp=max_hp,
            max_hp=max_hp,
            start_delay=start_delay,
            is_late_start=is_late_start,
            speed_variance_seed=speed_variance_seed,
            equipped_skills=list(stats.skills),  # Copy skills from stats
        )
        self.uma_states[stats.name] = state
        
    def reset(self) -> None:
        """Reset all Uma states to initial conditions."""
        for name in self.uma_states:
            stats = self.uma_stats[name]
            max_hp = self.calculate_max_hp(stats)
            start_delay, is_late_start = self.generate_start_delay(stats)
            # Generate new per-Uma speed variance seed
            speed_variance_seed = (random.random() - 0.5) * 0.02
            self.uma_states[name] = UmaState(
                name=name,
                lane=self.uma_states[name].lane,
                current_speed=self.STARTING_SPEED,
                hp=max_hp,
                max_hp=max_hp,
                start_delay=start_delay,
                is_late_start=is_late_start,
                speed_variance_seed=speed_variance_seed,
                equipped_skills=list(stats.skills),  # Copy skills from stats
            )
        self.current_time = 0.0
        self.is_finished = False
        
    def get_current_phase(self, progress: float) -> RacePhase:
        """Determine current race phase from progress (0.0 to 1.0)."""
        for phase, bounds in PHASE_CONFIGS.items():
            if bounds['start'] <= progress < bounds['end']:
                return phase
        return RacePhase.FINAL_SPURT
    
    def get_phase_name(self, phase: RacePhase) -> str:
        """Get phase name for coefficient lookup."""
        if phase == RacePhase.START:
            return 'opening'
        elif phase == RacePhase.MIDDLE:
            return 'middle'
        else:  # LATE or FINAL_SPURT
            return 'final'
    
    def calculate_base_speed_cap(self, uma_name: str, phase: RacePhase) -> float:
        """
        Calculate target speed from wiki formulas + GameTora enhancements.
        
        Opening/Middle Leg:
            BaseTargetSpeed = BaseSpeed × StrategyPhaseCoef
            (Speed stat does NOT affect this!)
        
        Final Leg/Last Spurt:
            BaseTargetSpeed = BaseSpeed × StrategyPhaseCoef + sqrt(500 × SpeedStat) × DistProf × 0.002
        
        GameTora additions:
            - Stat threshold bonus (+5% per 300 above threshold, max +20%)
            - Terrain/condition penalties applied via get_effective_stat
            
        LOW STAT PENALTY: Low Speed stat applies multiplicative penalty
        """
        stats = self.uma_stats[uma_name]
        phase_name = self.get_phase_name(phase)
        
        # Get strategy coefficient for this phase
        strategy_coef = STRATEGY_SPEED_COEF[stats.running_style][phase_name]
        
        # Base target speed (all phases)
        target_speed = self.base_speed * strategy_coef
        
        # Speed stat bonus ONLY in Final Leg and Last Spurt (from wiki)
        if phase in (RacePhase.LATE, RacePhase.FINAL_SPURT):
            # Apply terrain penalty to speed stat (GameTora)
            effective_speed = self.get_effective_stat(stats.speed, 'speed')
            
            # Distance proficiency modifier
            dist_prof = DISTANCE_APTITUDE_SPEED.get(stats.distance_aptitude, 0.9)
            
            # Wiki formula: + sqrt(500 × SpeedStat) × DistanceProf × 0.002
            speed_bonus = math.sqrt(500.0 * effective_speed) * dist_prof * 0.002
            target_speed += speed_bonus
            
            # Apply stat threshold bonus (GameTora: +5% per 300 above threshold)
            threshold_bonus = self.get_stat_threshold_bonus(stats.speed)
            target_speed *= threshold_bonus
        
        # Apply surface proficiency (affects adjusted speed)
        surf_prof = SURFACE_APTITUDE_SPEED.get(stats.surface_aptitude, 1.0)
        target_speed *= surf_prof
        
        # LOW STAT PENALTY: Very low Speed stat = noticeably slower
        effective_speed_for_penalty = self.get_effective_stat(stats.speed, 'speed')
        if effective_speed_for_penalty < self.CRITICAL_STAT_THRESHOLD:
            # Below 200: massive 15-20% speed reduction
            penalty = self.LOW_SPEED_PENALTY * 0.85  # ~0.81x
            target_speed *= penalty
        elif effective_speed_for_penalty < self.LOW_STAT_THRESHOLD:
            # Below 400: 5-10% speed reduction  
            target_speed *= self.LOW_SPEED_PENALTY  # 0.95x
        
        # Cap at 30 m/s (from wiki: Target speed cannot exceed 30 m/s)
        return min(target_speed, 30.0)
    
    def calculate_acceleration(self, uma_name: str, phase: RacePhase, is_start_dash: bool = False) -> float:
        """
        Calculate acceleration from wiki formula + GameTora enhancements:
        Accel = BaseAccel × sqrt(500.0 × PowerStat) × StrategyPhaseCoef × GroundProf × DistProf
        
        BaseAccel = 0.0006 m/s² (normal), 0.0004 m/s² (uphill)
        Start Dash: +24.0 m/s² additional acceleration (disabled if late start)
        
        GameTora: Late starts lose start dash bonus
        
        LOW STAT PENALTY: Low Power stat reduces acceleration
        """
        stats = self.uma_stats[uma_name]
        state = self.uma_states[uma_name]
        phase_name = self.get_phase_name(phase)
        
        # Base acceleration (0.0006 normal, 0.0004 uphill - we use normal)
        base_accel = self.BASE_ACCEL
        
        # Power contribution: sqrt(500.0 × PowerStat) with terrain penalty
        effective_power = self.get_effective_stat(stats.power, 'power')
        power_factor = math.sqrt(500.0 * effective_power)
        
        # Strategy phase coefficient for acceleration
        strategy_coef = STRATEGY_ACCEL_COEF[stats.running_style][phase_name]
        
        # Ground type (surface) proficiency
        ground_prof = SURFACE_APTITUDE_ACCEL.get(stats.surface_aptitude, 1.0)
        
        # Distance proficiency
        dist_prof = DISTANCE_APTITUDE_ACCEL.get(stats.distance_aptitude, 0.9)
        
        # Calculate acceleration
        acceleration = base_accel * power_factor * strategy_coef * ground_prof * dist_prof
        
        # LOW STAT PENALTY: Low Power = sluggish acceleration
        if effective_power < self.CRITICAL_STAT_THRESHOLD:
            # Below 200: severe 40% acceleration reduction
            acceleration *= self.LOW_POWER_ACCEL_PENALTY * 0.75  # ~0.6x
        elif effective_power < self.LOW_STAT_THRESHOLD:
            # Below 400: 20% acceleration reduction
            acceleration *= self.LOW_POWER_ACCEL_PENALTY  # 0.8x
        
        # Start dash bonus: +24.0 m/s² until speed reaches 0.85 × BaseSpeed
        # GameTora: Late starts (0.066s+ delay) LOSE start dash bonus
        if is_start_dash and not state.is_late_start:
            acceleration += self.START_DASH_ACCEL
        
        # HP penalty when low (simplified)
        hp_ratio = state.hp / state.max_hp
        if hp_ratio < 0.15:
            acceleration *= 0.5
        elif hp_ratio < 0.30:
            acceleration *= 0.7
        
        return acceleration
    
    def calculate_stamina_drain(self, uma_name: str, phase: RacePhase, current_speed: float) -> float:
        """
        Calculate HP consumption per second from wiki formula + GameTora:
        HPConsumption = 20.0 × (CurrentSpeed - BaseSpeed + 12.0)² / 144.0 × StatusMod × GroundMod
        
        In Final Leg/Last Spurt, multiply by Guts modifier:
        GutsModifier = 1.0 + (200 / sqrt(600.0 × GutsStat))
        
        GameTora additions:
        - Rushing: 1.6x HP consumption
        - Spot Struggle: 1.4x for FR
        - Soft/Heavy terrain: +2% HP consumption
        
        LOW STAT PENALTY: Low Stamina = faster HP drain
        """
        stats = self.uma_stats[uma_name]
        state = self.uma_states[uma_name]
        
        # Wiki formula: 20.0 × (CurrentSpeed - BaseSpeed + 12.0)² / 144.0
        speed_diff = current_speed - self.base_speed + 12.0
        hp_consumption = 20.0 * (speed_diff ** 2) / 144.0
        
        # Status modifier (GameTora)
        status_mod = 1.0
        if state.is_rushing:
            status_mod = self.RUSHING_HP_MULT  # 1.6x while rushing
        elif state.is_in_spot_struggle:
            status_mod = self.SPOT_STRUGGLE_HP_MULT  # 1.4x during spot struggle
        
        # Ground modifier (GameTora: soft/heavy = +2%)
        ground_mod = self.terrain_penalties.get('hp_mult', 1.0)
        
        hp_consumption *= status_mod * ground_mod
        
        # LOW STAT PENALTY: Low Stamina = burns through HP faster
        effective_stamina = self.get_effective_stat(stats.stamina)
        if effective_stamina < self.CRITICAL_STAT_THRESHOLD:
            # Below 200: severe 60% more HP drain
            hp_consumption *= self.LOW_STAMINA_HP_MULT * 1.25  # ~1.625x
        elif effective_stamina < self.LOW_STAT_THRESHOLD:
            # Below 400: 30% more HP drain
            hp_consumption *= self.LOW_STAMINA_HP_MULT  # 1.3x
        
        # Guts modifier in Final Leg and Last Spurt
        # GutsModifier = 1.0 + (200 / sqrt(600.0 × GutsStat))
        if phase in (RacePhase.LATE, RacePhase.FINAL_SPURT):
            effective_guts = self.get_effective_stat(stats.guts)
            # Prevent division by zero
            if effective_guts > 0:
                guts_modifier = 1.0 + (200.0 / math.sqrt(600.0 * effective_guts))
            else:
                guts_modifier = 2.0  # High penalty for 0 guts
            hp_consumption *= guts_modifier
            
            # LOW STAT PENALTY: Low Guts = even worse HP drain in final leg
            if effective_guts < self.CRITICAL_STAT_THRESHOLD:
                hp_consumption *= self.LOW_GUTS_DECEL_MULT  # 1.5x more
            elif effective_guts < self.LOW_STAT_THRESHOLD:
                hp_consumption *= 1.2  # 20% more
        
        return hp_consumption
    
    # =========================================================================
    # GAMETORA MECHANICS: Rushing, Dueling, Spot Struggle
    # =========================================================================
    
    def check_rushing(self, uma_name: str, progress: float, delta_time: float) -> None:
        """
        Check and update rushing state (GameTora).
        
        According to GameTora:
        - Random trigger between mid-Early (0.5/6) and mid-Mid-Race (2.5/6)
        - ONE chance per Uma per race (not continuous checking)
        - Probability based on Wisdom stat (lower = more likely)
        - Duration: 3-12 seconds
        - Effects: 1.6x HP consumption
        
        LOW STAT PENALTY: Very low wisdom drastically increases rushing chance
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return
        
        # Update existing rushing timer
        if state.is_rushing:
            state.rushing_timer -= delta_time
            if state.rushing_timer <= 0:
                state.is_rushing = False
                state.rushing_timer = 0.0
            return
        
        # Track if rushing check was already done (use negative timer as flag)
        if state.rushing_timer < 0:
            return  # Already checked, didn't trigger
        
        # Check if in valid range for rushing (mid-Early to mid-Mid)
        rush_start = 0.5 / 6.0  # Mid-Early-Race (~8.3%)
        rush_end = 2.5 / 6.0    # Mid-Mid-Race (~41.7%)
        if not (rush_start <= progress <= rush_end):
            return
        
        # ONE-TIME check at the start of the rush window
        # Wisdom affects rushing chance: lower wisdom = higher chance
        effective_wisdom = self.get_effective_stat(stats.wisdom)
        
        # Base chance: ~20% for 600 wisdom, scales down with higher wisdom
        # At 1200 wisdom: ~10%, at 400 wisdom: ~30%
        base_chance = 0.20
        wisdom_factor = 600.0 / max(effective_wisdom, 50)
        rush_chance = base_chance * wisdom_factor
        
        # LOW STAT PENALTY: Very low wisdom = almost guaranteed rushing
        if effective_wisdom < self.CRITICAL_STAT_THRESHOLD:
            # Below 200 wisdom: 70-90% chance to rush!
            rush_chance = 0.70 + (self.CRITICAL_STAT_THRESHOLD - effective_wisdom) / 1000.0
        elif effective_wisdom < self.LOW_STAT_THRESHOLD:
            # Below 400 wisdom: 40-70% chance
            rush_chance = 0.40 + (self.LOW_STAT_THRESHOLD - effective_wisdom) / 666.0
        
        rush_chance = min(0.95, max(0.05, rush_chance))  # Clamp 5-95%
        
        # Single roll
        if random.random() < rush_chance:
            state.is_rushing = True
            # Low wisdom = longer rushing duration (4-15 seconds instead of 3-12)
            base_duration = 3.0 if effective_wisdom >= self.LOW_STAT_THRESHOLD else 4.0
            max_extra = 9.0 if effective_wisdom >= self.LOW_STAT_THRESHOLD else 11.0
            state.rushing_timer = base_duration + random.random() * max_extra
        else:
            state.rushing_timer = -1.0  # Mark as checked (won't rush)
    
    def check_dueling(self, uma_name: str, delta_time: float) -> None:
        """
        Check and update dueling state based on GameTora/Wiki.
        
        Dueling is a RARE mechanic that only occurs when:
        - In Final Spurt (last 1/6 of race)
        - Only between the TOP 2 Uma in the race
        - Within 1.5m of each other (very close)
        - Both maintaining similar speed (within 0.5 m/s)
        - Both have 30%+ HP remaining
        - Must stay close for 3+ seconds to trigger
        
        Effects: Both gain speed and acceleration bonus from Guts
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return
        
        progress = state.distance / self.race_distance
        
        # Dueling ONLY in Final Spurt (last 1/6)
        if progress < 5.0 / 6.0:
            state.is_in_duel = False
            state.duel_partner = ""
            state.duel_proximity_timer = 0.0
            return
        
        # Need 30% HP to duel (stricter than basic 15%)
        if state.hp / state.max_hp < 0.30:
            state.is_in_duel = False
            state.duel_partner = ""
            state.duel_proximity_timer = 0.0
            return
        
        # Get active Uma sorted by distance (leaders first)
        active_uma = [
            (name, s.distance) for name, s in self.uma_states.items()
            if not s.is_finished and not s.is_dnf
        ]
        active_uma.sort(key=lambda x: x[1], reverse=True)
        
        # Only the top 2 Uma can duel
        if len(active_uma) < 2:
            state.is_in_duel = False
            state.duel_partner = ""
            return
        
        top_2_names = [active_uma[0][0], active_uma[1][0]]
        
        # This Uma must be in top 2
        if uma_name not in top_2_names:
            state.is_in_duel = False
            state.duel_partner = ""
            state.duel_proximity_timer = 0.0
            return
        
        # Get the other contender
        other_name = top_2_names[1] if uma_name == top_2_names[0] else top_2_names[0]
        other_state = self.uma_states[other_name]
        
        # Check other has enough HP
        if other_state.hp / other_state.max_hp < 0.30:
            state.is_in_duel = False
            state.duel_partner = ""
            state.duel_proximity_timer = 0.0
            return
        
        # Check distance (within 1.5m - very close)
        distance_diff = abs(other_state.distance - state.distance)
        if distance_diff > 1.5:
            state.is_in_duel = False
            state.duel_partner = ""
            state.duel_proximity_timer = 0.0
            return
        
        # Check speed similarity (within 0.5 m/s)
        speed_diff = abs(other_state.current_speed - state.current_speed)
        if speed_diff > 0.5:
            state.is_in_duel = False
            state.duel_partner = ""
            state.duel_proximity_timer = 0.0
            return
        
        # All conditions met - track proximity time
        state.duel_proximity_timer += delta_time
        
        # Need 3+ seconds of close proximity to trigger duel
        if state.duel_proximity_timer >= 3.0 and not state.is_in_duel:
            state.is_in_duel = True
            state.duel_partner = other_name
            other_state.is_in_duel = True
            other_state.duel_partner = uma_name
            other_state.duel_proximity_timer = state.duel_proximity_timer
    
    def check_spot_struggle(self, uma_name: str) -> None:
        """
        Check for Spot Struggle among Front Runners (GameTora).
        
        Conditions:
        - Front Runner or Runaway strategy
        - Within 3.75m of another FR
        - Between 150m after start and shortly after mid-Mid-Race
        
        Effects: 1.4x HP consumption, gain Target Speed from Guts
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return
        
        # Only FR can spot struggle
        if stats.running_style != RunningStyle.FR:
            return
        
        # Valid range: 150m after start to mid-Mid-Race
        if state.distance < 150 or state.distance > self.position_keep_end:
            state.is_in_spot_struggle = False
            return
        
        # Check for nearby Front Runners
        fr_threshold = 3.75  # meters
        for other_name, other_state in self.uma_states.items():
            if other_name == uma_name or other_state.is_finished or other_state.is_dnf:
                continue
            
            other_stats = self.uma_stats[other_name]
            if other_stats.running_style != RunningStyle.FR:
                continue
            
            distance_diff = abs(other_state.distance - state.distance)
            if distance_diff <= fr_threshold:
                state.is_in_spot_struggle = True
                return
        
        state.is_in_spot_struggle = False
    
    def get_duel_bonus(self, uma_name: str) -> Tuple[float, float]:
        """
        Calculate speed and acceleration bonuses from dueling (GameTora).
        Both depend on Guts stat.
        
        Returns: (speed_bonus, accel_bonus)
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if not state.is_in_duel:
            return 0.0, 0.0
        
        effective_guts = self.get_effective_stat(stats.guts)
        # Guts-based bonuses (scaled to reasonable values)
        speed_bonus = math.sqrt(effective_guts) * 0.005  # ~1.1 m/s at 1200 guts
        accel_bonus = math.sqrt(effective_guts) * 0.002  # ~0.07 m/s² at 1200 guts
        
        return speed_bonus, accel_bonus
    
    # =========================================================================
    # SKILLS SYSTEM
    # =========================================================================
    
    def check_skill_conditions(self, uma_name: str, skill_id: str, progress: float) -> bool:
        """
        Check if all conditions are met for a skill to activate.
        
        Returns: True if skill can activate
        """
        if not SKILLS_AVAILABLE:
            return False
        
        skill = get_skill_by_id(skill_id)
        if not skill:
            return False
        
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        cond = skill.condition
        
        # Check cooldown
        if skill_id in state.skill_cooldowns and state.skill_cooldowns[skill_id] > 0:
            return False
        
        # Check if skill is already active
        for active in state.active_skills:
            if active.skill_id == skill_id:
                return False
        
        # Check phase condition
        current_phase = self.get_current_phase(progress)
        if cond.phase != SkillTriggerPhase.ANY:
            phase_match = False
            if cond.phase == SkillTriggerPhase.EARLY and current_phase == RacePhase.START:
                phase_match = True
            elif cond.phase == SkillTriggerPhase.MID and current_phase == RacePhase.MIDDLE:
                phase_match = True
            elif cond.phase == SkillTriggerPhase.LATE and current_phase == RacePhase.LATE:
                phase_match = True
            elif cond.phase == SkillTriggerPhase.LAST_SPURT and current_phase == RacePhase.FINAL_SPURT:
                phase_match = True
            elif cond.phase == SkillTriggerPhase.SECOND_HALF and progress >= 0.5:
                phase_match = True
            if not phase_match:
                return False
        
        # Check position condition
        if cond.position != SkillTriggerPosition.ANY:
            rank = state.position
            total = len([s for s in self.uma_states.values() if not s.is_dnf])
            position_ratio = (rank - 1) / max(total - 1, 1)  # 0 = first, 1 = last
            
            pos_match = False
            if cond.position == SkillTriggerPosition.FRONT and position_ratio <= 0.25:
                pos_match = True
            elif cond.position == SkillTriggerPosition.MIDPACK and 0.25 < position_ratio <= 0.75:
                pos_match = True
            elif cond.position == SkillTriggerPosition.BACK and position_ratio > 0.75:
                pos_match = True
            if not pos_match:
                return False
        
        # Check terrain condition
        if cond.terrain != SkillTriggerTerrain.ANY:
            terrain_match = False
            if cond.terrain == SkillTriggerTerrain.STRAIGHT and state.current_terrain == "straight":
                terrain_match = True
            elif cond.terrain == SkillTriggerTerrain.CORNER and state.current_terrain == "corner":
                terrain_match = True
            elif cond.terrain == SkillTriggerTerrain.UPHILL and state.current_terrain == "uphill":
                terrain_match = True
            elif cond.terrain == SkillTriggerTerrain.DOWNHILL and state.current_terrain == "downhill":
                terrain_match = True
            if not terrain_match:
                return False
        
        # Check running style requirement
        if cond.running_style != RunningStyleRequirement.ANY:
            style_map = {
                RunningStyleRequirement.FR: RunningStyle.FR,
                RunningStyleRequirement.PC: RunningStyle.PC,
                RunningStyleRequirement.LS: RunningStyle.LS,
                RunningStyleRequirement.EC: RunningStyle.EC,
            }
            if stats.running_style != style_map.get(cond.running_style):
                return False
        
        # Check race type requirement
        if cond.race_type != RaceTypeRequirement.ANY:
            type_map = {
                RaceTypeRequirement.SPRINT: "Sprint",
                RaceTypeRequirement.MILE: "Mile",
                RaceTypeRequirement.MEDIUM: "Medium",
                RaceTypeRequirement.LONG: "Long",
            }
            if self.race_type != type_map.get(cond.race_type):
                return False
        
        # Check special conditions
        if cond.requires_challenge and not state.is_in_duel:
            return False
        if cond.requires_blocked and not state.is_blocked:
            return False
        if cond.requires_overtaken:
            # Check if being passed (simplification: position changed for worse)
            return False  # Would need history tracking
        if cond.requires_passing:
            # Check if passing another (simplification: check if speed > nearby Uma)
            for other_name, other_state in self.uma_states.items():
                if other_name == uma_name or other_state.is_finished or other_state.is_dnf:
                    continue
                # If we're slightly behind but faster, we might be passing
                dist_diff = state.distance - other_state.distance
                if -2.0 < dist_diff < 1.0 and state.current_speed > other_state.current_speed + 0.2:
                    break
            else:
                return False  # No one being passed
        
        # HP threshold check
        if cond.min_hp_percent > 0:
            hp_ratio = state.hp / state.max_hp
            if hp_ratio < cond.min_hp_percent:
                return False
        
        return True
    
    def try_activate_skill(self, uma_name: str, skill_id: str, progress: float) -> bool:
        """
        Try to activate a skill if conditions are met.
        Skills can only activate ONCE per race.
        
        Returns: True if skill was activated
        """
        if not SKILLS_AVAILABLE:
            return False
        
        state = self.uma_states[uma_name]
        
        # Check if skill has already been activated this race (skills only proc once)
        if skill_id in state.skills_activated_once:
            return False
        
        if not self.check_skill_conditions(uma_name, skill_id, progress):
            return False
        
        skill = get_skill_by_id(skill_id)
        if not skill:
            return False
        
        stats = self.uma_stats[uma_name]
        
        # Wisdom affects activation chance
        effective_wisdom = self.get_effective_stat(stats.wisdom)
        wisdom_factor = min(1.0, effective_wisdom / 800.0)  # 800 wisdom = 100% chance
        activation_chance = skill.activation_chance * (0.5 + 0.5 * wisdom_factor)
        
        if random.random() > activation_chance:
            return False
        
        # Skill activates!
        # Mark as activated once (can't proc again this race)
        state.skills_activated_once.add(skill_id)
        
        # Calculate effect values
        speed_bonus = 0.0
        accel_bonus = 0.0
        recovery_amount = 0.0
        stamina_save = 0.0
        duration = 0.0
        
        for effect in skill.effects:
            if effect.effect_type == SkillEffectType.SPEED:
                speed_bonus = effect.value
                duration = max(duration, effect.duration)
            elif effect.effect_type == SkillEffectType.CURRENT_SPEED:
                # Immediate speed boost (adds to current speed directly)
                state.current_speed += effect.value
            elif effect.effect_type == SkillEffectType.ACCELERATION:
                accel_bonus = effect.value
                duration = max(duration, effect.duration)
            elif effect.effect_type == SkillEffectType.RECOVERY:
                # Instant HP recovery (percentage of max HP)
                recovery_amount = effect.value * state.max_hp
                state.hp = min(state.max_hp, state.hp + recovery_amount)
            elif effect.effect_type == SkillEffectType.STAMINA_SAVE:
                stamina_save = effect.value
                duration = max(duration, effect.duration)
            elif effect.effect_type == SkillEffectType.START_BONUS:
                # Reduce start delay (only effective at race start)
                if self.current_time < 0.5:
                    state.start_delay *= (1.0 - effect.value)
        
        # Create active skill state if there's a duration effect
        if duration > 0:
            active_skill = ActiveSkillState(
                skill_id=skill_id,
                skill_name=skill.name,
                remaining_duration=duration,
                speed_bonus=speed_bonus,
                accel_bonus=accel_bonus,
                stamina_save=stamina_save,
            )
            state.active_skills.append(active_skill)
        
        # Set cooldown
        if skill.cooldown > 0:
            state.skill_cooldowns[skill_id] = skill.cooldown
        
        # Log activation for UI
        state.skills_activated_log.append(skill.name)
        
        # Debug: Log skill activation with terrain info
        print(f"[SKILL] {stats.name} activated '{skill.name}' @ {progress*100:.1f}% progress, terrain={state.current_terrain}")
        
        return True
    
    def update_active_skills(self, uma_name: str, delta_time: float) -> Tuple[float, float, float]:
        """
        Update active skill durations and calculate total bonuses.
        
        Returns: (total_speed_bonus, total_accel_bonus, total_stamina_save)
        """
        state = self.uma_states[uma_name]
        
        total_speed_bonus = 0.0
        total_accel_bonus = 0.0
        total_stamina_save = 0.0
        
        # Update cooldowns
        for skill_id in list(state.skill_cooldowns.keys()):
            state.skill_cooldowns[skill_id] -= delta_time
            if state.skill_cooldowns[skill_id] <= 0:
                del state.skill_cooldowns[skill_id]
        
        # Update active skills and sum bonuses
        still_active = []
        for active in state.active_skills:
            active.remaining_duration -= delta_time
            if active.remaining_duration > 0:
                still_active.append(active)
                total_speed_bonus += active.speed_bonus
                total_accel_bonus += active.accel_bonus
                total_stamina_save += active.stamina_save
        
        state.active_skills = still_active
        
        return total_speed_bonus, total_accel_bonus, total_stamina_save
    
    def check_and_activate_skills(self, uma_name: str, progress: float) -> List[str]:
        """
        Check all equipped skills and try to activate them.
        
        Returns: List of skill names that were activated this tick
        """
        if not SKILLS_AVAILABLE:
            return []
        
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        activated = []
        
        # Check each equipped skill
        for skill_id in stats.skills:
            if self.try_activate_skill(uma_name, skill_id, progress):
                skill = get_skill_by_id(skill_id)
                if skill:
                    activated.append(skill.name)
        
        return activated
    
    def simulate_terrain(self, uma_name: str, progress: float) -> None:
        """
        Simulate terrain changes based on race progress.
        This is a simplified model - real courses have specific terrain layouts.
        
        Pattern for a typical race course:
        - 0-15%: First straight (from gates)
        - 15-30%: First corner
        - 30-50%: Back straight
        - 50-65%: Far turn (corner)
        - 65-85%: Homestretch approach (may have slight uphill)
        - 85-100%: Final straight (homestretch)
        """
        state = self.uma_states[uma_name]
        
        # Simplified terrain simulation
        if progress < 0.15:
            state.current_terrain = "straight"
        elif progress < 0.30:
            state.current_terrain = "corner"
        elif progress < 0.50:
            state.current_terrain = "straight"
        elif progress < 0.65:
            state.current_terrain = "corner"
        elif progress < 0.75:
            # Some courses have uphill here
            if random.random() < 0.3:  # 30% chance of being on uphill segment
                state.current_terrain = "uphill"
            else:
                state.current_terrain = "straight"
        elif progress < 0.85:
            state.current_terrain = "corner"  # Final turn
        else:
            state.current_terrain = "straight"  # Final straight
    
    # =========================================================================
    # FINAL SPURT & BLOCKING
    # =========================================================================
    
    def check_final_spurt_activation(self, uma_name: str, progress: float) -> bool:
        """
        Check if Uma can activate final spurt.
        
        From wiki: Last spurt calculation occurs at beginning of Final Leg (4/6).
        Uma enters last spurt when they have enough HP to run remaining distance.
        Competition fight requires 15%+ HP to continue.
        """
        state = self.uma_states[uma_name]
        
        if state.in_final_spurt or state.is_finished or state.is_dnf:
            return False
        
        # Final spurt activates at start of Final Leg (4/6 = 66.67%)
        if progress < 4.0 / 6.0:
            return False
        
        # HP check - need sufficient HP to finish
        hp_percent = state.hp / state.max_hp
        return hp_percent >= self.HP_THRESHOLD_COMPETITION
    
    def apply_final_spurt(self, uma_name: str) -> None:
        """Apply final spurt state to Uma."""
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if not state.in_final_spurt:
            state.in_final_spurt = True

    
    def check_lane_blocking(self, uma_name: str) -> Tuple[bool, float]:
        """
        Check if Uma is blocked by others in adjacent lanes.
        
        Returns: (is_blocked, speed_multiplier)
        
        Blocking occurs when:
        - Another Uma is within LANE_PROXIMITY_THRESHOLD meters ahead
        - Power check determines if overtake succeeds
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return False, 1.0
        
        blockers = []
        for other_name, other_state in self.uma_states.items():
            if other_name == uma_name:
                continue
            if other_state.is_finished or other_state.is_dnf:
                continue
            
            # Check if other is ahead but within blocking range
            distance_diff = other_state.distance - state.distance
            if 0 < distance_diff <= self.LANE_PROXIMITY_THRESHOLD:
                # Lane proximity check (adjacent lanes)
                lane_diff = abs(other_state.lane - state.lane)
                if lane_diff <= 1:
                    blockers.append(other_name)
        
        if not blockers:
            state.is_blocked = False
            return False, 1.0
        
        # Power-based overtake check
        # Higher power = higher chance to push through
        effective_power = self.get_effective_stat(stats.power)
        power_factor = effective_power / 1200.0  # Normalized to 1200
        
        # Weighted random check (deterministic with controlled randomness)
        overtake_chance = 0.2 + (power_factor * 0.5)  # 20-70% base chance
        
        # Small random variance (±5%)
        variance = 0.95 + random.random() * 0.10
        
        if random.random() < overtake_chance * variance:
            # Successful push through, but slight speed penalty
            state.is_blocked = False
            return False, 0.98
        else:
            # Blocked
            state.is_blocked = True
            return True, self.LANE_BLOCK_SPEED_PENALTY
    
    def check_dnf(self, uma_name: str) -> bool:
        """
        Check if Uma should DNF (Did Not Finish).
        
        From wiki: When out of HP, target speed = minimum speed.
        Uma can still finish at minimum speed - they don't DNF just from HP depletion.
        DNF only occurs if they stop completely (catastrophic failure).
        
        LOW STAT PENALTY: Only EXTREMELY low stats (<100) have a tiny chance to cause DNF.
        Stats in range 100-1500 should virtually never cause DNF.
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return False
        
        # Only DNF if speed drops to near-zero (shouldn't happen with minimum speed)
        if state.current_speed < 1.0 and state.distance < self.race_distance * 0.99:
            state.is_dnf = True
            state.dnf_reason = "stopped"
            return True
        
        # LOW STAT PENALTY: Only CRITICALLY low stats (<100) = tiny risk of random DNF
        # Stats 100+ should be safe!
        critical_stats = [
            (stats.stamina, "exhaustion"),
            (stats.guts, "gave_up"),
            (stats.power, "injury"),
        ]
        
        for stat_value, reason in critical_stats:
            effective_stat = self.get_effective_stat(stat_value)
            # Only trigger if BELOW 100 (critical threshold)
            if effective_stat < self.CRITICAL_STAT_THRESHOLD:
                # Below 100: tiny chance per tick to DNF
                # Lower stat = higher chance, but still very rare
                stat_deficit = self.CRITICAL_STAT_THRESHOLD - effective_stat
                dnf_multiplier = stat_deficit / 100.0  # 0.0 at 100, 1.0 at 0
                dnf_chance = self.DNF_CHANCE_PER_TICK * (1.0 + dnf_multiplier)
                
                # Only apply after 30% into race AND only check occasionally (every ~2 seconds)
                race_progress = state.distance / self.race_distance
                if race_progress > 0.3 and race_progress < 0.9:
                    # Random check gate - only 10% of ticks actually check
                    if random.random() < 0.1:
                        if random.random() < dnf_chance:
                            state.is_dnf = True
                            state.dnf_reason = reason
                            return True
        
        return False
    
    def apply_guts_resistance(self, uma_name: str, speed_penalty: float) -> float:
        """
        When out of HP, target speed = minimum speed (from wiki).
        Guts affects minimum speed: MinSpeed = 0.85 × BaseSpeed + sqrt(200 × Guts) × 0.001
        """
        # This method is kept for compatibility but the main speed calc handles this
        return speed_penalty
    
    def tick(self, delta_time: float) -> Dict[str, UmaState]:
        """
        Advance simulation by one tick.
        
        Combines wiki formulas with GameTora mechanics:
        - Start delay (0-0.1s, late start loses start dash)
        - Rushing - random HP drain increase
        - Dueling - final straight speed boost
        - Spot Struggle - FR HP drain
        
        Args:
            delta_time: Time step in seconds
            
        Returns:
            Dictionary of Uma states after tick
        """
        if self.is_finished:
            return self.uma_states
        
        self.current_time += delta_time
        
        # Calculate positions for lane blocking
        positions = sorted(
            [(name, state.distance) for name, state in self.uma_states.items()
             if not state.is_finished and not state.is_dnf],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Update position rankings
        for rank, (name, _) in enumerate(positions):
            self.uma_states[name].position = rank + 1
        
        # Process each Uma
        for uma_name in self.uma_states:
            state = self.uma_states[uma_name]
            stats = self.uma_stats[uma_name]
            
            if state.is_finished or state.is_dnf:
                continue
            
            # GameTora: Start delay - Uma doesn't move until delay passes
            if self.current_time < state.start_delay:
                continue
            
            # Calculate progress
            progress = state.distance / self.race_distance
            
            # Get current phase
            phase = self.get_current_phase(progress)
            
            # GameTora mechanics checks
            self.check_rushing(uma_name, progress, delta_time)
            self.check_spot_struggle(uma_name)
            self.check_dueling(uma_name, delta_time)
            
            # Skills system: Update terrain and check skill activations
            self.simulate_terrain(uma_name, progress)
            self.check_and_activate_skills(uma_name, progress)
            skill_speed_bonus, skill_accel_bonus, skill_stamina_save = self.update_active_skills(uma_name, delta_time)
            
            # Check final spurt activation
            if self.check_final_spurt_activation(uma_name, progress):
                self.apply_final_spurt(uma_name)
            
            # Calculate speed cap (target speed)
            speed_cap = self.calculate_base_speed_cap(uma_name, phase)
            
            # Final spurt bonus: Guts affects last spurt target speed
            # Wiki: sqrt(500 × Guts) × 0.001 bonus in Last Spurt
            if state.in_final_spurt:
                effective_guts = self.get_effective_stat(stats.guts)
                guts_speed_bonus = math.sqrt(500.0 * effective_guts) * 0.001
                speed_cap += guts_speed_bonus
            
            # GameTora: Dueling bonus to speed cap
            duel_speed_bonus, duel_accel_bonus = self.get_duel_bonus(uma_name)
            speed_cap += duel_speed_bonus
            
            # Skills: Add speed bonus from active skills
            speed_cap += skill_speed_bonus
            
            # Start dash detection: applies until speed reaches 0.85 × BaseSpeed
            # GameTora: Late starts (0.066s+) LOSE this bonus
            start_dash_threshold = 0.85 * self.base_speed
            is_start_dash = (state.current_speed < start_dash_threshold and 
                           phase == RacePhase.START and 
                           not state.is_late_start)
            
            # Calculate acceleration with start dash flag
            acceleration = self.calculate_acceleration(uma_name, phase, is_start_dash)
            
            # GameTora: Add dueling acceleration bonus
            acceleration += duel_accel_bonus
            
            # Skills: Add acceleration bonus from active skills
            acceleration += skill_accel_bonus
            
            # Calculate minimum speed (from wiki formula)
            minimum_speed = self.calculate_minimum_speed(uma_name)
            
            # Update speed based on HP state
            if state.hp <= 0:
                # Out of HP: decelerate to minimum speed
                # Wiki: deceleration rates vary by phase
                if phase == RacePhase.START:
                    decel_rate = 1.2  # Opening phase: -1.2 m/s²
                elif phase == RacePhase.MIDDLE:
                    decel_rate = 0.8  # Middle phase: -0.8 m/s²
                else:
                    decel_rate = 1.0  # Final phase: -1.0 m/s²
                
                if state.current_speed > minimum_speed:
                    state.current_speed = max(
                        minimum_speed,
                        state.current_speed - decel_rate * delta_time
                    )
            else:
                # Normal movement: accelerate toward target speed
                if state.current_speed < speed_cap:
                    state.current_speed = min(
                        speed_cap,
                        state.current_speed + acceleration * delta_time
                    )
                elif state.current_speed > speed_cap:
                    # Decelerate if above cap (slower than acceleration)
                    state.current_speed = max(
                        speed_cap,
                        state.current_speed - 0.5 * delta_time
                    )
            
            # Enforce minimum speed floor
            state.current_speed = max(state.current_speed, minimum_speed)
            
            # Check lane blocking
            is_blocked, block_multiplier = self.check_lane_blocking(uma_name)
            
            # Calculate effective speed (with blocking penalty)
            effective_speed = state.current_speed * block_multiplier
            
            # Apply small random variance (±1.5%) for natural variation
            # Combines per-Uma seed with per-tick randomness
            base_variance = 1.0 + state.speed_variance_seed  # Per-Uma consistent factor
            tick_variance = 0.99 + random.random() * 0.02    # Per-tick randomness ±1%
            effective_speed *= base_variance * tick_variance
            
            # Store previous distance for precise finish calculation
            prev_distance = state.distance
            
            # Update distance
            state.distance += effective_speed * delta_time
            
            # Calculate HP drain (only if HP > 0)
            if state.hp > 0:
                hp_drain = self.calculate_stamina_drain(uma_name, phase, effective_speed)
                
                # Final spurt increases drain (wiki: additional consumption during spurt)
                if state.in_final_spurt:
                    hp_drain *= 1.6
                
                # Skills: Apply stamina save reduction from active skills
                if skill_stamina_save > 0:
                    hp_drain *= (1.0 - skill_stamina_save)
                
                state.hp = max(0.0, state.hp - hp_drain * delta_time)
            
            # Update fatigue (cumulative tracker for UI)
            state.fatigue = (1.0 - state.hp / state.max_hp) * 100.0
            
            # Check for finish with precise timing
            if state.distance >= self.race_distance and not state.is_finished:
                state.is_finished = True
                # Calculate exact finish time by interpolation
                # How far past the finish line did we go?
                overshoot = state.distance - self.race_distance
                # How long ago did we actually cross the line?
                if effective_speed > 0:
                    time_past_finish = overshoot / effective_speed
                    state.finish_time = self.current_time - time_past_finish
                else:
                    state.finish_time = self.current_time
                state.distance = self.race_distance
            
            # Check for DNF
            self.check_dnf(uma_name)
        
        # Check if race is finished
        active_count = sum(
            1 for s in self.uma_states.values()
            if not s.is_finished and not s.is_dnf
        )
        if active_count == 0:
            self.is_finished = True
        
        return self.uma_states
    
    def get_rankings(self) -> List[Tuple[str, float, bool, bool]]:
        """
        Get current rankings.
        
        Returns:
            List of (name, distance, is_finished, is_dnf) sorted by distance
        """
        rankings = [
            (name, state.distance, state.is_finished, state.is_dnf)
            for name, state in self.uma_states.items()
        ]
        rankings.sort(key=lambda x: x[1], reverse=True)
        return rankings
    
    def get_final_results(self) -> List[Tuple[int, str, float, str]]:
        """
        Get final race results.
        
        Returns:
            List of (position, name, time_or_distance, status) sorted by finish order
        """
        finished = [
            (name, state.finish_time, "FIN")
            for name, state in self.uma_states.items()
            if state.is_finished
        ]
        finished.sort(key=lambda x: x[1])
        
        dnf = [
            (name, state.distance, f"DNF ({state.dnf_reason})")
            for name, state in self.uma_states.items()
            if state.is_dnf
        ]
        dnf.sort(key=lambda x: x[1], reverse=True)
        
        results = []
        position = 1
        for name, time, status in finished:
            results.append((position, name, time, status))
            position += 1
        for name, distance, status in dnf:
            results.append((position, name, distance, status))
            position += 1
        
        return results


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_uma_stats_from_dict(uma_dict: dict) -> UmaStats:
    """Create UmaStats from a dictionary (e.g., from JSON config)."""
    stats = uma_dict.get('stats', {})
    
    # Parse running style
    style_str = uma_dict.get('running_style', 'PC').upper()
    style_map = {'FR': RunningStyle.FR, 'PC': RunningStyle.PC, 
                 'LS': RunningStyle.LS, 'EC': RunningStyle.EC}
    running_style = style_map.get(style_str, RunningStyle.PC)
    
    # Get aptitudes
    dist_apt = uma_dict.get('distance_aptitude', {})
    surf_apt = uma_dict.get('surface_aptitude', {})
    
    # Get skills (list of skill IDs)
    skills = uma_dict.get('skills', [])
    
    return UmaStats(
        name=uma_dict.get('name', 'Unknown'),
        speed=stats.get('Speed', 100),
        stamina=stats.get('Stamina', 100),
        power=stats.get('Power', 100),
        guts=stats.get('Guts', 100),
        wisdom=stats.get('Wit', 100),
        running_style=running_style,
        # Distance aptitude needs race type context, default to 'B'
        distance_aptitude='B',
        surface_aptitude='B',
        skills=skills,
    )


def create_race_engine_from_config(config_data: dict, seed: Optional[int] = None) -> RaceEngine:
    """Create a RaceEngine from a JSON config dictionary."""
    race_info = config_data.get('race', {})
    umas = config_data.get('umas', [])
    
    race_distance = race_info.get('distance', 2500)
    race_type = race_info.get('type', 'Medium')
    surface = race_info.get('surface', 'Turf')
    
    # Parse track condition (from UmaConfigGenerator)
    track_condition_str = race_info.get('track_condition', 'Good').lower()
    track_condition_map = {
        'firm': TrackCondition.FIRM,
        'good': TrackCondition.GOOD,
        'soft': TrackCondition.SOFT,
        'heavy': TrackCondition.HEAVY,
    }
    track_condition = track_condition_map.get(track_condition_str, TrackCondition.GOOD)
    
    # Parse terrain type from surface
    terrain_map = {
        'turf': TerrainType.TURF,
        'dirt': TerrainType.DIRT,
    }
    terrain = terrain_map.get(surface.lower(), TerrainType.TURF)
    
    # Get stat threshold (for speed bonus when exceeding threshold)
    stat_threshold = race_info.get('stat_threshold', 0)
    
    engine = RaceEngine(
        race_distance=race_distance, 
        race_type=race_type,
        terrain=terrain,
        track_condition=track_condition,
        stat_threshold=stat_threshold,
        seed=seed
    )
    
    for uma_dict in umas:
        uma_stats = create_uma_stats_from_dict(uma_dict)
        
        # Set aptitudes based on race type and surface
        dist_apt = uma_dict.get('distance_aptitude', {})
        surf_apt = uma_dict.get('surface_aptitude', {})
        uma_stats.distance_aptitude = dist_apt.get(race_type, 'B')
        uma_stats.surface_aptitude = surf_apt.get(surface, 'B')
        
        engine.add_uma(uma_stats)
    
    return engine
