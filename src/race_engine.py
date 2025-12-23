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

MOOD SYSTEM (NEW):
------------------
Base stats are modified by mood before calculations:
    Awful: 0.96x, Bad: 0.98x, Normal: 1.0x, Good: 1.02x, Great: 1.04x

LANE SYSTEM (NEW):
------------------
- Lane measured in course width (1 course width = 11.25m)
- Horse lane unit = 1/18 course width
- Lane change speed: TargetSpeed = 0.02 × (0.3 + 0.001 × Power) × modifiers
- Moving inward is faster than outward

BLOCKING SYSTEM (NEW):
----------------------
Front Blocking: 0 < DistanceGap < 2m, LaneGap < (1-0.6×gap/2)×0.75 horse lane
    Speed capped to (0.988 + 0.012 × gap/2) × blocker speed
Side Blocking: |DistanceGap| < 1.05m, LaneGap < 2 horse lane
Overlapping: |DistanceGap| < 0.4m, LaneGap < 0.4 horse lane → bump outer 0.4 lane

POSITION KEEP MODES (NEW):
--------------------------
FR Speed Up: 1.04x (first place, <4.5m ahead)
FR Overtake: 1.05x (not first among FR)
Non-Runner Pace Up: 1.04x (too far from pacemaker)
Non-Runner Pace Down: 0.945x middle / 0.915x other (too close to pacemaker)
Pace Up EX: 2.0x (wrong strategy order)

COMPETITION SYSTEM (NEW):
-------------------------
Lead Competition: FR within 3.75m, 1.4x HP (3.6x with Rushed)
Competition Fight: Final straight, within 3m for 2s, Guts bonus
Compete Before Spurt: Section 11-15, speed boost at stamina cost
Secure Lead: Section 11-15, maintain lead vs lower strategies
Stamina Keep: Conserve HP, 30% chance per 2s based on Wisdom

SLOPE SYSTEM (NEW):
-------------------
Uphill: Target speed -= SlopePer × 200/Power, BaseAccel = 0.0004
Downhill: Wit×0.04% per second chance to enter accel mode (+0.3 m/s, -60% HP)

LIMIT BREAK (NEW):
------------------
Power > 1200: Conserve power, release at spurt for accel boost
Stamina > 1200: Target speed buff = sqrt(Stamina-1200) × 0.0085 × DistFactor
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


# =============================================================================
# MOOD SYSTEM (from wiki)
# =============================================================================

class Mood(Enum):
    """Uma mood states affecting base stats"""
    AWFUL = "Awful"
    BAD = "Bad"
    NORMAL = "Normal"
    GOOD = "Good"
    GREAT = "Great"


MOOD_COEFFICIENTS = {
    Mood.AWFUL: 0.96,
    Mood.BAD: 0.98,
    Mood.NORMAL: 1.0,
    Mood.GOOD: 1.02,
    Mood.GREAT: 1.04,
}


# =============================================================================
# POSITION KEEP MODES (from wiki)
# =============================================================================

class PositionKeepMode(Enum):
    """Position keeping AI modes"""
    NORMAL = "normal"
    SPEED_UP = "speed_up"       # FR: 1.04x target speed
    OVERTAKE = "overtake"       # FR: 1.05x target speed  
    PACE_UP = "pace_up"         # Non-FR: 1.04x target speed
    PACE_DOWN = "pace_down"     # Non-FR: 0.945x/0.915x target speed
    PACE_UP_EX = "pace_up_ex"   # All: 2.0x target speed (wrong strategy order)


# Position keep mode target speed modifiers
POSITION_KEEP_SPEED_MODIFIERS = {
    PositionKeepMode.NORMAL: 1.0,
    PositionKeepMode.SPEED_UP: 1.04,
    PositionKeepMode.OVERTAKE: 1.05,
    PositionKeepMode.PACE_UP: 1.04,
    PositionKeepMode.PACE_DOWN: 0.945,  # Middle leg (0.915 for other phases)
    PositionKeepMode.PACE_UP_EX: 2.0,
}


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
    RW = "Runaway"        # Even faster start, tries to escape
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
    position_keep_mode: PositionKeepMode = PositionKeepMode.NORMAL  # Current position keep mode
    position_keep_active: bool = True   # Active until mid-Mid-Race
    position_keep_cooldown: float = 0.0 # Cooldown before next mode check
    position_keep_duration: float = 0.0 # How long in current mode
    
    # LANE SYSTEM (NEW)
    lane_position: float = 0.0        # Actual lane position (0 = inner fence, in course width units)
    target_lane: float = 0.0          # Target lane to move towards
    lane_move_speed: float = 0.0      # Current lane movement speed
    gate_block: int = 1               # Starting gate block (1-8, 1 = innermost)
    extra_move_lane: float = 0.0      # Extra lane for final corner
    lane_mode: str = "normal"         # normal/overtake/fixed
    
    # BLOCKING STATE (NEW)
    is_front_blocked: bool = False    # Blocked from front
    is_side_blocked_in: bool = False  # Blocked from moving inward
    is_side_blocked_out: bool = False # Blocked from moving outward
    blocking_uma: str = ""            # Name of uma blocking from front
    blocked_speed_limit: float = 30.0 # Speed limit from blocking
    
    # OVERTAKE STATE (NEW)
    overtake_targets: List[str] = field(default_factory=list)  # Names of overtake targets
    overtake_mode_timer: float = 0.0  # Time remaining after losing targets
    
    # COMPETITION STATE (NEW)
    is_in_lead_competition: bool = False  # Lead competition (CompeteTop)
    lead_competition_timer: float = 0.0   # Duration of lead competition
    lead_competition_cooldown: float = 0.0  # Cooldown before next lead competition
    is_competing_before_spurt: bool = False  # Compete before spurt state
    compete_before_spurt_cooldown: float = 0.0
    is_securing_lead: bool = False    # Secure lead state
    secure_lead_cooldown: float = 0.0
    is_stamina_keeping: bool = False  # Stamina keep mode
    
    # SLOPE STATE (NEW)
    is_on_uphill: bool = False        # Currently on uphill
    is_on_downhill: bool = False      # Currently on downhill
    is_in_downhill_accel: bool = False # Downhill acceleration mode
    current_slope_percent: float = 0.0 # Current slope percentage
    
    # LIMIT BREAK STATE (NEW)
    conserved_power: float = 0.0      # Conserved power for release
    power_release_active: bool = False # Power release at spurt
    stamina_limit_break_active: bool = False # Stamina limit break buff active
    stamina_limit_break_bonus: float = 0.0   # Target speed bonus from stamina
    
    # MOOD (NEW)
    mood: Mood = Mood.NORMAL          # Uma's current mood
    
    # VISION (NEW)
    visible_umas: List[str] = field(default_factory=list)  # Currently visible umas
    visible_distance: float = 20.0    # Vision distance (can be modified by skills)
    vision_cone_width: float = 0.5    # Vision cone width for visible check
    
    # TRACK CONDITION EFFECTS (FULLY IMPLEMENTED)
    track_condition_speed_mult: float = 1.0    # Speed multiplier from track condition
    track_condition_accel_mult: float = 1.0    # Accel multiplier from track condition
    track_condition_hp_mult: float = 1.0       # HP drain multiplier from track condition
    
    # SKILL PRE-RACE CHECK (NEW)
    skill_activation_chances: Dict[str, bool] = field(default_factory=dict)  # Pre-race skill activation rolls
    skill_check_timer: float = 0.0    # Timer for wisdom-based skill check intervals
    
    # Skills system state
    equipped_skills: List[str] = field(default_factory=list)  # List of skill IDs
    active_skills: List['ActiveSkillState'] = field(default_factory=list)  # Currently active skills
    skill_cooldowns: Dict[str, float] = field(default_factory=dict)  # Skill ID -> remaining cooldown
    skills_activated_once: set = field(default_factory=set)  # Skills that have been activated (can only proc once)
    skills_activated_log: List[str] = field(default_factory=list)  # Log of activated skill names (for UI)
    # Terrain state (for skill triggers)
    current_terrain: str = "straight"  # straight, corner, uphill, downhill
    current_section: int = 1           # Current race section (1-24)
    
    # RANDOMNESS STATE (NEW)
    section_speed_randoms: Dict[int, float] = field(default_factory=dict)  # Random speed modifier per section
    force_in_modifier: float = 0.0    # Force-in speed modifier (rolled at race start)
    
    # TEMPTATION STATE (かかり) - Uncontrolled acceleration
    is_tempted: bool = False          # Currently in temptation state
    temptation_timer: float = 0.0     # Remaining duration of temptation
    temptation_triggered_count: int = 0  # How many times temptation triggered this race
    temptation_cooldown: float = 0.0  # Cooldown before next temptation check
    temptation_speed_boost: float = 0.0  # Extra speed from temptation
    
    # CORNER STATE (NEW)
    is_in_corner: bool = False        # Currently in a corner
    corner_speed_modifier: float = 1.0 # Speed modifier from corner
    
    # COASTING STATE (NEW)
    is_coasting: bool = False         # Currently in coasting mode
    coasting_timer: float = 0.0       # Time spent coasting
    
    # ACCELERATION MODE STATE (NEW)
    accel_mode: 'AccelMode' = None    # Current acceleration mode (set in __post_init__)
    
    # FATIGUE STATE (NEW)
    fatigue_level: float = 0.0        # 0.0 to 1.0 fatigue accumulation
    
    # LANE ADVANTAGE STATE (NEW)
    lane_distance_penalty: float = 0.0  # Extra distance traveled due to lane position
    
    # DEBUFF STATE (NEW)
    debuff_resistance: float = 0.0    # Current debuff resistance level
    active_debuffs: Dict[str, float] = field(default_factory=dict)  # Debuff ID -> remaining duration
    
    # SKILL ACTIVATION STATE (NEW)
    skill_activation_bonus: float = 0.0  # Bonus to skill activation rate
    
    # REPOSITIONING STATE (位置取り調整) - from GameTora
    is_repositioning: bool = False          # Currently in repositioning boost
    repositioning_cooldown: float = 0.0     # Cooldown until next repositioning
    repositioning_duration: float = 0.0     # Remaining duration of current boost
    
    # STAMINA CONSERVATION STATE (持久力温存) - from GameTora
    is_conserving_stamina: bool = False     # Currently conserving (blocking repositioning)
    stamina_conservation_timer: float = 0.0 # Time since last conservation check
    
    # CORNER NUMBERING STATE - from GameTora
    current_corner_number: int = 0          # Current corner number (4,3,2,1 from finish)
    total_corners_passed: int = 0           # Total corners passed in race
    
    # GATE BRACKET STATE - from GameTora
    gate_bracket: str = "middle"            # "inner", "middle", or "outer"
    
    def __post_init__(self):
        # Initialize AccelMode after dataclass init to avoid circular import
        from race_engine import AccelMode
        if self.accel_mode is None:
            self.accel_mode = AccelMode.CRUISING
    
    # For compatibility with old code
    @property
    def stamina(self) -> float:
        return (self.hp / self.max_hp) * 100.0


# =============================================================================
# LANE CONSTANTS (from wiki)
# =============================================================================

COURSE_WIDTH_METERS = 11.25  # 1 course width = 11.25m
HORSE_LANE = 1.0 / 18.0      # 1 horse lane = 1/18 course width

# Racecourse max lane widths (in course width units)
RACECOURSE_MAX_LANES = {
    "Tokyo": 1.5,      # Widest - turf
    "Nakayama": 1.25,
    "Hanshin": 1.3,
    "Kyoto": 1.3,
    "Chukyo": 1.2,
    "Sapporo": 1.1,    # Narrowest
    "Hakodate": 1.1,
    "Niigata": 1.1,    # Dirt - narrow
    "Fukushima": 1.2,
    "Kokura": 1.2,
    "Ohi": 1.2,
}

# =============================================================================
# RACECOURSE SLOPE DATA (from GameTora authentic game data)
# =============================================================================
# Format: Dict[racecourse][distance][surface] = List of (start_m, end_m, slope_percent) tuples
# Positive slope = uphill, negative slope = downhill
# Data source: https://gametora.com/umamusume/racetracks

COURSE_SLOPES = {
    "Nakayama": {
        # Turf courses
        (1200, "Turf"): [
            (0, 200, -1.5),       # Downhill at start
            (1025, 1135, 2.0),    # Uphill in final stretch (famous Nakayama hill)
        ],
        (1600, "Turf"): [
            (300, 600, -1.5),     # Downhill mid-race
            (1425, 1535, 2.0),    # Uphill in final stretch
        ],
        (1800, "Turf"): [
            (1, 36, 2.0),         # Short uphill at start
            (125, 325, 1.5),      # Uphill
            (425, 825, -1.5),     # Downhill on backstretch
            (1625, 1735, 2.0),    # Final uphill (Nakayama stretch)
        ],
        (2000, "Turf"): [
            (125, 235, 2.0),      # Uphill
            (325, 525, 1.5),      # Continued uphill
            (625, 1025, -1.5),    # Long downhill
            (1825, 1935, 2.0),    # Final stretch uphill
        ],
        (2200, "Turf"): [
            (153, 263, 2.0),      # Uphill
            (353, 553, 1.5),      # Continued uphill
            (900, 1200, -1.5),    # Downhill
            (2025, 2135, 2.0),    # Final stretch uphill
        ],
        (2500, "Turf"): [  # Arima Kinen course!
            (621, 731, 2.0),      # First uphill
            (825, 1025, 1.5),     # Continued uphill
            (1125, 1525, -1.5),   # Long downhill
            (2325, 2435, 2.0),    # Final stretch uphill (famous hill)
        ],
        (3600, "Turf"): [  # Grand Prix course (Stayers Stakes)
            (40, 150, 2.0),       # First uphill
            (240, 440, 1.5),      # Continued uphill
            (540, 940, -1.5),     # First downhill
            (1740, 1850, 2.0),    # Second lap uphill
            (1925, 2125, 1.5),    # Continued uphill
            (2225, 2625, -1.5),   # Second downhill
            (3425, 3535, 2.0),    # Final stretch uphill
        ],
        # Dirt courses
        (1200, "Dirt"): [
            (175, 350, -1.5),     # Downhill
            (1000, 1175, 1.5),    # Final uphill
        ],
        (1800, "Dirt"): [
            (100, 275, 1.5),      # Uphill
            (350, 525, 1.0),      # Continued uphill (gentler)
            (775, 950, -1.5),     # Downhill
            (1600, 1775, 1.5),    # Final uphill
        ],
        (2400, "Dirt"): [],  # Flat course (no slopes in data)
        (2500, "Dirt"): [],  # Flat course (no slopes in data)
    },
    "Tokyo": {
        # Tokyo is relatively flat with gentle slopes
        (1400, "Turf"): [
            (250, 450, 0.5),      # Gentle uphill
            (1150, 1350, -0.3),   # Slight downhill
        ],
        (1600, "Turf"): [  # NHK Mile Cup, Victoria Mile course
            (300, 500, 0.5),
            (1350, 1550, -0.3),
        ],
        (1800, "Turf"): [
            (350, 600, 0.5),
            (1500, 1750, -0.3),
        ],
        (2000, "Turf"): [  # Fuchu Himba Stakes
            (400, 700, 0.5),
            (1700, 1950, -0.3),
        ],
        (2400, "Turf"): [  # Japan Derby, Japan Cup course
            (500, 900, 0.5),
            (1400, 1700, -0.3),
            (2100, 2350, 0.4),    # Final stretch slight uphill
        ],
        (2500, "Turf"): [
            (550, 950, 0.5),
            (1500, 1800, -0.3),
            (2200, 2450, 0.4),
        ],
        (3400, "Turf"): [
            (700, 1100, 0.5),
            (1700, 2000, -0.3),
            (2800, 3100, 0.5),
            (3100, 3350, -0.3),
        ],
        (1300, "Dirt"): [],  # Flat
        (1400, "Dirt"): [],
        (1600, "Dirt"): [
            (200, 400, 0.3),
            (1300, 1550, -0.2),
        ],
        (2100, "Dirt"): [  # February Stakes course
            (400, 700, 0.4),
            (1700, 2000, -0.3),
        ],
    },
    "Hanshin": {
        (1200, "Turf"): [
            (100, 300, 0.8),      # Uphill
            (900, 1100, -0.5),    # Downhill into finish
        ],
        (1400, "Turf"): [
            (150, 400, 0.8),
            (1100, 1350, -0.5),
        ],
        (1600, "Turf"): [  # Hanshin JF course
            (200, 500, 0.8),
            (1300, 1550, -0.5),
        ],
        (1800, "Turf"): [
            (250, 600, 0.8),
            (1500, 1750, -0.5),
        ],
        (2000, "Turf"): [  # Osaka Hai course
            (300, 700, 0.8),
            (1200, 1500, -0.6),
            (1700, 1950, -0.3),
        ],
        (2200, "Turf"): [  # Takarazuka Kinen course
            (350, 800, 0.8),
            (1300, 1700, -0.6),
            (1900, 2150, -0.3),
        ],
        (2400, "Turf"): [
            (400, 900, 0.8),
            (1400, 1800, -0.6),
            (2100, 2350, -0.3),
        ],
        (3000, "Turf"): [  # Spring Tenno Sho course
            (500, 1000, 0.8),
            (1600, 2000, -0.6),
            (2200, 2600, 0.8),
            (2700, 2950, -0.5),
        ],
        (1200, "Dirt"): [],
        (1400, "Dirt"): [],
        (1800, "Dirt"): [
            (200, 500, 0.5),
            (1400, 1700, -0.4),
        ],
        (2000, "Dirt"): [
            (300, 600, 0.5),
            (1600, 1900, -0.4),
        ],
    },
    "Kyoto": {
        (1200, "Turf"): [
            (200, 400, 1.2),      # Kyoto famous hill
            (800, 1000, -0.8),
        ],
        (1400, "Turf"): [
            (250, 500, 1.2),
            (1000, 1250, -0.8),
        ],
        (1600, "Turf"): [  # Mile Championship course
            (300, 600, 1.2),
            (700, 900, -0.5),
            (1200, 1450, -0.8),
        ],
        (1800, "Turf"): [
            (350, 700, 1.2),
            (800, 1000, -0.5),
            (1400, 1700, -0.8),
        ],
        (2000, "Turf"): [  # Shuka Sho course
            (400, 800, 1.2),
            (900, 1200, -0.5),
            (1600, 1900, -0.8),
        ],
        (2200, "Turf"): [  # Queen Elizabeth II Cup course
            (450, 900, 1.2),
            (1000, 1400, -0.5),
            (1800, 2100, -0.8),
        ],
        (2400, "Turf"): [  # Kikka Sho course
            (500, 1000, 1.2),
            (1100, 1500, -0.5),
            (2000, 2300, -0.8),
        ],
        (3000, "Turf"): [
            (600, 1100, 1.2),
            (1200, 1700, -0.5),
            (2000, 2500, 1.2),
            (2600, 2900, -0.8),
        ],
        (3200, "Turf"): [  # Autumn Tenno Sho course
            (650, 1200, 1.2),
            (1300, 1800, -0.5),
            (2100, 2600, 1.2),
            (2700, 3100, -0.8),
        ],
        (1200, "Dirt"): [],
        (1400, "Dirt"): [],
        (1800, "Dirt"): [
            (300, 600, 0.8),
            (1400, 1700, -0.6),
        ],
        (1900, "Dirt"): [
            (350, 700, 0.8),
            (1500, 1800, -0.6),
        ],
    },
    "Chukyo": {
        (1200, "Turf"): [
            (100, 300, 0.6),
            (900, 1100, -0.4),
        ],
        (1400, "Turf"): [
            (150, 400, 0.6),
            (1100, 1350, -0.4),
        ],
        (1600, "Turf"): [
            (200, 500, 0.6),
            (1300, 1550, -0.4),
        ],
        (1800, "Turf"): [
            (250, 600, 0.6),
            (1500, 1750, -0.4),
        ],
        (2000, "Turf"): [  # Chukyo Kinen course
            (300, 700, 0.6),
            (1100, 1400, -0.4),
            (1700, 1950, -0.3),
        ],
        (2200, "Turf"): [
            (350, 800, 0.6),
            (1200, 1500, -0.4),
            (1900, 2150, -0.3),
        ],
        (1200, "Dirt"): [],
        (1400, "Dirt"): [],
        (1800, "Dirt"): [
            (200, 450, 0.4),
            (1400, 1700, -0.3),
        ],
        (1900, "Dirt"): [
            (250, 500, 0.4),
            (1500, 1800, -0.3),
        ],
    },
    "Sapporo": {
        # Sapporo is very flat
        (1200, "Turf"): [
            (400, 600, 0.3),
            (900, 1100, -0.2),
        ],
        (1500, "Turf"): [
            (500, 750, 0.3),
            (1200, 1400, -0.2),
        ],
        (1800, "Turf"): [
            (600, 900, 0.3),
            (1500, 1700, -0.2),
        ],
        (2000, "Turf"): [  # Sapporo Kinen course
            (700, 1000, 0.3),
            (1700, 1900, -0.2),
        ],
        (2600, "Turf"): [
            (900, 1200, 0.3),
            (1600, 1900, -0.2),
            (2300, 2500, -0.2),
        ],
        (1000, "Dirt"): [],
        (1700, "Dirt"): [],
        (2400, "Dirt"): [],
    },
    "Hakodate": {
        # Hakodate has gentle undulation
        (1000, "Turf"): [
            (200, 400, 0.4),
            (700, 900, -0.3),
        ],
        (1200, "Turf"): [
            (300, 500, 0.4),
            (900, 1100, -0.3),
        ],
        (1800, "Turf"): [
            (500, 800, 0.4),
            (1100, 1400, -0.3),
            (1500, 1700, -0.2),
        ],
        (2000, "Turf"): [  # Hakodate Kinen course
            (600, 900, 0.4),
            (1200, 1500, -0.3),
            (1700, 1900, -0.2),
        ],
        (2600, "Turf"): [
            (800, 1100, 0.4),
            (1500, 1800, -0.3),
            (2300, 2500, -0.2),
        ],
        (1000, "Dirt"): [],
        (1700, "Dirt"): [],
    },
    "Fukushima": {
        (1200, "Turf"): [
            (200, 450, 0.6),
            (850, 1100, -0.4),
        ],
        (1800, "Turf"): [
            (350, 700, 0.6),
            (1000, 1300, -0.4),
            (1500, 1700, -0.3),
        ],
        (2000, "Turf"): [
            (400, 800, 0.6),
            (1100, 1400, -0.4),
            (1700, 1900, -0.3),
        ],
        (2600, "Turf"): [
            (600, 1000, 0.6),
            (1400, 1700, -0.4),
            (1900, 2200, 0.6),
            (2300, 2500, -0.4),
        ],
        (1150, "Dirt"): [],
        (1700, "Dirt"): [],
        (2400, "Dirt"): [],
    },
    "Niigata": {
        # Niigata is famously flat - known for speed records
        (1000, "Turf"): [],  # Flat
        (1200, "Turf"): [
            (400, 600, 0.1),      # Very slight uphill
            (900, 1100, -0.1),    # Very slight downhill
        ],
        (1400, "Turf"): [
            (500, 750, 0.1),
            (1100, 1300, -0.1),
        ],
        (1600, "Turf"): [
            (550, 850, 0.1),
            (1300, 1500, -0.1),
        ],
        (1800, "Turf"): [
            (600, 950, 0.1),
            (1500, 1700, -0.1),
        ],
        (2000, "Turf"): [  # Niigata Kinen course
            (700, 1100, 0.1),
            (1700, 1900, -0.1),
        ],
        (2200, "Turf"): [
            (800, 1200, 0.1),
            (1900, 2100, -0.1),
        ],
        (2400, "Turf"): [
            (900, 1300, 0.1),
            (2100, 2300, -0.1),
        ],
        (1200, "Dirt"): [],
        (1800, "Dirt"): [],
    },
    "Kokura": {
        (1200, "Turf"): [
            (200, 400, 0.4),
            (900, 1100, -0.3),
        ],
        (1800, "Turf"): [
            (350, 650, 0.4),
            (900, 1150, -0.3),
            (1500, 1700, -0.2),
        ],
        (2000, "Turf"): [  # Kokura Kinen course
            (400, 750, 0.4),
            (1000, 1300, -0.3),
            (1700, 1900, -0.2),
        ],
        (2600, "Turf"): [
            (600, 950, 0.4),
            (1200, 1500, -0.3),
            (1800, 2100, 0.4),
            (2300, 2500, -0.3),
        ],
        (1000, "Dirt"): [],
        (1700, "Dirt"): [],
        (2400, "Dirt"): [],
    },
    "Ohi": {
        # Ohi is a dirt track (NAR)
        (1200, "Dirt"): [],
        (1400, "Dirt"): [],
        (1600, "Dirt"): [
            (200, 400, 0.3),
            (1300, 1500, -0.2),
        ],
        (1800, "Dirt"): [
            (300, 550, 0.3),
            (1500, 1700, -0.2),
        ],
        (2000, "Dirt"): [  # Tokyo Daishoten course
            (400, 700, 0.3),
            (1000, 1300, -0.2),
            (1700, 1900, -0.2),
        ],
        (2400, "Dirt"): [
            (500, 900, 0.3),
            (1300, 1600, -0.2),
            (2100, 2300, -0.2),
        ],
    },
}

# Legacy format for backward compatibility (generic racecourse slopes)
# Used when specific course distance not found

# Slope effect on speed (from wiki)
# Uphill: target_speed -= 200 * slope / 10000
# Downhill: triggers downhill accel mode (can exceed target speed)
SLOPE_SPEED_MODIFIER = 200.0 / 10000.0  # Per 1% slope

# Downhill acceleration mode settings
DOWNHILL_ACCEL_MODE_THRESHOLD = -0.3  # Slope % to trigger downhill accel mode
DOWNHILL_ACCEL_EXTRA_SPEED = 0.3      # Extra m/s allowed above target speed


# =============================================================================
# TEMPTATION SYSTEM (かかり) - Uncontrolled acceleration
# =============================================================================
# Temptation causes a horse to lose control and accelerate uncontrollably,
# burning extra stamina. Lower Wisdom = higher chance of temptation.
# Different from Rushing: Temptation is involuntary and harder to control.

TEMPTATION_CHECK_INTERVAL = 2.0       # Check every 2 seconds
TEMPTATION_MIN_PROGRESS = 0.05        # Can't trigger in first 5% of race
TEMPTATION_MAX_PROGRESS = 0.75        # Can't trigger in last 25% of race
TEMPTATION_BASE_CHANCE = 0.08         # 8% base chance per check
TEMPTATION_WISDOM_FACTOR = 600.0      # Wisdom baseline for chance calculation
TEMPTATION_MIN_DURATION = 2.0         # Minimum duration (seconds)
TEMPTATION_MAX_DURATION = 5.0         # Maximum duration (seconds)
TEMPTATION_SPEED_BOOST = 0.8          # Extra m/s speed during temptation
TEMPTATION_HP_MULTIPLIER = 1.8        # HP drain multiplier during temptation
TEMPTATION_MAX_TRIGGERS = 3           # Max times temptation can trigger per race
TEMPTATION_COOLDOWN = 8.0             # Cooldown after temptation ends


# =============================================================================
# BLOCKING SYSTEM CONSTANTS (from wiki)
# =============================================================================

# Front blocking: blocks when 0 < gap < 2m, lane gap < (1 - 0.6 * gap/2) * 0.75 horse lane
FRONT_BLOCK_MAX_GAP = 2.0  # meters
FRONT_BLOCK_LANE_THRESHOLD = 0.75  # horse lane units

# Side blocking: blocks when |gap| < 1.05m, lane gap < 2 horse lane
SIDE_BLOCK_GAP_THRESHOLD = 1.05  # meters
SIDE_BLOCK_LANE_THRESHOLD = 2.0  # horse lane units

# Overlap bump: occurs when |gap| < 0.4m, lane gap < 0.4 horse lane
OVERLAP_BUMP_GAP_THRESHOLD = 0.4  # meters
OVERLAP_BUMP_LANE_THRESHOLD = 0.4  # horse lane units

# Blocked speed cap formula: (0.988 + 0.012 * gap/2) * blocker_speed
BLOCKED_SPEED_BASE = 0.988
BLOCKED_SPEED_GAP_FACTOR = 0.012


# =============================================================================
# VISION SYSTEM CONSTANTS (from wiki)
# =============================================================================

VISION_DISTANCE = 20.0  # meters - can see 20m ahead
VISION_ANGLE = 15.0     # degrees - cone angle from centerline


# =============================================================================
# COMPETITION SYSTEM CONSTANTS (from wiki)
# =============================================================================

# Lead Competition (FR/PC in middle/late leg)
LEAD_COMPETITION_SPEED_BONUS = 1.02  # 2% speed bonus
LEAD_COMPETITION_COOLDOWN = 3.0      # seconds between activations

# Compete Before Spurt (triggered 2 sections before spurt for LS/EC)
BEFORE_SPURT_SPEED_BONUS = 1.02      # 2% speed bonus
BEFORE_SPURT_DISTANCE = 200.0        # meters before spurt start

# Secure Lead (leader tries to maintain distance)
SECURE_LEAD_MIN_GAP = 5.0            # meters minimum to secure
SECURE_LEAD_SPEED_BONUS = 1.01       # 1% speed bonus

# Stamina Keep (conserve stamina when behind pacemaker)
STAMINA_KEEP_HP_SAVE = 0.05          # 5% HP consumption reduction
STAMINA_KEEP_MAX_BEHIND = 3.0        # meters behind pacemaker to activate

# =============================================================================
# PACEMAKER SYSTEM CONSTANTS (from wiki)
# =============================================================================

# Target distance behind pacemaker (leader) by running style
# Non-FR runners maintain position relative to the pacemaker
PACEMAKER_TARGET_DISTANCE = {
    RunningStyle.FR: 0.0,    # FR aims to BE the pacemaker
    RunningStyle.RW: 0.0,    # RW also aims to be pacemaker
    RunningStyle.PC: 4.0,    # PC stays ~4m behind
    RunningStyle.LS: 8.0,    # LS stays ~8m behind
    RunningStyle.EC: 15.0,   # EC stays ~15m behind
}

# Tolerance for position keep triggers
PACEMAKER_TOO_CLOSE = 2.0    # meters - trigger PACE_DOWN if closer than (target - this)
PACEMAKER_TOO_FAR = 3.0      # meters - trigger PACE_UP if farther than (target + this)

# FR specific: gap ahead to maintain
FR_TARGET_LEAD = 4.5         # meters ahead FR wants to be
FR_SPEED_UP_GAP = 2.0        # If lead < this, SPEED_UP triggers


# =============================================================================
# LIMIT BREAK CONSTANTS (from wiki)
# =============================================================================

# Power Limit Break: Power > 1200 gives conserved power
POWER_LIMIT_BREAK_THRESHOLD = 1200
POWER_CONSERVE_RATE = 0.01  # Per point above 1200

# Power Release: Uses conserved power for speed boost
POWER_RELEASE_SPEED_MULT = 1.05  # 5% speed boost when active

# Stamina Contest (スタミナ勝負): Stamina > 1200 gives Target Speed bonus
# Per GameTora: "The strength of this buff depends on her Stamina and Power stats
#               and the length of the race."
STAMINA_LIMIT_BREAK_THRESHOLD = 1200
STAMINA_LIMIT_BREAK_RATE = 0.005      # Base rate per stamina point above 1200
STAMINA_LIMIT_BREAK_POWER_FACTOR = 0.0001  # Additional bonus from Power stat


# =============================================================================
# CORNER SYSTEM CONSTANTS (NEW)
# =============================================================================
# Speed reduction when entering corners based on Power stat and corner sharpness

CORNER_SPEED_REDUCTION_BASE = 0.97    # Base speed multiplier in corners (97%)
CORNER_POWER_FACTOR = 0.00002         # Power reduces corner speed loss
CORNER_SHARPNESS_MULTIPLIER = 0.015   # Per degree of turn sharpness

# Corner sharpness by racecourse (degrees of turn)
# Higher value = sharper corner = more speed reduction
RACECOURSE_CORNER_SHARPNESS = {
    "Tokyo": 15.0,       # Wide, gentle turns
    "Nakayama": 22.0,    # Tighter turns, famous for difficult corners
    "Hanshin": 18.0,     # Moderate turns
    "Kyoto": 20.0,       # Slightly tight turns
    "Chukyo": 17.0,      # Gentle turns
    "Sapporo": 16.0,     # Gentle turns
    "Hakodate": 18.0,    # Moderate turns
    "Fukushima": 20.0,   # Slightly tight
    "Niigata": 14.0,     # Very gentle (straight course)
    "Kokura": 19.0,      # Moderate turns
    "Ohi": 22.0,         # Tight turns (oval track)
}


# =============================================================================
# LANE ADVANTAGE SYSTEM CONSTANTS (NEW)
# =============================================================================
# Inner lanes have shorter distance, outer lanes easier to overtake

LANE_DISTANCE_FACTOR = 0.002          # Extra distance per lane position (in course width)
LANE_OVERTAKE_BONUS = 0.01            # Easier overtaking bonus per lane width
LANE_INNER_BLOCKING_CHANCE = 0.15     # Higher chance of being blocked on inner lanes


# =============================================================================
# COASTING MODE CONSTANTS (NEW)
# =============================================================================
# Energy-saving mode when in good position relative to pacemaker

COASTING_HP_REDUCTION = 0.15          # 15% HP consumption reduction while coasting
COASTING_SPEED_REDUCTION = 0.02       # 2% speed reduction while coasting
COASTING_MIN_WISDOM = 400             # Minimum wisdom to use coasting effectively
COASTING_POSITION_TOLERANCE = 3.0     # Meters from target position to activate coasting


# =============================================================================
# ACCELERATION MODE CONSTANTS (NEW)
# =============================================================================
# Distinct acceleration states with different speed/HP trade-offs

class AccelMode(Enum):
    CONSERVING = auto()   # Saving energy, slower acceleration
    CRUISING = auto()     # Normal pace
    PUSHING = auto()      # Aggressive, faster but more HP drain
    SPRINTING = auto()    # Maximum effort, final spurt

ACCEL_MODE_MODIFIERS = {
    AccelMode.CONSERVING: {'speed': 0.97, 'accel': 0.9, 'hp': 0.85},   # -3% speed, -10% accel, -15% HP drain
    AccelMode.CRUISING: {'speed': 1.0, 'accel': 1.0, 'hp': 1.0},       # Normal
    AccelMode.PUSHING: {'speed': 1.02, 'accel': 1.1, 'hp': 1.15},      # +2% speed, +10% accel, +15% HP drain
    AccelMode.SPRINTING: {'speed': 1.04, 'accel': 1.2, 'hp': 1.25},    # +4% speed, +20% accel, +25% HP drain
}


# =============================================================================
# SKILL STACKING RULES CONSTANTS (NEW)
# =============================================================================
# How multiple skill effects combine

SKILL_STACK_SAME_TYPE_MODE = "additive"       # Same effect types add together
SKILL_STACK_DIFFERENT_TYPE_MODE = "multiplicative"  # Different types multiply
SKILL_STACK_DIMINISHING_RATE = 0.7            # Each subsequent effect at 70% of previous
SKILL_MAX_SPEED_BONUS = 0.5                   # Cap at +50% total speed bonus
SKILL_MAX_ACCEL_BONUS = 0.6                   # Cap at +60% total accel bonus
SKILL_MAX_HP_SAVE = 0.4                       # Cap at 40% HP save


# =============================================================================
# ACTIVATION RATE CONSTANTS (NEW)
# =============================================================================
# Skills have base % chance modified by wisdom and conditions

SKILL_BASE_ACTIVATION_RATE = 0.7      # 70% base activation rate
SKILL_WISDOM_FACTOR = 0.0003          # Wisdom bonus to activation rate
SKILL_MAX_ACTIVATION_RATE = 0.95      # Max 95% activation rate
SKILL_CONDITION_BONUS = 0.1           # +10% when conditions are perfect


# =============================================================================
# RECOVERY SKILL CONSTANTS (NEW)
# =============================================================================
# HP restoration skill effects

RECOVERY_BASE_AMOUNT = 0.03           # Base 3% HP recovery
RECOVERY_STAMINA_FACTOR = 0.00005     # Stamina stat bonus to recovery
RECOVERY_MAX_AMOUNT = 0.15            # Max 15% HP recovery per skill


# =============================================================================
# DEBUFF RESISTANCE CONSTANTS (NEW)
# =============================================================================
# Wisdom and skills reduce debuff effectiveness

DEBUFF_WISDOM_RESISTANCE = 0.0002     # Wisdom reduces debuff effect
DEBUFF_MAX_RESISTANCE = 0.5           # Max 50% debuff resistance
DEBUFF_DURATION_REDUCTION = 0.3       # 30% duration reduction with high resistance


# =============================================================================
# FATIGUE SYSTEM CONSTANTS (NEW)
# =============================================================================
# Cumulative tiredness affecting late-race performance

FATIGUE_ACCUMULATION_RATE = 0.001     # Fatigue gain per second of high effort
FATIGUE_THRESHOLD = 0.3               # Fatigue level where penalties start
FATIGUE_SPEED_PENALTY = 0.05          # Max 5% speed penalty at full fatigue
FATIGUE_ACCEL_PENALTY = 0.08          # Max 8% accel penalty at full fatigue
FATIGUE_RECOVERY_RATE = 0.0005        # Fatigue recovery when coasting


# =============================================================================
# SPEED RANDOMNESS CONSTANTS (from wiki)
# =============================================================================

# Each section gets a random speed modifier
SECTION_SPEED_RANDOM_MIN = 0.98  # -2%
SECTION_SPEED_RANDOM_MAX = 1.02  # +2%
NUM_RACE_SECTIONS = 24           # Standard 24 sections


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
    strategy_aptitude: str = "A"  # Running style aptitude - affects Wit effectiveness
    skills: List[str] = field(default_factory=list)  # List of equipped skill IDs
    mood: Mood = Mood.NORMAL  # Affects all base stats
    gate_number: int = 1  # Starting gate position (1-18 standard, depends on racecourse)


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
    RunningStyle.RW: {'opening': 1.063, 'middle': 0.962, 'final': 0.95},  # Runaway - fastest start, slowest end
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
    RunningStyle.RW: {'opening': 1.17, 'middle': 0.94, 'final': 0.956},  # Runaway - highest opening accel
    RunningStyle.FR: {'opening': 1.0, 'middle': 1.0, 'final': 0.996},
    RunningStyle.PC: {'opening': 0.985, 'middle': 1.0, 'final': 0.996},
    RunningStyle.LS: {'opening': 0.975, 'middle': 1.0, 'final': 1.0},
    RunningStyle.EC: {'opening': 0.945, 'middle': 1.0, 'final': 0.967},
}

# HP (Stamina) Conversion Coefficients from wiki
# | Runaway     | Front Runner | Pace Chaser | Late Surger | End Closer |
# |    0.86     |    0.95      |    0.89     |    1.0      |   0.995    |

STRATEGY_HP_COEF = {
    RunningStyle.RW: 0.86,   # Runaway burns stamina fastest
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
    RunningStyle.RW: RunningStyleConfig(  # Runaway - tries to stay far ahead
        target_position_ratio=0.05,  # Aims for 1st place, far ahead
        early_accel_bonus=1.17,
        mid_accel_bonus=0.94,
        late_accel_bonus=0.956,
        final_accel_bonus=0.956,
        stamina_efficiency=0.86,  # Burns stamina fastest
        hp_recovery_bonus=0.8,
    ),
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
# STRATEGY APTITUDE MODIFIER FOR WISDOM (from GameTora)
# =============================================================================
# Running style aptitude affects Wit (Wisdom) effectiveness for:
# - Skill activation rates
# - Stamina conservation checks
# - Repositioning calculations
# | S    | A   | B    | C    | D   | E   | F   | G   |
# | 1.1  | 1.0 | 0.85 | 0.75 | 0.6 | 0.4 | 0.2 | 0.1 |

STRATEGY_APTITUDE_WIT_MODIFIER = {
    'S': 1.1, 'A': 1.0, 'B': 0.85, 'C': 0.75,
    'D': 0.6, 'E': 0.4, 'F': 0.2, 'G': 0.1,
}

# =============================================================================
# REPOSITIONING (位置取り調整) CONSTANTS - from GameTora
# =============================================================================
# Mid-race positioning adjustment mechanic
# Triggers when: large gap to leader OR many nearby uma
# Consumes HP for temporary speed boost
REPOSITIONING_GAP_THRESHOLD = 4.5  # meters - triggers if gap > this
REPOSITIONING_NEARBY_COUNT = 3     # triggers if this many uma within 3m
REPOSITIONING_NEARBY_RADIUS = 3.0  # meters - radius to count nearby uma
REPOSITIONING_HP_COST = 0.02       # HP percentage consumed
REPOSITIONING_SPEED_BONUS = 1.025  # 2.5% speed boost
REPOSITIONING_DURATION = 1.5       # seconds
REPOSITIONING_COOLDOWN = 4.0       # seconds between activations
REPOSITIONING_MIN_PHASE = 1        # Only in middle leg or later

# =============================================================================
# STAMINA CONSERVATION (持久力温存) CONSTANTS - from GameTora  
# =============================================================================
# Prevents repositioning when HP too low for final spurt
# Wit-based check every 2 seconds
STAMINA_CONSERVATION_CHECK_INTERVAL = 2.0  # seconds
STAMINA_CONSERVATION_HP_THRESHOLD = 0.30   # 30% HP minimum for repositioning
STAMINA_CONSERVATION_WIT_FACTOR = 0.0005   # Higher Wit = smarter conservation

# =============================================================================
# CORNER NUMBERING SYSTEM - from GameTora
# =============================================================================
# Corners are numbered backwards from finish: last corner = 4, then 3, 2, 1
# Used for corner-specific skill triggers (e.g. "Corner 3 skill")
CORNER_NUMBERING_BACKWARDS = True  # Corners count from finish backwards

# =============================================================================
# GATE BRACKET SYSTEM - from GameTora (CORRECTED)
# =============================================================================
# Gate BRACKETS (not gates!) are numbered 1-8
# - Brackets 1-3 are "Inner Brackets" (内枠)
# - Brackets 4-5 are "Middle Brackets"
# - Brackets 6-8 are "Outer Brackets" (外枠)
#
# For ≤8 participants: gate = bracket (1:1 mapping)
# For >8 participants: extra gates added in reverse from bracket 8
# Example: 9 participants = gates 1-8 map to brackets 1-8, gate 9 -> bracket 8
#          10 participants = gate 10 -> bracket 7
#
# Inner/Outer determination is by BRACKET number, not gate number
GATE_BRACKET_INNER = [1, 2, 3]       # Bracket numbers considered "inner"
GATE_BRACKET_MIDDLE = [4, 5]         # Bracket numbers considered "middle"  
GATE_BRACKET_OUTER = [6, 7, 8]       # Bracket numbers considered "outer"

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
    TEMPTATION_HP_MULT = 1.8          # HP consumption multiplier during temptation
    LATE_START_THRESHOLD = 0.066     # 0.066s+ = late start
    DUEL_DISTANCE_THRESHOLD = 3.0    # 3m proximity for dueling
    DUEL_SPEED_THRESHOLD = 0.6       # Must be within 0.6 m/s
    DUEL_HP_THRESHOLD = 0.15         # Need 15% HP to duel
    
    def __init__(self, race_distance: float, race_type: str = 'Medium', 
                 terrain: TerrainType = TerrainType.TURF,
                 track_condition: TrackCondition = TrackCondition.GOOD,
                 stat_threshold: int = 0,
                 seed: Optional[int] = None,
                 racecourse: str = "Tokyo"):
        """
        Initialize the race engine.
        
        Args:
            race_distance: Total race distance in meters
            race_type: One of 'Sprint', 'Mile', 'Medium', 'Long' (for categorization)
            terrain: TerrainType.TURF or TerrainType.DIRT
            track_condition: TrackCondition (FIRM/GOOD/SOFT/HEAVY)
            stat_threshold: Course stat threshold for speed bonus (0 = none)
            seed: Optional random seed for reproducibility
            racecourse: Name of the racecourse (for corner sharpness, slopes)
        """
        self.race_distance = race_distance
        self.race_type = race_type
        self.terrain = terrain
        self.track_condition = track_condition
        self.stat_threshold = stat_threshold
        self.racecourse = racecourse  # NEW: For corner sharpness lookup
        
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
    
    def has_runaway_skill(self, uma_or_stats) -> bool:
        """
        Check if an Uma has the Runaway skill equipped.
        Runaway is a skill that enhances Front Runner behavior.
        
        Args:
            uma_or_stats: Either uma_name (str) or UmaStats object
        
        Returns: True if Uma has "runaway" skill in their skill list
        """
        if isinstance(uma_or_stats, str):
            if uma_or_stats not in self.uma_stats:
                return False
            stats = self.uma_stats[uma_or_stats]
        else:
            stats = uma_or_stats
        # Check if "runaway" skill ID is in the Uma's skill list
        return "runaway" in [s.lower() for s in stats.skills]
    
    def get_effective_running_style(self, uma_or_stats) -> RunningStyle:
        """
        Get the effective running style for an Uma.
        If FR has Runaway skill, they behave like RW internally.
        
        Args:
            uma_or_stats: Either uma_name (str) or UmaStats object
        
        Returns: RunningStyle (RW if FR+Runaway, otherwise their actual style)
        """
        if isinstance(uma_or_stats, str):
            stats = self.uma_stats[uma_or_stats]
            uma_name = uma_or_stats
        else:
            stats = uma_or_stats
            # Need to find uma_name from stats for has_runaway_skill
            uma_name = None
            for name, s in self.uma_stats.items():
                if s is stats:
                    uma_name = name
                    break
        
        if stats.running_style == RunningStyle.FR:
            if uma_name and self.has_runaway_skill(uma_name):
                return RunningStyle.RW  # Treat as Runaway internally
            elif isinstance(uma_or_stats, UmaStats):
                # Check directly from stats.skills
                if "runaway" in [s.lower() for s in stats.skills]:
                    return RunningStyle.RW
        return stats.running_style

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
    
    def get_effective_stat_with_mood(self, stat_value: int, mood: Mood, 
                                      stat_type: str = 'other') -> float:
        """
        Apply mood modifier to stat, then terrain penalty and soft cap.
        Mood affects base stat before any other calculations.
        
        Args:
            stat_value: Raw stat value
            mood: Uma's current mood (affects all stats)
            stat_type: 'speed', 'power', or 'other' for terrain penalties
        """
        # Apply mood modifier first (affects base stat)
        mood_coefficient = MOOD_COEFFICIENTS.get(mood, 1.0)
        mood_adjusted = int(stat_value * mood_coefficient)
        
        # Then apply terrain penalty and soft cap
        return self.get_effective_stat(mood_adjusted, stat_type)
    
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
        
        Mood affects stamina stat before calculation.
        
        Stamina Limit Break (from GameTora):
        - ONLY activates on races > 2100m (long distance)
        - +0.5% HP per stamina point above 1200
        
        Note: Front Runner with Runaway skill uses RW HP coefficient.
        """
        # Apply mood to stamina
        effective_stamina = self.get_effective_stat_with_mood(stats.stamina, stats.mood)
        
        # Get effective running style (FR with Runaway skill uses RW coefficients)
        effective_style = self.get_effective_running_style(stats)
        strategy_coef = STRATEGY_HP_COEF.get(effective_style, 1.0)
        
        max_hp = 0.8 * strategy_coef * effective_stamina + self.race_distance
        
        # Stamina Limit Break bonus - ONLY on races > 2100m (from GameTora)
        if self.race_distance > 2100 and stats.stamina > STAMINA_LIMIT_BREAK_THRESHOLD:
            excess = stats.stamina - STAMINA_LIMIT_BREAK_THRESHOLD
            limit_break_bonus = 1.0 + (excess * STAMINA_LIMIT_BREAK_RATE)
            max_hp *= limit_break_bonus
        
        return max_hp
    
    def calculate_minimum_speed(self, uma_name: str) -> float:
        """
        Calculate minimum speed from wiki formula:
        MinSpeed = 0.85 × BaseSpeed + sqrt(200.0 × GutsStat) × 0.001 [m/s]
        """
        stats = self.uma_stats[uma_name]
        effective_guts = self.get_effective_stat_with_mood(stats.guts, stats.mood)
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
    
    def generate_section_speed_randoms(self) -> List[float]:
        """Generate random speed modifiers for each race section (wiki mechanic)."""
        return [
            random.uniform(SECTION_SPEED_RANDOM_MIN, SECTION_SPEED_RANDOM_MAX)
            for _ in range(NUM_RACE_SECTIONS)
        ]
    
    def calculate_initial_lane_position(self, gate_number: int, racecourse: str = "Tokyo") -> float:
        """
        Calculate initial lane position from gate number.
        Gate 1 = innermost lane, higher gates = outer lanes.
        Lane position is in course width units (0.0 = inner rail).
        """
        max_lanes = RACECOURSE_MAX_LANES.get(racecourse, 1.2)
        # Distribute gates evenly across available lane space
        lane_per_gate = max_lanes / 18.0  # Assuming max 18 gates
        return gate_number * lane_per_gate
    
    def determine_gate_bracket(self, gate_number: int, num_participants: int = 8) -> str:
        """
        Determine gate bracket for gate-specific skill triggers.
        
        From GameTora (CORRECTED):
        - Gate BRACKETS 1-3 are "inner" (内枠)
        - Gate BRACKETS 4-5 are "middle"
        - Gate BRACKETS 6-8 are "outer" (外枠)
        
        For ≤8 participants: gate number = bracket number
        For >8 participants: extra gates are assigned to brackets in reverse
        
        Returns: "inner", "middle", or "outer"
        """
        # Calculate which bracket this gate belongs to
        bracket_number = self.gate_to_bracket(gate_number, num_participants)
        
        if bracket_number in GATE_BRACKET_INNER:
            return "inner"
        elif bracket_number in GATE_BRACKET_MIDDLE:
            return "middle"
        else:
            return "outer"
    
    def gate_to_bracket(self, gate_number: int, num_participants: int = 8) -> int:
        """
        Convert gate number to bracket number based on participant count.
        
        From GameTora:
        - For ≤8 participants: gate = bracket (1:1)
        - For >8 participants: gates 1-8 map to brackets 1-8,
          extra gates assigned in reverse starting from bracket 8
        
        Example with 10 participants:
        - Gates 1-8 -> Brackets 1-8
        - Gate 9 -> Bracket 8
        - Gate 10 -> Bracket 7
        
        Returns: Bracket number (1-8)
        """
        if num_participants <= 8:
            # Direct 1:1 mapping
            return min(gate_number, 8)
        
        if gate_number <= 8:
            # First 8 gates map directly
            return gate_number
        
        # Extra gates (9+) are assigned in reverse from bracket 8
        # Gate 9 -> bracket 8, Gate 10 -> bracket 7, etc.
        extra_gate_index = gate_number - 8  # 1-based index of extra gate
        bracket = 8 - ((extra_gate_index - 1) % 8)  # Cycle through 8,7,6,5,4,3,2,1
        return bracket
    
    def calculate_conserved_power(self, stats: UmaStats) -> float:
        """Calculate conserved power for limit break (wiki mechanic)."""
        if stats.power > POWER_LIMIT_BREAK_THRESHOLD:
            excess = stats.power - POWER_LIMIT_BREAK_THRESHOLD
            return excess * POWER_CONSERVE_RATE
        return 0.0
        
    def add_uma(self, stats: UmaStats, racecourse: str = "Tokyo") -> None:
        """Add an Uma to the race with initial state including all new mechanics."""
        self.uma_stats[stats.name] = stats
        max_hp = self.calculate_max_hp(stats)
        
        # Generate start delay (GameTora mechanic)
        start_delay, is_late_start = self.generate_start_delay(stats)
        
        # Generate per-Uma speed variance seed (-1% to +1%)
        speed_variance_seed = (random.random() - 0.5) * 0.02
        
        # Generate section speed randoms (wiki mechanic)
        section_speed_randoms = self.generate_section_speed_randoms()
        
        # Calculate initial lane position from gate
        lane_position = self.calculate_initial_lane_position(stats.gate_number, racecourse)
        
        # Calculate conserved power for limit break
        conserved_power = self.calculate_conserved_power(stats)
        
        # Calculate Stamina Contest bonus - ONLY on races > 2100m (from GameTora)
        # Per GameTora: Strength depends on Stamina, Power, and race length
        stamina_limit_break_bonus = 0.0
        if self.race_distance > 2100 and stats.stamina > STAMINA_LIMIT_BREAK_THRESHOLD:
            excess_stamina = stats.stamina - STAMINA_LIMIT_BREAK_THRESHOLD
            # Base bonus from stamina
            stamina_bonus = excess_stamina * STAMINA_LIMIT_BREAK_RATE
            # Additional bonus from Power stat (per GameTora)
            power_bonus = stats.power * STAMINA_LIMIT_BREAK_POWER_FACTOR
            # Race length factor (longer races = stronger effect)
            length_factor = self.race_distance / 2400.0  # Normalized to 2400m
            stamina_limit_break_bonus = (stamina_bonus + power_bonus) * length_factor
        
        # Determine gate bracket (inner/middle/outer) for gate-specific skills
        # Note: bracket calculation depends on total participants, assume 8 for now
        # Will be recalculated when race starts with actual participant count
        num_participants = len(self.uma_stats) + 1  # +1 for the uma being added
        gate_bracket = self.determine_gate_bracket(stats.gate_number, num_participants)
        
        state = UmaState(
            name=stats.name,
            lane=len(self.uma_states),  # Display lane (for visualization)
            current_speed=self.STARTING_SPEED,  # 3 m/s from wiki
            hp=max_hp,
            max_hp=max_hp,
            start_delay=start_delay,
            is_late_start=is_late_start,
            speed_variance_seed=speed_variance_seed,
            equipped_skills=list(stats.skills),
            # New lane system fields
            lane_position=lane_position,
            target_lane=lane_position,
            gate_block=stats.gate_number,
            gate_bracket=gate_bracket,  # NEW: Gate bracket for skills
            # Mood from stats
            mood=stats.mood,
            # Section speed randoms
            section_speed_randoms=section_speed_randoms,
            # Limit break
            conserved_power=conserved_power,
            stamina_limit_break_bonus=stamina_limit_break_bonus,
        )
        self.uma_states[stats.name] = state
        
    def reset(self, racecourse: str = "Tokyo") -> None:
        """Reset all Uma states to initial conditions."""
        for name in self.uma_states:
            stats = self.uma_stats[name]
            max_hp = self.calculate_max_hp(stats)
            start_delay, is_late_start = self.generate_start_delay(stats)
            speed_variance_seed = (random.random() - 0.5) * 0.02
            section_speed_randoms = self.generate_section_speed_randoms()
            lane_position = self.calculate_initial_lane_position(stats.gate_number, racecourse)
            conserved_power = self.calculate_conserved_power(stats)
            
            # Calculate Stamina Contest bonus - ONLY on races > 2100m (from GameTora)
            # Per GameTora: Strength depends on Stamina, Power, and race length
            stamina_limit_break_bonus = 0.0
            if self.race_distance > 2100 and stats.stamina > STAMINA_LIMIT_BREAK_THRESHOLD:
                excess_stamina = stats.stamina - STAMINA_LIMIT_BREAK_THRESHOLD
                # Base bonus from stamina
                stamina_bonus = excess_stamina * STAMINA_LIMIT_BREAK_RATE
                # Additional bonus from Power stat (per GameTora)
                power_bonus = stats.power * STAMINA_LIMIT_BREAK_POWER_FACTOR
                # Race length factor (longer races = stronger effect)
                length_factor = self.race_distance / 2400.0
                stamina_limit_break_bonus = (stamina_bonus + power_bonus) * length_factor
            
            # Determine gate bracket for reset - use total participant count
            num_participants = len(self.uma_stats)
            gate_bracket = self.determine_gate_bracket(stats.gate_number, num_participants)
            
            self.uma_states[name] = UmaState(
                name=name,
                lane=self.uma_states[name].lane,
                current_speed=self.STARTING_SPEED,
                hp=max_hp,
                max_hp=max_hp,
                start_delay=start_delay,
                is_late_start=is_late_start,
                speed_variance_seed=speed_variance_seed,
                equipped_skills=list(stats.skills),
                lane_position=lane_position,
                target_lane=lane_position,
                gate_block=stats.gate_number,
                gate_bracket=gate_bracket,  # NEW: Gate bracket for skills
                mood=stats.mood,
                section_speed_randoms=section_speed_randoms,
                conserved_power=conserved_power,
                stamina_limit_break_bonus=stamina_limit_break_bonus,
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
            - Mood affects base stats
            - Runaway skill enhances FR to behave like RW
            
        LOW STAT PENALTY: Low Speed stat applies multiplicative penalty
        """
        stats = self.uma_stats[uma_name]
        phase_name = self.get_phase_name(phase)
        
        # Get effective running style (FR with Runaway skill = RW behavior)
        effective_style = self.get_effective_running_style(uma_name)
        
        # Get strategy coefficient for this phase using effective style
        strategy_coef = STRATEGY_SPEED_COEF[effective_style][phase_name]
        
        # Base target speed (all phases)
        target_speed = self.base_speed * strategy_coef
        
        # Speed stat bonus ONLY in Final Leg and Last Spurt (from wiki)
        if phase in (RacePhase.LATE, RacePhase.FINAL_SPURT):
            # Apply mood and terrain penalty to speed stat
            effective_speed = self.get_effective_stat_with_mood(stats.speed, stats.mood, 'speed')
            
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
        effective_speed_for_penalty = self.get_effective_stat_with_mood(stats.speed, stats.mood, 'speed')
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
        Mood: Affects power stat
        Runaway skill: FR with Runaway uses RW acceleration coefficients
        
        LOW STAT PENALTY: Low Power stat reduces acceleration
        """
        stats = self.uma_stats[uma_name]
        state = self.uma_states[uma_name]
        phase_name = self.get_phase_name(phase)
        
        # Get effective running style (FR with Runaway skill = RW behavior)
        effective_style = self.get_effective_running_style(uma_name)
        
        # Base acceleration (0.0006 normal, 0.0004 uphill)
        # Use reduced base accel if on uphill
        if state.is_on_uphill:
            base_accel = self.BASE_ACCEL * 0.67  # 0.0004 for uphill
        else:
            base_accel = self.BASE_ACCEL  # 0.0006 normal
        
        # Power contribution: sqrt(500.0 × PowerStat) with mood and terrain penalty
        effective_power = self.get_effective_stat_with_mood(stats.power, stats.mood, 'power')
        power_factor = math.sqrt(500.0 * effective_power)
        
        # Strategy phase coefficient for acceleration using effective style
        strategy_coef = STRATEGY_ACCEL_COEF[effective_style][phase_name]
        
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
        if state.is_tempted:
            status_mod = self.TEMPTATION_HP_MULT  # 1.8x during temptation (highest drain)
        elif state.is_rushing:
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
    
    def check_temptation(self, uma_name: str, progress: float, delta_time: float) -> None:
        """
        Check and update Temptation (かかり) state.
        
        Temptation is an INVOLUNTARY loss of control where the horse accelerates
        uncontrollably, burning extra stamina. Different from Rushing:
        - Rushing: Voluntary but wasteful acceleration
        - Temptation: Involuntary, harder to control, more HP drain
        
        Mechanics:
        - Can trigger multiple times per race (up to 3)
        - Lower Wisdom = higher chance AND longer duration
        - Triggers between 5% and 75% race progress
        - Provides speed boost but massive HP drain (1.8x)
        - Has cooldown period after each occurrence
        - Running style affects chance (FR/RW more prone)
        
        Effects:
        - +0.8 m/s speed boost (uncontrollable)
        - 1.8x HP consumption
        - Cannot use position keep properly
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return
        
        # Update cooldown
        if state.temptation_cooldown > 0:
            state.temptation_cooldown -= delta_time
        
        # Update existing temptation timer
        if state.is_tempted:
            state.temptation_timer -= delta_time
            if state.temptation_timer <= 0:
                # Temptation ends
                state.is_tempted = False
                state.temptation_timer = 0.0
                state.temptation_speed_boost = 0.0
                state.temptation_cooldown = TEMPTATION_COOLDOWN  # Start cooldown
            return
        
        # Check if can trigger new temptation
        if state.temptation_cooldown > 0:
            return  # Still on cooldown
        
        if state.temptation_triggered_count >= TEMPTATION_MAX_TRIGGERS:
            return  # Already triggered max times
        
        # Check valid progress range
        if progress < TEMPTATION_MIN_PROGRESS or progress > TEMPTATION_MAX_PROGRESS:
            return
        
        # Check interval (don't check every tick)
        # Use a simple timer approach - check roughly every TEMPTATION_CHECK_INTERVAL
        check_chance = delta_time / TEMPTATION_CHECK_INTERVAL
        if random.random() > check_chance:
            return
        
        # Calculate temptation chance based on Wisdom
        effective_wisdom = self.get_effective_stat_with_mood(stats.wisdom, stats.mood)
        
        # Base chance modified by Wisdom: lower wisdom = higher chance
        # At 600 wisdom: base chance, at 1200: half chance, at 300: double chance
        wisdom_modifier = TEMPTATION_WISDOM_FACTOR / max(effective_wisdom, 100)
        temptation_chance = TEMPTATION_BASE_CHANCE * wisdom_modifier
        
        # Running style modifier: FR and RW are more prone to temptation
        # Note: FR with Runaway skill is treated as RW for this check
        effective_style = self.get_effective_running_style(stats)
        if effective_style in [RunningStyle.FR, RunningStyle.RW]:
            temptation_chance *= 1.3  # 30% more likely
        elif effective_style == RunningStyle.EC:
            temptation_chance *= 0.7  # 30% less likely (EC are more patient)
        
        # Mood modifier: Bad mood = more prone to temptation
        mood_modifier = {
            Mood.AWFUL: 1.4,   # 40% more likely
            Mood.BAD: 1.2,     # 20% more likely
            Mood.NORMAL: 1.0,
            Mood.GOOD: 0.9,    # 10% less likely
            Mood.GREAT: 0.8,   # 20% less likely
        }.get(stats.mood, 1.0)
        temptation_chance *= mood_modifier
        
        # Position modifier: Being behind increases temptation (frustration)
        position_ratio = state.position / max(len(self.uma_states), 1)
        if position_ratio > 0.5:  # Back half of pack
            temptation_chance *= 1.0 + (position_ratio - 0.5) * 0.4  # Up to +20%
        
        # Clamp chance
        temptation_chance = min(0.25, max(0.02, temptation_chance))  # 2-25% per check
        
        # Roll for temptation
        if random.random() < temptation_chance:
            state.is_tempted = True
            state.temptation_triggered_count += 1
            
            # Duration based on Wisdom (lower wisdom = longer)
            duration_modifier = TEMPTATION_WISDOM_FACTOR / max(effective_wisdom, 100)
            base_duration = TEMPTATION_MIN_DURATION + random.random() * (TEMPTATION_MAX_DURATION - TEMPTATION_MIN_DURATION)
            state.temptation_timer = base_duration * min(duration_modifier, 2.0)  # Cap at 2x duration
            
            # Speed boost during temptation
            state.temptation_speed_boost = TEMPTATION_SPEED_BOOST
            
            # Debug log
            print(f"[TEMPTATION] {stats.name} lost control! Duration: {state.temptation_timer:.1f}s (Trigger #{state.temptation_triggered_count})")
    
    def get_temptation_effects(self, uma_name: str) -> Tuple[float, float]:
        """
        Get temptation effects for speed and HP.
        
        Returns: (speed_boost, hp_multiplier)
        """
        state = self.uma_states[uma_name]
        
        if state.is_tempted:
            return state.temptation_speed_boost, TEMPTATION_HP_MULTIPLIER
        return 0.0, 1.0

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
        Note: FR with Runaway skill also triggers spot struggle.
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return
        
        # Only FR (or FR with Runaway) can spot struggle
        effective_style = self.get_effective_running_style(stats)
        if effective_style not in [RunningStyle.FR, RunningStyle.RW]:
            return
        
        # Valid range: 150m after start to mid-Mid-Race
        if state.distance < 150 or state.distance > self.position_keep_end:
            state.is_in_spot_struggle = False
            return
        
        # Check for nearby Front Runners (or FR with Runaway)
        fr_threshold = 3.75  # meters
        for other_name, other_state in self.uma_states.items():
            if other_name == uma_name or other_state.is_finished or other_state.is_dnf:
                continue
            
            other_stats = self.uma_stats[other_name]
            other_effective_style = self.get_effective_running_style(other_stats)
            if other_effective_style not in [RunningStyle.FR, RunningStyle.RW]:
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
        
        Wiki-accurate activation mechanics:
        - Base activation rate from skill definition
        - Wisdom affects activation chance (higher wisdom = higher chance)
        - Mood affects activation (GREAT: +10%, GOOD: +5%, NORMAL: 0%, BAD: -5%, AWFUL: -10%)
        - Random roll determines if skill activates
        
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
        
        # =================================================================
        # SKILL ACTIVATION CHANCE CALCULATION (wiki-based)
        # =================================================================
        
        # Base chance from skill
        base_chance = skill.activation_chance
        
        # Use comprehensive activation rate calculation (includes wisdom, mood, state bonus)
        state = self.uma_states[uma_name]
        final_chance = self.calculate_skill_activation_rate(uma_name, base_chance)
        
        if random.random() > final_chance:
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
        
        Uses skill stacking rules:
        - Same skill type: Only strongest effect active
        - Different skill types: Stack with diminishing returns
        
        Returns: (total_speed_bonus, total_accel_bonus, total_stamina_save)
        """
        state = self.uma_states[uma_name]
        
        # Update cooldowns
        for skill_id in list(state.skill_cooldowns.keys()):
            state.skill_cooldowns[skill_id] -= delta_time
            if state.skill_cooldowns[skill_id] <= 0:
                del state.skill_cooldowns[skill_id]
        
        # Update active skills and remove expired ones
        still_active = []
        for active in state.active_skills:
            active.remaining_duration -= delta_time
            if active.remaining_duration > 0:
                still_active.append(active)
        
        state.active_skills = still_active
        
        # Collect all bonuses by type for stacking calculation
        speed_bonuses = [s.speed_bonus for s in state.active_skills if s.speed_bonus > 0]
        accel_bonuses = [s.accel_bonus for s in state.active_skills if s.accel_bonus > 0]
        stamina_saves = [s.stamina_save for s in state.active_skills if s.stamina_save > 0]
        
        # Apply stacking rules with caps
        total_speed_bonus = min(SKILL_MAX_SPEED_BONUS, self.calculate_stacked_skill_effects(speed_bonuses))
        total_accel_bonus = min(SKILL_MAX_ACCEL_BONUS, self.calculate_stacked_skill_effects(accel_bonuses))
        total_stamina_save = min(SKILL_MAX_HP_SAVE, self.calculate_stacked_skill_effects(stamina_saves))
        
        return total_speed_bonus, total_accel_bonus, total_stamina_save
    
    def check_and_activate_skills(self, uma_name: str, progress: float) -> List[str]:
        """
        Check all equipped skills and try to activate them.
        
        Wiki-based mechanics:
        - Wisdom affects skill check frequency (higher wisdom = more frequent checks)
        - Each skill is checked independently when timer allows
        
        Returns: List of skill names that were activated this tick
        """
        if not SKILLS_AVAILABLE:
            return []
        
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        activated = []
        
        # Wisdom-based check interval
        # Base interval: 0.5 seconds, reduced by wisdom (min 0.1 at 1200 wisdom)
        effective_wisdom = self.get_effective_stat_with_mood(stats.wisdom, stats.mood)
        check_interval = max(0.1, 0.5 - (effective_wisdom / 3000.0))  # 0.1-0.5s interval
        
        # Only check skills if timer has elapsed
        if state.skill_check_timer > 0:
            return []
        
        # Reset timer for next check
        state.skill_check_timer = check_interval
        
        # Check each equipped skill
        for skill_id in stats.skills:
            if self.try_activate_skill(uma_name, skill_id, progress):
                skill = get_skill_by_id(skill_id)
                if skill:
                    activated.append(skill.name)
        
        return activated
    
    def simulate_terrain(self, uma_name: str, progress: float) -> None:
        """
        Simulate terrain changes based on race progress with full feature integration.
        Includes corner detection, track conditions, and vision system.
        
        CORNER NUMBERING (from GameTora):
        Corners are numbered backwards from finish: 4 (last), 3, 2, 1 (first)
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        # Track previous terrain for corner entry detection
        prev_terrain = state.current_terrain
        was_in_corner = state.is_in_corner
        
        # Determine current terrain based on progress
        # Standard track layout: 4 corners total
        # Corner positions (approximate for generic racecourse):
        # Corner 1: ~15-30% (first corner after start)
        # Corner 2: ~40-50% (backstretch corner)
        # Corner 3: ~55-65% (third corner)
        # Corner 4: ~75-85% (final corner before home straight)
        if progress < 0.15:
            state.current_terrain = "straight"
            state.is_in_corner = False
            state.current_corner_number = 0
        elif progress < 0.30:
            state.current_terrain = "corner"
            state.is_in_corner = True
            state.current_corner_number = 1  # First corner = numbered 1 from start
        elif progress < 0.40:
            state.current_terrain = "straight"
            state.is_in_corner = False
            state.current_corner_number = 0
        elif progress < 0.50:
            state.current_terrain = "corner"
            state.is_in_corner = True
            state.current_corner_number = 2  # Second corner
        elif progress < 0.55:
            if random.random() < 0.3:
                state.current_terrain = "uphill"
            else:
                state.current_terrain = "straight"
            state.is_in_corner = False
            state.current_corner_number = 0
        elif progress < 0.65:
            state.current_terrain = "corner"
            state.is_in_corner = True
            state.current_corner_number = 3  # Third corner
        elif progress < 0.75:
            state.current_terrain = "straight"
            state.is_in_corner = False
            state.current_corner_number = 0
        elif progress < 0.85:
            state.current_terrain = "corner"  # Final turn
            state.is_in_corner = True
            state.current_corner_number = 4  # Fourth (final) corner - same as "Corner 4" skills
        else:
            state.current_terrain = "straight"  # Final straight
            state.is_in_corner = False
            state.current_corner_number = 0
        
        # Track corners passed (for stats/debugging)
        if state.is_in_corner and not was_in_corner:
            state.total_corners_passed += 1
        
        # FEATURE 1: CORNER SPEED REDUCTION (FULLY IMPLEMENTED)
        if state.is_in_corner:
            state.corner_speed_modifier = self.calculate_corner_speed_modifier(uma_name)
        else:
            state.corner_speed_modifier = 1.0
        
        # FEATURE 2: TRACK CONDITION EFFECTS (FULLY IMPLEMENTED)
        self.apply_track_condition_effects(uma_name)
        
        # FEATURE 3: VISION SYSTEM (FULLY IMPLEMENTED)
        self.update_vision_system(uma_name)
    
    def calculate_corner_speed_modifier(self, uma_name: str) -> float:
        """
        Calculate speed modifier when in a corner (FULLY IMPLEMENTED).
        
        Factors:
        - Racecourse corner sharpness (15-22 degrees)
        - Uma's power stat (reduces speed loss via corner stability)
        - Uma's running style (affects corner handling technique)
        - Track condition (affects grip/traction in corners)
        """
        stats = self.uma_stats[uma_name]
        state = self.uma_states[uma_name]
        
        # Get corner sharpness (15-22 degrees per racecourse)
        sharpness = RACECOURSE_CORNER_SHARPNESS.get(self.racecourse, 18.0)
        
        # Base corner speed reduction (0.95 = 5% reduction)
        base_modifier = CORNER_SPEED_REDUCTION_BASE
        
        # Sharpness penalty: tighter corners = more speed loss
        sharpness_penalty = (sharpness - 10.0) * CORNER_SHARPNESS_MULTIPLIER / 100.0
        
        # Power bonus: high power = better corner stability
        effective_power = self.get_effective_stat_with_mood(stats.power, stats.mood, 'power')
        power_bonus = min(0.05, effective_power * CORNER_POWER_FACTOR)
        
        # Running style bonus
        style_bonus = 0.0
        if stats.running_style == RunningStyle.FR:
            style_bonus = 0.01  # FR: aggressive cornering
        elif stats.running_style == RunningStyle.EC:
            style_bonus = 0.015  # EC: good mid-corner acceleration
        
        # Track condition: wet reduces grip in corners
        condition_modifier = self.get_track_condition_corner_modifier()
        
        modifier = base_modifier - sharpness_penalty + power_bonus + style_bonus
        modifier *= condition_modifier
        
        return max(0.80, min(1.0, modifier))
    
    def calculate_lane_distance_penalty(self, uma_name: str) -> float:
        """
        Calculate extra distance traveled due to lane position.
        Outer lanes travel more distance in corners.
        """
        state = self.uma_states[uma_name]
        
        # Lane position affects distance only in corners
        if not state.is_in_corner:
            return 0.0
        
        # Extra distance based on lane position
        lane_factor = state.lane_position * LANE_DISTANCE_FACTOR
        
        # Convert to actual meters based on race distance
        extra_distance = self.race_distance * lane_factor
        
        return extra_distance
    
    def apply_track_condition_effects(self, uma_name: str) -> None:
        """
        Apply track condition effects to speed and acceleration (FULLY IMPLEMENTED).
        
        Track conditions (FIRM/GOOD/SOFT/HEAVY) affect:
        - Speed reduction multiplier
        - Acceleration reduction multiplier  
        - HP drain increase (harder running conditions)
        """
        state = self.uma_states[uma_name]
        
        condition_key = (self.terrain, self.track_condition)
        penalties = TERRAIN_STAT_PENALTIES.get(condition_key, {'speed': 0, 'power': 0, 'hp_mult': 1.0})
        
        # Convert stat penalties to speed/accel multipliers
        speed_penalty_mult = 1.0 - (penalties.get('speed', 0) / 2500.0)
        accel_penalty_mult = 1.0 - (penalties.get('power', 0) / 2500.0)
        hp_mult = penalties.get('hp_mult', 1.0)
        
        # Store in state for use in calculations
        state.track_condition_speed_mult = max(0.90, speed_penalty_mult)
        state.track_condition_accel_mult = max(0.85, accel_penalty_mult)
        state.track_condition_hp_mult = hp_mult
    
    def get_track_condition_corner_modifier(self) -> float:
        """
        Get track condition modifier for corner handling.
        Wet/muddy tracks increase speed loss in corners.
        """
        condition_modifiers = {
            TrackCondition.FIRM: 1.0,      # No penalty
            TrackCondition.GOOD: 0.98,     # 2% worse
            TrackCondition.SOFT: 0.96,     # 4% worse
            TrackCondition.HEAVY: 0.94,    # 6% worse
        }
        return condition_modifiers.get(self.track_condition, 1.0)
    
    def get_lane_overtake_bonus(self, uma_name: str) -> float:
        """
        Calculate overtaking bonus from being on outer lane.
        Outer lanes make it easier to pass but add distance.
        """
        state = self.uma_states[uma_name]
        
        # Bonus scales with lane position
        return state.lane_position * LANE_OVERTAKE_BONUS
    
    # =========================================================================
    # COASTING MODE SYSTEM
    # =========================================================================
    
    def check_coasting_activation(self, uma_name: str) -> None:
        """
        Check if Uma should enter coasting mode.
        Coasting activates when in good position relative to target.
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return
        
        # Can't coast during final spurt or temptation
        if state.in_final_spurt or state.is_tempted:
            state.is_coasting = False
            return
        
        # Need minimum wisdom for effective coasting
        effective_wisdom = self.get_effective_stat_with_mood(stats.wisdom, stats.mood)
        if effective_wisdom < COASTING_MIN_WISDOM:
            state.is_coasting = False
            return
        
        # Get pacemaker info
        pacemaker_name, pacemaker_distance, distance_to_pacemaker = self.get_pacemaker_info(uma_name)
        
        # Get target distance based on running style
        effective_style = self.get_effective_running_style(stats)
        target_distance = PACEMAKER_TARGET_DISTANCE.get(effective_style, 8.0)
        
        # Check if in good position (within tolerance of target)
        position_diff = abs(distance_to_pacemaker - target_distance)
        
        if position_diff <= COASTING_POSITION_TOLERANCE:
            # Good position - can coast
            if not state.is_coasting:
                state.is_coasting = True
                state.coasting_timer = 0.0
        else:
            # Out of position - stop coasting
            state.is_coasting = False
    
    def get_coasting_effects(self, uma_name: str) -> Tuple[float, float]:
        """
        Get speed and HP modifiers from coasting.
        Returns: (speed_modifier, hp_modifier)
        """
        state = self.uma_states[uma_name]
        
        if not state.is_coasting:
            return 1.0, 1.0
        
        # Coasting reduces speed but saves HP
        speed_mod = 1.0 - COASTING_SPEED_REDUCTION
        hp_mod = 1.0 - COASTING_HP_REDUCTION
        
        return speed_mod, hp_mod
    
    # =========================================================================
    # ACCELERATION MODE SYSTEM
    # =========================================================================
    
    def update_accel_mode(self, uma_name: str, progress: float) -> None:
        """
        Update acceleration mode based on race conditions.
        Mode affects speed, acceleration, and HP consumption.
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return
        
        # Final spurt = sprinting mode
        if state.in_final_spurt:
            state.accel_mode = AccelMode.SPRINTING
            return
        
        # Coasting = conserving mode
        if state.is_coasting:
            state.accel_mode = AccelMode.CONSERVING
            return
        
        # Position keep modes affect accel mode
        if state.position_keep_mode in [PositionKeepMode.OVERTAKE, PositionKeepMode.SPEED_UP]:
            state.accel_mode = AccelMode.PUSHING
            return
        
        if state.position_keep_mode == PositionKeepMode.PACE_DOWN:
            state.accel_mode = AccelMode.CONSERVING
            return
        
        # Default to cruising
        state.accel_mode = AccelMode.CRUISING
    
    def get_accel_mode_modifiers(self, uma_name: str) -> Dict[str, float]:
        """
        Get speed, accel, and HP modifiers from current accel mode.
        """
        state = self.uma_states[uma_name]
        return ACCEL_MODE_MODIFIERS.get(state.accel_mode, ACCEL_MODE_MODIFIERS[AccelMode.CRUISING])
    
    # =========================================================================
    # FATIGUE SYSTEM
    # =========================================================================
    
    def update_fatigue(self, uma_name: str, delta_time: float) -> None:
        """
        Update fatigue accumulation based on current effort level.
        High effort (pushing, sprinting) increases fatigue.
        Coasting decreases fatigue.
        """
        state = self.uma_states[uma_name]
        
        if state.is_finished or state.is_dnf:
            return
        
        # Determine effort level based on accel mode
        if state.accel_mode == AccelMode.SPRINTING:
            fatigue_change = FATIGUE_ACCUMULATION_RATE * 2.0 * delta_time
        elif state.accel_mode == AccelMode.PUSHING:
            fatigue_change = FATIGUE_ACCUMULATION_RATE * 1.5 * delta_time
        elif state.accel_mode == AccelMode.CONSERVING or state.is_coasting:
            fatigue_change = -FATIGUE_RECOVERY_RATE * delta_time
        else:
            fatigue_change = FATIGUE_ACCUMULATION_RATE * 0.5 * delta_time
        
        # Temptation causes rapid fatigue gain
        if state.is_tempted:
            fatigue_change += FATIGUE_ACCUMULATION_RATE * 1.5 * delta_time
        
        # Update fatigue level
        state.fatigue_level = max(0.0, min(1.0, state.fatigue_level + fatigue_change))
    
    def get_fatigue_penalties(self, uma_name: str) -> Tuple[float, float]:
        """
        Get speed and acceleration penalties from fatigue.
        Returns: (speed_penalty, accel_penalty) as multipliers
        """
        state = self.uma_states[uma_name]
        
        if state.fatigue_level < FATIGUE_THRESHOLD:
            return 1.0, 1.0
        
        # Calculate penalty based on fatigue above threshold
        fatigue_factor = (state.fatigue_level - FATIGUE_THRESHOLD) / (1.0 - FATIGUE_THRESHOLD)
        
        speed_penalty = 1.0 - (FATIGUE_SPEED_PENALTY * fatigue_factor)
        accel_penalty = 1.0 - (FATIGUE_ACCEL_PENALTY * fatigue_factor)
        
        return speed_penalty, accel_penalty
    
    # =========================================================================
    # SKILL STACKING AND ACTIVATION RATE
    # =========================================================================
    
    def calculate_skill_activation_rate(self, uma_name: str, skill_id: str) -> float:
        """
        Calculate actual activation rate for a skill.
        Base rate modified by wisdom and conditions.
        
        STRATEGY APTITUDE affects Wit effectiveness (from GameTora):
        - S aptitude: Wit x1.1
        - A aptitude: Wit x1.0  
        - D aptitude: Wit x0.6
        - G aptitude: Wit x0.1
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        # Base activation rate
        base_rate = SKILL_BASE_ACTIVATION_RATE
        
        # Get strategy aptitude modifier for Wit effectiveness
        strategy_apt = getattr(stats, 'strategy_aptitude', 'A')
        wit_modifier = STRATEGY_APTITUDE_WIT_MODIFIER.get(strategy_apt, 1.0)
        
        # Wisdom bonus - now modified by strategy aptitude
        effective_wisdom = self.get_effective_stat_with_mood(stats.wisdom, stats.mood)
        modified_wisdom = effective_wisdom * wit_modifier  # Apply strategy aptitude
        wisdom_bonus = modified_wisdom * SKILL_WISDOM_FACTOR
        
        # Any activation bonus from state
        state_bonus = state.skill_activation_bonus
        
        # Calculate final rate
        final_rate = base_rate + wisdom_bonus + state_bonus
        
        # Clamp to max
        return min(SKILL_MAX_ACTIVATION_RATE, final_rate)
    
    def calculate_stacked_skill_effects(self, effect_values: List[float]) -> float:
        """
        Calculate total stacked skill effect with diminishing returns.
        
        Stacking rule: First effect = 100%, subsequent effects at reduced rate.
        
        Args:
            effect_values: List of effect values from active skills
            
        Returns: Total stacked effect value
        """
        if not effect_values:
            return 0.0
        
        # Sort descending to get strongest first
        sorted_effects = sorted(effect_values, reverse=True)
        
        total = 0.0
        for i, value in enumerate(sorted_effects):
            if i == 0:
                # First (strongest) effect at full value
                total += value
            else:
                # Subsequent effects at diminishing rate
                multiplier = SKILL_STACK_DIMINISHING_RATE ** i
                total += value * multiplier
        
        return total
    
    # =========================================================================
    # RECOVERY AND DEBUFF SYSTEMS
    # =========================================================================
    
    def apply_recovery_effect(self, uma_name: str, base_recovery: float) -> float:
        """
        Apply HP recovery from a skill.
        Recovery amount scales with stamina stat.
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        # Calculate recovery amount
        stamina_bonus = stats.stamina * RECOVERY_STAMINA_FACTOR
        recovery_amount = base_recovery + stamina_bonus
        
        # Cap at maximum
        recovery_amount = min(RECOVERY_MAX_AMOUNT, recovery_amount)
        
        # Apply recovery
        hp_recovered = state.max_hp * recovery_amount
        state.hp = min(state.max_hp, state.hp + hp_recovered)
        
        return hp_recovered
    
    def calculate_debuff_resistance(self, uma_name: str) -> float:
        """
        Calculate debuff resistance from wisdom and skills.
        """
        stats = self.uma_stats[uma_name]
        
        # Wisdom-based resistance
        effective_wisdom = self.get_effective_stat_with_mood(stats.wisdom, stats.mood)
        wisdom_resistance = effective_wisdom * DEBUFF_WISDOM_RESISTANCE
        
        # Cap at maximum
        return min(DEBUFF_MAX_RESISTANCE, wisdom_resistance)
    
    def apply_debuff(self, uma_name: str, debuff_id: str, duration: float, effect: float) -> float:
        """
        Apply a debuff with resistance calculation.
        Returns actual effect after resistance.
        """
        state = self.uma_states[uma_name]
        
        # Calculate resistance
        resistance = self.calculate_debuff_resistance(uma_name)
        
        # Reduce effect and duration
        actual_effect = effect * (1.0 - resistance)
        actual_duration = duration * (1.0 - (resistance * DEBUFF_DURATION_REDUCTION))
        
        # Store debuff
        state.active_debuffs[debuff_id] = actual_duration
        
        return actual_effect
    
    def update_debuffs(self, uma_name: str, delta_time: float) -> None:
        """
        Update debuff timers and remove expired debuffs.
        """
        state = self.uma_states[uma_name]
        
        expired = []
        for debuff_id, remaining in state.active_debuffs.items():
            new_remaining = remaining - delta_time
            if new_remaining <= 0:
                expired.append(debuff_id)
            else:
                state.active_debuffs[debuff_id] = new_remaining
        
        for debuff_id in expired:
            del state.active_debuffs[debuff_id]
    
    # =========================================================================
    # REPOSITIONING SYSTEM (位置取り調整) - from GameTora
    # =========================================================================
    
    def check_repositioning(self, uma_name: str, progress: float, delta_time: float) -> float:
        """
        Check and apply repositioning mechanic (位置取り調整).
        
        Triggers in mid-race when:
        1. Large gap to leader (>4.5m), OR
        2. Many nearby uma (3+ within 3m)
        
        Effect: Temporary speed boost at HP cost.
        Blocked by stamina conservation when HP is low.
        
        Returns: Speed bonus multiplier (1.0 if not active)
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        # Repositioning only in middle leg or later
        phase = self.get_current_phase(progress)
        if phase == RacePhase.START:
            return 1.0
        
        # Update cooldown
        if state.repositioning_cooldown > 0:
            state.repositioning_cooldown -= delta_time
        
        # Update active repositioning duration
        if state.is_repositioning:
            state.repositioning_duration -= delta_time
            if state.repositioning_duration <= 0:
                state.is_repositioning = False
                state.repositioning_duration = 0.0
                return 1.0
            return REPOSITIONING_SPEED_BONUS
        
        # Check if on cooldown
        if state.repositioning_cooldown > 0:
            return 1.0
        
        # Check stamina conservation - blocks repositioning when HP too low
        if self.check_stamina_conservation(uma_name):
            return 1.0
        
        # Check trigger conditions
        should_reposition = False
        
        # Condition 1: Large gap to leader
        gap_to_leader = self.get_gap_to_leader(uma_name)
        if gap_to_leader > REPOSITIONING_GAP_THRESHOLD:
            should_reposition = True
        
        # Condition 2: Many nearby uma
        nearby_count = self.count_nearby_uma(uma_name, REPOSITIONING_NEARBY_RADIUS)
        if nearby_count >= REPOSITIONING_NEARBY_COUNT:
            should_reposition = True
        
        if should_reposition:
            # Activate repositioning
            state.is_repositioning = True
            state.repositioning_duration = REPOSITIONING_DURATION
            state.repositioning_cooldown = REPOSITIONING_COOLDOWN
            
            # Consume HP (modified by Power and Guts)
            effective_power = self.get_effective_stat_with_mood(stats.power, stats.mood)
            effective_guts = self.get_effective_stat_with_mood(stats.guts, stats.mood)
            
            # Higher Power/Guts = less HP cost
            power_guts_factor = 1.0 - (effective_power + effective_guts) / 2000.0
            power_guts_factor = max(0.5, min(1.5, power_guts_factor))
            
            hp_cost = state.max_hp * REPOSITIONING_HP_COST * power_guts_factor
            state.hp = max(0.0, state.hp - hp_cost)
            
            return REPOSITIONING_SPEED_BONUS
        
        return 1.0
    
    def check_stamina_conservation(self, uma_name: str) -> bool:
        """
        Check stamina conservation (持久力温存) mechanic.
        
        Prevents repositioning when HP is too low for final spurt.
        Wit-based check - higher Wit = smarter conservation.
        
        Returns: True if conserving (repositioning blocked), False otherwise
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        # Update conservation timer
        state.stamina_conservation_timer += 0.0  # Will be updated in tick
        
        # Get effective wisdom with strategy aptitude modifier
        strategy_apt = getattr(stats, 'strategy_aptitude', 'A')
        wit_modifier = STRATEGY_APTITUDE_WIT_MODIFIER.get(strategy_apt, 1.0)
        effective_wisdom = self.get_effective_stat_with_mood(stats.wisdom, stats.mood) * wit_modifier
        
        # Calculate HP threshold (higher Wit = more accurate prediction)
        base_threshold = STAMINA_CONSERVATION_HP_THRESHOLD
        wit_adjustment = effective_wisdom * STAMINA_CONSERVATION_WIT_FACTOR
        adjusted_threshold = base_threshold + wit_adjustment
        
        # Check if HP is below conservation threshold
        hp_percentage = state.hp / state.max_hp
        if hp_percentage < adjusted_threshold:
            state.is_conserving_stamina = True
            return True
        
        state.is_conserving_stamina = False
        return False
    
    def get_gap_to_leader(self, uma_name: str) -> float:
        """Get the distance gap to the race leader."""
        my_distance = self.uma_states[uma_name].distance
        
        leader_distance = 0.0
        for name, state in self.uma_states.items():
            if not state.is_finished and not state.is_dnf:
                if state.distance > leader_distance:
                    leader_distance = state.distance
        
        return leader_distance - my_distance
    
    def count_nearby_uma(self, uma_name: str, radius: float) -> int:
        """Count how many uma are within the specified radius."""
        my_state = self.uma_states[uma_name]
        my_distance = my_state.distance
        count = 0
        
        for name, state in self.uma_states.items():
            if name == uma_name:
                continue
            if state.is_finished or state.is_dnf:
                continue
            
            distance_diff = abs(state.distance - my_distance)
            if distance_diff <= radius:
                count += 1
        
        return count
    
    # =========================================================================
    # PACEMAKER SELECTION SYSTEM
    # =========================================================================
    
    def select_initial_pacemaker(self) -> str:
        """
        Select the initial pacemaker at race start.
        Typically the FR/RW with highest speed stat becomes pacemaker.
        """
        candidates = []
        
        for name, stats in self.uma_stats.items():
            effective_style = self.get_effective_running_style(stats)
            if effective_style in [RunningStyle.FR, RunningStyle.RW]:
                # Evaluate based on speed and power
                score = stats.speed * 0.7 + stats.power * 0.3
                candidates.append((name, score))
        
        if candidates:
            # Sort by score, highest first
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        # Fallback: fastest PC
        for name, stats in self.uma_stats.items():
            if stats.running_style == RunningStyle.PC:
                return name
        
        # Ultimate fallback: first uma
        return list(self.uma_stats.keys())[0] if self.uma_stats else ""
    
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

    # =========================================================================
    # NEW SYSTEMS: Slope, Blocking, Position Keep, Vision, Competition
    # =========================================================================
    
    def get_current_slope(self, distance: float, racecourse: str = "Tokyo", 
                          race_distance: int = None, surface: str = "Turf") -> float:
        """
        Get the current slope at the given race distance position.
        Uses authentic game data from COURSE_SLOPES.
        
        Args:
            distance: Current distance traveled (meters)
            racecourse: Name of racecourse
            race_distance: Total race distance (for course lookup)
            surface: "Turf" or "Dirt"
        
        Returns: slope_percent (positive = uphill, negative = downhill)
        """
        if race_distance is None:
            race_distance = int(self.race_distance)
        
        # Try to find specific course slopes
        if racecourse in COURSE_SLOPES:
            course_key = (race_distance, surface)
            if course_key in COURSE_SLOPES[racecourse]:
                slopes = COURSE_SLOPES[racecourse][course_key]
                for start_m, end_m, slope in slopes:
                    if start_m <= distance < end_m:
                        return slope
        
        # No slope data found = flat
        return 0.0
    
    def apply_slope_effects(self, uma_name: str, distance: float, 
                            racecourse: str = "Tokyo", race_distance: int = None,
                            surface: str = "Turf") -> Tuple[float, float]:
        """
        Apply slope effects to target speed and acceleration.
        
        Args:
            uma_name: Name of the Uma
            distance: Current distance traveled in meters
            racecourse: Name of racecourse (e.g., "Nakayama", "Tokyo")
            race_distance: Total race distance in meters (for course lookup)
            surface: "Turf" or "Dirt"
        
        Returns: (speed_modifier, accel_modifier)
        
        Uphill: target_speed -= 200 * slope / 10000 (per 1% slope)
        Downhill: triggers downhill accel mode (can exceed target speed)
        """
        state = self.uma_states[uma_name]
        slope = self.get_current_slope(distance, racecourse, race_distance, surface)
        
        state.current_slope_percent = slope
        speed_modifier = 0.0
        accel_modifier = 1.0
        
        if slope > 0:
            # Uphill - reduce target speed and acceleration
            state.is_on_uphill = True
            state.is_on_downhill = False
            state.is_in_downhill_accel = False
            speed_modifier = -SLOPE_SPEED_MODIFIER * slope  # Negative = slower
            accel_modifier = 0.67  # 2/3 acceleration on uphill (0.0004 vs 0.0006)
        elif slope < DOWNHILL_ACCEL_MODE_THRESHOLD:
            # Downhill steep enough for accel mode
            state.is_on_uphill = False
            state.is_on_downhill = True
            state.is_in_downhill_accel = True
            # Downhill accel mode allows exceeding target speed
            speed_modifier = DOWNHILL_ACCEL_EXTRA_SPEED  # Positive = faster allowed
            accel_modifier = 1.2  # Faster acceleration downhill
        elif slope < 0:
            # Mild downhill - slight speed benefit
            state.is_on_uphill = False
            state.is_on_downhill = True
            state.is_in_downhill_accel = False
            speed_modifier = -slope * 0.1  # Small speed benefit
        else:
            state.is_on_uphill = False
            state.is_on_downhill = False
            state.is_in_downhill_accel = False
        
        return speed_modifier, accel_modifier
    
    def check_front_blocking(self, uma_name: str) -> Tuple[bool, Optional[str], float]:
        """
        Check if Uma is front-blocked (from wiki formula).
        
        Front blocking: blocks when 0 < gap < 2m, lane gap < (1 - 0.6 * gap/2) * 0.75 horse lane
        Speed cap: (0.988 + 0.012 * gap/2) * blocker_speed
        
        Returns: (is_blocked, blocker_name, speed_cap)
        """
        state = self.uma_states[uma_name]
        
        if state.is_finished or state.is_dnf:
            return False, None, float('inf')
        
        for other_name, other_state in self.uma_states.items():
            if other_name == uma_name:
                continue
            if other_state.is_finished or other_state.is_dnf:
                continue
            
            # Check distance gap (other must be ahead)
            gap = other_state.distance - state.distance
            if not (0 < gap < FRONT_BLOCK_MAX_GAP):
                continue
            
            # Check lane gap (using proper lane position)
            lane_gap = abs(other_state.lane_position - state.lane_position)
            lane_threshold = (1.0 - 0.6 * gap / 2.0) * FRONT_BLOCK_LANE_THRESHOLD * HORSE_LANE
            
            if lane_gap < lane_threshold:
                # Blocked!
                speed_cap = (BLOCKED_SPEED_BASE + BLOCKED_SPEED_GAP_FACTOR * gap / 2.0) * other_state.current_speed
                return True, other_name, speed_cap
        
        return False, None, float('inf')
    
    def check_side_blocking(self, uma_name: str) -> Tuple[bool, bool, Optional[str]]:
        """
        Check if Uma is side-blocked (inward or outward).
        
        Side blocking: blocks when |gap| < 1.05m, lane gap < 2 horse lane
        
        Returns: (is_blocked_inward, is_blocked_outward, blocker_name)
        """
        state = self.uma_states[uma_name]
        
        if state.is_finished or state.is_dnf:
            return False, False, None
        
        blocked_in = False
        blocked_out = False
        blocker = None
        
        for other_name, other_state in self.uma_states.items():
            if other_name == uma_name:
                continue
            if other_state.is_finished or other_state.is_dnf:
                continue
            
            # Check distance gap (side blocking can be ahead or behind)
            gap = abs(other_state.distance - state.distance)
            if gap >= SIDE_BLOCK_GAP_THRESHOLD:
                continue
            
            # Check lane gap
            lane_gap = abs(other_state.lane_position - state.lane_position)
            lane_threshold = SIDE_BLOCK_LANE_THRESHOLD * HORSE_LANE
            
            if lane_gap < lane_threshold:
                blocker = other_name
                # Determine if blocking inward or outward
                if other_state.lane_position < state.lane_position:
                    blocked_in = True
                else:
                    blocked_out = True
        
        return blocked_in, blocked_out, blocker
    
    def check_overlap_bump(self, uma_name: str) -> Tuple[bool, Optional[str]]:
        """
        Check for overlapping bump (Uma too close, outer one gets bumped).
        
        Overlap bump: occurs when |gap| < 0.4m, lane gap < 0.4 horse lane
        
        Returns: (should_bump_outer, other_uma_name)
        """
        state = self.uma_states[uma_name]
        
        if state.is_finished or state.is_dnf:
            return False, None
        
        for other_name, other_state in self.uma_states.items():
            if other_name == uma_name:
                continue
            if other_state.is_finished or other_state.is_dnf:
                continue
            
            # Check distance gap
            gap = abs(other_state.distance - state.distance)
            if gap >= OVERLAP_BUMP_GAP_THRESHOLD:
                continue
            
            # Check lane gap
            lane_gap = abs(other_state.lane_position - state.lane_position)
            lane_threshold = OVERLAP_BUMP_LANE_THRESHOLD * HORSE_LANE
            
            if lane_gap < lane_threshold:
                # Bump the outer Uma
                if state.lane_position > other_state.lane_position:
                    # We're the outer one, we get bumped
                    return True, other_name
        
        return False, None
    
    def get_pacemaker_info(self, uma_name: str) -> tuple:
        """
        Get pacemaker (leader) information for position keeping.
        
        Returns:
            (pacemaker_name, pacemaker_distance, distance_to_pacemaker)
            Returns (None, 0, 0) if no valid pacemaker found.
        """
        state = self.uma_states[uma_name]
        
        if state.is_finished or state.is_dnf:
            return None, 0.0, 0.0
        
        # Find the current leader (pacemaker)
        pacemaker_name = None
        pacemaker_distance = 0.0
        
        for other_name, other_state in self.uma_states.items():
            if other_state.is_finished or other_state.is_dnf:
                continue
            if other_state.distance > pacemaker_distance:
                pacemaker_distance = other_state.distance
                pacemaker_name = other_name
        
        if pacemaker_name is None or pacemaker_name == uma_name:
            # We are the pacemaker or no others exist
            return uma_name, state.distance, 0.0
        
        distance_to_pacemaker = pacemaker_distance - state.distance
        return pacemaker_name, pacemaker_distance, distance_to_pacemaker
    
    def update_lane_position(self, uma_name: str, delta_time: float, 
                             racecourse: str = "Tokyo") -> None:
        """
        Update Uma's lane position based on movement speed and targets.
        
        Lane change speed is based on Power stat.
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return
        
        # Calculate lane change speed based on Power
        effective_power = self.get_effective_stat_with_mood(stats.power, stats.mood, 'power')
        lane_move_speed = 0.05 + (effective_power / 1200.0) * 0.1  # 0.05 to 0.15 per second
        state.lane_move_speed = lane_move_speed
        
        # Move toward target lane
        if state.lane_position < state.target_lane:
            state.lane_position = min(
                state.target_lane,
                state.lane_position + lane_move_speed * delta_time
            )
        elif state.lane_position > state.target_lane:
            state.lane_position = max(
                state.target_lane,
                state.lane_position - lane_move_speed * delta_time
            )
        
        # Check for overlap bump
        should_bump, _ = self.check_overlap_bump(uma_name)
        if should_bump:
            # Get bumped outward
            max_lane = RACECOURSE_MAX_LANES.get(racecourse, 1.2)
            state.lane_position = min(max_lane, state.lane_position + HORSE_LANE * 0.5)
    
    def update_position_keep_mode(self, uma_name: str, progress: float) -> PositionKeepMode:
        """
        Update and return the Uma's position keep mode based on wiki mechanics.
        
        PACEMAKER SYSTEM:
        - FR/RW: Try to BE the pacemaker
          - SPEED_UP: If lead < 4.5m or not 1st
          - OVERTAKE: If not 1st among same-style runners
        - Non-FR (PC/LS/EC): Follow the pacemaker
          - PACE_DOWN: If too close to pacemaker (closer than target - tolerance)
          - PACE_UP: If too far from pacemaker (farther than target + tolerance)
        - All: PACE_UP_EX if wrong strategy order detected (rare)
        
        Position keep is only active in opening and middle phases (first 2/3 of race).
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        # Position keep only active in first 2/3 of race (opening + middle)
        if progress > 0.67:
            state.position_keep_mode = PositionKeepMode.NORMAL
            return PositionKeepMode.NORMAL
        
        # Get pacemaker info
        pacemaker_name, pacemaker_distance, distance_to_pacemaker = self.get_pacemaker_info(uma_name)
        
        # Get sorted positions
        positions = sorted(
            [(n, s.distance) for n, s in self.uma_states.items()
             if not s.is_finished and not s.is_dnf],
            key=lambda x: x[1], reverse=True
        )
        
        my_rank = next((i for i, (n, _) in enumerate(positions) if n == uma_name), 0)
        total_uma = len(positions)
        
        # Wisdom affects mode transitions (higher wisdom = faster reactions)
        effective_wisdom = self.get_effective_stat_with_mood(stats.wisdom, stats.mood)
        wisdom_factor = min(1.5, effective_wisdom / 600.0)
        
        # Get effective running style (FR with Runaway skill uses RW behavior)
        effective_style = self.get_effective_running_style(stats)
        
        if effective_style in [RunningStyle.FR, RunningStyle.RW]:
            # =================================================================
            # FRONT RUNNER / RUNAWAY: Try to BE the pacemaker
            # =================================================================
            if pacemaker_name == uma_name:
                # We ARE the pacemaker
                # Check if 2nd place is too close
                if my_rank == 0 and total_uma > 1:
                    second_distance = positions[1][1]
                    lead_gap = state.distance - second_distance
                    
                    if lead_gap < FR_SPEED_UP_GAP:
                        # 2nd place too close, speed up
                        if random.random() < 0.5 * wisdom_factor:
                            state.position_keep_mode = PositionKeepMode.SPEED_UP
                        else:
                            state.position_keep_mode = PositionKeepMode.NORMAL
                    else:
                        state.position_keep_mode = PositionKeepMode.NORMAL
                else:
                    state.position_keep_mode = PositionKeepMode.NORMAL
            else:
                # We're NOT the pacemaker - need to catch up
                if distance_to_pacemaker > FR_TARGET_LEAD:
                    # Very far behind - OVERTAKE mode
                    if random.random() < 0.4 * wisdom_factor:
                        state.position_keep_mode = PositionKeepMode.OVERTAKE
                    else:
                        state.position_keep_mode = PositionKeepMode.SPEED_UP
                else:
                    # Close but not leading - SPEED_UP
                    if random.random() < 0.3 * wisdom_factor:
                        state.position_keep_mode = PositionKeepMode.SPEED_UP
                    else:
                        state.position_keep_mode = PositionKeepMode.NORMAL
        else:
            # =================================================================
            # NON-FR (PC/LS/EC): Follow the pacemaker
            # =================================================================
            target_distance = PACEMAKER_TARGET_DISTANCE.get(stats.running_style, 8.0)
            
            # Add some variance based on wisdom (smarter = more precise)
            variance = (1.0 - (wisdom_factor / 1.5)) * 2.0  # 0-2m variance
            
            if distance_to_pacemaker < target_distance - PACEMAKER_TOO_CLOSE:
                # Too CLOSE to pacemaker - slow down
                if random.random() < 0.4 * wisdom_factor:
                    state.position_keep_mode = PositionKeepMode.PACE_DOWN
                else:
                    state.position_keep_mode = PositionKeepMode.NORMAL
            elif distance_to_pacemaker > target_distance + PACEMAKER_TOO_FAR + variance:
                # Too FAR from pacemaker - speed up
                if random.random() < 0.3 * wisdom_factor:
                    state.position_keep_mode = PositionKeepMode.PACE_UP
                else:
                    state.position_keep_mode = PositionKeepMode.NORMAL
            else:
                # In good position
                state.position_keep_mode = PositionKeepMode.NORMAL
        
        # =================================================================
        # Check for wrong strategy order (Pace Up EX) - rare event
        # =================================================================
        # If a slower strategy is ahead of a faster one unexpectedly
        if my_rank > 0:  # Not first place
            ahead_name = positions[my_rank - 1][0]
            ahead_stats = self.uma_stats.get(ahead_name)
            if ahead_stats:
                # Strategy speed expectation: RW > FR > PC > LS > EC
                # Note: FR with Runaway skill is treated as RW for ordering
                style_order = {
                    RunningStyle.RW: 0, RunningStyle.FR: 1, 
                    RunningStyle.PC: 2, RunningStyle.LS: 3, RunningStyle.EC: 4
                }
                my_effective_style = self.get_effective_running_style(stats)
                ahead_effective_style = self.get_effective_running_style(ahead_name)
                my_order = style_order.get(my_effective_style, 2)
                ahead_order = style_order.get(ahead_effective_style, 2)
                
                # If we're a faster strategy (lower order) but behind a slower one
                if my_order < ahead_order - 1:  # We're 2+ faster but behind
                    if random.random() < 0.05:  # 5% chance to trigger
                        state.position_keep_mode = PositionKeepMode.PACE_UP_EX
        
        return state.position_keep_mode
    
    def update_vision_system(self, uma_name: str) -> None:
        """
        Update visible Uma list for vision-based decisions (FULLY IMPLEMENTED).
        
        Vision system is affected by:
        - Wisdom: Smart Uma see further (base 20m ± wisdom modifier)
        - Running Style: FR sees less far, LS/EC see further
        - Position: Leaders see less, back positions see more
        - Distance/Lane: Cone-based visibility check
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        state.visible_umas = []
        
        if state.is_finished or state.is_dnf:
            return
        
        # Wisdom-based vision range (15-35m range)
        effective_wisdom = self.get_effective_stat_with_mood(stats.wisdom, stats.mood)
        vision_range = VISION_DISTANCE + (effective_wisdom - 600) * 0.01
        vision_range = max(15.0, min(35.0, vision_range))
        
        # Running style affects vision focus
        vision_cone_width = 0.5
        if stats.running_style == RunningStyle.FR:
            vision_range *= 0.9  # FR: focused forward, shorter range
            vision_cone_width = 0.3  # Narrow cone
        elif stats.running_style == RunningStyle.PC:
            vision_range *= 1.0  # PC: normal vision
            vision_cone_width = 0.5
        elif stats.running_style == RunningStyle.LS:
            vision_range *= 1.1  # LS: sees behind, longer range
            vision_cone_width = 0.7
        elif stats.running_style == RunningStyle.EC:
            vision_range *= 1.15  # EC: strategic awareness
            vision_cone_width = 0.8
        
        # Position-based vision
        if state.position == 1:
            vision_range *= 0.8  # Leader less aware of threats
        elif state.position >= 6:
            vision_range *= 1.1  # Back: more strategic awareness
        
        for other_name, other_state in self.uma_states.items():
            if other_name == uma_name or other_state.is_finished or other_state.is_dnf:
                continue
            
            distance_diff = other_state.distance - state.distance
            
            if distance_diff > vision_range or distance_diff < -10.0:
                continue
            
            lane_gap = abs(other_state.lane_position - state.lane_position)
            if distance_diff > 0:
                max_lane_gap = vision_cone_width + (distance_diff / vision_range) * (1.0 - vision_cone_width)
            else:
                max_lane_gap = vision_cone_width + 0.5
            
            if lane_gap <= max_lane_gap:
                state.visible_umas.append(other_name)
        
        state.visible_distance = vision_range
        state.vision_cone_width = vision_cone_width
    
    def check_competition_systems(self, uma_name: str, progress: float, 
                                   delta_time: float) -> Tuple[float, float]:
        """
        Check and apply competition system effects.
        
        Returns: (speed_bonus, hp_save)
        
        Systems:
        - Lead Competition: FR/PC in middle/late leg compete for lead
        - Compete Before Spurt: LS/EC 2 sections before spurt
        - Secure Lead: Leader tries to maintain gap
        - Stamina Keep: Conserve when behind pacemaker
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        speed_bonus = 0.0
        hp_save = 0.0
        
        if state.is_finished or state.is_dnf:
            return speed_bonus, hp_save
        
        # Update cooldowns
        if state.lead_competition_cooldown > 0:
            state.lead_competition_cooldown -= delta_time
        if state.secure_lead_cooldown > 0:
            state.secure_lead_cooldown -= delta_time
        
        # Get leader info
        positions = sorted(
            [(n, s.distance) for n, s in self.uma_states.items()
             if not s.is_finished and not s.is_dnf],
            key=lambda x: x[1], reverse=True
        )
        
        if not positions:
            return speed_bonus, hp_save
        
        leader_name, leader_distance = positions[0]
        my_rank = next((i for i, (n, _) in enumerate(positions) if n == uma_name), 0)
        
        # Get effective running style (FR with Runaway skill uses RW behavior)
        effective_style = self.get_effective_running_style(stats)
        
        # Lead Competition: FR/PC near leader in middle/late leg
        if effective_style in [RunningStyle.FR, RunningStyle.PC, RunningStyle.RW]:
            if 1/6 <= progress < 5/6:  # Middle to late leg
                if my_rank <= 2:  # Top 3
                    distance_to_leader = leader_distance - state.distance
                    if 0 < distance_to_leader < 5.0:  # Close to leader
                        if state.lead_competition_cooldown <= 0:
                            state.is_in_lead_competition = True
                            speed_bonus += (LEAD_COMPETITION_SPEED_BONUS - 1.0) * self.base_speed
                            state.lead_competition_cooldown = LEAD_COMPETITION_COOLDOWN
        
        # Compete Before Spurt: LS/EC before spurt starts
        if stats.running_style in [RunningStyle.LS, RunningStyle.EC]:
            spurt_start = 5/6
            before_spurt_start = spurt_start - (BEFORE_SPURT_DISTANCE / self.race_distance)
            if before_spurt_start <= progress < spurt_start:
                if len(state.visible_umas) > 0:  # Can see someone to compete with
                    state.is_competing_before_spurt = True
                    speed_bonus += (BEFORE_SPURT_SPEED_BONUS - 1.0) * self.base_speed
        
        # Secure Lead: Leader maintains distance
        if my_rank == 0 and len(positions) > 1:
            second_distance = positions[1][1]
            gap = state.distance - second_distance
            if gap > SECURE_LEAD_MIN_GAP:
                if state.secure_lead_cooldown <= 0:
                    state.is_securing_lead = True
                    speed_bonus += (SECURE_LEAD_SPEED_BONUS - 1.0) * self.base_speed
                    state.secure_lead_cooldown = 2.0  # 2 second cooldown
        
        # Stamina Keep: Behind pacemaker
        if my_rank > 0:
            distance_behind = leader_distance - state.distance
            if 0 < distance_behind <= STAMINA_KEEP_MAX_BEHIND:
                state.is_stamina_keeping = True
                hp_save = STAMINA_KEEP_HP_SAVE
        
        return speed_bonus, hp_save
    
    def check_power_release(self, uma_name: str, progress: float) -> float:
        """
        Check and apply power release from conserved power.
        
        Returns: speed_bonus
        """
        state = self.uma_states[uma_name]
        
        # Power release only in final stretch
        if progress < 5/6:
            state.power_release_active = False
            return 0.0
        
        if state.conserved_power > 0:
            state.power_release_active = True
            # Use conserved power for speed boost
            speed_bonus = state.conserved_power * POWER_RELEASE_SPEED_MULT
            # Consume power over time
            state.conserved_power *= 0.95  # Decay
            return speed_bonus
        
        return 0.0
    
    def get_section_speed_random(self, uma_name: str, progress: float) -> float:
        """Get the speed random modifier for the current section."""
        state = self.uma_states[uma_name]
        section = int(progress * NUM_RACE_SECTIONS)
        section = min(section, NUM_RACE_SECTIONS - 1)
        state.current_section = section
        
        if state.section_speed_randoms:
            return state.section_speed_randoms[section]
        return 1.0

    def check_lane_blocking(self, uma_name: str) -> Tuple[bool, float]:
        """
        Check if Uma is blocked using the new wiki-accurate blocking system.
        
        Returns: (is_blocked, speed_multiplier)
        
        Uses front blocking with proper gap/lane calculations:
        - Front blocking: 0 < gap < 2m, lane gap < (1 - 0.6 * gap/2) * 0.75 horse lane
        - Speed cap: (0.988 + 0.012 * gap/2) * blocker_speed
        
        Falls back to simplified blocking if new system doesn't find blocks.
        """
        state = self.uma_states[uma_name]
        stats = self.uma_stats[uma_name]
        
        if state.is_finished or state.is_dnf:
            return False, 1.0
        
        # First, check using new wiki-accurate front blocking
        is_front_blocked, blocker_name, speed_cap = self.check_front_blocking(uma_name)
        
        if is_front_blocked and blocker_name:
            state.is_blocked = True
            state.is_front_blocked = True
            state.blocking_uma = blocker_name
            state.blocked_speed_limit = speed_cap
            
            # Calculate speed multiplier based on speed cap vs current speed
            if state.current_speed > 0:
                speed_mult = min(1.0, speed_cap / state.current_speed)
            else:
                speed_mult = 1.0
            
            # Power-based overtake attempt
            effective_power = self.get_effective_stat_with_mood(stats.power, stats.mood, 'power')
            power_factor = effective_power / 1200.0
            overtake_chance = 0.15 + (power_factor * 0.35)  # 15-50% base chance
            
            if random.random() < overtake_chance:
                # Successful push through
                state.is_blocked = False
                state.is_front_blocked = False
                state.blocking_uma = ""
                return False, 0.97  # Slight penalty for effort
            
            return True, max(0.85, speed_mult)  # Minimum 85% speed
        
        # Check side blocking
        blocked_in, blocked_out, side_blocker = self.check_side_blocking(uma_name)
        state.is_side_blocked_in = blocked_in
        state.is_side_blocked_out = blocked_out
        
        if blocked_in or blocked_out:
            # Side blocking limits lane changing, slight speed penalty
            if side_blocker:
                state.blocking_uma = side_blocker
            return False, 0.98  # Small penalty
        
        # No blocking
        state.is_blocked = False
        state.is_front_blocked = False
        state.blocking_uma = ""
        return False, 1.0
    
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
        
        # One-time race start initialization (first tick only)
        if self.current_time == 0.0:
            # Select initial pacemaker for position keep system
            pacemaker = self.select_initial_pacemaker()
            if pacemaker:
                for state in self.uma_states.values():
                    state.pace_target = pacemaker
        
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
            self.check_temptation(uma_name, progress, delta_time)  # Temptation (かかり)
            self.check_spot_struggle(uma_name)
            self.check_dueling(uma_name, delta_time)
            
            # NEW: Repositioning (位置取り調整) - mid-race positioning boost
            repositioning_bonus = self.check_repositioning(uma_name, progress, delta_time)
            
            # NEW SYSTEMS: Update lane, vision, position keep, competition
            self.update_lane_position(uma_name, delta_time)
            self.update_vision_system(uma_name)
            position_keep_mode = self.update_position_keep_mode(uma_name, progress)
            comp_speed_bonus, comp_hp_save = self.check_competition_systems(uma_name, progress, delta_time)
            power_release_bonus = self.check_power_release(uma_name, progress)
            section_speed_mult = self.get_section_speed_random(uma_name, progress)
            
            # NEW: Update coasting, accel mode, fatigue, debuffs
            self.check_coasting_activation(uma_name)
            self.update_accel_mode(uma_name, progress)
            self.update_fatigue(uma_name, delta_time)
            self.update_debuffs(uma_name, delta_time)
            
            # Get modifiers from new systems
            coasting_speed_mod, coasting_hp_mod = self.get_coasting_effects(uma_name)
            accel_mode_mods = self.get_accel_mode_modifiers(uma_name)
            fatigue_speed_mod, fatigue_accel_mod = self.get_fatigue_penalties(uma_name)
            
            # Skills system: Update terrain and check skill activations
            self.simulate_terrain(uma_name, progress)
            
            # Decrement skill check timer
            state.skill_check_timer = max(0, state.skill_check_timer - delta_time)
            
            self.check_and_activate_skills(uma_name, progress)
            skill_speed_bonus, skill_accel_bonus, skill_stamina_save = self.update_active_skills(uma_name, delta_time)
            
            # Check final spurt activation
            if self.check_final_spurt_activation(uma_name, progress):
                self.apply_final_spurt(uma_name)
            
            # Calculate speed cap (target speed)
            speed_cap = self.calculate_base_speed_cap(uma_name, phase)
            
            # Apply position keep mode modifier
            position_keep_modifier = POSITION_KEEP_SPEED_MODIFIERS.get(position_keep_mode, 1.0)
            speed_cap *= position_keep_modifier
            
            # Apply slope effects (using actual distance, not progress)
            surface = "Turf" if self.terrain == TerrainType.TURF else "Dirt"
            slope_speed_mod, slope_accel_mod = self.apply_slope_effects(
                uma_name, state.distance, self.racecourse, self.race_distance, surface
            )
            speed_cap += slope_speed_mod
            
            # Apply section speed random
            speed_cap *= section_speed_mult
            
            # NEW: Apply corner speed modifier
            speed_cap *= state.corner_speed_modifier
            
            # NEW: Apply coasting and fatigue modifiers
            speed_cap *= coasting_speed_mod
            speed_cap *= accel_mode_mods['speed']
            speed_cap *= fatigue_speed_mod
            
            # Final spurt bonus: Guts affects last spurt target speed
            # Wiki: sqrt(500 × Guts) × 0.001 bonus in Last Spurt
            if state.in_final_spurt:
                effective_guts = self.get_effective_stat_with_mood(stats.guts, stats.mood)
                guts_speed_bonus = math.sqrt(500.0 * effective_guts) * 0.001
                speed_cap += guts_speed_bonus
            
            # GameTora: Dueling bonus to speed cap
            duel_speed_bonus, duel_accel_bonus = self.get_duel_bonus(uma_name)
            speed_cap += duel_speed_bonus
            
            # Temptation (かかり): Involuntary speed boost when losing control
            temptation_speed_boost, _ = self.get_temptation_effects(uma_name)
            speed_cap += temptation_speed_boost
            
            # Skills: Add speed bonus from active skills
            # Add competition and power release bonuses
            speed_cap += comp_speed_bonus
            speed_cap += power_release_bonus
            speed_cap += skill_speed_bonus
            
            # NEW: Apply repositioning bonus multiplier (位置取り調整)
            speed_cap *= repositioning_bonus
            
            # Start dash detection: applies until speed reaches 0.85 × BaseSpeed
            # GameTora: Late starts (0.066s+) LOSE this bonus
            start_dash_threshold = 0.85 * self.base_speed
            is_start_dash = (state.current_speed < start_dash_threshold and 
                           phase == RacePhase.START and 
                           not state.is_late_start)
            
            # Calculate acceleration with start dash flag
            acceleration = self.calculate_acceleration(uma_name, phase, is_start_dash)
            
            # Apply slope acceleration modifier
            acceleration *= slope_accel_mod
            
            # GameTora: Add dueling acceleration bonus
            acceleration += duel_accel_bonus
            
            # Skills: Add acceleration bonus from active skills
            acceleration += skill_accel_bonus
            
            # NEW: Apply accel mode and fatigue modifiers to acceleration
            acceleration *= accel_mode_mods['accel']
            acceleration *= fatigue_accel_mod
            
            # Calculate minimum speed (from wiki formula)
            minimum_speed = self.calculate_minimum_speed(uma_name)
            
            # Update speed based on HP state
            if state.hp <= 0:
                # Out of HP: decelerate to minimum speed
                # Wiki: deceleration rates vary by phase (strategy-specific)
                if phase == RacePhase.START:
                    decel_rate = 1.2  # Opening phase: -1.2 m/s²
                elif phase == RacePhase.MIDDLE:
                    decel_rate = 0.8  # Middle phase: -0.8 m/s²
                else:
                    decel_rate = 1.0  # Final phase: -1.0 m/s²
                
                # Strategy affects decel rate (use effective style for FR with Runaway)
                effective_style = self.get_effective_running_style(stats)
                if effective_style in [RunningStyle.EC, RunningStyle.LS]:
                    decel_rate *= 0.9  # Slower decel for late runners
                elif effective_style in [RunningStyle.FR, RunningStyle.RW]:
                    decel_rate *= 1.1  # Faster decel for front runners
                
                if state.current_speed > minimum_speed:
                    state.current_speed = max(
                        minimum_speed,
                        state.current_speed - decel_rate * delta_time
                    )
            else:
                # Normal movement: accelerate toward target speed
                # Downhill accel mode can exceed target speed
                effective_cap = speed_cap
                if state.is_in_downhill_accel:
                    effective_cap += DOWNHILL_ACCEL_EXTRA_SPEED
                
                if state.current_speed < effective_cap:
                    state.current_speed = min(
                        effective_cap,
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
                
                # Uphill increases HP drain
                if state.is_on_uphill:
                    hp_drain *= 1.1 + abs(state.current_slope_percent) * 0.1
                
                # Coasting HP modifier (reduces drain when coasting)
                hp_drain *= coasting_hp_mod
                
                # Acceleration mode HP modifier
                hp_drain *= accel_mode_mods['hp']
                
                # Skills: Apply stamina save reduction from active skills
                if skill_stamina_save > 0:
                    hp_drain *= (1.0 - skill_stamina_save)
                
                # Competition system stamina keep
                if comp_hp_save > 0:
                    hp_drain *= (1.0 - comp_hp_save)
                
                # Stamina limit break bonus (reduces HP drain)
                if state.stamina_limit_break_bonus > 0:
                    hp_drain *= (1.0 - state.stamina_limit_break_bonus * 0.5)
                
                state.hp = max(0.0, state.hp - hp_drain * delta_time)
            
            # Update fatigue (cumulative tracker for UI)
            state.fatigue = (1.0 - state.hp / state.max_hp) * 100.0
            
            # Check for finish with precise timing
            if state.distance >= self.race_distance and not state.is_finished:
                state.is_finished = True
                # Calculate exact finish time by interpolation
                overshoot = state.distance - self.race_distance
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
    # Note: RW (Runaway) is kept for backwards compatibility with old configs.
    # New configs should use FR with Runaway skill instead.
    style_str = uma_dict.get('running_style', 'PC').upper()
    style_map = {'FR': RunningStyle.FR, 'PC': RunningStyle.PC, 
                 'LS': RunningStyle.LS, 'EC': RunningStyle.EC,
                 'RW': RunningStyle.RW}
    running_style = style_map.get(style_str, RunningStyle.PC)
    
    # Get aptitudes
    dist_apt = uma_dict.get('distance_aptitude', {})
    surf_apt = uma_dict.get('surface_aptitude', {})
    
    # Get skills (list of skill IDs)
    skills = uma_dict.get('skills', [])
    
    # Parse mood
    mood_str = uma_dict.get('mood', 'Normal').upper()
    mood_map = {
        'AWFUL': Mood.AWFUL,
        'BAD': Mood.BAD,
        'NORMAL': Mood.NORMAL,
        'GOOD': Mood.GOOD,
        'GREAT': Mood.GREAT,
    }
    mood = mood_map.get(mood_str, Mood.NORMAL)
    
    # Get gate number (1-18, default 1)
    gate_number = uma_dict.get('gate_number', 1)
    if not isinstance(gate_number, int) or gate_number < 1:
        gate_number = 1
    if gate_number > 18:
        gate_number = 18
    
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
        mood=mood,
        gate_number=gate_number,
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
