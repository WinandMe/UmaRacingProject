"""
Harness Racing Engine - Extended Race Simulation

This module provides harness racing mechanics that complement the flat racing
engine in race_engine.py. Both engines use the same core philosophy but with
different stat calculations and race mechanics.

Key Differences from Flat Racing:
1. Pulling Power replaces Speed as primary stat
2. Sulky weight (700-850kg) affects performance
3. Gait consistency is critical for maintaining speed
4. Heats system for major races
5. Different acceleration model (from standing start with gate)
"""

import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple
from dataclasses import asdict

from harness_races import HarnessRace, HorseType, HarnessRaceFormat, HarnessRaceType
from HarnessConfigGenerator import HarnessHorseStats


# =============================================================================
# HARNESS RACING ENUMS
# =============================================================================

class HarnessRacePhase(Enum):
    """Phases of a harness race"""
    START = "start"        # 0-200m: Acceleration from standing start
    EARLY = "early"        # 200m-600m: Initial settling
    MID = "mid"            # 600m - Last 600m: Cruising
    LATE = "late"          # Last 600m - Final 200m: Attack setup
    FINAL_SPURT = "final"  # Last 200m: Final push


class HarnessRunningStyle(Enum):
    """Harness racing tactics"""
    FRONT_RUNNER = "FR"      # Lead from start
    MIDDLE_RUNNER = "MR"     # Middle position
    CLOSER = "CL"            # Come from behind


class HarnessGaitType(Enum):
    """Types of harness racing gaits"""
    TROTTER = "Trotter"      # 2:2 diagonal gait (most common in Europe)
    PACER = "Pacer"          # 2:2 lateral gait


# =============================================================================
# SULKY WEIGHT SYSTEM
# =============================================================================

@dataclass
class SulkyConfiguration:
    """Sulky and equipment weight"""
    sulky_weight: int = 700              # kg - European standard
    harness_weight: int = 25             # kg
    total_weight: int = field(default=725, init=False)
    
    def __post_init__(self):
        self.total_weight = self.sulky_weight + self.harness_weight
    
    def efficiency_factor(self) -> float:
        """How much weight affects efficiency (0.8-1.0)"""
        # Lighter sulkies (700-750kg) = 1.0x efficiency
        # Heavier sulkies (750-850kg) = reduced efficiency
        if self.total_weight <= 750:
            return 1.0
        elif self.total_weight > 850:
            return 0.85
        else:
            # Linear interpolation between 750-850kg
            return 1.0 - (self.total_weight - 750) / 100 * 0.15


@dataclass
class HarnessHorseState:
    """Current state of a harness racing horse during race"""
    # Basic info
    horse_id: str
    distance_covered: float = 0.0      # meters
    current_speed: float = 5.0         # m/s (walking speed)
    target_speed: float = 10.0         # m/s
    
    # Position
    current_position: int = 1           # 1 = leading, 2 = second, etc
    position_meters_ahead: float = 0.0  # Distance ahead of horse behind
    
    # Stamina/Energy
    current_stamina: float = 100.0      # 0-100 percentage
    stamina_consumed_this_lap: float = 0.0
    
    # Gait
    gait_quality: float = 1.0           # 0.8-1.2, affects speed consistency
    gait_breaks: int = 0                # Number of times broke gait (disqualified if too many)
    is_breaking_gait: bool = False      # Currently in gait break
    
    # Heats (if applicable)
    current_heat: int = 1               # Which heat in the race
    cumulative_position: int = 1        # Overall position across heats
    heat_recovery_index: float = 1.0    # 1.0 fresh, <1.0 tired from previous heat
    
    # Race tactics
    running_style: HarnessRunningStyle = HarnessRunningStyle.MIDDLE_RUNNER
    is_racing_aggression: bool = False  # In direct competition with another horse
    
    # Finish status
    is_finished: bool = False
    finish_time: float = 0.0
    
    def get_effective_stamina(self) -> float:
        """Get stamina considering heat fatigue"""
        return self.current_stamina * self.heat_recovery_index


# =============================================================================
# HARNESS RACE SIMULATION ENGINE
# =============================================================================

class HarnessRaceEngine:
    """Simulates a harness racing event"""
    
    # Physical constants for harness racing
    TRACK_DISTANCE_STANDARD = 1000      # meters - standard European track
    STARTING_SPEED = 3.0                # m/s - walking speed at start
    SULKY_DRAG_COEFFICIENT = 0.15       # How much sulky weight slows acceleration
    
    # Phase durations (as percentage of total race)
    PHASE_DURATIONS = {
        HarnessRacePhase.START: 0.08,       # 200m of typical 2400m race
        HarnessRacePhase.EARLY: 0.16,       # 400m
        HarnessRacePhase.MID: 0.50,         # 1200m
        HarnessRacePhase.LATE: 0.18,        # 400m
        HarnessRacePhase.FINAL_SPURT: 0.08, # 200m
    }
    
    def __init__(self, race: HarnessRace, horses: List[Tuple[str, 'HarnessHorseStats']], 
                 sulky_config: Optional[SulkyConfiguration] = None):
        """
        Initialize a harness race
        
        Args:
            race: HarnessRace object
            horses: List of (horse_id, HarnessHorseStats) tuples
            sulky_config: Custom sulky configuration
        """
        self.race = race
        self.horses = horses
        self.sulky_config = sulky_config or SulkyConfiguration()
        
        # Initialize horse states
        self.horse_states: Dict[str, HarnessHorseState] = {}
        for i, (horse_id, stats) in enumerate(horses):
            self.horse_states[horse_id] = HarnessHorseState(
                horse_id=horse_id,
                current_position=i + 1,
                current_speed=self.STARTING_SPEED,
                gait_quality=0.9 + stats.gait_consistency / 500  # 0.9-1.1 range
            )
        
        # Assign tactics based on horse stats
        self._assign_tactics()
        
        # Race state
        self.current_phase = HarnessRacePhase.START
        self.elapsed_time = 0.0              # seconds
        self.lap_number = 0
        self.is_finished = False
        self.race_result: List[str] = []    # Horse IDs in finishing order
    
    def _assign_tactics(self):
        """Assign optimal tactics to each horse"""
        horses_list = list(self.horse_states.items())
        
        # Sort by acceleration stat
        sorted_horses = sorted(
            horses_list,
            key=lambda x: getattr(x[1], 'start_acceleration', 50),
            reverse=True
        )
        
        for i, (horse_id, state) in enumerate(sorted_horses):
            if i == 0:
                state.running_style = HarnessRunningStyle.FRONT_RUNNER
            elif i < len(sorted_horses) // 2:
                state.running_style = HarnessRunningStyle.MIDDLE_RUNNER
            else:
                state.running_style = HarnessRunningStyle.CLOSER
    
    def get_target_speed(self, horse_id: str, phase: HarnessRacePhase, 
                        stats: 'HarnessHorseStats') -> float:
        """
        Calculate target speed for horse based on phase and stats
        
        Formula adapted from flat racing but using Pulling Power instead of Speed
        Realistic harness racing speeds: 11-14 m/s average (40-50 km/h)
        World record pace: ~15 m/s for short bursts
        """
        # Base speed for harness racing - realistic for trotters
        base_speed = 11.5  # Base speed in m/s for elite trotters
        
        # Phase modifiers - gradual speed increase
        phase_modifiers = {
            HarnessRacePhase.START: 0.5,        # Slow start from standstill
            HarnessRacePhase.EARLY: 0.8,        # Building up speed
            HarnessRacePhase.MID: 1.0,          # Steady cruising pace
            HarnessRacePhase.LATE: 1.05,        # Picking up pace
            HarnessRacePhase.FINAL_SPURT: 1.12, # Final effort
        }
        
        # Pulling power bonus - moderate range
        pulling_bonus = (stats.pulling_power - 50) * 0.002  # -0.1 to +0.1 range
        
        # Gait consistency bonus - helps maintain speed
        gait_bonus = (stats.gait_consistency - 50) * 0.001  # -0.05 to +0.05 range
        
        # Distance-specific modifier
        distance_factor = self._get_distance_factor()
        
        # Sulky weight penalty
        weight_penalty = 1.0 - (self.sulky_config.total_weight - 700) / 150 * 0.08
        
        target = (base_speed * phase_modifiers.get(phase, 1.0) * 
                 (1.0 + pulling_bonus + gait_bonus) * 
                 distance_factor * weight_penalty)
        
        # Realistic speed limits for harness racing
        # 11-14 m/s = 40-50 km/h (typical harness racing speed)
        # Peak speeds can reach 15-16 m/s for world-class horses
        return max(5.0, min(target, 16.0))  # Clamp between 5-16 m/s
    
    def _get_distance_factor(self) -> float:
        """Get speed modifier based on race distance"""
        distance = self.race.distance
        
        # Longer distances require more conservative pacing
        if distance <= 1300:
            return 1.02      # Short sprint races
        elif distance <= 1700:
            return 0.98      # Medium distance
        elif distance <= 2200:
            return 0.95      # Long distance
        elif distance <= 2700:
            return 0.92      # Very long (Prix d'Amérique)
        else:
            return 0.88      # Ultra distance
    
    def get_stamina_consumption(self, horse_id: str, current_speed: float, 
                               target_speed: float, stats: 'HarnessHorseStats') -> float:
        """
        Calculate stamina consumed per second
        
        Higher speeds and sulky weight increase consumption
        """
        state = self.horse_states[horse_id]
        
        # Base consumption: 15 HP/second
        base_consumption = 15.0
        
        # Speed deviation from target (efficiency loss)
        speed_error = abs(current_speed - target_speed)
        consumption = base_consumption * (1.0 + speed_error * 0.1)
        
        # Sulky weight penalty
        weight_factor = 1.0 + (self.sulky_config.total_weight - 700) / 150 * 0.15
        
        # Endurance bonus (stamina efficiency)
        endurance_factor = 1.0 - (stats.endurance / 200 * 0.25)
        
        # Gait breaks increase consumption dramatically
        if state.gait_breaks > 0:
            endurance_factor *= (1.0 + state.gait_breaks * 0.3)
        
        return consumption * weight_factor * endurance_factor
    
    def simulate_lap(self):
        """Simulate one lap of the track (simplified lap unit)"""
        self.lap_number += 1
        self.elapsed_time += 0.1  # 0.1 second per lap
        
        # Update phase based on distance
        self._update_phase()
        
        # Process each horse
        for horse_id, state in self.horse_states.items():
            if state.distance_covered >= self.race.distance:
                continue  # Already finished
            
            stats = self._get_horse_stats(horse_id)
            
            # Calculate target speed
            target = self.get_target_speed(horse_id, self.current_phase, stats)
            
            # Update actual speed (acceleration/deceleration)
            self._update_speed(state, target, stats)
            
            # Check for gait breaks (random chance based on gait quality)
            self._check_gait_break(state, stats)
            
            # Consume stamina
            consumption = self.get_stamina_consumption(horse_id, state.current_speed, 
                                                       target, stats)
            state.current_stamina = max(0, state.current_stamina - consumption)
            
            # Update distance - move based on speed and timestep (0.1 seconds)
            state.distance_covered += state.current_speed * 0.1
        
        # Update positions
        self._update_positions()
        
        # Check for race completion
        self._check_race_completion()
    
    def _update_phase(self):
        """Update current race phase based on progress"""
        # Find the leading horse's distance
        max_distance = max((state.distance_covered for state in self.horse_states.values()), default=0)
        
        # Calculate progress through race (0.0 to 1.0)
        progress = min(1.0, max_distance / self.race.distance) if self.race.distance > 0 else 0
        
        cumulative = 0
        for phase, duration in self.PHASE_DURATIONS.items():
            cumulative += duration
            if progress < cumulative:
                self.current_phase = phase
                return
        
        self.current_phase = HarnessRacePhase.FINAL_SPURT
    
    def _update_speed(self, state: HarnessHorseState, target: float, 
                     stats: 'HarnessHorseStats'):
        """Update horse speed with acceleration/deceleration"""
        # Acceleration in harness racing (m/s per timestep)
        # Based on Start Acceleration stat
        # Realistic harness horses reach cruising speed in 15-30 seconds
        accel_rate = 0.4 + (stats.start_acceleration / 500 * 0.2)  # 0.4-0.6 m/s per timestep
        
        # Adjust for sulky weight
        accel_rate *= self.sulky_config.efficiency_factor()
        
        # If at target, maintain. If below, accelerate. If above, decelerate.
        if abs(state.current_speed - target) < 0.3:
            state.current_speed = target
        elif state.current_speed < target:
            state.current_speed = min(target, state.current_speed + accel_rate * 0.1)  # Multiply by timestep
        else:
            state.current_speed = max(target * 0.9, state.current_speed - accel_rate * 0.05)  # Slower decel
        
        # Apply stamina penalty if going too fast
        if state.current_speed > target * 1.1 and state.current_stamina < 30:
            state.current_speed = target
    
    def _check_gait_break(self, state: HarnessHorseState, stats: 'HarnessHorseStats'):
        """Check if horse breaks gait (random chance based on consistency)"""
        # Gait consistency affects break probability
        # Higher consistency = lower probability
        base_break_chance = 0.002  # 0.2% base chance per lap (reduced from 2%)
        consistency_factor = 1.0 - (stats.gait_consistency / 150)  # Less punishing
        
        # Fatigue increases break probability only when very tired
        stamina_factor = 1.0
        if state.current_stamina < 20:
            stamina_factor = 1.5
        elif state.current_stamina < 10:
            stamina_factor = 2.5
        
        total_chance = base_break_chance * consistency_factor * stamina_factor
        
        if random.random() < total_chance:
            state.gait_breaks += 1
            state.is_breaking_gait = True
            state.current_speed *= 0.85  # Less severe speed loss
        else:
            state.is_breaking_gait = False
    
    def _update_positions(self):
        """Update horse positions based on distance covered"""
        horses_by_distance = sorted(
            self.horse_states.items(),
            key=lambda x: -x[1].distance_covered
        )
        
        for i, (horse_id, state) in enumerate(horses_by_distance):
            state.current_position = i + 1
    
    def _check_race_completion(self):
        """Check if any horses finished"""
        current_time = self.elapsed_time
        
        for horse_id, state in self.horse_states.items():
            if state.distance_covered >= self.race.distance and not state.is_finished:
                state.is_finished = True
                state.finish_time = current_time
                self.race_result.append(horse_id)
        
        if len(self.race_result) == len(self.horses):
            self.is_finished = True
    
    def _get_horse_stats(self, horse_id: str) -> 'HarnessHorseStats':
        """Get stats for a horse"""
        # This would be integrated with the actual horse data in real use
        return self.horses[list(dict(self.horses).keys()).index(horse_id)][1]
    
    def run_race(self) -> List[str]:
        """Run the complete race simulation"""
        # Run until all horses finish or max iterations reached
        max_iterations = 100000  # Increased from 10000
        while not self.is_finished and self.lap_number < max_iterations:
            self.simulate_lap()
        
        # If race didn't complete, force finish based on distance
        if not self.is_finished:
            horses_by_distance = sorted(
                self.horse_states.items(),
                key=lambda x: -x[1].distance_covered
            )
            self.race_result = [horse_id for horse_id, _ in horses_by_distance]
        
        return self.race_result
    
    def get_race_summary(self) -> Dict:
        """Get race summary with results"""
        return {
            "race_name": self.race.name,
            "distance": self.race.distance,
            "laps_simulated": self.lap_number,
            "results": self.race_result,
            "final_positions": {
                horse_id: (i + 1) for i, horse_id in enumerate(self.race_result)
            },
            "horse_states": {
                horse_id: {
                    "distance_covered": state.distance_covered,
                    "final_speed": state.current_speed,
                    "gait_breaks": state.gait_breaks,
                    "stamina_remaining": state.current_stamina
                }
                for horse_id, state in self.horse_states.items()
            }
        }


if __name__ == "__main__":
    print("Harness Racing Engine loaded successfully")
    print(f"Available race phases: {[p.value for p in HarnessRacePhase]}")
    print(f"Available running styles: {[s.value for s in HarnessRunningStyle]}")
