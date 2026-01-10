"""
Harness Racing Horse Configuration Generator

Generates harness racing horse profiles with stats adapted for trotting.
Different from flat racing horses due to the need to pull a sulky.

Horse Type: European Trotters
Stat Categories adapted for harness racing mechanics
"""

import json
import random
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from pathlib import Path

from harness_races import HarnessStatCategory, STAT_MAPPING


@dataclass
class HarnessHorseStats:
    """Horse stats for harness racing - adapted for sulky pulling"""
    pulling_power: int          # 0-100: Ability to pull sulky effectively
    endurance: int              # 0-100: Stamina for long-distance trotting
    gait_consistency: int       # 0-100: Ability to maintain trotting rhythm
    heat_recovery: int          # 0-100: Recovery between heats
    start_acceleration: int     # 0-100: Acceleration from standing start
    temperament: int            # 0-100: Mental toughness/racing aggression
    sulky_tolerance: int        # 0-100: Efficiency while pulling sulky
    
    def total_stats(self) -> int:
        """Sum of all stats"""
        return (self.pulling_power + self.endurance + self.gait_consistency +
                self.heat_recovery + self.start_acceleration + self.temperament +
                self.sulky_tolerance)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)
    
    def __str__(self) -> str:
        return (f"PP:{self.pulling_power:3d} | END:{self.endurance:3d} | "
                f"GAIT:{self.gait_consistency:3d} | REC:{self.heat_recovery:3d} | "
                f"ACC:{self.start_acceleration:3d} | TEM:{self.temperament:3d} | "
                f"SULT:{self.sulky_tolerance:3d} | TOTAL:{self.total_stats():3d}")


@dataclass
class HarnessHorseProfile:
    """Complete harness racing horse profile"""
    id: str
    name: str
    age: int                              # 2 or 3 years old
    gender: str                           # "Stallion", "Mare", "Colt", "Filly"
    type_: str                            # "Trotter"
    origin_country: str                   # Country of origin
    breeding_line: Optional[str]          # Prestigious bloodline
    
    stats: HarnessHorseStats
    
    # Harness-specific attributes
    best_distance: str                    # "Short", "Medium", "Long"
    preferred_track_surface: str          # "Dirt", "Sand", "Auto"
    best_position_in_heat: str            # "Front", "Middle", "Back", "Flexible"
    experience_heats: int                 # Number of heats raced (0-100)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "gender": self.gender,
            "type": self.type_,
            "origin": self.origin_country,
            "breeding_line": self.breeding_line,
            "stats": self.stats.to_dict(),
            "best_distance": self.best_distance,
            "preferred_surface": self.preferred_track_surface,
            "best_position": self.best_position_in_heat,
            "heat_experience": self.experience_heats,
        }
    
    def __str__(self) -> str:
        return (f"{self.name} ({self.gender} {self.type_}, Age {self.age})\n"
                f"  Origin: {self.origin_country}\n"
                f"  Stats: {self.stats}\n"
                f"  Best Distance: {self.best_distance}\n"
                f"  Preferred Surface: {self.preferred_track_surface}\n"
                f"  Position: {self.best_position_in_heat}\n"
                f"  Heat Experience: {self.experience_heats}")


class HarnessHorseGenerator:
    """Generates harness racing horse profiles"""
    
    # Famous European trotting bloodlines
    BLOODLINES = [
        "Orloff Line", "French Trotter", "Italian Trotter",
        "Swedish Standard", "Norwegian Elite", "Finnish Heritage",
        "Belgian Champion", "German Royal"
    ]
    
    # Horse names
    FIRST_NAMES = [
        "Storm", "Victory", "Thunder", "Silver", "Prince", "King",
        "Star", "Night", "Fire", "Wind", "Dream", "Hope",
        "Valor", "Glory", "Pride", "Speed", "Power", "Force"
    ]
    
    LAST_NAMES = [
        "Trotter", "Runner", "Sprint", "Nordic", "Royal", "Elite",
        "Champion", "Legend", "Spirit", "Soul", "Heart", "Mind",
        "Fury", "Storm", "Flash", "Arrow", "Bolt", "Strike"
    ]
    
    COUNTRIES = ["France", "Italy", "Sweden", "Norway", "Finland", "Germany", "Belgium"]
    
    def generate_random_stats(self, age: int = 3) -> HarnessHorseStats:
        """
        Generate random harness racing stats
        Younger horses (2yo) have lower base stats
        """
        if age == 2:
            base_multiplier = 0.7  # 70% of mature stats
        else:
            base_multiplier = 1.0
        
        def random_stat():
            # Generate with variance around 60-70 average (scaled for age)
            base = random.randint(55, 75)
            variance = random.randint(-10, 15)
            stat = int((base + variance) * base_multiplier)
            return min(100, max(20, stat))  # Clamp between 20-100
        
        return HarnessHorseStats(
            pulling_power=random_stat(),
            endurance=random_stat(),
            gait_consistency=random_stat(),
            heat_recovery=random_stat(),
            start_acceleration=random_stat(),
            temperament=random_stat(),
            sulky_tolerance=random_stat()
        )
    
    def determine_best_distance(self, stats: HarnessHorseStats) -> str:
        """Determine best racing distance based on stats"""
        endurance_score = stats.endurance + stats.heat_recovery
        acceleration = stats.start_acceleration
        consistency = stats.gait_consistency
        
        if endurance_score > 140 and consistency > 70:
            return "Long"
        elif acceleration > 75 and stats.pulling_power > 70:
            return "Short"
        else:
            return "Medium"
    
    def determine_preferred_surface(self) -> str:
        """Most harness races are on auto-start, but some prefer dirt"""
        choice = random.random()
        if choice < 0.85:
            return "Auto"  # Most European races use auto-start
        elif choice < 0.95:
            return "Sand"
        else:
            return "Dirt"
    
    def determine_best_position(self, stats: HarnessHorseStats) -> str:
        """Determine best position in race based on acceleration and temperament"""
        if stats.start_acceleration > 75 and stats.temperament > 70:
            return "Front"
        elif stats.endurance > 75 and stats.heat_recovery > 70:
            return "Back"  # Better from back for closing strength
        else:
            return "Middle"
    
    def generate_horse(self, age: int = 3, gender: Optional[str] = None) -> HarnessHorseProfile:
        """Generate a complete harness racing horse profile"""
        
        if gender is None:
            gender = random.choice(["Stallion", "Mare", "Colt", "Filly"])
        
        # Validate gender with age
        if age == 2:
            gender = random.choice(["Colt", "Filly"])
        
        stats = self.generate_random_stats(age)
        
        horse_id = f"horse_{random.randint(10000, 99999)}"
        name = f"{random.choice(self.FIRST_NAMES)} {random.choice(self.LAST_NAMES)}"
        country = random.choice(self.COUNTRIES)
        
        # Better horses (higher total stats) are more likely to have prestigious bloodlines
        has_bloodline = random.random() < (stats.total_stats() / 700 * 0.6)
        bloodline = random.choice(self.BLOODLINES) if has_bloodline else None
        
        return HarnessHorseProfile(
            id=horse_id,
            name=name,
            age=age,
            gender=gender,
            type_="Trotter",
            origin_country=country,
            breeding_line=bloodline,
            stats=stats,
            best_distance=self.determine_best_distance(stats),
            preferred_track_surface=self.determine_preferred_surface(),
            best_position_in_heat=self.determine_best_position(stats),
            experience_heats=random.randint(0, 50) if age == 3 else 0
        )
    
    def generate_multi_horse_stable(self, count: int = 5) -> List[HarnessHorseProfile]:
        """Generate a stable of multiple horses"""
        horses = []
        
        # Mix of ages - mostly 3yo, some 2yo
        num_3yo = max(count - 2, int(count * 0.7))
        num_2yo = count - num_3yo
        
        for _ in range(num_3yo):
            horses.append(self.generate_horse(age=3))
        
        for _ in range(num_2yo):
            horses.append(self.generate_horse(age=2))
        
        return horses


class HarnessConfigManager:
    """Manages loading/saving harness racing horse configurations"""
    
    def __init__(self, config_dir: str = "."):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def save_horse(self, horse: HarnessHorseProfile, filename: Optional[str] = None) -> str:
        """Save a horse configuration to JSON file"""
        if filename is None:
            filename = f"{horse.id}_harness.json"
        
        filepath = self.config_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(horse.to_dict(), f, indent=2)
        
        return str(filepath)
    
    def save_stable(self, horses: List[HarnessHorseProfile], filename: str = "harness_stable.json") -> str:
        """Save multiple horses to JSON file"""
        filepath = self.config_dir / filename
        
        horse_data = [h.to_dict() for h in horses]
        
        with open(filepath, 'w') as f:
            json.dump({
                "stable_size": len(horses),
                "horses": horse_data,
                "total_pulling_power": sum(h.stats.pulling_power for h in horses)
            }, f, indent=2)
        
        return str(filepath)
    
    def load_horse(self, filename: str) -> HarnessHorseProfile:
        """Load a horse configuration from JSON file"""
        filepath = self.config_dir / filename
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        stats = HarnessHorseStats(**data['stats'])
        
        return HarnessHorseProfile(
            id=data['id'],
            name=data['name'],
            age=data['age'],
            gender=data['gender'],
            type_=data['type'],
            origin_country=data['origin'],
            breeding_line=data.get('breeding_line'),
            stats=stats,
            best_distance=data['best_distance'],
            preferred_track_surface=data['preferred_surface'],
            best_position_in_heat=data['best_position'],
            experience_heats=data['heat_experience']
        )


def main():
    """Demo/test the harness horse generator"""
    print("="*70)
    print("HARNESS RACING HORSE CONFIGURATION GENERATOR")
    print("="*70)
    
    generator = HarnessHorseGenerator()
    
    print("\n--- Single Horse Generation ---")
    horse = generator.generate_horse(age=3)
    print(horse)
    
    print("\n--- Stable Generation (5 horses) ---")
    stable = generator.generate_multi_horse_stable(count=5)
    for i, h in enumerate(stable, 1):
        print(f"\nHorse {i}: {h.name}")
        print(f"  Stats Total: {h.stats.total_stats()}")
        print(f"  Best Distance: {h.best_distance}")
        print(f"  Best Position: {h.best_position_in_heat}")
    
    print("\n" + "="*70)
    print(f"Average stable pulling power: {sum(h.stats.pulling_power for h in stable) / len(stable):.1f}")
    print("="*70)


if __name__ == "__main__":
    main()
