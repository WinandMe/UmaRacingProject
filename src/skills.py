"""
Uma Musume Skill System
=======================
Based on GameTora Global version skills.
https://gametora.com/umamusume/skills

Skill Effects (from GameTora race-mechanics):
- Speed/Velocity skills: Increase Target Speed (m/s)
- Acceleration skills: Increase acceleration rate (m/s²)  
- Recovery skills: Recover HP as percentage of max HP
- Stamina drain skills: Increase/decrease HP consumption

Effect Magnitudes (approximate from GameTora):
- "Slightly" = ~0.15-0.25 m/s speed, ~0.1-0.2 m/s² accel, ~1.5% recovery
- "Moderately" = ~0.25-0.35 m/s speed, ~0.2-0.4 m/s² accel, ~3.5% recovery  
- "Increase" (gold) = ~0.35-0.45 m/s speed, ~0.4-0.6 m/s² accel, ~5.5% recovery
- "Greatly" = ~0.45-0.65 m/s speed, ~0.6-0.8 m/s² accel, ~7.5% recovery

Duration (from GameTora):
- Short = ~1.2-1.8 seconds
- Medium = ~2.4-3.0 seconds  
- Long = ~3.6-5.0 seconds
- Very Long = ~5.0+ seconds
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Callable, Set


class SkillRarity(Enum):
    """Skill rarity levels"""
    WHITE = "white"       # Common/Normal skills (◯)
    GOLD = "gold"         # Rare/Gold skills (◎)
    UNIQUE = "unique"     # Character-specific unique skills
    EVOLUTION = "evolution"  # Evolved unique skills


class SkillTriggerPhase(Enum):
    """Race phases for skill activation"""
    ANY = "any"
    EARLY = "early"           # 0-1/6 of race
    MID = "mid"               # 1/6-4/6 of race  
    LATE = "late"             # 4/6-5/6 of race
    LAST_SPURT = "last_spurt" # 5/6-6/6 of race
    SECOND_HALF = "second_half"  # 3/6+ of race


class SkillTriggerPosition(Enum):
    """Position conditions for skill activation"""
    ANY = "any"
    FRONT = "front"           # Top 25% of runners
    MIDPACK = "midpack"       # Middle 50% of runners
    BACK = "back"             # Bottom 25% of runners


class SkillTriggerTerrain(Enum):
    """Terrain conditions for skill activation"""
    ANY = "any"
    STRAIGHT = "straight"
    CORNER = "corner"
    UPHILL = "uphill"
    DOWNHILL = "downhill"


class SkillEffectType(Enum):
    """Types of skill effects"""
    SPEED = "speed"                   # Increase Target Speed
    CURRENT_SPEED = "current_speed"   # Immediate speed boost (no accel needed)
    ACCELERATION = "acceleration"     # Increase acceleration rate
    RECOVERY = "recovery"             # Recover HP percentage
    STAMINA_SAVE = "stamina_save"     # Reduce HP consumption
    DEBUFF_SPEED = "debuff_speed"     # Decrease others' speed
    VISION = "vision"                 # Increase field of view (navigation)
    START_BONUS = "start_bonus"       # Reduce start delay


class RunningStyleRequirement(Enum):
    """Running style requirements for skills"""
    ANY = "any"
    FR = "FR"      # Front Runner only
    PC = "PC"      # Pace Chaser only
    LS = "LS"      # Late Surger only
    EC = "EC"      # End Closer only


class RaceTypeRequirement(Enum):
    """Race distance type requirements"""
    ANY = "any"
    SPRINT = "Sprint"
    MILE = "Mile"
    MEDIUM = "Medium"
    LONG = "Long"


@dataclass
class SkillEffect:
    """A single effect component of a skill"""
    effect_type: SkillEffectType
    value: float              # Effect magnitude
    duration: float = 3.0     # Duration in seconds (0 = instant)
    

@dataclass  
class SkillCondition:
    """Activation conditions for a skill"""
    phase: SkillTriggerPhase = SkillTriggerPhase.ANY
    position: SkillTriggerPosition = SkillTriggerPosition.ANY
    terrain: SkillTriggerTerrain = SkillTriggerTerrain.ANY
    running_style: RunningStyleRequirement = RunningStyleRequirement.ANY
    race_type: RaceTypeRequirement = RaceTypeRequirement.ANY
    # Special conditions
    requires_challenge: bool = False      # Engaged in a challenge/duel
    requires_passing: bool = False        # Passing another runner
    requires_blocked: bool = False        # Way ahead is blocked
    requires_overtaken: bool = False      # Being passed by another
    min_hp_percent: float = 0.0           # Minimum HP required
    remaining_distance: Optional[float] = None  # Specific distance remaining (e.g., 200m)
    # Section-based triggers (NEW)
    section_start: Optional[int] = None   # Trigger at section N (1-24)
    section_end: Optional[int] = None     # End trigger at section N
    corner_number: Optional[int] = None   # Specific corner (4 = final corner)


@dataclass
class Skill:
    """Definition of a skill"""
    id: str                              # Unique skill identifier
    name: str                            # Display name
    description: str                     # Skill description
    rarity: SkillRarity                  # Skill rarity
    effects: List[SkillEffect]           # List of effects
    condition: SkillCondition            # Activation conditions
    activation_chance: float = 1.0       # Base activation chance (affected by Wit)
    cooldown: float = 0.0                # Cooldown between activations
    icon: str = "⚡"                      # Display icon/emoji
    # Skill classification (NEW)
    is_unique: bool = False              # True for unique skills (固有スキル) - always 100% activation
    is_inherited: bool = False           # True for inherited skills (継承スキル) - +5% activation bonus
    is_evolved: bool = False             # True for evolved/awakened skills (進化スキル)
    evolved_from: Optional[str] = None   # Original skill ID this evolved from
    uma_specific: Optional[str] = None   # Uma name if this is their unique skill


@dataclass
class ActiveSkill:
    """Runtime state for an active skill effect"""
    skill: Skill
    remaining_duration: float
    effects_applied: bool = False


# =============================================================================
# SKILL CLASSIFICATION CONSTANTS
# =============================================================================

# Unique skills (固有スキル) - Character-specific, always activate when conditions met
UNIQUE_SKILL_ACTIVATION_RATE = 1.0        # 100% activation rate
UNIQUE_SKILL_EFFECT_MULTIPLIER = 1.2      # 20% stronger effects

# Inherited skills (継承スキル) - From parents, slight activation bonus
INHERITED_SKILL_ACTIVATION_BONUS = 0.05   # +5% activation rate
INHERITED_SKILL_EFFECT_MULTIPLIER = 1.0   # Normal effects

# Evolved skills (進化スキル/覚醒スキル) - Upgraded versions
EVOLVED_SKILL_EFFECT_MULTIPLIER = 1.5     # 50% stronger effects
EVOLVED_SKILL_DURATION_MULTIPLIER = 1.3   # 30% longer duration


# =============================================================================
# SKILL DATABASE - Global Version Only
# =============================================================================
# Organized by category following GameTora structure

SKILLS_DATABASE: Dict[str, Skill] = {}


def register_skill(skill: Skill) -> Skill:
    """Register a skill in the database"""
    SKILLS_DATABASE[skill.id] = skill
    return skill


def get_skill_activation_modifier(skill: Skill) -> float:
    """Get activation rate modifier based on skill classification"""
    if skill.is_unique:
        return UNIQUE_SKILL_ACTIVATION_RATE
    if skill.is_inherited:
        return INHERITED_SKILL_ACTIVATION_BONUS
    return 0.0


def get_skill_effect_modifier(skill: Skill) -> float:
    """Get effect multiplier based on skill classification"""
    if skill.is_evolved:
        return EVOLVED_SKILL_EFFECT_MULTIPLIER
    if skill.is_unique:
        return UNIQUE_SKILL_EFFECT_MULTIPLIER
    return 1.0


def get_skill_duration_modifier(skill: Skill) -> float:
    """Get duration multiplier based on skill classification"""
    if skill.is_evolved:
        return EVOLVED_SKILL_DURATION_MULTIPLIER
    return 1.0


# -----------------------------------------------------------------------------
# SPEED/VELOCITY SKILLS - Increase Target Speed
# -----------------------------------------------------------------------------

# Straightaway Skills
register_skill(Skill(
    id="straightaway_adept",
    name="Straightaway Adept",
    description="Slightly increase velocity on a straight.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.STRAIGHT),
    icon="➡️"
))

register_skill(Skill(
    id="beeline_burst",
    name="Beeline Burst", 
    description="Increase velocity on a straight.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.STRAIGHT),
    icon="⚡"
))

# Corner Skills
register_skill(Skill(
    id="corner_adept",
    name="Corner Adept",
    description="Slightly increase velocity on a corner with skilled turning.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.CORNER),
    icon="↩️"
))

register_skill(Skill(
    id="professor_of_curvature",
    name="Professor of Curvature",
    description="Increase velocity on a corner with skilled turning.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.CORNER),
    icon="🔄"
))

# Homestretch/Last Spurt Skills
register_skill(Skill(
    id="homestretch_haste",
    name="Homestretch Haste",
    description="Slightly increase velocity in the last spurt.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="🏁"
))

register_skill(Skill(
    id="in_body_and_mind",
    name="In Body and Mind",
    description="Increase velocity in the last spurt.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="💪"
))

# Passing/Overtake Skills
register_skill(Skill(
    id="ramp_up",
    name="Ramp Up",
    description="Slightly increase velocity when passing another runner mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID, requires_passing=True),
    icon="📈"
))

register_skill(Skill(
    id="its_on",
    name="It's On!",
    description="Increase velocity when passing another runner mid-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID, requires_passing=True),
    icon="🔥"
))

# Downhill Skills
register_skill(Skill(
    id="downhill_speedster",
    name="Downhill Speedster",
    description="Slightly increase velocity on downhills.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.DOWNHILL),
    icon="⬇️"
))

# -----------------------------------------------------------------------------
# RUNNING STYLE SPECIFIC SPEED SKILLS
# -----------------------------------------------------------------------------

# Front Runner Skills
register_skill(Skill(
    id="fast_paced",
    name="Fast-Paced",
    description="Slightly increase ability to go to the front mid-race. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.FR
    ),
    icon="🏃"
))

register_skill(Skill(
    id="escape_artist",
    name="Escape Artist",
    description="Increase ability to go to the front mid-race. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.FR
    ),
    icon="💨"
))

# Pace Chaser Skills
register_skill(Skill(
    id="prepared_to_pass",
    name="Prepared to Pass",
    description="Slightly increase ability to break out of the pack on the final corner. (Pace Chaser)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.PC
    ),
    icon="🎯"
))

register_skill(Skill(
    id="speed_star",
    name="Speed Star",
    description="Increase ability to break out of the pack on the final corner. (Pace Chaser)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.PC
    ),
    icon="⭐"
))

# Late Surger Skills
register_skill(Skill(
    id="position_pilfer",
    name="Position Pilfer",
    description="Slightly increase velocity mid-race. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.LS
    ),
    icon="📍"
))

register_skill(Skill(
    id="fast_and_furious",
    name="Fast & Furious",
    description="Increase velocity mid-race. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.LS
    ),
    icon="🔥"
))

register_skill(Skill(
    id="outer_swell",
    name="Outer Swell",
    description="Slightly increase velocity when passing another runner on the outside on the final corner. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.LS,
        requires_passing=True
    ),
    icon="↗️"
))

register_skill(Skill(
    id="rising_dragon",
    name="Rising Dragon",
    description="Increase velocity when passing another runner on the outside on the final corner. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.LS,
        requires_passing=True
    ),
    icon="🐉"
))

# End Closer Skills
register_skill(Skill(
    id="masterful_gambit",
    name="Masterful Gambit",
    description="Slightly move up in preparation to close the gap when positioned toward the back late-race. (End Closer)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.EC
    ),
    icon="♟️"
))

register_skill(Skill(
    id="sturm_und_drang",
    name="Sturm und Drang",
    description="Move up in preparation to close the gap when positioned toward the back late-race. (End Closer)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.EC
    ),
    icon="⛈️"
))

# -----------------------------------------------------------------------------
# RACE DISTANCE SPECIFIC SPEED SKILLS
# -----------------------------------------------------------------------------

# Sprint Skills
register_skill(Skill(
    id="sprint_straightaways_white",
    name="Sprint Straightaways",
    description="Slightly increase velocity on a straight. (Sprint)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="💨"
))

register_skill(Skill(
    id="sprint_straightaways_gold",
    name="Sprint Straightaways",
    description="Moderately increase velocity on a straight. (Sprint)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="💨"
))

register_skill(Skill(
    id="sprint_corners_white",
    name="Sprint Corners",
    description="Slightly increase velocity on a corner. (Sprint)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="↩️"
))

register_skill(Skill(
    id="sprint_corners_gold",
    name="Sprint Corners",
    description="Moderately increase velocity on a corner. (Sprint)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="↩️"
))

register_skill(Skill(
    id="huge_lead",
    name="Huge Lead",
    description="Slightly increase ability to maintain the lead when leading by a large margin mid-race. (Sprint)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="👑"
))

register_skill(Skill(
    id="staggering_lead",
    name="Staggering Lead",
    description="Increase ability to maintain the lead when leading by a large margin mid-race. (Sprint)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="👑"
))

register_skill(Skill(
    id="light_as_a_feather",
    name="Light as a Feather",
    description="Slightly increase velocity when positioned toward the front upon approaching late-race. (Sprint)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="🪶"
))

register_skill(Skill(
    id="in_high_spirits",
    name="In High Spirits",
    description="Increase velocity when positioned toward the front upon approaching late-race. (Sprint)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="✨"
))

register_skill(Skill(
    id="gap_closer",
    name="Gap Closer",
    description="Slightly increase spurting ability when positioned toward the back late-race. (Sprint)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="🎯"
))

register_skill(Skill(
    id="blinding_flash",
    name="Blinding Flash",
    description="Increase spurting ability when positioned toward the back late-race. (Sprint)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="⚡"
))

# Mile Skills
register_skill(Skill(
    id="mile_straightaways_white",
    name="Mile Straightaways",
    description="Slightly increase velocity on a straight. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="💨"
))

register_skill(Skill(
    id="mile_straightaways_gold",
    name="Mile Straightaways",
    description="Moderately increase velocity on a straight. (Mile)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="💨"
))

register_skill(Skill(
    id="mile_corners_white",
    name="Mile Corners",
    description="Slightly increase velocity on a corner. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="↩️"
))

register_skill(Skill(
    id="mile_corners_gold",
    name="Mile Corners",
    description="Moderately increase velocity on a corner. (Mile)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="↩️"
))

register_skill(Skill(
    id="shifting_gears",
    name="Shifting Gears",
    description="Slightly increase passing ability when positioned toward the front mid-race. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="⚙️"
))

register_skill(Skill(
    id="changing_gears",
    name="Changing Gears",
    description="Increase passing ability when positioned toward the front mid-race. (Mile)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="⚙️"
))

register_skill(Skill(
    id="unyielding_spirit",
    name="Unyielding Spirit",
    description="Slightly increase passing ability. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        race_type=RaceTypeRequirement.MILE
    ),
    icon="💪"
))

register_skill(Skill(
    id="big_sisterly",
    name="Big-Sisterly",
    description="Increase passing ability. (Mile)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        race_type=RaceTypeRequirement.MILE
    ),
    icon="👭"
))

register_skill(Skill(
    id="pumped",
    name="Pumped",
    description="When positioned toward the back on the final corner, slightly increase velocity. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="💥"
))

register_skill(Skill(
    id="full_of_vigor",
    name="Full of Vigor",
    description="When positioned toward the back on the final corner, increase velocity. (Mile)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="💥"
))

register_skill(Skill(
    id="productive_plan",
    name="Productive Plan",
    description="Slightly widen the margin when positioned toward the front early-race. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="📋"
))

register_skill(Skill(
    id="mile_maven",
    name="Mile Maven",
    description="Widen the margin when positioned toward the front early-race. (Mile)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="🏆"
))

# Medium Skills
register_skill(Skill(
    id="medium_straightaways_white",
    name="Medium Straightaways",
    description="Slightly increase velocity on a straight. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="💨"
))

register_skill(Skill(
    id="medium_straightaways_gold",
    name="Medium Straightaways",
    description="Moderately increase velocity on a straight. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="💨"
))

register_skill(Skill(
    id="medium_corners_white",
    name="Medium Corners",
    description="Slightly increase velocity on a corner. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="↩️"
))

register_skill(Skill(
    id="medium_corners_gold",
    name="Medium Corners",
    description="Moderately increase velocity on a corner. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="↩️"
))

register_skill(Skill(
    id="steadfast",
    name="Steadfast",
    description="Slightly increase ability to fight back when passed by another runner on the final corner. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.MEDIUM,
        requires_overtaken=True
    ),
    icon="🛡️"
))

register_skill(Skill(
    id="unyielding",
    name="Unyielding",
    description="Increase ability to fight back when passed by another runner on the final corner. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.MEDIUM,
        requires_overtaken=True
    ),
    icon="🛡️"
))

register_skill(Skill(
    id="flash_forward",
    name="Flash Forward",
    description="Increase velocity on a straight. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="⚡"
))

register_skill(Skill(
    id="refraction_arc",
    name="Refraction Arc",
    description="Increase velocity on corners. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🌈"
))

register_skill(Skill(
    id="all_i_ve_got",
    name="All I've Got",
    description="Slightly increase velocity when well-positioned on a straight in the last spurt. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="💯"
))

register_skill(Skill(
    id="come_what_may",
    name="Come What May",
    description="Increase velocity when well-positioned on a straight in the last spurt. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="✨"
))

register_skill(Skill(
    id="eager",
    name="Eager",
    description="When positioned toward the back mid-race, slightly increase velocity. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🔥"
))

register_skill(Skill(
    id="elated",
    name="Elated",
    description="When positioned toward the back mid-race, increase velocity. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🔥"
))

register_skill(Skill(
    id="fighting_spirit",
    name="Fighting Spirit",
    description="When engaged in a challenge midpack mid-race, very slightly recover endurance and slightly increase velocity. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[
        SkillEffect(SkillEffectType.RECOVERY, 0.01, 0),
        SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.MIDPACK,
        race_type=RaceTypeRequirement.MEDIUM,
        requires_challenge=True
    ),
    icon="🥊"
))

register_skill(Skill(
    id="burning_soul",
    name="Burning Soul",
    description="When engaged in a challenge midpack mid-race, moderately recover endurance and moderately increase velocity. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.RECOVERY, 0.035, 0),
        SkillEffect(SkillEffectType.SPEED, 0.25, 2.4)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.MIDPACK,
        race_type=RaceTypeRequirement.MEDIUM,
        requires_challenge=True
    ),
    icon="🥊"
))

register_skill(Skill(
    id="with_all_my_soul",
    name="With All My Soul",
    description="When positioned toward the front mid-race, slightly increase velocity and minimally decrease the velocity of runners behind. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="❤️"
))

register_skill(Skill(
    id="wild_wind",
    name="Wild Wind",
    description="When positioned toward the front mid-race, increase velocity and slightly decrease the velocity of runners behind. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="💨"
))

register_skill(Skill(
    id="up_tempo",
    name="Up-Tempo",
    description="Slightly increase positioning ability when positioned toward the front mid-race. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🎵"
))

register_skill(Skill(
    id="killer_tunes",
    name="Killer Tunes",
    description="Increase positioning ability when positioned toward the front mid-race. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🎸"
))

# Long Skills
register_skill(Skill(
    id="long_straightaways_white",
    name="Long Straightaways",
    description="Slightly increase velocity on a straight. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="💨"
))

register_skill(Skill(
    id="long_straightaways_gold",
    name="Long Straightaways",
    description="Moderately increase velocity on a straight. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="💨"
))

register_skill(Skill(
    id="long_corners_white",
    name="Long Corners",
    description="Slightly increase velocity on a corner. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="↩️"
))

register_skill(Skill(
    id="long_corners_gold",
    name="Long Corners",
    description="Moderately increase velocity on a corner. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="↩️"
))

register_skill(Skill(
    id="blast_forward",
    name="Blast Forward",
    description="Increase velocity on a straight. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="💥"
))

register_skill(Skill(
    id="feature_act",
    name="Feature Act",
    description="Slightly increase velocity when positioned toward the front upon approaching late-race. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="🎬"
))

register_skill(Skill(
    id="headliner",
    name="Headliner",
    description="Increase velocity when positioned toward the front upon approaching late-race. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="⭐"
))

register_skill(Skill(
    id="keeping_the_lead",
    name="Keeping the Lead",
    description="Slightly increase ability to maintain the lead when leading by a fair margin mid-race. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.6)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="👑"
))

register_skill(Skill(
    id="vanguard_spirit",
    name="Vanguard Spirit",
    description="Increase ability to maintain the lead when leading by a fair margin mid-race. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.6)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="⚔️"
))

register_skill(Skill(
    id="pressure",
    name="Pressure",
    description="Slightly increase velocity when passing another runner late-race. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        race_type=RaceTypeRequirement.LONG,
        requires_passing=True
    ),
    icon="💢"
))

register_skill(Skill(
    id="overwhelming_pressure",
    name="Overwhelming Pressure",
    description="Increase velocity when passing another runner late-race. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        race_type=RaceTypeRequirement.LONG,
        requires_passing=True
    ),
    icon="🔥"
))

register_skill(Skill(
    id="inside_scoop",
    name="Inside Scoop",
    description="Slightly increase velocity when near the inner rail on the final corner. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="🎢"
))

register_skill(Skill(
    id="innate_experience",
    name="Innate Experience",
    description="Increase velocity when near the inner rail on the final corner. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="🧠"
))

# Running Style Straightaways/Corners
register_skill(Skill(
    id="front_runner_straightaways_white",
    name="Front Runner Straightaways",
    description="Slightly increase velocity on a straight. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.FR
    ),
    icon="💨"
))

register_skill(Skill(
    id="front_runner_straightaways_gold",
    name="Front Runner Straightaways",
    description="Moderately increase velocity on a straight. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.FR
    ),
    icon="💨"
))

register_skill(Skill(
    id="front_runner_corners_white",
    name="Front Runner Corners",
    description="Slightly increase velocity on a corner. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.FR
    ),
    icon="↩️"
))

register_skill(Skill(
    id="front_runner_corners_gold",
    name="Front Runner Corners",
    description="Moderately increase velocity on a corner. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.FR
    ),
    icon="↩️"
))

register_skill(Skill(
    id="leader_s_pride",
    name="Leader's Pride",
    description="Slightly increase ability to pass or challenge another runner early-race or mid-race. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.FR
    ),
    icon="👑"
))

register_skill(Skill(
    id="top_runner",
    name="Top Runner",
    description="Increase ability to pass or challenge another runner early-race or mid-race. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.FR
    ),
    icon="👑"
))

register_skill(Skill(
    id="pace_chaser_straightaways_white",
    name="Pace Chaser Straightaways",
    description="Slightly increase velocity on a straight. (Pace Chaser)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.PC
    ),
    icon="💨"
))

register_skill(Skill(
    id="pace_chaser_straightaways_gold",
    name="Pace Chaser Straightaways",
    description="Moderately increase velocity on a straight. (Pace Chaser)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.PC
    ),
    icon="💨"
))

register_skill(Skill(
    id="pace_chaser_corners_white",
    name="Pace Chaser Corners",
    description="Slightly increase velocity on a corner. (Pace Chaser)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.PC
    ),
    icon="↩️"
))

register_skill(Skill(
    id="pace_chaser_corners_gold",
    name="Pace Chaser Corners",
    description="Moderately increase velocity on a corner. (Pace Chaser)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.PC
    ),
    icon="↩️"
))

register_skill(Skill(
    id="late_surger_straightaways_white",
    name="Late Surger Straightaways",
    description="Slightly increase velocity on a straight. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.LS
    ),
    icon="💨"
))

register_skill(Skill(
    id="late_surger_straightaways_gold",
    name="Late Surger Straightaways",
    description="Moderately increase velocity on a straight. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.LS
    ),
    icon="💨"
))

register_skill(Skill(
    id="late_surger_corners_white",
    name="Late Surger Corners",
    description="Slightly increase velocity on a corner. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.LS
    ),
    icon="↩️"
))

register_skill(Skill(
    id="late_surger_corners_gold",
    name="Late Surger Corners",
    description="Moderately increase velocity on a corner. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.LS
    ),
    icon="↩️"
))

register_skill(Skill(
    id="1_500_000_cc",
    name="1,500,000 CC",
    description="Slightly increase velocity on an uphill. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.UPHILL,
        running_style=RunningStyleRequirement.LS
    ),
    icon="⛰️"
))

register_skill(Skill(
    id="15_000_000_cc",
    name="15,000,000 CC",
    description="Increase velocity on an uphill. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.UPHILL,
        running_style=RunningStyleRequirement.LS
    ),
    icon="⛰️"
))

register_skill(Skill(
    id="fearless",
    name="Fearless",
    description="When positioned in the midpack during the second half of the race, slightly increase velocity and very minimally increase acceleration. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.15, 3.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.05, 3.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.MIDPACK,
        running_style=RunningStyleRequirement.LS
    ),
    icon="💪"
))

register_skill(Skill(
    id="dauntless",
    name="Dauntless",
    description="When positioned in the midpack during the second half of the race, increase velocity and very slightly increase acceleration. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.35, 3.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.1, 3.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.MIDPACK,
        running_style=RunningStyleRequirement.LS
    ),
    icon="💪"
))

register_skill(Skill(
    id="full_throttle",
    name="Full Throttle",
    description="Greatly consume endurance mid-race and moderately increase velocity. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.LS
    ),
    icon="⚡"
))

register_skill(Skill(
    id="keep_going",
    name="Keep Going!",
    description="Greatly consume endurance mid-race and greatly increase velocity. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.LS
    ),
    icon="⚡"
))

register_skill(Skill(
    id="end_closer_straightaways_white",
    name="End Closer Straightaways",
    description="Slightly increase velocity on a straight. (End Closer)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.EC
    ),
    icon="💨"
))

register_skill(Skill(
    id="end_closer_straightaways_gold",
    name="End Closer Straightaways",
    description="Moderately increase velocity on a straight. (End Closer)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.EC
    ),
    icon="💨"
))

register_skill(Skill(
    id="end_closer_corners_white",
    name="End Closer Corners",
    description="Slightly increase velocity on a corner. (End Closer)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.EC
    ),
    icon="↩️"
))

register_skill(Skill(
    id="end_closer_corners_gold",
    name="End Closer Corners",
    description="Moderately increase velocity on a corner. (End Closer)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.EC
    ),
    icon="↩️"
))

register_skill(Skill(
    id="moonlit_flash",
    name="Moonlit Flash",
    description="Increase velocity on straights. (End Closer)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.EC
    ),
    icon="🌙"
))

register_skill(Skill(
    id="early_start",
    name="Early Start",
    description="Very slightly increase velocity for a medium duration when positioned toward the back mid-race. (End Closer)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.1, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.EC
    ),
    icon="🏁"
))

register_skill(Skill(
    id="daring_strike",
    name="Daring Strike",
    description="Moderately increase velocity for a medium duration when positioned toward the back mid-race. (End Closer)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.EC
    ),
    icon="⚔️"
))

# Misc Speed Skills
register_skill(Skill(
    id="superstan",
    name="Superstan",
    description="Increase velocity when close to many runners.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(position=SkillTriggerPosition.MIDPACK),
    icon="⭐"
))

register_skill(Skill(
    id="tail_nine",
    name="Tail Nine",
    description="Increase velocity after activating many skills mid-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="9️⃣"
))

register_skill(Skill(
    id="dream_run",
    name="Dream Run",
    description="Increase velocity on the final straight due to a strong desire to cross the finish line.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="✨"
))

register_skill(Skill(
    id="see_ya_later",
    name="See Ya Later!",
    description="Increase velocity when followed by another runner directly behind for a long time.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(),
    icon="👋"
))

register_skill(Skill(
    id="risky_business",
    name="Risky Business",
    description="Moderately increase velocity in the second half of the race, but also greatly increase fatigue sometimes.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.SECOND_HALF),
    icon="🎲"
))

register_skill(Skill(
    id="nothing_ventured",
    name="Nothing Ventured",
    description="Greatly increase velocity in the second half of the race, but also greatly increase fatigue sometimes.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.SECOND_HALF),
    icon="🎲"
))

# -----------------------------------------------------------------------------
# ACCELERATION SKILLS
# -----------------------------------------------------------------------------

register_skill(Skill(
    id="straightaway_acceleration",
    name="Straightaway Acceleration",
    description="Slightly increase acceleration on a straight.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.1, 3.0)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.STRAIGHT),
    icon="⚡"
))

register_skill(Skill(
    id="rushing_gale",
    name="Rushing Gale!",
    description="Increase acceleration on a straight.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.3, 3.0)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.STRAIGHT),
    icon="🌪️"
))

register_skill(Skill(
    id="corner_acceleration",
    name="Corner Acceleration",
    description="Slightly increase acceleration on a corner with masterful turning.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.1, 2.4)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.CORNER),
    icon="↩️"
))

register_skill(Skill(
    id="corner_connoisseur",
    name="Corner Connoisseur",
    description="Increase acceleration on a corner with masterful turning.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.3, 2.4)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.CORNER),
    icon="🎯"
))

# Running Style Specific Acceleration
register_skill(Skill(
    id="early_lead",
    name="Early Lead",
    description="Slightly increase ability to go to the front early-race. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        running_style=RunningStyleRequirement.FR
    ),
    icon="🏃"
))

register_skill(Skill(
    id="taking_the_lead",
    name="Taking the Lead",
    description="Increase ability to go to the front early-race. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.4, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        running_style=RunningStyleRequirement.FR
    ),
    icon="👑"
))

register_skill(Skill(
    id="final_push",
    name="Final Push",
    description="Slightly increase ability to keep the lead on the final corner. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.1, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.FR
    ),
    icon="💪"
))

register_skill(Skill(
    id="unrestrained",
    name="Unrestrained",
    description="Increase ability to keep the lead on the final corner. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.3, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        running_style=RunningStyleRequirement.FR
    ),
    icon="🔓"
))

register_skill(Skill(
    id="slick_surge",
    name="Slick Surge",
    description="Slightly increase acceleration late-race. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.LS
    ),
    icon="📈"
))

register_skill(Skill(
    id="on_your_left",
    name="On Your Left!",
    description="Increase acceleration late-race. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.4, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.LS
    ),
    icon="⬅️"
))

register_skill(Skill(
    id="straightaway_spurt",
    name="Straightaway Spurt",
    description="Slightly increase acceleration on a straight in the last spurt. (End Closer)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.EC
    ),
    icon="💨"
))

register_skill(Skill(
    id="encroaching_shadow",
    name="Encroaching Shadow",
    description="Increase acceleration on a straight in the last spurt. (End Closer)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.4, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT,
        running_style=RunningStyleRequirement.EC
    ),
    icon="👤"
))

# Race Type Specific Acceleration
register_skill(Skill(
    id="sprinting_gear",
    name="Sprinting Gear",
    description="Slightly increase acceleration on a straight. (Sprint)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="⚙️"
))

register_skill(Skill(
    id="turbo_sprint",
    name="Turbo Sprint",
    description="Increase acceleration on a straight. (Sprint)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.4, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="🚀"
))

register_skill(Skill(
    id="countermeasure",
    name="Countermeasure",
    description="Slightly increase passing ability when positioned toward the front upon approaching late-race. (Sprint)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="🛡️"
))

register_skill(Skill(
    id="plan_x",
    name="Plan X",
    description="Increase passing ability when positioned toward the front upon approaching late-race. (Sprint)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.4, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="❌"
))

register_skill(Skill(
    id="acceleration",
    name="Acceleration",
    description="Slightly increase acceleration when passing another runner mid-race. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        race_type=RaceTypeRequirement.MILE,
        requires_passing=True
    ),
    icon="⚡"
))

register_skill(Skill(
    id="step_on_the_gas",
    name="Step on the Gas!",
    description="Increase acceleration when passing another runner mid-race. (Mile)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.4, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        race_type=RaceTypeRequirement.MILE,
        requires_passing=True
    ),
    icon="⚡"
))

register_skill(Skill(
    id="updrafters",
    name="Updrafters",
    description="Slightly increase passing ability when positioned toward the back late-race. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="⬆️"
))

register_skill(Skill(
    id="furious_feat",
    name="Furious Feat",
    description="Increase passing ability when positioned toward the back late-race. (Mile)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.4, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="🔥"
))

register_skill(Skill(
    id="take_the_chance",
    name="Take the Chance",
    description="If positioned toward the back late-race, slightly increase acceleration. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🎯"
))

register_skill(Skill(
    id="from_the_brink",
    name="From the Brink",
    description="If positioned toward the back late-race, increase acceleration. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.4, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🎯"
))

# Running Style Specific Acceleration
register_skill(Skill(
    id="second_wind",
    name="Second Wind",
    description="Slightly increase acceleration when not in the lead mid-race. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.FR
    ),
    icon="💨"
))

register_skill(Skill(
    id="reignition",
    name="Reignition",
    description="Increase acceleration when not in the lead mid-race. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.4, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.FR
    ),
    icon="🔥"
))

register_skill(Skill(
    id="shrewd_step",
    name="Shrewd Step",
    description="Slightly increase ability to navigate smoothly. (Pace Chaser)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.1, 3.0)],
    condition=SkillCondition(running_style=RunningStyleRequirement.PC),
    icon="👣"
))

register_skill(Skill(
    id="technician",
    name="Technician",
    description="Moderately increase ability to navigate smoothly. (Pace Chaser)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.25, 3.0)],
    condition=SkillCondition(running_style=RunningStyleRequirement.PC),
    icon="🛠️"
))

register_skill(Skill(
    id="straight_descent",
    name="Straight Descent",
    description="Slightly improve running on a downhill. (Pace Chaser)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.1, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.DOWNHILL,
        running_style=RunningStyleRequirement.PC
    ),
    icon="⬇️"
))

register_skill(Skill(
    id="determined_descent",
    name="Determined Descent",
    description="Moderately improve running on a downhill. (Pace Chaser)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.25, 2.4)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.DOWNHILL,
        running_style=RunningStyleRequirement.PC
    ),
    icon="⬇️"
))

register_skill(Skill(
    id="tactical_tweak",
    name="Tactical Tweak",
    description="Slightly increase acceleration when positioned toward the back mid-race. (Pace Chaser)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.PC
    ),
    icon="⚙️"
))

register_skill(Skill(
    id="shatterproof",
    name="Shatterproof",
    description="Moderately increase acceleration when positioned toward the back mid-race. (Pace Chaser)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.PC
    ),
    icon="💎"
))

register_skill(Skill(
    id="head_on",
    name="Head-On",
    description="Slightly increase acceleration when positioned toward the front late-race. (Pace Chaser)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        running_style=RunningStyleRequirement.PC
    ),
    icon="👊"
))

register_skill(Skill(
    id="neck_and_neck",
    name="Neck and Neck",
    description="Increase acceleration when positioned toward the front late-race. (Pace Chaser)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.4, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        running_style=RunningStyleRequirement.PC
    ),
    icon="👊"
))

register_skill(Skill(
    id="fighter",
    name="Fighter",
    description="Slightly increase acceleration for a medium duration when trying to pass another runner. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 2.4)],
    condition=SkillCondition(
        running_style=RunningStyleRequirement.LS,
        requires_passing=True
    ),
    icon="🥊"
))

register_skill(Skill(
    id="hard_worker",
    name="Hard Worker",
    description="Moderately increase acceleration for a medium duration when trying to pass another runner. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.35, 2.4)],
    condition=SkillCondition(
        running_style=RunningStyleRequirement.LS,
        requires_passing=True
    ),
    icon="🥊"
))

# Misc Acceleration
register_skill(Skill(
    id="highlander",
    name="Highlander",
    description="Slightly improve running on an uphill.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.1, 2.4)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.UPHILL),
    icon="⛰️"
))

register_skill(Skill(
    id="groundwork",
    name="Groundwork",
    description="Slightly increase acceleration after activating many skills early-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.15, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="🔨"
))

# -----------------------------------------------------------------------------
# RECOVERY SKILLS - Recover HP/Stamina
# -----------------------------------------------------------------------------

# Basic Recovery
register_skill(Skill(
    id="straightaway_recovery",
    name="Straightaway Recovery",
    description="Slightly recover endurance on a straight.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.015, 0)],  # 1.5% HP
    condition=SkillCondition(terrain=SkillTriggerTerrain.STRAIGHT),
    icon="💚"
))

register_skill(Skill(
    id="breath_of_fresh_air",
    name="Breath of Fresh Air",
    description="Recover endurance on a straight.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.055, 0)],  # 5.5% HP
    condition=SkillCondition(terrain=SkillTriggerTerrain.STRAIGHT),
    icon="🌬️"
))

register_skill(Skill(
    id="corner_recovery",
    name="Corner Recovery",
    description="Slightly recover endurance on a corner with efficient turning.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.015, 0)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.CORNER),
    icon="💚"
))

register_skill(Skill(
    id="swinging_maestro",
    name="Swinging Maestro",
    description="Recover endurance on a corner with efficient turning.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.055, 0)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.CORNER),
    icon="🎵"
))

# Position-Based Recovery
register_skill(Skill(
    id="lay_low",
    name="Lay Low",
    description="Slightly recover endurance when the way ahead is jammed early-race or mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.015, 0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID, requires_blocked=True),
    icon="🛡️"
))

register_skill(Skill(
    id="iron_will",
    name="Iron Will",
    description="Recover endurance when the way ahead is jammed early-race or mid-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.055, 0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID, requires_blocked=True),
    icon="🛡️"
))

register_skill(Skill(
    id="pace_strategy",
    name="Pace Strategy",
    description="Slightly recover endurance when passed by another runner mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.015, 0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID, requires_overtaken=True),
    icon="📊"
))

register_skill(Skill(
    id="indomitable",
    name="Indomitable",
    description="Recover endurance when passed by another runner mid-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.055, 0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID, requires_overtaken=True),
    icon="💪"
))

register_skill(Skill(
    id="calm_in_a_crowd",
    name="Calm in a Crowd",
    description="Slightly recover endurance when surrounded mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.015, 0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID, position=SkillTriggerPosition.MIDPACK),
    icon="😌"
))

register_skill(Skill(
    id="unruffled",
    name="Unruffled",
    description="Recover endurance when surrounded mid-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.055, 0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID, position=SkillTriggerPosition.MIDPACK),
    icon="😎"
))

# Long Race Recovery
register_skill(Skill(
    id="extra_tank",
    name="Extra Tank",
    description="Slightly regain the energy to run when close to exhausting strength. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.025, 0)],
    condition=SkillCondition(race_type=RaceTypeRequirement.LONG, min_hp_percent=0.0),  # Low HP trigger
    icon="⛽"
))

register_skill(Skill(
    id="adrenaline_rush",
    name="Adrenaline Rush",
    description="Regain the energy to run when close to exhausting strength. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.075, 0)],
    condition=SkillCondition(race_type=RaceTypeRequirement.LONG, min_hp_percent=0.0),
    icon="💉"
))

# Running Style Recovery
register_skill(Skill(
    id="be_still",
    name="Be Still",
    description="Slightly recover endurance when positioned toward the back upon approaching mid-race. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.015, 0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.LS
    ),
    icon="🧘"
))

register_skill(Skill(
    id="lie_in_wait",
    name="Lie in Wait",
    description="Recover endurance when positioned toward the back upon approaching mid-race. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.055, 0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.LS
    ),
    icon="🐆"
))

# Additional Recovery Skills
register_skill(Skill(
    id="triple_7s",
    name="Triple 7s",
    description="Slightly gain energy with 777m remaining.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.015, 0)],
    condition=SkillCondition(remaining_distance=777.0),
    icon="7️⃣"
))

register_skill(Skill(
    id="shake_it_out",
    name="Shake It Out",
    description="Slightly recover endurance after activating many skills late-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.015, 0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🎉"
))

register_skill(Skill(
    id="vip_pass",
    name="VIP Pass",
    description="Decrease fatigue when determined to pass another runner. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.05, 2.4)],
    condition=SkillCondition(
        race_type=RaceTypeRequirement.LONG,
        requires_passing=True
    ),
    icon="🎫"
))

register_skill(Skill(
    id="passing_pro",
    name="Passing Pro",
    description="Slightly decrease fatigue when determined to pass another runner. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.05, 2.4)],
    condition=SkillCondition(
        race_type=RaceTypeRequirement.LONG,
        requires_passing=True
    ),
    icon="🏁"
))

register_skill(Skill(
    id="gourmand",
    name="Gourmand",
    description="Recover endurance mid-race. (End Closer)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.025, 0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.EC
    ),
    icon="🍽️"
))

register_skill(Skill(
    id="free_spirited",
    name="Free-Spirited",
    description="If positioned in the midpack around when the mid-race starts, slightly decrease velocity and moderately recover endurance. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.035, 0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.MIDPACK,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="🕊️"
))

register_skill(Skill(
    id="of_calm_mind",
    name="Of Calm Mind",
    description="If positioned in the midpack around when the mid-race starts, slightly decrease velocity and greatly recover endurance. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.075, 0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.MIDPACK,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="🧘"
))

register_skill(Skill(
    id="soft_step",
    name="Soft Step",
    description="Slightly decrease fatigue when moving sideways. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.05, 2.4)],
    condition=SkillCondition(race_type=RaceTypeRequirement.MEDIUM),
    icon="👟"
))

register_skill(Skill(
    id="miraculous_step",
    name="Miraculous Step",
    description="Decrease fatigue when moving sideways. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.15, 2.4)],
    condition=SkillCondition(race_type=RaceTypeRequirement.MEDIUM),
    icon="✨"
))

register_skill(Skill(
    id="keen_eye",
    name="Keen Eye",
    description="Decrease fatigue, then moderately decrease velocity of runners ahead when positioned toward the back upon approaching mid-race. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.08, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="👁️"
))

register_skill(Skill(
    id="watchful_eye",
    name="Watchful Eye",
    description="Slightly decrease fatigue, then very slightly decrease velocity of runners ahead when positioned toward the back upon approaching mid-race. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.05, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="👀"
))

# -----------------------------------------------------------------------------
# FATIGUE REDUCTION SKILLS
# -----------------------------------------------------------------------------

register_skill(Skill(
    id="moxie",
    name="Moxie",
    description="Slightly reduce fatigue on an uphill. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.05, 3.0)],  # 5% less drain
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.UPHILL,
        running_style=RunningStyleRequirement.FR
    ),
    icon="💪"
))

register_skill(Skill(
    id="restless",
    name="Restless",
    description="Reduce fatigue on an uphill. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.UPHILL,
        running_style=RunningStyleRequirement.FR
    ),
    icon="🔥"
))

register_skill(Skill(
    id="rosy_outlook",
    name="Rosy Outlook",
    description="Slightly decrease fatigue when positioned toward the front mid-race. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.05, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🌹"
))

register_skill(Skill(
    id="trackblazer",
    name="Trackblazer",
    description="Decrease fatigue when positioned toward the front mid-race. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🏃"
))

register_skill(Skill(
    id="deep_breaths",
    name="Deep Breaths",
    description="Slightly decrease fatigue by taking a breather upon entering a straight. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.05, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="😤"
))

register_skill(Skill(
    id="cooldown",
    name="Cooldown",
    description="Decrease fatigue by taking a breather upon entering a straight. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, 0.15, 3.0)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.STRAIGHT,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="❄️"
))

# -----------------------------------------------------------------------------
# START SKILLS
# -----------------------------------------------------------------------------

register_skill(Skill(
    id="focus",
    name="Focus",
    description="Slightly decrease time lost to slow starts.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.START_BONUS, 0.3, 0)],  # 30% less delay
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="🎯"
))

register_skill(Skill(
    id="concentration",
    name="Concentration",
    description="Decrease time lost to slow starts.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.START_BONUS, 0.5, 0)],  # 50% less delay
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="🧠"
))

# -----------------------------------------------------------------------------
# NAVIGATION/VISION SKILLS
# -----------------------------------------------------------------------------

register_skill(Skill(
    id="nimble_navigator",
    name="Nimble Navigator",
    description="Slightly increase maneuverability when the way ahead is blocked in the last spurt.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.1, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        requires_blocked=True
    ),
    icon="👁️"
))

register_skill(Skill(
    id="no_stopping_me",
    name="No Stopping Me!",
    description="Increase maneuverability when the way ahead is blocked in the last spurt.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.25, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        requires_blocked=True
    ),
    icon="🚀"
))

# Additional Navigation/Vision Skills
register_skill(Skill(
    id="hawkeye",
    name="Hawkeye",
    description="Moderately widen field of view with heightened observation early-race. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🦅"
))

register_skill(Skill(
    id="clairvoyance",
    name="Clairvoyance",
    description="Widen field of view with heightened observation early-race. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.3, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🔮"
))

register_skill(Skill(
    id="studious",
    name="Studious",
    description="Slightly widen field of view with heightened observation mid-race. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.1, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.LS
    ),
    icon="📚"
))

register_skill(Skill(
    id="the_bigger_picture",
    name="The Bigger Picture",
    description="Widen field of view with heightened observation mid-race. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.25, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        running_style=RunningStyleRequirement.LS
    ),
    icon="🖼️"
))

register_skill(Skill(
    id="i_can_see_right_through_you",
    name="I Can See Right Through You",
    description="Slightly widen field of view with situational awareness when moving sideways. (End Closer)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.1, 2.4)],
    condition=SkillCondition(running_style=RunningStyleRequirement.EC),
    icon="👓"
))

register_skill(Skill(
    id="the_coast_is_clear",
    name="The Coast Is Clear!",
    description="Moderately widen field of view with situational awareness when moving sideways. (End Closer)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.2, 2.4)],
    condition=SkillCondition(running_style=RunningStyleRequirement.EC),
    icon="🌊"
))

register_skill(Skill(
    id="strategist",
    name="Strategist",
    description="Slightly widen field of view when positioned toward the back late-race. (End Closer)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.1, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.EC
    ),
    icon="🧠"
))

register_skill(Skill(
    id="crusader",
    name="Crusader",
    description="Widen field of view when positioned toward the back late-race. (End Closer)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.25, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.EC
    ),
    icon="⚔️"
))

register_skill(Skill(
    id="prudent_positioning",
    name="Prudent Positioning",
    description="Increase navigation early-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.15, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="🎯"
))

register_skill(Skill(
    id="center_stage",
    name="Center Stage",
    description="Greatly increase navigation early-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.35, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="⭐"
))

register_skill(Skill(
    id="go_with_the_flow",
    name="Go with the Flow",
    description="Moderately increase navigation late-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.2, 2.4)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🌊"
))

register_skill(Skill(
    id="lane_legerdemain",
    name="Lane Legerdemain",
    description="Increase navigation late-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.3, 2.4)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="✨"
))

# Special Navigation Skills
register_skill(Skill(
    id="perfect_prep",
    name="Perfect Prep!",
    description="Prepare to make for the finish line for a medium duration mid-race. (Sprint)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.25, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="🏁"
))

register_skill(Skill(
    id="meticulous_measures",
    name="Meticulous Measures",
    description="Moderately prepare to make for the finish line for a medium duration mid-race. (Sprint)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="📐"
))

register_skill(Skill(
    id="lightning_step",
    name="Lightning Step",
    description="Avoid becoming surrounded for a medium duration when positioned toward the back mid-race. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.25, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="⚡"
))

register_skill(Skill(
    id="thunderbolt_step",
    name="Thunderbolt Step",
    description="Moderately avoid becoming surrounded for a medium duration when positioned toward the back mid-race. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.15, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="⚡"
))

register_skill(Skill(
    id="sixth_sense",
    name="Sixth Sense",
    description="Avoid becoming surrounded early-race. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.25, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        running_style=RunningStyleRequirement.FR
    ),
    icon="🔮"
))

register_skill(Skill(
    id="dodging_danger",
    name="Dodging Danger",
    description="Moderately avoid becoming surrounded early-race. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        running_style=RunningStyleRequirement.FR
    ),
    icon="🛡️"
))

# -----------------------------------------------------------------------------
# DEBUFF SKILLS - Affect Other Runners
# -----------------------------------------------------------------------------

# Running Style Debuffs
register_skill(Skill(
    id="hesitant_front_runners",
    name="Hesitant Front Runners",
    description="Slightly decrease velocity of front runners late-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.1, 2.4)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🔻"
))

register_skill(Skill(
    id="hesitant_pace_chasers",
    name="Hesitant Pace Chasers",
    description="Slightly decrease velocity of pace chasers late-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.1, 2.4)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🔻"
))

register_skill(Skill(
    id="hesitant_late_surgers",
    name="Hesitant Late Surgers",
    description="Slightly decrease velocity of late surgers late-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.1, 2.4)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🔻"
))

register_skill(Skill(
    id="hesitant_end_closers",
    name="Hesitant End Closers",
    description="Slightly decrease velocity of end closers late-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.1, 2.4)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🔻"
))

# Position-Based Debuffs
register_skill(Skill(
    id="intimidate",
    name="Intimidate",
    description="Moderately intimidate runners behind when positioned toward the front early-race. (Sprint)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.1, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="😤"
))

register_skill(Skill(
    id="adored_by_all",
    name="Adored by All",
    description="Intimidate runners behind when positioned toward the front early-race. (Sprint)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.15, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="⭐"
))

register_skill(Skill(
    id="speed_eater",
    name="Speed Eater",
    description="Slightly steal velocity from runners behind when positioned toward the front mid-race. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="👹"
))

register_skill(Skill(
    id="greed_for_speed",
    name="Greed for Speed",
    description="Moderately steal velocity from runners behind when positioned toward the front mid-race. (Mile)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.12, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="👹"
))

register_skill(Skill(
    id="tether",
    name="Tether",
    description="Slightly decrease velocity of runners ahead when positioned toward the back late-race. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="⛓️"
))

register_skill(Skill(
    id="dominator",
    name="Dominator",
    description="Decrease velocity of runners ahead when positioned toward the back late-race. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.12, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="⛓️"
))

register_skill(Skill(
    id="opening_gambit",
    name="Opening Gambit",
    description="Slightly dull movement for runners ahead when positioned toward the back early-race. (Mile)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="♟️"
))

register_skill(Skill(
    id="battle_formation",
    name="Battle Formation",
    description="Dull movement for runners ahead when positioned toward the back early-race. (Mile)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.12, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.MILE
    ),
    icon="⚔️"
))

register_skill(Skill(
    id="restart",
    name="Restart",
    description="Slightly dull movement for runners ahead when not in the lead early-race. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        running_style=RunningStyleRequirement.FR
    ),
    icon="🔄"
))

register_skill(Skill(
    id="runaway",
    name="Runaway",
    description="Attempt to gain an especially large lead and keep it until the finish. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.4, 5.0)],
    condition=SkillCondition(
        position=SkillTriggerPosition.FRONT,
        running_style=RunningStyleRequirement.FR
    ),
    icon="🏃"
))

# Additional Debuff Skills - Frenzied
register_skill(Skill(
    id="frenzied_front_runners",
    name="Frenzied Front Runners",
    description="Increase time needed for front runners to calm down when they become rushed.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 3.0)],
    condition=SkillCondition(),
    icon="😵"
))

register_skill(Skill(
    id="frenzied_pace_chasers",
    name="Frenzied Pace Chasers",
    description="Increase time needed for pace chasers to calm down when they become rushed.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 3.0)],
    condition=SkillCondition(),
    icon="😵"
))

register_skill(Skill(
    id="frenzied_late_surgers",
    name="Frenzied Late Surgers",
    description="Increase time needed for late surgers to calm down when they become rushed.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 3.0)],
    condition=SkillCondition(),
    icon="😵"
))

register_skill(Skill(
    id="frenzied_end_closers",
    name="Frenzied End Closers",
    description="Increase time needed for end closers to calm down when they become rushed.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 3.0)],
    condition=SkillCondition(),
    icon="😵"
))

# Trick Skills
register_skill(Skill(
    id="trick_front",
    name="Trick (Front)",
    description="Slightly increase fatigue for rushed runners behind when positioned toward the front mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🎭"
))

register_skill(Skill(
    id="trick_rear",
    name="Trick (Rear)",
    description="Slightly increase fatigue for rushed runners ahead when positioned toward the back mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK
    ),
    icon="🎭"
))

register_skill(Skill(
    id="tantalizing_trick",
    name="Tantalizing Trick",
    description="Increase fatigue for rushed runners behind when positioned toward the front mid-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.1, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🎭"
))

# Subdued/Flustered Skills
register_skill(Skill(
    id="subdued_front_runners",
    name="Subdued Front Runners",
    description="Slightly increase fatigue for front runners early-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="😔"
))

register_skill(Skill(
    id="flustered_front_runners",
    name="Flustered Front Runners",
    description="Slightly increase fatigue for front runners mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="😳"
))

register_skill(Skill(
    id="subdued_pace_chasers",
    name="Subdued Pace Chasers",
    description="Slightly increase fatigue for pace chasers early-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="😔"
))

register_skill(Skill(
    id="flustered_pace_chasers",
    name="Flustered Pace Chasers",
    description="Slightly increase fatigue for pace chasers mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="😳"
))

register_skill(Skill(
    id="subdued_late_surgers",
    name="Subdued Late Surgers",
    description="Slightly increase fatigue for late surgers early-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="😔"
))

register_skill(Skill(
    id="flustered_late_surgers",
    name="Flustered Late Surgers",
    description="Slightly increase fatigue for late surgers mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="😳"
))

register_skill(Skill(
    id="subdued_end_closers",
    name="Subdued End Closers",
    description="Slightly increase fatigue for end closers early-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="😔"
))

register_skill(Skill(
    id="flustered_end_closers",
    name="Flustered End Closers",
    description="Slightly increase fatigue for end closers mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="😳"
))

# Gaze Skills
register_skill(Skill(
    id="intense_gaze",
    name="Intense Gaze",
    description="Slightly unnerve runners in focus late-race. (End Closer)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.EC
    ),
    icon="👁️"
))

register_skill(Skill(
    id="petrifying_gaze",
    name="Petrifying Gaze",
    description="Unnerve runners in focus late-race. (End Closer)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.12, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.EC
    ),
    icon="👁️"
))

register_skill(Skill(
    id="sharp_gaze",
    name="Sharp Gaze",
    description="Slightly startle other runners late-race. (Late Surger)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.LS
    ),
    icon="👁️"
))

register_skill(Skill(
    id="all_seeing_eyes",
    name="All-Seeing Eyes",
    description="Startle other runners late-race. (Late Surger)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.12, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.LS
    ),
    icon="👁️"
))

# Sprint Debuffs
register_skill(Skill(
    id="stop_right_there",
    name="Stop Right There!",
    description="Slightly cause panic in and very slightly dull movement for runners ahead when positioned toward the back early-race. (Sprint)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="🛑"
))

register_skill(Skill(
    id="youve_got_no_shot",
    name="You've Got No Shot",
    description="Cause panic in and moderately dull movement for runners ahead when positioned toward the back early-race. (Sprint)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.12, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.SPRINT
    ),
    icon="🚫"
))

# Medium Distance Debuffs
register_skill(Skill(
    id="murmur",
    name="Murmur",
    description="Slightly disturb runners directly ahead mid-race. (Medium)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🗣️"
))

register_skill(Skill(
    id="mystifying_murmur",
    name="Mystifying Murmur",
    description="Disturb runners directly ahead mid-race. (Medium)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.1, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🗣️"
))

# Long Distance Debuffs
register_skill(Skill(
    id="stamina_eater",
    name="Stamina Eater",
    description="Very slightly steal endurance from runners ahead when positioned toward the back mid-race. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.05, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="😈"
))

register_skill(Skill(
    id="stamina_siphon",
    name="Stamina Siphon",
    description="Slightly steal endurance from runners ahead when positioned toward the back mid-race. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="😈"
))

register_skill(Skill(
    id="smoke_screen",
    name="Smoke Screen",
    description="Moderately narrow the field of view for runners ahead late-race. (Long)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.08, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="💨"
))

register_skill(Skill(
    id="illusionist",
    name="Illusionist",
    description="Narrow the field of view for runners ahead late-race. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.12, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        race_type=RaceTypeRequirement.LONG
    ),
    icon="🎩"
))

# Pace Chaser Debuffs
register_skill(Skill(
    id="disorient",
    name="Disorient",
    description="Slightly narrow the field of view for runners behind when positioned toward the front late-race. (Pace Chaser)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.06, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        running_style=RunningStyleRequirement.PC
    ),
    icon="😵‍💫"
))

register_skill(Skill(
    id="dazzling_disorientation",
    name="Dazzling Disorientation",
    description="Moderately narrow the field of view for runners behind when positioned toward the front late-race. (Pace Chaser)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.1, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        running_style=RunningStyleRequirement.PC
    ),
    icon="✨"
))

# -----------------------------------------------------------------------------
# CONDITION SKILLS (Track/Weather)
# -----------------------------------------------------------------------------

register_skill(Skill(
    id="firm_conditions_gold",
    name="Firm Conditions",
    description="Increase performance on firm ground.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Track condition checked at runtime
    icon="☀️"
))

register_skill(Skill(
    id="firm_conditions_white",
    name="Firm Conditions",
    description="Slightly increase performance on firm ground.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Track condition checked at runtime
    icon="☀️"
))

register_skill(Skill(
    id="wet_conditions_gold",
    name="Wet Conditions",
    description="Increase performance on good, soft, and heavy ground.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Track condition checked at runtime
    icon="🌧️"
))

register_skill(Skill(
    id="wet_conditions_white",
    name="Wet Conditions",
    description="Slightly increase performance on good, soft, and heavy ground.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Track condition checked at runtime
    icon="🌧️"
))

# Track Direction Skills
register_skill(Skill(
    id="right_handed_gold",
    name="Right-Handed",
    description="Increase performance on tracks that curve clockwise.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Track direction checked at runtime
    icon="↪️"
))

register_skill(Skill(
    id="right_handed_white",
    name="Right-Handed",
    description="Slightly increase performance on tracks that curve clockwise.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Track direction checked at runtime
    icon="↪️"
))

register_skill(Skill(
    id="left_handed_gold",
    name="Left-Handed",
    description="Increase performance on tracks that curve counter-clockwise.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Track direction checked at runtime
    icon="↩️"
))

register_skill(Skill(
    id="left_handed_white",
    name="Left-Handed",
    description="Slightly increase performance on tracks that curve counter-clockwise.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Track direction checked at runtime
    icon="↩️"
))

# Season Skills
register_skill(Skill(
    id="spring_runner_gold",
    name="Spring Runner",
    description="Increase performance in spring.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Season checked at runtime
    icon="🌸"
))

register_skill(Skill(
    id="spring_runner_white",
    name="Spring Runner",
    description="Slightly increase performance in spring.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Season checked at runtime
    icon="🌸"
))

register_skill(Skill(
    id="summer_runner_gold",
    name="Summer Runner",
    description="Increase performance in summer.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Season checked at runtime
    icon="☀️"
))

register_skill(Skill(
    id="summer_runner_white",
    name="Summer Runner",
    description="Slightly increase performance in summer.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Season checked at runtime
    icon="☀️"
))

register_skill(Skill(
    id="fall_runner_gold",
    name="Fall Runner",
    description="Increase performance in fall.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Season checked at runtime
    icon="🍂"
))

register_skill(Skill(
    id="fall_runner_white",
    name="Fall Runner",
    description="Slightly increase performance in fall.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Season checked at runtime
    icon="🍂"
))

register_skill(Skill(
    id="winter_runner_gold",
    name="Winter Runner",
    description="Increase performance in winter.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Season checked at runtime
    icon="❄️"
))

register_skill(Skill(
    id="winter_runner_white",
    name="Winter Runner",
    description="Slightly increase performance in winter.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Season checked at runtime
    icon="❄️"
))

# Weather Skills
register_skill(Skill(
    id="sunny_days_gold",
    name="Sunny Days",
    description="Increase performance on sunny days.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Weather checked at runtime
    icon="☀️"
))

register_skill(Skill(
    id="sunny_days_white",
    name="Sunny Days",
    description="Slightly increase performance on sunny days.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Weather checked at runtime
    icon="☀️"
))

register_skill(Skill(
    id="cloudy_days_gold",
    name="Cloudy Days",
    description="Increase performance on cloudy days.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Weather checked at runtime
    icon="☁️"
))

register_skill(Skill(
    id="cloudy_days_white",
    name="Cloudy Days",
    description="Slightly increase performance on cloudy days.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Weather checked at runtime
    icon="☁️"
))

register_skill(Skill(
    id="rainy_days_gold",
    name="Rainy Days",
    description="Increase performance on rainy days.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Weather checked at runtime
    icon="🌧️"
))

register_skill(Skill(
    id="rainy_days_white",
    name="Rainy Days",
    description="Slightly increase performance on rainy days.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Weather checked at runtime
    icon="🌧️"
))

register_skill(Skill(
    id="snowy_days_gold",
    name="Snowy Days",
    description="Increase performance on snowy days.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # Weather checked at runtime
    icon="🌨️"
))

register_skill(Skill(
    id="snowy_days_white",
    name="Snowy Days",
    description="Slightly increase performance on snowy days.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.15, 5.0)],
    condition=SkillCondition(),  # Weather checked at runtime
    icon="🌨️"
))

# Post Position Skills
register_skill(Skill(
    id="inner_post_proficiency_gold",
    name="Inner Post Proficiency",
    description="Increase performance when starting from an inner post position.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.START_BONUS, 0.3, 1.0)],
    condition=SkillCondition(),  # Post position checked at runtime
    icon="1️⃣"
))

register_skill(Skill(
    id="inner_post_proficiency_white",
    name="Inner Post Proficiency",
    description="Slightly increase performance when starting from an inner post position.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.START_BONUS, 0.2, 1.0)],
    condition=SkillCondition(),  # Post position checked at runtime
    icon="1️⃣"
))

register_skill(Skill(
    id="outer_post_proficiency_gold",
    name="Outer Post Proficiency",
    description="Increase performance when starting from an outer post position.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.START_BONUS, 0.3, 1.0)],
    condition=SkillCondition(),  # Post position checked at runtime
    icon="8️⃣"
))

register_skill(Skill(
    id="outer_post_proficiency_white",
    name="Outer Post Proficiency",
    description="Slightly increase performance when starting from an outer post position.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.START_BONUS, 0.2, 1.0)],
    condition=SkillCondition(),  # Post position checked at runtime
    icon="8️⃣"
))

# Competitive Skills
register_skill(Skill(
    id="competitive_spirit_gold",
    name="Competitive Spirit",
    description="Increase performance when going against a popular horse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.3, 5.0)],
    condition=SkillCondition(),  # Rival checked at runtime
    icon="🔥"
))

register_skill(Skill(
    id="competitive_spirit_white",
    name="Competitive Spirit",
    description="Slightly increase performance when going against a popular horse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.2, 5.0)],
    condition=SkillCondition(),  # Rival checked at runtime
    icon="🔥"
))

register_skill(Skill(
    id="target_in_sight_gold",
    name="Target in Sight",
    description="Increase performance when going against a specific horse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.3, 5.0)],
    condition=SkillCondition(),  # Target checked at runtime
    icon="🎯"
))

register_skill(Skill(
    id="target_in_sight_white",
    name="Target in Sight",
    description="Slightly increase performance when going against a specific horse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.2, 5.0)],
    condition=SkillCondition(),  # Target checked at runtime
    icon="🎯"
))

# Lead the Charge
register_skill(Skill(
    id="lead_the_charge",
    name="Lead the Charge",
    description="Move to where the race will be decided and steadfastly stay there. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 4.0)],
    condition=SkillCondition(running_style=RunningStyleRequirement.FR),
    icon="⚔️"
))

register_skill(Skill(
    id="forward_march",
    name="Forward March",
    description="Moderately move to where the race will be decided and steadfastly stay there. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 4.0)],
    condition=SkillCondition(running_style=RunningStyleRequirement.FR),
    icon="🚶"
))


# =============================================================================
# UNIQUE CHARACTER SKILLS
# =============================================================================
# These are character-specific unique skills available in Global version.
# Each character has their own base unique skill and evolved version.

# Special Week
register_skill(Skill(
    id="shooting_star",
    name="Shooting Star",
    description="Ride the momentum to increase velocity and very slightly increase acceleration after passing another runner toward the front late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.35, 3.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.1, 3.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT
    ),
    icon="⭐"
))

# Silence Suzuka
register_skill(Skill(
    id="the_view_from_the_lead_is_mine",
    name="The View from the Lead Is Mine!",
    description="Increase velocity by drawing on all remaining strength when in the lead by a fair margin in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 4.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.FRONT
    ),
    icon="👑"
))

# Tokai Teio
register_skill(Skill(
    id="sky_high_teio_step",
    name="Sky-High Teio Step",
    description="Greatly increase velocity with flashy footwork when closing the gap to runners ahead on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="👟"
))

# Mejiro McQueen
register_skill(Skill(
    id="the_duty_of_dignity_calls",
    name="The Duty of Dignity Calls",
    description="Increase velocity with the determination to not be overtaken when positioned toward the front on the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT
    ),
    icon="👸"
))

# Gold Ship
register_skill(Skill(
    id="anchors_aweigh",
    name="Anchors Aweigh!",
    description="Moderately increase velocity steadily with a long spurt starting halfway through the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.SECOND_HALF),
    icon="⚓"
))

register_skill(Skill(
    id="warning_shot",
    name="Warning Shot!",
    description="Slightly increase velocity with a long spurt starting halfway through the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.SECOND_HALF),
    icon="⚓"
))

# Vodka
register_skill(Skill(
    id="cut_and_drive",
    name="Cut and Drive!",
    description="Become stronger at challenging rivals and increase velocity when positioned toward the front with 200m or less remaining.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🔪"
))

register_skill(Skill(
    id="xceleration",
    name="Xceleration",
    description="Become stronger at challenging rivals and moderately increase velocity when positioned toward the front with 200m or less remaining.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🔪"
))

# Daiwa Scarlet
register_skill(Skill(
    id="resplendent_red_ace",
    name="Resplendent Red Ace",
    description="Swell with the determination to be number one when positioned toward the front in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.4, 4.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.FRONT
    ),
    icon="♠️"
))

register_skill(Skill(
    id="red_ace",
    name="Red Ace",
    description="Slightly swell with the determination to be number one when positioned toward the front in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.3, 4.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.FRONT
    ),
    icon="♠️"
))

# Grass Wonder
register_skill(Skill(
    id="where_theres_a_will_theres_a_way",
    name="Where There's a Will, There's a Way",
    description="Increase velocity with a strong turn of foot when passing another runner toward the back on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.BACK
    ),
    icon="🌿"
))

register_skill(Skill(
    id="focused_mind",
    name="Focused Mind",
    description="Moderately increase velocity with a strong turn of foot when passing another runner toward the back on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.BACK
    ),
    icon="🌿"
))

# El Condor Pasa
register_skill(Skill(
    id="victoria_por_plancha",
    name="Victoria por plancha ☆",
    description="Hang onto the advantage when positioned toward the front with energy to spare on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.4, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🦅"
))

register_skill(Skill(
    id="corazon_ardiente",
    name="Corazón ☆ Ardiente",
    description="Slightly hang on to the advantage when positioned toward the front with energy to spare on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.3, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🦅"
))

# Air Groove
register_skill(Skill(
    id="blazing_pride",
    name="Blazing Pride",
    description="Increase velocity with the stride of an empress when passing another runner from midpack or further back on the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="✈️"
))

register_skill(Skill(
    id="empresss_pride",
    name="Empress's Pride",
    description="Moderately increase velocity with the stride of an empress when passing another runner from midpack or further back on the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="✈️"
))

# TM Opera O
register_skill(Skill(
    id="this_dance_is_for_vittoria",
    name="This Dance Is for Vittoria!",
    description="Increase velocity with royal brilliance when positioned toward the front and close to the runner ahead or behind on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🎭"
))

# Symboli Rudolf
register_skill(Skill(
    id="behold_thine_emperors_divine_might",
    name="Behold Thine Emperor's Divine Might",
    description="Greatly increase velocity on the final straight after passing another runner 3 times late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="👑"
))

# Oguri Cap
register_skill(Skill(
    id="triumphant_pulse",
    name="Triumphant Pulse",
    description="Greatly increase ability to break out of the pack by opening up a path when positioned toward the front with 200m remaining.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="💓"
))

# Sakura Bakushin O
register_skill(Skill(
    id="genius_x_bakushin_victory",
    name="Genius x Bakushin = Victory",
    description="Increase velocity with BAKUSHIN power when engaged in a challenge toward the front in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🌸"
))

register_skill(Skill(
    id="class_rep_speed_bakushin",
    name="Class Rep + Speed = Bakushin",
    description="Moderately increase velocity with BAKUSHIN power when engaged in a challenge toward the front in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🌸"
))

# Rice Shower
register_skill(Skill(
    id="blue_rose_closer",
    name="Blue Rose Closer",
    description="Increase velocity with strong willpower on the final straight after passing another runner in the front part of the pack on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🌹"
))

# Mihono Bourbon
register_skill(Skill(
    id="g00_1st_f",
    name="G00 1st. F∞;",
    description="Increase velocity when positioned toward the front after making it to the final straight without faltering.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🤖"
))

# Biwa Hayahide
register_skill(Skill(
    id="win_qed",
    name="∴win Q.E.D.",
    description="Increase velocity by deriving the winning equation when passing another runner toward the front on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT
    ),
    icon="📐"
))

# Mayano Top Gun
register_skill(Skill(
    id="flashy_landing",
    name="Flashy☆Landing",
    description="Increase ability to break out of the pack on the straight after engaging in a challenge toward the front on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="✈️"
))

register_skill(Skill(
    id="1st_place_kiss",
    name="1st Place Kiss☆",
    description="Slightly increase ability to break out of the pack on the straight after engaging in a challenge toward the front on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="💋"
))

# Winning Ticket
register_skill(Skill(
    id="our_ticket_to_win",
    name="Our Ticket to Win!",
    description="Increase velocity with winning ambition when positioned toward the front on the final straight after engaging in a challenge on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🎫"
))

register_skill(Skill(
    id="v_is_for_victory",
    name="V Is for Victory!",
    description="Moderately increase velocity with winning ambition when positioned toward the front on the final straight after engaging in a challenge on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="✌️"
))

# Matikanefukukitaru
register_skill(Skill(
    id="i_see_victory_in_my_future",
    name="I See Victory in My Future!",
    description="Clear a path forward with the power of divination when the way ahead is jammed late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.4, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🔮"
))

register_skill(Skill(
    id="luck_be_with_me",
    name="Luck Be with Me!",
    description="Moderately clear a path forward with the power of divination when the way ahead is jammed late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.3, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🍀"
))

# Nice Nature
register_skill(Skill(
    id="just_a_little_farther",
    name="Just a Little Farther!",
    description="Increase velocity with flaring fighting spirit when positioned 3rd and about to lose late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="💪"
))

register_skill(Skill(
    id="i_can_win_sometimes_right",
    name="I Can Win Sometimes, Right?",
    description="Moderately increase velocity with an arousal of fighting spirit when positioned 3rd and about to lose late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="😅"
))

# King Halo
register_skill(Skill(
    id="prideful_king",
    name="Prideful King",
    description="Greatly increase velocity in a true display of skill with 200m remaining after racing calmly.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 2.4)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="👑"
))

register_skill(Skill(
    id="call_me_king",
    name="Call Me King",
    description="Increase velocity in a true display of skill with 200m remaining after racing calmly.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 2.4)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="👑"
))

# Maruzensky
register_skill(Skill(
    id="red_shift_lp1211m",
    name="Red Shift/LP1211-M",
    description="Increase acceleration by shifting gears when positioned toward the front on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.6, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🔴"
))

# Taiki Shuttle
register_skill(Skill(
    id="shooting_for_victory",
    name="Shooting for Victory!",
    description="Increase acceleration with a pow, a wow, and a bang when well-positioned upon approaching the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.55, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="🚀"
))

# Mejiro Ryan
register_skill(Skill(
    id="feel_the_burn",
    name="Feel the Burn!",
    description="Moderately increase acceleration in an attempt to move up on a corner late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="💪"
))

register_skill(Skill(
    id="lets_pump_some_iron",
    name="Let's Pump Some Iron!",
    description="Increase acceleration in an attempt to move up on a corner late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.55, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="🏋️"
))

# Seiun Sky
register_skill(Skill(
    id="angling_and_scheming",
    name="Angling and Scheming",
    description="Increase acceleration at an opportune moment when in the lead on a corner late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.55, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="🎣"
))

# Narita Brian
register_skill(Skill(
    id="shadow_break",
    name="Shadow Break",
    description="Increase velocity with beastly strength when passing another runner on the outside on the final corner or later. If engaged in a challenge mid-race, greatly increase velocity instead.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🐯"
))

# Narita Taishin
register_skill(Skill(
    id="nemesis",
    name="Nemesis",
    description="Increase velocity with smoldering ambition when moving up from midpack on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="🔥"
))

# Smart Falcon
register_skill(Skill(
    id="sparkly_stardom",
    name="SPARKLY☆STARDOM",
    description="Become empowered to keep the spotlight when positioned toward the front and close to the runner behind on a straight mid-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="⭐"
))

# Curren Chan
register_skill(Skill(
    id="lookatcurren",
    name="#LookatCurren",
    description="Gain momentum and begin to advance when passing another runner while well-positioned around halfway through the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="📸"
))

# Fuji Kiseki
register_skill(Skill(
    id="lights_of_vaudeville",
    name="Lights of Vaudeville",
    description="Greatly increase velocity with a dazzling display when just breaking out of the pack toward the front on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🎪"
))

# Agnes Tachyon
register_skill(Skill(
    id="u_ma_2",
    name="U=ma2",
    description="Recover endurance and moderately increase velocity for a moderate duration when sitting off the pace on a corner in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.RECOVERY, 3.5, 1.0),
        SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="🔬"
))

# Super Creek
register_skill(Skill(
    id="pure_heart",
    name="Pure Heart",
    description="Greatly recover endurance when well-positioned mid-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 7.5, 1.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="💚"
))

register_skill(Skill(
    id="clear_heart",
    name="Clear Heart",
    description="Recover endurance when well-positioned mid-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 5.5, 1.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="💚"
))

# Haru Urara
register_skill(Skill(
    id="super_duper_climax",
    name="Super-Duper Climax",
    description="Recover endurance with a glance at nearby runners when positioned toward the back on the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 5.5, 1.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK
    ),
    icon="🌸"
))

register_skill(Skill(
    id="super_duper_stoked",
    name="Super-Duper Stoked",
    description="Moderately recover endurance with a glance at nearby runners when positioned toward the back on the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 3.5, 1.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK
    ),
    icon="🌸"
))

# Kitasan Black
register_skill(Skill(
    id="victory_cheer",
    name="Victory Cheer!",
    description="Moderately increase velocity when positioned toward the front on the third corner in the second half of the race. Or, kick forward hard when toward the front on the backstretch late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.FRONT
    ),
    icon="📣"
))

# Satono Diamond
register_skill(Skill(
    id="eternal_encompassing_shine",
    name="Eternal Encompassing Shine",
    description="If well-positioned at the start of the final straight, her strong willpower to win increases velocity. If positioned near the front, greatly increase velocity instead.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="💎"
))

# Hishi Amazon
register_skill(Skill(
    id="you_and_me_one_on_one",
    name="You and Me! One-on-One!",
    description="Increase velocity on the final straight after passing another runner on the outside toward the back on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.BACK
    ),
    icon="🤜"
))

# Manhattan Cafe
register_skill(Skill(
    id="chasing_after_you",
    name="Chasing After You",
    description="Chase after an unseen friend when in midpack in the second half of the race, moderately increasing velocity steadily and very slightly intimidating runners ahead.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.35, 4.0),
        SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.05, 4.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="☕"
))

# Kawakami Princess
register_skill(Skill(
    id="a_princess_must_seize_victory",
    name="A Princess Must Seize Victory!",
    description="Increase velocity with pretty princess power when engaged in a challenge on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="👸"
))

# Fine Motion
register_skill(Skill(
    id="fairy_tale",
    name="Fairy Tale",
    description="Increase velocity with the excitement of running when engaged in a challenge while well-positioned in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.SECOND_HALF),
    icon="🧚"
))

# Tamamo Cross
register_skill(Skill(
    id="white_lightning_comin_through",
    name="White Lightning Comin' Through!",
    description="Bolt down the track like lightning when well-positioned or aiming for the front from midpack on a straight in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="⚡"
))

# Admire Vega
register_skill(Skill(
    id="shooting_star_of_dioskouroi",
    name="Shooting Star of Dioskouroi",
    description="Increase velocity with guidance from the stars when far from the lead on the final straight. If positioned around the very back, greatly increase velocity instead.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.BACK
    ),
    icon="🌟"
))

# Inari One
register_skill(Skill(
    id="now_were_cruisin",
    name="Now We're Cruisin'!",
    description="When competing for the lead if positioned in the midpack or further for the first half of the race, show off some Edo spirit and greatly increase velocity.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(position=SkillTriggerPosition.MIDPACK),
    icon="🦊"
))

# Sweep Tosho
register_skill(Skill(
    id="victory_belongs_to_me_strelitzia",
    name="Victory belongs to me—Strelitzia! ☆",
    description="If positioned toward the back until the start of the final corner, when there are 300m remaining, cast a magic spell to increase velocity continuously.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 4.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK
    ),
    icon="🌺"
))

# Eishin Flash
register_skill(Skill(
    id="schwarzes_schwert",
    name="Schwarzes Schwert",
    description="Increase velocity in a dash for the lead after running calmly and according to plan up until the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="⚔️"
))

# Mejiro Dober
register_skill(Skill(
    id="moving_past_and_beyond",
    name="Moving Past, and Beyond",
    description="Having run the race calmly, increase acceleration with hardened determination when making a move mid-race, or on a crucial corner late-race whilst in midpack.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.55, 3.0)],
    condition=SkillCondition(position=SkillTriggerPosition.MIDPACK),
    icon="🐕"
))

# Nishino Flower
register_skill(Skill(
    id="budding_blossom",
    name="Budding Blossom",
    description="If the skill user engaged in a challenge on a mid-race corner, increase acceleration when well-positioned late-race at least halfway through the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.55, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🌼"
))

# Hishi Akebono
register_skill(Skill(
    id="yummy_speed",
    name="YUMMY☆SPEED!",
    description="Kick forward hard with renewed vigor when starting to get tired while well-positioned halfway through the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="🍰"
))

# Agnes Digital
register_skill(Skill(
    id="omg_the_final_sprint",
    name="OMG! (ﾟ∀ﾟ) The Final Sprint! ☆",
    description="Increase velocity and navigation with the pure euphoria of being within breathing distance of precious waifus after passing another runner 2 times late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 3.0),
        SkillEffect(SkillEffectType.VISION, 0.2, 3.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="💻"
))

# Tosen Jordan
register_skill(Skill(
    id="pop_and_polish",
    name="Pop & Polish",
    description="Get hyped and increase velocity when pressured by or passing another runner while well-positioned on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="💅"
))

# Gold City
register_skill(Skill(
    id="keep_it_real",
    name="KEEP IT REAL.",
    description="Moderately increase acceleration steadily with a wink when starting to make a move from midpack in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="💛"
))

# Meisho Doto
register_skill(Skill(
    id="i_never_goof_up",
    name="I Never Goof Up!",
    description="Aim for the front with unwavering determination when passing another runner from midpack or further back on a corner late-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="😤"
))

# Ines Fujin
register_skill(Skill(
    id="all_charged_its_go_time",
    name="All Charged! It's Go Time!",
    description="Moderately increase velocity when positioned toward the front with about 300m remaining. If coming out of an uphill, greatly increase velocity instead.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 2.4)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="⚡"
))

# Yaeno Muteki
register_skill(Skill(
    id="peerless_dance_of_flowering_flames",
    name="Peerless Dance of Flowering Flames",
    description="If the skill user passes another runner on the final corner or later, increase velocity with fiery fighting spirit when in the front part of the pack with 300m remaining.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🔥"
))

# Sakura Chiyono O
register_skill(Skill(
    id="ambition_to_surpass_the_sakura",
    name="Ambition to Surpass the Sakura",
    description="Increase velocity with blossoming ambition when well-positioned and close to the runner ahead with 300m or less remaining.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="🌸"
))

# Mejiro Ardan
register_skill(Skill(
    id="a_lifelong_dream_a_moments_flight",
    name="A Lifelong Dream, A Moment's Flight",
    description="Seize the moment when close to the runner behind on the final straight, slightly consuming endurance to greatly increase velocity for a moderate duration.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="🦋"
))

# Mejiro Bright
register_skill(Skill(
    id="lovely_spring_breeze",
    name="Lovely Spring Breeze",
    description="From the midpack in the second half of the race, slightly increase velocity steadily for a duration based on remaining endurance.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 4.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="🌸"
))

# Mejiro Palmer
register_skill(Skill(
    id="keep_pushing_ahead",
    name="Keep Pushing Ahead",
    description="If positioned toward the front from the start of the race until the second half of the race, good vibes recover endurance and moderately increase velocity steadily.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.RECOVERY, 3.5, 1.0),
        SkillEffect(SkillEffectType.SPEED, 0.35, 4.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🌴"
))

# Air Shakur
register_skill(Skill(
    id="trigger_beat",
    name="trigger:BEAT",
    description="When near the inner rail midpack on the final corner or later, calculate the path to victory, increasing velocity and ability to navigate smoothly on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 3.0),
        SkillEffect(SkillEffectType.VISION, 0.2, 3.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="🎵"
))

# =============================================================================
# ALTERNATE COSTUME UNIQUE SKILLS
# =============================================================================
# These are unique skills for alternate costume versions of characters.

# Special Week (Commander)
register_skill(Skill(
    id="dreams_donned_with_pride",
    name="Dreams Donned with Pride!",
    description="If the skill user activates another skill on the final corner late-race, take the crowd's cheers to heart and moderately increase velocity. If racing at Nakayama Racecourse, greatly increase velocity instead.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="🎖️"
))

# Special Week (Summer)
register_skill(Skill(
    id="dazzln_diver",
    name="Dazzl'n ♪ Diver",
    description="Recover endurance by relaxing after activating 2 skills when positioned midpack mid-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 3.5, 1.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="🏊"
))

# Tokai Teio (Anime Collab)
register_skill(Skill(
    id="certain_victory",
    name="Certain Victory",
    description="Greatly increase velocity with an indomitable fighting spirit on the final straight after being on the heels of another runner toward the front on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="👑"
))

# Mejiro McQueen (Anime Collab)
register_skill(Skill(
    id="legacy_of_the_strong",
    name="Legacy of the Strong",
    description="Increase velocity continuously when pressured by another runner and running out of energy toward the front on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 4.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT
    ),
    icon="👑"
))

# Grass Wonder (Fantasy)
register_skill(Skill(
    id="superior_heal",
    name="Superior Heal",
    description="Greatly recover endurance with a gentle light when overtaken toward the back mid-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 5.5, 1.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK
    ),
    icon="✨"
))

# El Condor Pasa (Fantasy)
register_skill(Skill(
    id="condors_fury",
    name="Condor's Fury",
    description="Increase acceleration with blazing passion when aiming for the front from midpack on the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="🦅"
))

# Air Groove (Wedding)
register_skill(Skill(
    id="eternal_moments",
    name="Eternal Moments",
    description="Increase velocity when starting to make a move from a position toward the front mid-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT
    ),
    icon="💒"
))

# Mayano Top Gun (Wedding)
register_skill(Skill(
    id="flowery_maneuver",
    name="Flowery☆Maneuver",
    description="Increase velocity when passing another runner toward the front on the final corner. If passing toward the back, increase acceleration instead.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 3.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.3, 3.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="💐"
))

# Fine Motion (Wedding)
register_skill(Skill(
    id="best_day_ever",
    name="Best Day Ever",
    description="If well-positioned late-race on the final corner or later, increase velocity. If there's a large distance left to the finish, also increase acceleration very slightly with perfect form.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 3.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.15, 3.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="💒"
))

# Curren Chan (Wedding)
register_skill(Skill(
    id="one_true_color",
    name="One True Color",
    description="If positioned toward the front with 350m remaining and there is another Umamusume close behind, the determination to stay ahead makes it easier to break out of the pack.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🌈"
))

# Super Creek (Halloween)
register_skill(Skill(
    id="give_mummy_a_hug",
    name="Give Mummy a Hug ♡",
    description="Increase ability to break out of the pack when well-positioned and close to the runner ahead on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="🧟"
))

# Rice Shower (Halloween)
register_skill(Skill(
    id="every_rose_has_its_fangs",
    name="Every Rose Has Its Fangs",
    description="Suck endurance from runners ahead when well-positioned and pressured by another runner mid-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.RECOVERY, 2.5, 1.0),
        SkillEffect(SkillEffectType.DEBUFF_SPEED, 0.15, 2.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="🦇"
))

# Maruzensky (Summer)
register_skill(Skill(
    id="a_kiss_for_courage",
    name="A Kiss for Courage",
    description="Increase velocity enthusiastically when positioned toward the front in the second half of the race after recovering endurance with a skill.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.FRONT
    ),
    icon="💋"
))

# Symboli Rudolf (Festival)
register_skill(Skill(
    id="arrows_whistle_shadows_disperse",
    name="Arrows Whistle, Shadows Disperse",
    description="Increase velocity with a blazing spirit when pressured by another runner in the front part of the pack on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🎌"
))

# Gold City (Festival)
register_skill(Skill(
    id="dancing_in_the_leaves",
    name="Dancing in the Leaves",
    description="Increase ability to break out of the pack when engaged in a challenge in midpack on the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="🍂"
))

# Oguri Cap (Christmas)
register_skill(Skill(
    id="festive_miracle",
    name="Festive Miracle",
    description="Control breathing and kick forward hard toward victory in the second half of the race after recovering endurance with skills at least 3 times.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 3.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.3, 3.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.SECOND_HALF),
    icon="🎄"
))

# Biwa Hayahide (Christmas)
register_skill(Skill(
    id="presents_from_x",
    name="Presents from X",
    description="Increase velocity by deriving a path to victory mid-race after staying well-positioned from the start of the race up until the second half.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="🎁"
))

# TM Opera O (New Year)
register_skill(Skill(
    id="barcarole_of_blessings",
    name="Barcarole of Blessings",
    description="Increase velocity for a moderate duration when in the front part of the pack with 400m remaining. If at least 7 skills have been activated, greatly increase velocity for a moderate duration instead.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🎍"
))

# Haru Urara (New Year)
register_skill(Skill(
    id="114th_times_the_charm",
    name="114th Time's the Charm",
    description="Give max effort when far from the lead on the final corner, moderately increasing velocity steadily for a duration proportional to distance from the lead.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 4.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="🎍"
))

# Matikanefukukitaru (Full Armor)
register_skill(Skill(
    id="bountiful_harvest",
    name="Bountiful Harvest",
    description="Increase velocity with a surge of great fortune when pressured by another runner toward the back in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        position=SkillTriggerPosition.BACK
    ),
    icon="🌾"
))

# Mihono Bourbon (Valentine)
register_skill(Skill(
    id="operation_cacao",
    name="Operation Cacao",
    description="Take a slight breather and increase velocity when in the front part of the pack and detecting another runner coming from behind on a corner mid-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.35, 3.0),
        SkillEffect(SkillEffectType.RECOVERY, 1.5, 1.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="🍫"
))

# Eishin Flash (Valentine)
register_skill(Skill(
    id="guten_appetit",
    name="Guten Appetit ♪",
    description="Increase velocity continuously with a patissiere's pride on the final straight after passing another runner 3 times on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 4.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="🍰"
))

# Taiki Shuttle (Camping)
register_skill(Skill(
    id="joyful_voyage",
    name="Joyful Voyage!",
    description="If positioned toward the front with 200m remaining, increase velocity. Then, if also positioned near the leading Umamusume, gather strength to move slightly forward.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="🏕️"
))

# Mejiro Dober (Camping)
register_skill(Skill(
    id="wherever_this_wonder_leads",
    name="Wherever This Wonder Leads",
    description="If positioned midpack on a downhill just before late-race and there's a large distance left to the finish, enjoy the race to the fullest, increasing velocity.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="🏕️"
))

# Seiun Sky (Ballroom)
register_skill(Skill(
    id="break_it_down",
    name="Break It Down!",
    description="If positioned toward the front on a straight late-race, increase velocity with high spirits. If the straight is on the backstretch, also increase acceleration very slightly.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 3.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.15, 3.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="💃"
))

# Fuji Kiseki (Ballroom)
register_skill(Skill(
    id="ravissant",
    name="Ravissant",
    description="When passing another racer at the front part of the pack on the final corner or later, perform a dazzling display that greatly increases velocity for a moderate duration.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="💃"
))

# Nice Nature (Cheerleader)
register_skill(Skill(
    id="go_go_goal",
    name="Go☆Go☆Goal!",
    description="If the skill user passes another runner on the final corner or later, increase velocity from the midpack onward on the final straight. If the skill user isn't one of the top favorites, muster resolve to keep steadily increasing velocity.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 4.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="📣"
))

# King Halo (Cheerleader)
register_skill(Skill(
    id="louder_tracen_cheer",
    name="Louder! Tracen Cheer!",
    description="If the skill user stays toward the very back during the first half of the race without being rushed, unleash fighting spirit to increase acceleration on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="📣"
))

# =============================================================================
# ADDITIONAL COMMON SKILLS (Dirt, Team Spirit, Career)
# =============================================================================

# Dirt Skills
register_skill(Skill(
    id="trending_in_the_charts",
    name="Trending in the Charts!",
    description="Increase velocity when engaged in a challenge mid-race. (Dirt)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="📈"
))

register_skill(Skill(
    id="top_pick",
    name="Top Pick",
    description="Slightly increase velocity when engaged in a challenge mid-race. (Dirt)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="📈"
))

register_skill(Skill(
    id="master_of_the_sands",
    name="Master of the Sands",
    description="Recover endurance and increase velocity when positioned toward the back mid-race. (Dirt)",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.RECOVERY, 2.5, 1.0),
        SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK
    ),
    icon="🏜️"
))

register_skill(Skill(
    id="familiar_ground",
    name="Familiar Ground",
    description="Slightly recover endurance when positioned toward the back mid-race. (Dirt)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 1.5, 1.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK
    ),
    icon="🏜️"
))

# Maverick (Solo Running)
register_skill(Skill(
    id="maverick_gold",
    name="Maverick",
    description="Greatly increase performance when no other runners nearby.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 5.0)],
    condition=SkillCondition(),
    icon="🐺"
))

register_skill(Skill(
    id="maverick_white",
    name="Maverick",
    description="Moderately increase performance when no other runners nearby.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.3, 5.0)],
    condition=SkillCondition(),
    icon="🐺"
))

# G1 Great / G1 Averseness
register_skill(Skill(
    id="g1_great_gold",
    name="G1 Great",
    description="Increase performance in G1 or otherwise important races.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),  # G1 checked at runtime
    icon="🏆"
))

register_skill(Skill(
    id="g1_great_white",
    name="G1 Great",
    description="Moderately increase performance in G1 or otherwise important races.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),  # G1 checked at runtime
    icon="🏆"
))

# Best in Japan (Long race Final Corner)
register_skill(Skill(
    id="best_in_japan",
    name="Best in Japan",
    description="Everyone's expectations strongly inspire the skill user, increasing velocity on the final corner. (Long)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        race_type=RaceTypeRequirement.LONG,
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="🇯🇵"
))

# Career Star Skills
register_skill(Skill(
    id="radiant_star",
    name="Radiant Star",
    description="Control breathing and kick forward in the second half of the race. Effect is increased in proportion to number of career wins.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.35, 3.0),
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.2, 3.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.SECOND_HALF),
    icon="⭐"
))

register_skill(Skill(
    id="glittering_star",
    name="Glittering Star",
    description="Very slightly control breathing and kick forward in the second half of the race. Effect is increased in proportion to number of career wins.",
    rarity=SkillRarity.WHITE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.2, 3.0),
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.1, 3.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.SECOND_HALF),
    icon="⭐"
))

# Team Spirit Skills (Burning Spirit - Gold)
register_skill(Skill(
    id="burning_spirit_spd",
    name="Burning Spirit SPD",
    description="Burn bright with team spirit, increasing velocity in proportion to the total Speed of racing team members mid-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="🔥"
))

register_skill(Skill(
    id="burning_spirit_sta",
    name="Burning Spirit STA",
    description="Burn bright with team spirit, recovering endurance in proportion to the total Stamina of racing team members mid-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 3.5, 1.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="🔥"
))

register_skill(Skill(
    id="burning_spirit_pwr",
    name="Burning Spirit PWR",
    description="Burn bright with team spirit, increasing acceleration in proportion to the total Power of racing team members late-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.35, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🔥"
))

register_skill(Skill(
    id="burning_spirit_guts",
    name="Burning Spirit GUTS",
    description="Burn bright with team spirit, increasing vigor in proportion to the total Guts of racing team members late-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.3, 3.0)],  # Vigor affects last spurt
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🔥"
))

register_skill(Skill(
    id="burning_spirit_wit",
    name="Burning Spirit WIT",
    description="Burn bright with team spirit, increasing strategic navigation for a medium duration in proportion to the total Wit of racing team members early-race.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.VISION, 0.35, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="🔥"
))

# Team Spirit Skills (Ignited Spirit - White)
register_skill(Skill(
    id="ignited_spirit_spd",
    name="Ignited Spirit SPD",
    description="Burn bright with team spirit, slightly increasing velocity in proportion to the total Speed of racing team members mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="🔥"
))

register_skill(Skill(
    id="ignited_spirit_sta",
    name="Ignited Spirit STA",
    description="Burn bright with team spirit, slightly recovering endurance in proportion to the total Stamina of racing team members mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 2.0, 1.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="🔥"
))

register_skill(Skill(
    id="ignited_spirit_pwr",
    name="Ignited Spirit PWR",
    description="Burn bright with team spirit, slightly increasing acceleration in proportion to the total Power of racing team members late-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.25, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🔥"
))

register_skill(Skill(
    id="ignited_spirit_guts",
    name="Ignited Spirit GUTS",
    description="Burn bright with team spirit, very slightly increasing vigor in proportion to the total Guts of racing team members late-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.2, 3.0)],  # Vigor affects last spurt
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🔥"
))

register_skill(Skill(
    id="ignited_spirit_wit",
    name="Ignited Spirit WIT",
    description="Burn bright with team spirit, slightly increasing strategic navigation for a medium duration in proportion to the total Wit of racing team members early-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.VISION, 0.25, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="🔥"
))


# =============================================================================
# MISSING UNIQUE CHARACTER SKILLS
# =============================================================================

# Hishi Amazon
register_skill(Skill(
    id="you_and_me_one_on_one",
    name="You and Me! One-on-One!",
    description="Increase velocity on the final straight after passing another runner on the outside toward the back on the final corner or later.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="👊"
))

# Hishi Akebono
register_skill(Skill(
    id="yummy_speed",
    name="YUMMY☆SPEED!",
    description="Kick forward hard with renewed vigor when starting to get tired while well-positioned halfway through the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="🍔"
))

# Tamamo Cross
register_skill(Skill(
    id="white_lightning_comin_through",
    name="White Lightning Comin' Through!",
    description="Bolt down the track like lightning when well-positioned or aiming for the front from midpack on a straight in the second half of the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="⚡"
))

# Inari One
register_skill(Skill(
    id="now_were_cruisin",
    name="Now We're Cruisin'!",
    description="When competing for the lead if positioned in the midpack or further for the first half of the race, show off some Edo spirit and greatly increase velocity.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="🦊"
))

# Sweep Tosho
register_skill(Skill(
    id="victory_belongs_to_me_strelitzia",
    name="Victory belongs to me—Strelitzia! ☆",
    description="If positioned toward the back until the start of the final corner, when there are 300m remaining, cast a magic spell to increase velocity continuously.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 4.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.BACK
    ),
    icon="🌺"
))

# Admire Vega
register_skill(Skill(
    id="shooting_star_of_dioskouroi",
    name="Shooting Star of Dioskouroi",
    description="Increase velocity with guidance from the stars when far from the lead on the final straight. If positioned around the very back, greatly increase velocity instead.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.BACK,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="⭐"
))

# Kawakami Princess
register_skill(Skill(
    id="a_princess_must_seize_victory",
    name="A Princess Must Seize Victory!",
    description="Increase velocity with pretty princess power when engaged in a challenge on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="👑"
))

# Nishino Flower
register_skill(Skill(
    id="budding_blossom",
    name="Budding Blossom",
    description="If the skill user engaged in a challenge on a mid-race corner, increase acceleration when well-positioned late-race at least halfway through the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="🌸"
))

# Matikanetannhauser (Ready, Go!)
register_skill(Skill(
    id="ready_go",
    name="Ready, Go!",
    description="Moderately recover endurance and slightly increase velocity with newfound resolve when in midpack around halfway through the race.",
    rarity=SkillRarity.WHITE,
    effects=[
        SkillEffect(SkillEffectType.RECOVERY, 2.5, 1.0),
        SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="🎵"
))

# Matikanetannhauser (Go, Go, Mun!)
register_skill(Skill(
    id="go_go_mun",
    name="Go, Go, Mun!",
    description="Recover endurance and moderately increase velocity with newfound resolve when in midpack around halfway through the race.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.RECOVERY, 3.5, 1.0),
        SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="🎵"
))

# =============================================================================
# MISSING DEBUFF/NEGATIVE SKILLS
# =============================================================================

# Packphobia
register_skill(Skill(
    id="packphobia",
    name="Packphobia",
    description="Moderately lose endurance when surrounded.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, -2.5, 1.0)],
    condition=SkillCondition(),
    icon="😰"
))

# Ramp Revulsion
register_skill(Skill(
    id="ramp_revulsion",
    name="Ramp Revulsion",
    description="Moderately increase fatigue on an uphill.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, -0.25, 3.0)],
    condition=SkillCondition(),
    icon="⛰️"
))

# Running Idle
register_skill(Skill(
    id="running_idle",
    name="Running Idle",
    description="Moderately increase fatigue when positioned toward the back mid-race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.STAMINA_SAVE, -0.25, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.BACK
    ),
    icon="😴"
))

# Defeatist
register_skill(Skill(
    id="defeatist",
    name="Defeatist",
    description="Moderately increase urge to give up when positioned around the very back on the final straight.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.BACK,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    icon="😔"
))

# Reckless
register_skill(Skill(
    id="reckless",
    name="Reckless",
    description="Moderately increase carelessness when in the lead with around 200m remaining.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.2, 2.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    icon="😵"
))

# Blatant Fear
register_skill(Skill(
    id="blatant_fear",
    name="Blatant Fear",
    description="Greatly decrease velocity on a corner in the second half of the race due to Trainer's obvious anxiety.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.45, 3.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="😨"
))

# Gatekept
register_skill(Skill(
    id="gatekept",
    name="Gatekept",
    description="Moderately increase time lost to slow starts.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.START_BONUS, -0.25, 1.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="🚫"
))

# Feelin' a Bit Silly
register_skill(Skill(
    id="feelin_a_bit_silly",
    name="Feelin' a Bit Silly",
    description="Greatly decrease the racer's proficiency in starting races. Effects include slow starts and reduced starting acceleration.",
    rarity=SkillRarity.WHITE,
    effects=[
        SkillEffect(SkillEffectType.START_BONUS, -0.35, 1.0),
        SkillEffect(SkillEffectType.ACCELERATION, -0.2, 2.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="🤪"
))

# You're Not the Boss of Me!
register_skill(Skill(
    id="youre_not_the_boss_of_me",
    name="You're Not the Boss of Me!",
    description="Increase time lost to slow starts and moderately decrease Wit.",
    rarity=SkillRarity.WHITE,
    effects=[
        SkillEffect(SkillEffectType.START_BONUS, -0.25, 1.0),
        SkillEffect(SkillEffectType.VISION, -0.2, 5.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.EARLY),
    icon="😤"
))

# Corner Adept ×
register_skill(Skill(
    id="corner_adept_x",
    name="Corner Adept ×",
    description="Moderately decrease velocity on a corner with clumsy turning.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 2.0)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.CORNER),
    icon="🔄"
))

# Corner Recovery ×
register_skill(Skill(
    id="corner_recovery_x",
    name="Corner Recovery ×",
    description="Moderately lose endurance on a corner with inefficient turning.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.RECOVERY, -2.0, 1.0)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.CORNER),
    icon="🔄"
))

# Corner Acceleration ×
register_skill(Skill(
    id="corner_acceleration_x",
    name="Corner Acceleration ×",
    description="Moderately decrease acceleration on a corner with awkward turning.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, -0.25, 2.0)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.CORNER),
    icon="🔄"
))

# Wallflower
register_skill(Skill(
    id="wallflower",
    name="Wallflower",
    description="Moderately decrease performance when many other runners are using the same strategy.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🌸"
))

# 99 Problems
register_skill(Skill(
    id="99_problems",
    name="99 Problems",
    description="Get overwhelmed by powerful opponents, moderately decreasing Guts and Wit.",
    rarity=SkillRarity.WHITE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, -0.2, 5.0),
        SkillEffect(SkillEffectType.VISION, -0.15, 5.0)
    ],
    condition=SkillCondition(),
    icon="😓"
))

# Paddock Fright
register_skill(Skill(
    id="paddock_fright",
    name="Paddock Fright",
    description="Moderately decrease performance when the favorite.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="😰"
))

# Inner Post Averseness
register_skill(Skill(
    id="inner_post_averseness",
    name="Inner Post Averseness",
    description="Moderately decrease performance in brackets 1-3.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.START_BONUS, -0.2, 1.0)],
    condition=SkillCondition(),
    icon="1️⃣"
))

# Outer Post Averseness
register_skill(Skill(
    id="outer_post_averseness",
    name="Outer Post Averseness",
    description="Moderately decrease performance in brackets 6-8.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.START_BONUS, -0.2, 1.0)],
    condition=SkillCondition(),
    icon="8️⃣"
))

# Standard Distance ×
register_skill(Skill(
    id="standard_distance_x",
    name="Standard Distance ×",
    description="Moderately decrease performance over standard distances (multiples of 400m).",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.2, 5.0)],
    condition=SkillCondition(),
    icon="📏"
))

# Non-Standard Distance ×
register_skill(Skill(
    id="non_standard_distance_x",
    name="Non-Standard Distance ×",
    description="Moderately decrease performance over non-standard distances (non-multiples of 400m).",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.2, 5.0)],
    condition=SkillCondition(),
    icon="📏"
))

# =============================================================================
# ADDITIONAL POSITIVE SKILLS
# =============================================================================

# Ruler of Japan
register_skill(Skill(
    id="ruler_of_japan",
    name="Ruler of Japan",
    description="I'll tackle this with everything I've got!",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 4.0)],
    condition=SkillCondition(),
    icon="🇯🇵"
))

# Front Runner Savvy
register_skill(Skill(
    id="front_runner_savvy_gold",
    name="Front Runner Savvy",
    description="Increase ability to get into pace early-race. (Front Runner)",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 3.0)],
    condition=SkillCondition(
        running_style=RunningStyleRequirement.FR,
        phase=SkillTriggerPhase.EARLY
    ),
    icon="🏃"
))

register_skill(Skill(
    id="front_runner_savvy_white",
    name="Front Runner Savvy",
    description="Slightly increase ability to get into pace early-race. (Front Runner)",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.0)],
    condition=SkillCondition(
        running_style=RunningStyleRequirement.FR,
        phase=SkillTriggerPhase.EARLY
    ),
    icon="🏃"
))


# =============================================================================
# RACECOURSE SKILLS (Positive)
# =============================================================================

register_skill(Skill(
    id="tokyo_racecourse_gold",
    name="Tokyo Racecourse",
    description="Increase performance at Tokyo Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="tokyo_racecourse_white",
    name="Tokyo Racecourse",
    description="Moderately increase performance at Tokyo Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="nakayama_racecourse_gold",
    name="Nakayama Racecourse",
    description="Increase performance at Nakayama Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="nakayama_racecourse_white",
    name="Nakayama Racecourse",
    description="Moderately increase performance at Nakayama Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="hanshin_racecourse_gold",
    name="Hanshin Racecourse",
    description="Increase performance at Hanshin Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="hanshin_racecourse_white",
    name="Hanshin Racecourse",
    description="Moderately increase performance at Hanshin Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="kyoto_racecourse_gold",
    name="Kyoto Racecourse",
    description="Increase performance at Kyoto Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="kyoto_racecourse_white",
    name="Kyoto Racecourse",
    description="Moderately increase performance at Kyoto Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="chukyo_racecourse_gold",
    name="Chukyo Racecourse",
    description="Increase performance at Chukyo Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="chukyo_racecourse_white",
    name="Chukyo Racecourse",
    description="Moderately increase performance at Chukyo Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="sapporo_racecourse_gold",
    name="Sapporo Racecourse",
    description="Increase performance at Sapporo Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="sapporo_racecourse_white",
    name="Sapporo Racecourse",
    description="Moderately increase performance at Sapporo Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="hakodate_racecourse_gold",
    name="Hakodate Racecourse",
    description="Increase performance at Hakodate Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="hakodate_racecourse_white",
    name="Hakodate Racecourse",
    description="Moderately increase performance at Hakodate Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="fukushima_racecourse_gold",
    name="Fukushima Racecourse",
    description="Increase performance at Fukushima Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="fukushima_racecourse_white",
    name="Fukushima Racecourse",
    description="Moderately increase performance at Fukushima Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="niigata_racecourse_gold",
    name="Niigata Racecourse",
    description="Increase performance at Niigata Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="niigata_racecourse_white",
    name="Niigata Racecourse",
    description="Moderately increase performance at Niigata Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="kokura_racecourse_gold",
    name="Kokura Racecourse",
    description="Increase performance at Kokura Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="kokura_racecourse_white",
    name="Kokura Racecourse",
    description="Moderately increase performance at Kokura Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="oi_racecourse_gold",
    name="Oi Racecourse",
    description="Increase performance at Oi Racecourse.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="oi_racecourse_white",
    name="Oi Racecourse",
    description="Moderately increase performance at Oi Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

# =============================================================================
# RACECOURSE SKILLS (Negative)
# =============================================================================

register_skill(Skill(
    id="tokyo_racecourse_x",
    name="Tokyo Racecourse ×",
    description="Moderately decrease performance at Tokyo Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="nakayama_racecourse_x",
    name="Nakayama Racecourse ×",
    description="Moderately decrease performance at Nakayama Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="hanshin_racecourse_x",
    name="Hanshin Racecourse ×",
    description="Moderately decrease performance at Hanshin Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="kyoto_racecourse_x",
    name="Kyoto Racecourse ×",
    description="Moderately decrease performance at Kyoto Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="chukyo_racecourse_x",
    name="Chukyo Racecourse ×",
    description="Moderately decrease performance at Chukyo Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="sapporo_racecourse_x",
    name="Sapporo Racecourse ×",
    description="Moderately decrease performance at Sapporo Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="hakodate_racecourse_x",
    name="Hakodate Racecourse ×",
    description="Moderately decrease performance at Hakodate Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="fukushima_racecourse_x",
    name="Fukushima Racecourse ×",
    description="Moderately decrease performance at Fukushima Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="niigata_racecourse_x",
    name="Niigata Racecourse ×",
    description="Moderately decrease performance at Niigata Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="kokura_racecourse_x",
    name="Kokura Racecourse ×",
    description="Moderately decrease performance at Kokura Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="oi_racecourse_x",
    name="Oi Racecourse ×",
    description="Moderately decrease performance at Oi Racecourse.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏟️"
))

# =============================================================================
# CONDITION NEGATIVE SKILLS
# =============================================================================

register_skill(Skill(
    id="right_handed_x",
    name="Right-Handed ×",
    description="Moderately decrease performance on right-handed tracks.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="➡️"
))

register_skill(Skill(
    id="left_handed_x",
    name="Left-Handed ×",
    description="Moderately decrease performance on left-handed tracks.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="⬅️"
))

register_skill(Skill(
    id="spring_runner_x",
    name="Spring Runner ×",
    description="Moderately decrease performance in spring.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🌸"
))

register_skill(Skill(
    id="summer_runner_x",
    name="Summer Runner ×",
    description="Moderately decrease performance in summer.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="☀️"
))

register_skill(Skill(
    id="fall_runner_x",
    name="Fall Runner ×",
    description="Moderately decrease performance in fall.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🍂"
))

register_skill(Skill(
    id="winter_runner_x",
    name="Winter Runner ×",
    description="Moderately decrease performance in winter.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="❄️"
))

register_skill(Skill(
    id="firm_conditions_x",
    name="Firm Conditions ×",
    description="Moderately decrease performance on firm ground.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="☀️"
))

register_skill(Skill(
    id="3d_nail_art",
    name="♡ 3D Nail Art",
    description="Moderately decrease performance on firm ground.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="💅"
))

register_skill(Skill(
    id="wet_conditions_x",
    name="Wet Conditions ×",
    description="Moderately decrease performance on good, soft, and heavy ground.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="💧"
))

register_skill(Skill(
    id="rainy_days_x",
    name="Rainy Days ×",
    description="Moderately decrease performance in rainy weather.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🌧️"
))

register_skill(Skill(
    id="g1_averseness",
    name="G1 Averseness",
    description="Moderately decrease performance in G1 or otherwise important races.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, -0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏆"
))

# =============================================================================
# SPECIAL CONDITION SKILLS
# =============================================================================

register_skill(Skill(
    id="fall_frenzy",
    name="Fall Frenzy",
    description="Increase performance in fall, boosting Speed and Power.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.35, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.2, 5.0)
    ],
    condition=SkillCondition(),
    icon="🍂"
))

register_skill(Skill(
    id="spring_spectacle",
    name="Spring Spectacle",
    description="Increase performance in spring, boosting Speed and Power.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.35, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.2, 5.0)
    ],
    condition=SkillCondition(),
    icon="🌸"
))

register_skill(Skill(
    id="right_handed_demon",
    name="Right-Handed Demon",
    description="Increase proficiency in right-handed tracks, increasing Speed and Power.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.35, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.2, 5.0)
    ],
    condition=SkillCondition(),
    icon="➡️"
))

register_skill(Skill(
    id="firm_course_menace",
    name="Firm Course Menace",
    description="Increase performance on firm ground, boosting Power and Speed.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.35, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.2, 5.0)
    ],
    condition=SkillCondition(),
    icon="☀️"
))

register_skill(Skill(
    id="yodo_invicta",
    name="Yodo Invicta",
    description="Increase performance at Kyoto Racecourse, boosting Stamina and Wit.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.RECOVERY, 2.5, 1.0),
        SkillEffect(SkillEffectType.VISION, 0.2, 5.0)
    ],
    condition=SkillCondition(),
    icon="🏟️"
))

register_skill(Skill(
    id="unchanging",
    name="Unchanging",
    description="Greatly increase performance with the same ambition of days past.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 5.0)],
    condition=SkillCondition(),
    icon="💪"
))

register_skill(Skill(
    id="unquenched_thirst",
    name="Unquenched Thirst",
    description="Moderately increase performance with the desire to race.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🔥"
))

register_skill(Skill(
    id="chin_up_derby_umamusume",
    name="Chin Up, Derby Umamusume!",
    description="Feel closer to being Japan's top racer, moderately increasing performance.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 5.0)],
    condition=SkillCondition(),
    icon="🏇"
))

register_skill(Skill(
    id="for_the_team",
    name="For the Team",
    description="The whole team feels super determined to win this special race, greatly increasing performance.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.45, 5.0)],
    condition=SkillCondition(),
    icon="👥"
))

# =============================================================================
# CHARACTER SUPPORT SKILLS (Silence Suzuka themed)
# =============================================================================

register_skill(Skill(
    id="towards_the_scenery_i_seek",
    name="Towards the Scenery I Seek",
    description="Moderately increase performance in pursuit of that long sought-after scenery.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 4.0)],
    condition=SkillCondition(),
    icon="🏔️"
))

register_skill(Skill(
    id="show_me_what_lies_beyond",
    name="Show Me What Lies Beyond!",
    description="Moderately increase Silence Suzuka's performance thanks to the desire to see her running reach new heights.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 4.0)],
    condition=SkillCondition(),
    icon="🌅"
))

register_skill(Skill(
    id="hoiya_have_a_good_run",
    name="Hoiya! Have a Good Run!",
    description="Moderately increase Silence Suzuka's performance thanks to a charm that guarantees a satisfying run.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 4.0)],
    condition=SkillCondition(),
    icon="🎋"
))

register_skill(Skill(
    id="as_a_friend_and_rival",
    name="As a Friend and Rival",
    description="Moderately increase Silence Suzuka's performance through the happiness felt seeing a friend find their running style.",
    rarity=SkillRarity.WHITE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 4.0)],
    condition=SkillCondition(),
    icon="🤝"
))

register_skill(Skill(
    id="cheers_of_a_fellow_dreamer",
    name="Cheers of a Fellow Dreamer",
    description="Recover Silence Suzuka's endurance on a corner in the second half of the race through a friend's cheers of support.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 3.5, 1.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.SECOND_HALF,
        terrain=SkillTriggerTerrain.CORNER
    ),
    icon="📣"
))


# =============================================================================
# SKILL UTILITIES
# =============================================================================

def get_skill_by_id(skill_id: str) -> Optional[Skill]:
    """Get a skill by its ID"""
    return SKILLS_DATABASE.get(skill_id)


def get_skills_by_rarity(rarity: SkillRarity) -> List[Skill]:
    """Get all skills of a specific rarity"""
    return [s for s in SKILLS_DATABASE.values() if s.rarity == rarity]


def get_skills_by_running_style(style: RunningStyleRequirement) -> List[Skill]:
    """Get all skills available for a running style (including ANY)"""
    return [
        s for s in SKILLS_DATABASE.values() 
        if s.condition.running_style in (style, RunningStyleRequirement.ANY)
    ]


def get_skills_by_race_type(race_type: RaceTypeRequirement) -> List[Skill]:
    """Get all skills available for a race type (including ANY)"""
    return [
        s for s in SKILLS_DATABASE.values()
        if s.condition.race_type in (race_type, RaceTypeRequirement.ANY)
    ]


def get_all_skill_ids() -> List[str]:
    """Get list of all skill IDs"""
    return list(SKILLS_DATABASE.keys())


def get_skill_categories() -> Dict[str, List[str]]:
    """Get skills organized by category for UI"""
    categories = {
        "Speed - General": [],
        "Speed - Front Runner": [],
        "Speed - Pace Chaser": [],
        "Speed - Late Surger": [],
        "Speed - End Closer": [],
        "Speed - Sprint": [],
        "Speed - Mile": [],
        "Speed - Medium": [],
        "Speed - Long": [],
        "Acceleration": [],
        "Recovery": [],
        "Stamina Save": [],
        "Start": [],
        "Navigation": [],
        "Debuff": [],
        "Conditions": [],
        "Unique": [],
    }
    
    for skill_id, skill in SKILLS_DATABASE.items():
        # Put unique skills in their own category
        if skill.rarity == SkillRarity.UNIQUE or skill.rarity == SkillRarity.EVOLUTION:
            categories["Unique"].append(skill_id)
            continue
            
        # Categorize by effect type first
        primary_effect = skill.effects[0].effect_type if skill.effects else None
        
        if primary_effect == SkillEffectType.SPEED or primary_effect == SkillEffectType.CURRENT_SPEED:
            # Sub-categorize speed skills
            if skill.condition.running_style == RunningStyleRequirement.FR:
                categories["Speed - Front Runner"].append(skill_id)
            elif skill.condition.running_style == RunningStyleRequirement.PC:
                categories["Speed - Pace Chaser"].append(skill_id)
            elif skill.condition.running_style == RunningStyleRequirement.LS:
                categories["Speed - Late Surger"].append(skill_id)
            elif skill.condition.running_style == RunningStyleRequirement.EC:
                categories["Speed - End Closer"].append(skill_id)
            elif skill.condition.race_type == RaceTypeRequirement.SPRINT:
                categories["Speed - Sprint"].append(skill_id)
            elif skill.condition.race_type == RaceTypeRequirement.MILE:
                categories["Speed - Mile"].append(skill_id)
            elif skill.condition.race_type == RaceTypeRequirement.MEDIUM:
                categories["Speed - Medium"].append(skill_id)
            elif skill.condition.race_type == RaceTypeRequirement.LONG:
                categories["Speed - Long"].append(skill_id)
            else:
                categories["Speed - General"].append(skill_id)
        elif primary_effect == SkillEffectType.ACCELERATION:
            categories["Acceleration"].append(skill_id)
        elif primary_effect == SkillEffectType.RECOVERY:
            categories["Recovery"].append(skill_id)
        elif primary_effect == SkillEffectType.STAMINA_SAVE:
            categories["Stamina Save"].append(skill_id)
        elif primary_effect == SkillEffectType.START_BONUS:
            categories["Start"].append(skill_id)
        elif primary_effect == SkillEffectType.VISION:
            categories["Navigation"].append(skill_id)
        elif primary_effect == SkillEffectType.DEBUFF_SPEED:
            categories["Debuff"].append(skill_id)
        else:
            categories["Conditions"].append(skill_id)
    
    # Remove empty categories
    return {k: v for k, v in categories.items() if v}


# =============================================================================
# SAMPLE UNIQUE SKILLS (固有スキル) - Character-specific skills
# =============================================================================
# These always activate at 100% when conditions are met
# Effects are 20% stronger than normal skills

register_skill(Skill(
    id="special_week_unique",
    name="Winning Dream",
    description="Unique skill of Special Week. Greatly increases velocity in the final stretch.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 4.0)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    activation_chance=1.0,
    icon="🏆",
    is_unique=True,
    uma_specific="Special Week"
))

register_skill(Skill(
    id="silence_suzuka_unique",
    name="Silent Sprint",
    description="Unique skill of Silence Suzuka. Greatly increases speed when leading mid-race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.50, 5.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        running_style=RunningStyleRequirement.FR
    ),
    activation_chance=1.0,
    icon="🔇",
    is_unique=True,
    uma_specific="Silence Suzuka"
))

register_skill(Skill(
    id="tokai_teio_unique",
    name="Emperor's Majesty",
    description="Unique skill of Tokai Teio. Greatly increases acceleration on the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.ACCELERATION, 0.65, 3.5)],
    condition=SkillCondition(
        terrain=SkillTriggerTerrain.CORNER,
        corner_number=4  # Final corner
    ),
    activation_chance=1.0,
    icon="👑",
    is_unique=True,
    uma_specific="Tokai Teio"
))

register_skill(Skill(
    id="rice_shower_unique",
    name="Cursed Runner",
    description="Unique skill of Rice Shower. Greatly increases velocity when chasing the leader in late race.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.48, 4.5)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK
    ),
    activation_chance=1.0,
    icon="🌧️",
    is_unique=True,
    uma_specific="Rice Shower"
))


# =============================================================================
# COMPLETE UNIQUE SKILLS DATABASE (固有スキル) - All Uma Musume Characters
# =============================================================================

# --- Vodka ---
register_skill(Skill(
    id="vodka_unique",
    name="Straight Line Demon",
    description="Vodka's unique skill. Dramatically increases speed on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.52, 4.5)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    activation_chance=1.0,
    icon="🍸",
    is_unique=True,
    uma_specific="Vodka"
))

# --- Daiwa Scarlet ---
register_skill(Skill(
    id="daiwa_scarlet_unique",
    name="Scarlet Pride",
    description="Daiwa Scarlet's unique skill. Greatly increases speed when competing neck and neck.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.35, 4.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        requires_challenge=True
    ),
    activation_chance=1.0,
    icon="🌹",
    is_unique=True,
    uma_specific="Daiwa Scarlet"
))

# --- Gold Ship ---
register_skill(Skill(
    id="gold_ship_unique",
    name="Full Speed Ahead!",
    description="Gold Ship's unique skill. Greatly increases speed when making a late surge from behind.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.EC
    ),
    activation_chance=1.0,
    icon="🚢",
    is_unique=True,
    uma_specific="Gold Ship"
))

# --- Mejiro McQueen ---
register_skill(Skill(
    id="mejiro_mcqueen_unique",
    name="Immutable Nobility",
    description="Mejiro McQueen's unique skill. Greatly increases speed when maintaining position.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.48, 5.0)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="👸",
    is_unique=True,
    uma_specific="Mejiro McQueen"
))

# --- Oguri Cap ---
register_skill(Skill(
    id="oguri_cap_unique",
    name="Unstoppable Will",
    description="Oguri Cap's unique skill. Greatly increases speed and recovers stamina.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.RECOVERY, 0.05, 0.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    activation_chance=1.0,
    icon="🧢",
    is_unique=True,
    uma_specific="Oguri Cap"
))

# --- Grass Wonder ---
register_skill(Skill(
    id="grass_wonder_unique",
    name="Wonder of the World",
    description="Grass Wonder's unique skill. Greatly increases speed when surging from mid-pack.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.50, 4.5)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.MIDPACK
    ),
    activation_chance=1.0,
    icon="🌿",
    is_unique=True,
    uma_specific="Grass Wonder"
))

# --- El Condor Pasa ---
register_skill(Skill(
    id="el_condor_pasa_unique",
    name="Condor's Flight",
    description="El Condor Pasa's unique skill. Dramatically increases speed on the final straight.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.38, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    activation_chance=1.0,
    icon="🦅",
    is_unique=True,
    uma_specific="El Condor Pasa"
))

# --- Haru Urara ---
register_skill(Skill(
    id="haru_urara_unique",
    name="Never Give Up!",
    description="Haru Urara's unique skill. Greatly increases speed when far behind.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.50, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.BACK
    ),
    activation_chance=1.0,
    icon="🌸",
    is_unique=True,
    uma_specific="Haru Urara"
))

# --- Maruzensky ---
register_skill(Skill(
    id="maruzensky_unique",
    name="Super Car",
    description="Maruzensky's unique skill. Dramatically increases speed when escaping at the front.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        running_style=RunningStyleRequirement.FR
    ),
    activation_chance=1.0,
    icon="🏎️",
    is_unique=True,
    uma_specific="Maruzensky"
))

# --- Taiki Shuttle ---
register_skill(Skill(
    id="taiki_shuttle_unique",
    name="Mile Legend",
    description="Taiki Shuttle's unique skill. Dramatically increases speed in mile races.",
    rarity=SkillRarity.UNIQUE,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.55, 4.5)],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        race_type=RaceTypeRequirement.MILE
    ),
    activation_chance=1.0,
    icon="🚀",
    is_unique=True,
    uma_specific="Taiki Shuttle"
))

# --- Twin Turbo ---
register_skill(Skill(
    id="twin_turbo_unique",
    name="Turbo Engine",
    description="Twin Turbo's unique skill. Dramatically increases speed when escaping early.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.58, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.50, 4.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.EARLY,
        position=SkillTriggerPosition.FRONT,
        running_style=RunningStyleRequirement.FR
    ),
    activation_chance=1.0,
    icon="💨",
    is_unique=True,
    uma_specific="Twin Turbo"
))

# --- Narita Brian ---
register_skill(Skill(
    id="narita_brian_unique",
    name="Shadow of Assassin",
    description="Narita Brian's unique skill. Greatly increases speed when overtaking on the final corner.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.42, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        requires_passing=True
    ),
    activation_chance=1.0,
    icon="🗡️",
    is_unique=True,
    uma_specific="Narita Brian"
))

# --- Symboli Rudolf ---
register_skill(Skill(
    id="symboli_rudolf_unique",
    name="Emperor's Dignity",
    description="Symboli Rudolf's unique skill. Greatly increases speed when maintaining lead.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 5.0),
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.15, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT
    ),
    activation_chance=1.0,
    icon="🏛️",
    is_unique=True,
    uma_specific="Symboli Rudolf"
))

# --- Sakura Bakushin O ---
register_skill(Skill(
    id="sakura_bakushin_o_unique",
    name="Bakushin Power!",
    description="Sakura Bakushin O's unique skill. Dramatically increases speed in sprint races.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.58, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.52, 4.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    activation_chance=1.0,
    icon="🌸",
    is_unique=True,
    uma_specific="Sakura Bakushin O"
))

# --- Kitasan Black ---
register_skill(Skill(
    id="kitasan_black_unique",
    name="Song of Victory",
    description="Kitasan Black's unique skill. Dramatically increases speed when leading.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.50, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.FRONT
    ),
    activation_chance=1.0,
    icon="🎤",
    is_unique=True,
    uma_specific="Kitasan Black"
))

# --- Satono Diamond ---
register_skill(Skill(
    id="satono_diamond_unique",
    name="Diamond Sparkle",
    description="Satono Diamond's unique skill. Greatly increases speed with dazzling acceleration.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 4.5)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    activation_chance=1.0,
    icon="💎",
    is_unique=True,
    uma_specific="Satono Diamond"
))

# --- Manhattan Cafe ---
register_skill(Skill(
    id="manhattan_cafe_unique",
    name="Dark Surge",
    description="Manhattan Cafe's unique skill. Greatly increases speed when surging from behind.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.48, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        position=SkillTriggerPosition.BACK,
        running_style=RunningStyleRequirement.EC
    ),
    activation_chance=1.0,
    icon="☕",
    is_unique=True,
    uma_specific="Manhattan Cafe"
))

# --- Agnes Tachyon ---
register_skill(Skill(
    id="agnes_tachyon_unique",
    name="Speed of Light",
    description="Agnes Tachyon's unique skill. Dramatically increases speed, breaking the limits.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.58, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.55, 4.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    activation_chance=1.0,
    icon="💡",
    is_unique=True,
    uma_specific="Agnes Tachyon"
))

# --- Smart Falcon ---
register_skill(Skill(
    id="smart_falcon_unique",
    name="Falcon Sprint",
    description="Smart Falcon's unique skill. Greatly increases speed on dirt tracks.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.48, 4.5)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    activation_chance=1.0,
    icon="🦅",
    is_unique=True,
    uma_specific="Smart Falcon"
))

# --- Copano Rickey ---
register_skill(Skill(
    id="copano_rickey_unique",
    name="Dirt Emperor",
    description="Copano Rickey's unique skill. Dramatically increases speed on dirt tracks.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.50, 4.5)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    activation_chance=1.0,
    icon="👑",
    is_unique=True,
    uma_specific="Copano Rickey"
))

# --- Meisho Doto ---
register_skill(Skill(
    id="meisho_doto_unique",
    name="Raging Storm",
    description="Meisho Doto's unique skill. Greatly increases speed when surging from behind.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER,
        position=SkillTriggerPosition.BACK
    ),
    activation_chance=1.0,
    icon="🌊",
    is_unique=True,
    uma_specific="Meisho Doto"
))

# --- Air Groove ---
register_skill(Skill(
    id="air_groove_unique",
    name="Elegant Groove",
    description="Air Groove's unique skill. Greatly increases speed with elegant running.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.42, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="💃",
    is_unique=True,
    uma_specific="Air Groove"
))

# --- Seiun Sky ---
register_skill(Skill(
    id="seiun_sky_unique",
    name="Sky's Leap",
    description="Seiun Sky's unique skill. Dramatically increases speed when escaping.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.50, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        running_style=RunningStyleRequirement.FR
    ),
    activation_chance=1.0,
    icon="☁️",
    is_unique=True,
    uma_specific="Seiun Sky"
))

# --- King Halo ---
register_skill(Skill(
    id="king_halo_unique",
    name="Halo's Blessing",
    description="King Halo's unique skill. Greatly increases speed with divine light.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.RECOVERY, 0.03, 0.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    activation_chance=1.0,
    icon="👑",
    is_unique=True,
    uma_specific="King Halo"
))

# --- T.M. Opera O ---
register_skill(Skill(
    id="tm_opera_o_unique",
    name="Opera's Grand Finale",
    description="T.M. Opera O's unique skill. Dramatically increases speed in the final act.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.50, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="🎭",
    is_unique=True,
    uma_specific="T.M. Opera O"
))

# --- Admire Vega ---
register_skill(Skill(
    id="admire_vega_unique",
    name="Vega's Star",
    description="Admire Vega's unique skill. Greatly increases speed like a shooting star.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    activation_chance=1.0,
    icon="⭐",
    is_unique=True,
    uma_specific="Admire Vega"
))

# --- Narita Taishin ---
register_skill(Skill(
    id="narita_taishin_unique",
    name="Taishin's Conviction",
    description="Narita Taishin's unique skill. Greatly increases speed with pure determination.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.48, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        requires_passing=True
    ),
    activation_chance=1.0,
    icon="💪",
    is_unique=True,
    uma_specific="Narita Taishin"
))

# --- Winning Ticket ---
register_skill(Skill(
    id="winning_ticket_unique",
    name="Winning Chance",
    description="Winning Ticket's unique skill. Greatly increases speed with winning spirit.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.42, 4.5)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    activation_chance=1.0,
    icon="🎫",
    is_unique=True,
    uma_specific="Winning Ticket"
))

# --- Biwa Hayahide ---
register_skill(Skill(
    id="biwa_hayahide_unique",
    name="Professor's Calculation",
    description="Biwa Hayahide's unique skill. Greatly increases speed with calculated precision.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 5.0),
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.12, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="📖",
    is_unique=True,
    uma_specific="Biwa Hayahide"
))

# --- Mayano Top Gun ---
register_skill(Skill(
    id="mayano_top_gun_unique",
    name="Top Gun's Assault",
    description="Mayano Top Gun's unique skill. Dramatically increases speed with aerial assault.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.48, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        requires_passing=True
    ),
    activation_chance=1.0,
    icon="✈️",
    is_unique=True,
    uma_specific="Mayano Top Gun"
))

# --- Zenno Rob Roy ---
register_skill(Skill(
    id="zenno_rob_roy_unique",
    name="Outlaw's Freedom",
    description="Zenno Rob Roy's unique skill. Greatly increases speed with fearless running.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.CORNER
    ),
    activation_chance=1.0,
    icon="🏴",
    is_unique=True,
    uma_specific="Zenno Rob Roy"
))

# --- Fine Motion ---
register_skill(Skill(
    id="fine_motion_unique",
    name="Motion Picture",
    description="Fine Motion's unique skill. Greatly increases speed with graceful movement.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.42, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="🎬",
    is_unique=True,
    uma_specific="Fine Motion"
))

# --- Jungle Pocket ---
register_skill(Skill(
    id="jungle_pocket_unique",
    name="Jungle Force",
    description="Jungle Pocket's unique skill. Dramatically increases speed with raw power.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.48, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        requires_challenge=True
    ),
    activation_chance=1.0,
    icon="🌴",
    is_unique=True,
    uma_specific="Jungle Pocket"
))

# --- Agnes Digital ---
register_skill(Skill(
    id="agnes_digital_unique",
    name="Digital Processing",
    description="Agnes Digital's unique skill. Dramatically increases speed with digital precision.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.50, 4.5)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    activation_chance=1.0,
    icon="💻",
    is_unique=True,
    uma_specific="Agnes Digital"
))

# --- Curren Chan ---
register_skill(Skill(
    id="curren_chan_unique",
    name="Curren's Flow",
    description="Curren Chan's unique skill. Greatly increases speed with steady pace.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.10, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="💧",
    is_unique=True,
    uma_specific="Curren Chan"
))

# --- Tamamo Cross ---
register_skill(Skill(
    id="tamamo_cross_unique",
    name="Cross Counter",
    description="Tamamo Cross's unique skill. Dramatically increases speed with counterattack.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.48, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK,
        requires_passing=True
    ),
    activation_chance=1.0,
    icon="✨",
    is_unique=True,
    uma_specific="Tamamo Cross"
))

# --- Duramente ---
register_skill(Skill(
    id="duramente_unique",
    name="Duramente's Force",
    description="Duramente's unique skill. Dramatically increases speed with overwhelming power.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.52, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="⚡",
    is_unique=True,
    uma_specific="Duramente"
))

# --- Mihono Bourbon ---
register_skill(Skill(
    id="mihono_bourbon_unique",
    name="Cyborg Sprint",
    description="Mihono Bourbon's unique skill. Dramatically increases speed with machine-like precision.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.50, 4.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.FRONT,
        running_style=RunningStyleRequirement.FR
    ),
    activation_chance=1.0,
    icon="🤖",
    is_unique=True,
    uma_specific="Mihono Bourbon"
))

# --- Nice Nature ---
register_skill(Skill(
    id="nice_nature_unique",
    name="Nice and Steady",
    description="Nice Nature's unique skill. Greatly increases speed with consistent performance.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 5.0),
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.12, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK
    ),
    activation_chance=1.0,
    icon="😊",
    is_unique=True,
    uma_specific="Nice Nature"
))

# --- Super Creek ---
register_skill(Skill(
    id="super_creek_unique",
    name="Creek's Flow",
    description="Super Creek's unique skill. Greatly increases stamina efficiency.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.18, 6.0),
        SkillEffect(SkillEffectType.SPEED, 0.35, 6.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    activation_chance=1.0,
    icon="🌊",
    is_unique=True,
    uma_specific="Super Creek"
))

# --- Ines Fujin ---
register_skill(Skill(
    id="ines_fujin_unique",
    name="Wind God's Blessing",
    description="Ines Fujin's unique skill. Dramatically increases speed with divine wind.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.48, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    activation_chance=1.0,
    icon="🌬️",
    is_unique=True,
    uma_specific="Ines Fujin"
))

# --- Sweep Tosho ---
register_skill(Skill(
    id="sweep_tosho_unique",
    name="Sweeping Victory",
    description="Sweep Tosho's unique skill. Dramatically increases speed in the final stretch.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    activation_chance=1.0,
    icon="🧹",
    is_unique=True,
    uma_specific="Sweep Tosho"
))

# --- Yaeno Muteki ---
register_skill(Skill(
    id="yaeno_muteki_unique",
    name="Invincible Spirit",
    description="Yaeno Muteki's unique skill. Greatly increases speed with indomitable spirit.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 4.5),
        SkillEffect(SkillEffectType.RECOVERY, 0.03, 0.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        requires_challenge=True
    ),
    activation_chance=1.0,
    icon="🛡️",
    is_unique=True,
    uma_specific="Yaeno Muteki"
))

# --- Eishin Flash ---
register_skill(Skill(
    id="eishin_flash_unique",
    name="Flash Strike",
    description="Eishin Flash's unique skill. Dramatically increases speed with lightning fast burst.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.52, 4.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    activation_chance=1.0,
    icon="⚡",
    is_unique=True,
    uma_specific="Eishin Flash"
))

# --- Seeking the Pearl ---
register_skill(Skill(
    id="seeking_the_pearl_unique",
    name="Pearl Discovery",
    description="Seeking the Pearl's unique skill. Greatly increases speed when finding the gap.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.42, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        requires_passing=True
    ),
    activation_chance=1.0,
    icon="🦪",
    is_unique=True,
    uma_specific="Seeking the Pearl"
))

# --- Matikanetannahauser ---
register_skill(Skill(
    id="matikanetannahauser_unique",
    name="Tannhauser Gate",
    description="Matikanetannahauser's unique skill. Dramatically increases speed in long races.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 5.0),
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.15, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        race_type=RaceTypeRequirement.LONG
    ),
    activation_chance=1.0,
    icon="🚪",
    is_unique=True,
    uma_specific="Matikanetannahauser"
))

# --- Narita Top Road ---
register_skill(Skill(
    id="narita_top_road_unique",
    name="Top Road",
    description="Narita Top Road's unique skill. Greatly increases speed on the best path.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT
    ),
    activation_chance=1.0,
    icon="🛤️",
    is_unique=True,
    uma_specific="Narita Top Road"
))

# --- Sakura Chiyono O ---
register_skill(Skill(
    id="sakura_chiyono_o_unique",
    name="Eternal Sakura",
    description="Sakura Chiyono O's unique skill. Greatly increases speed with timeless grace.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        running_style=RunningStyleRequirement.EC
    ),
    activation_chance=1.0,
    icon="🌸",
    is_unique=True,
    uma_specific="Sakura Chiyono O"
))

# --- Daiichi Ruby ---
register_skill(Skill(
    id="daiichi_ruby_unique",
    name="Ruby Sparkle",
    description="Daiichi Ruby's unique skill. Greatly increases speed with gem-like brilliance.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        race_type=RaceTypeRequirement.SPRINT
    ),
    activation_chance=1.0,
    icon="💎",
    is_unique=True,
    uma_specific="Daiichi Ruby"
))

# --- Nishino Flower ---
register_skill(Skill(
    id="nishino_flower_unique",
    name="Flower Bloom",
    description="Nishino Flower's unique skill. Greatly increases speed with blooming spirit.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.42, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="🌺",
    is_unique=True,
    uma_specific="Nishino Flower"
))


# =============================================================================
# JP-EXCLUSIVE SKILLS (日本版専用スキル)
# =============================================================================

# --- Scenario-Specific Skills ---
register_skill(Skill(
    id="aoharu_burst",
    name="Aoharu Burst",
    description="JP: Aoharu scenario skill. Greatly increases speed with team spirit.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.42, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.35, 4.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="💙"
))

register_skill(Skill(
    id="climax_domination",
    name="Climax Domination",
    description="JP: Climax scenario skill. Dramatically increases speed in climax races.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.42, 4.5)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="🔥"
))

register_skill(Skill(
    id="grand_masters_pride",
    name="Grand Masters Pride",
    description="JP: Grand Masters scenario skill. Greatly increases speed with veteran wisdom.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 4.5),
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.12, 4.5)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🏆"
))

register_skill(Skill(
    id="make_a_new_track",
    name="Make a New Track!!",
    description="JP: Make a New Track scenario skill. Creates new possibilities.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.40, 4.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="🎵"
))

# --- L'Arc Scenario Skills ---
register_skill(Skill(
    id="larc_arc_de_triomphe",
    name="L'Arc Spirit",
    description="JP: L'Arc scenario skill. Greatly increases speed when racing in France.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        race_type=RaceTypeRequirement.MEDIUM
    ),
    icon="🇫🇷"
))

register_skill(Skill(
    id="larc_victory",
    name="L'Arc Victory",
    description="JP: L'Arc scenario skill. Dramatically increases speed aiming for victory.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.48, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        requires_challenge=True
    ),
    icon="🏆"
))

# --- Event-Limited Skills ---
register_skill(Skill(
    id="valentine_heart",
    name="Valentine Heart",
    description="JP: Valentine event skill. Increases speed with love.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.38, 3.5)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="💝"
))

register_skill(Skill(
    id="christmas_miracle",
    name="Christmas Miracle",
    description="JP: Christmas event skill. Increases speed with holiday spirit.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.40, 3.5),
        SkillEffect(SkillEffectType.RECOVERY, 0.02, 0.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🎄"
))

register_skill(Skill(
    id="summer_festival",
    name="Summer Festival",
    description="JP: Summer event skill. Increases speed with summer energy.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.40, 3.5)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="🎆"
))

register_skill(Skill(
    id="new_year_blessing",
    name="New Year Blessing",
    description="JP: New Year event skill. Increases speed with new year fortune.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.38, 3.5),
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.08, 3.5)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="🎍"
))

# --- Anniversary Skills ---
register_skill(Skill(
    id="anniversary_celebration",
    name="Anniversary Celebration",
    description="JP: Anniversary skill. Greatly increases speed in celebration.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.45, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.40, 4.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="🎉"
))

register_skill(Skill(
    id="halloween_spirit",
    name="Halloween Spirit",
    description="JP: Halloween event skill. Increases speed with Halloween energy.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.40, 3.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.35, 3.5)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LATE),
    icon="🎃"
))

register_skill(Skill(
    id="white_day_blessing",
    name="White Day Blessing",
    description="JP: White Day event skill. Increases speed with spring blessing.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.38, 3.5),
        SkillEffect(SkillEffectType.RECOVERY, 0.02, 0.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.MID),
    icon="🌷"
))

register_skill(Skill(
    id="cinderella_glass",
    name="Cinderella Glass (Collab)",
    description="JP: Cinderella Glass collab skill. Increases speed with magical pumpkin.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.42, 4.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="🎪"
))

register_skill(Skill(
    id="uaf_champion",
    name="UAF Champion",
    description="JP: Uma Association Championship skill. Ultimate racing spirit.",
    rarity=SkillRarity.GOLD,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.48, 5.0),
        SkillEffect(SkillEffectType.STAMINA_SAVE, 0.10, 5.0)
    ],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="🏅"
))

# --- More Unique Skills for Additional Characters ---

register_skill(Skill(
    id="mejiro_ryan_unique",
    name="Ryan's Pride",
    description="Mejiro Ryan's unique skill. Greatly increases speed with Irish spirit.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="🍀",
    is_unique=True,
    uma_specific="Mejiro Ryan"
))

register_skill(Skill(
    id="mejiro_molotov_unique",
    name="Molotov Break",
    description="Mejiro Molotov's unique skill. Dramatically increases speed with explosive power.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.55, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.52, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.FRONT
    ),
    activation_chance=1.0,
    icon="💣",
    is_unique=True,
    uma_specific="Mejiro Molotov"
))

register_skill(Skill(
    id="gold_city_unique",
    name="City Lights",
    description="Gold City's unique skill. Increases speed with metropolitan spirit.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.42, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="🌃",
    is_unique=True,
    uma_specific="Gold City"
))

register_skill(Skill(
    id="mejiro_ardan_unique",
    name="Ardan's Charge",
    description="Mejiro Ardan's unique skill. Dramatically increases speed with noble charge.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.50, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        position=SkillTriggerPosition.MIDPACK,
        requires_passing=True
    ),
    activation_chance=1.0,
    icon="⚔️",
    is_unique=True,
    uma_specific="Mejiro Ardan"
))

register_skill(Skill(
    id="tosen_jordan_unique",
    name="Jordan's Flight",
    description="Tosen Jordan's unique skill. Greatly increases speed in the final stretch.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.50, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.48, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        terrain=SkillTriggerTerrain.STRAIGHT
    ),
    activation_chance=1.0,
    icon="✈️",
    is_unique=True,
    uma_specific="Tosen Jordan"
))

register_skill(Skill(
    id="fine_motion_light_unique",
    name="Light Footwork",
    description="Fine Motion Light's unique skill. Greatly increases speed with fluid motion.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.45, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        running_style=RunningStyleRequirement.LS
    ),
    activation_chance=1.0,
    icon="💫",
    is_unique=True,
    uma_specific="Fine Motion Light"
))

register_skill(Skill(
    id="silence_suzuka_2_unique",
    name="Eternal Silence",
    description="Silence Suzuka (Derived)'s unique skill. Ultimate speed with eternal silence.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.58, 5.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.55, 5.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        running_style=RunningStyleRequirement.PC
    ),
    activation_chance=1.0,
    icon="🔇",
    is_unique=True,
    uma_specific="Silence Suzuka (Derived)"
))

register_skill(Skill(
    id="mejiro_dober_unique",
    name="Dober's Sprint",
    description="Mejiro Dober's unique skill. Dramatically increases speed in burst runs.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.52, 4.0),
        SkillEffect(SkillEffectType.ACCELERATION, 0.50, 4.0)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LAST_SPURT,
        running_style=RunningStyleRequirement.EC
    ),
    activation_chance=1.0,
    icon="🐕",
    is_unique=True,
    uma_specific="Mejiro Dober"
))

register_skill(Skill(
    id="water_sprite_unique",
    name="Water Spirit",
    description="Water Sprite's unique skill. Increases speed with water's flow.",
    rarity=SkillRarity.UNIQUE,
    effects=[
        SkillEffect(SkillEffectType.SPEED, 0.48, 4.5),
        SkillEffect(SkillEffectType.ACCELERATION, 0.42, 4.5)
    ],
    condition=SkillCondition(
        phase=SkillTriggerPhase.LATE,
        running_style=RunningStyleRequirement.LS
    ),
    activation_chance=1.0,
    icon="💦",
    is_unique=True,
    uma_specific="Water Sprite"
))


# =============================================================================
# SAMPLE EVOLVED SKILLS (進化スキル) - Awakened versions of existing skills
# =============================================================================
# These have 50% stronger effects and 30% longer duration

register_skill(Skill(
    id="straightaway_adept_evolved",
    name="Straightaway Mastery",
    description="Evolved version: Significantly increase velocity on a straight.",
    rarity=SkillRarity.EVOLUTION,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 4.0)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.STRAIGHT),
    icon="⚡➡️",
    is_evolved=True,
    evolved_from="straightaway_adept"
))

register_skill(Skill(
    id="corner_adept_evolved",
    name="Corner Mastery",
    description="Evolved version: Significantly increase velocity on a corner.",
    rarity=SkillRarity.EVOLUTION,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.25, 3.2)],
    condition=SkillCondition(terrain=SkillTriggerTerrain.CORNER),
    icon="⚡↩️",
    is_evolved=True,
    evolved_from="corner_adept"
))

register_skill(Skill(
    id="homestretch_haste_evolved",
    name="Homestretch Domination",
    description="Evolved version: Greatly increase velocity in the last spurt.",
    rarity=SkillRarity.EVOLUTION,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.35, 4.5)],
    condition=SkillCondition(phase=SkillTriggerPhase.LAST_SPURT),
    icon="⚡🏁",
    is_evolved=True,
    evolved_from="homestretch_haste"
))


# =============================================================================
# SAMPLE INHERITED SKILLS (継承スキル) - Skills passed from parent builds
# =============================================================================
# These get +5% activation bonus

register_skill(Skill(
    id="inherited_endurance",
    name="Inherited Endurance",
    description="An inherited skill from a champion. Recover stamina when positioned in the pack.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.RECOVERY, 0.04, 0.0)],  # Instant 4% recovery
    condition=SkillCondition(
        phase=SkillTriggerPhase.MID,
        position=SkillTriggerPosition.MIDPACK
    ),
    icon="🧬",
    is_inherited=True
))

register_skill(Skill(
    id="inherited_speed_burst",
    name="Inherited Speed Gene",
    description="An inherited skill granting a speed burst in the final sections.",
    rarity=SkillRarity.GOLD,
    effects=[SkillEffect(SkillEffectType.SPEED, 0.30, 3.0)],
    condition=SkillCondition(
        section_start=20,  # Sections 20-24 (late race)
        section_end=24
    ),
    icon="🧬",
    is_inherited=True
))


# Export commonly needed items
__all__ = [
    'Skill', 'SkillEffect', 'SkillCondition', 'ActiveSkill',
    'SkillRarity', 'SkillTriggerPhase', 'SkillTriggerPosition', 
    'SkillTriggerTerrain', 'SkillEffectType',
    'RunningStyleRequirement', 'RaceTypeRequirement',
    'SKILLS_DATABASE', 'get_skill_by_id', 'get_all_skill_ids',
    'get_skills_by_rarity', 'get_skills_by_running_style',
    'get_skills_by_race_type', 'get_skill_categories',
    # NEW exports
    'get_skill_activation_modifier', 'get_skill_effect_modifier', 'get_skill_duration_modifier',
    'UNIQUE_SKILL_ACTIVATION_RATE', 'INHERITED_SKILL_ACTIVATION_BONUS',
    'UNIQUE_SKILL_EFFECT_MULTIPLIER', 'EVOLVED_SKILL_EFFECT_MULTIPLIER',
    'EVOLVED_SKILL_DURATION_MULTIPLIER',
]
