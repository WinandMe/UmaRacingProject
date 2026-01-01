"""
Harness Racing - European Standard Rules Implementation

Harness racing is a form of horse racing where horses pull a 2-wheeled cart (sulky)
rather than being ridden. This implementation follows European (Continental) harness
racing standards, primarily used in France, Italy, Sweden, and other European countries.

Key Differences from Flat Racing:
1. Horses are trotters or pacers (specific gaits trained from birth)
2. Pulling a sulky (700-850kg) affects speed and stamina consumption
3. Races typically on dirt/sand tracks with tight turns
4. Different horse types with specific racing capabilities
5. European tracks typically oval with 1000m - 2700m distances
6. Heats system for major races (qualifying heats + final)

Horse Types in Harness Racing:
1. Trotter - Natural trotting gait (more common in Europe)
2. Pacer - Lateral gait (more common in North America)

This implementation focuses on European trotting standards.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class HarnessRacecourse(Enum):
    """European harness racing tracks"""
    # France
    PARIS_VINCENNES = "Paris-Vincennes"  # Most prestigious French track
    CAGNES_SUR_MER = "Cagnes-sur-Mer"
    
    # Italy
    MILAN_SAN_SIRO = "Milan (San Siro)"
    ROME_CAPANNELLE = "Rome (Capannelle)"
    TURIN = "Turin"
    AGNANO = "Agnano (Naples)"
    CESENA = "Cesena"
    
    # Sweden
    SOLVALLA = "Solvalla (Stockholm)"
    JÄGERSRO = "Jägersro (Malmö)"
    ÅBY = "Åby"
    
    # Norway
    BJERKE = "Bjerke (Oslo)"
    JARLSBERG = "Jarlsberg"
    ØVREVOLL = "Øvrevoll"
    
    # Germany
    COLOGNE = "Cologne"
    
    # Belgium
    MONS = "Mons"
    
    # Finland
    KOUVOLA = "Kouvola"
    
    # Canada
    WOODBINE_MOHAWK = "Woodbine Mohawk Park (Ontario)"


# Harness track layouts and configurations
# European harness tracks are typically 1000m ovals with varying characteristics
HARNESS_TRACK_LAYOUTS = {
    "Paris-Vincennes": {
        "direction": "Left",  # Counter-clockwise
        "width_ratio": 1.8,   # Elongated oval
        "corner_tightness": 0.65,  # Tighter corners
        "track_type": "Grand Prix",
        "surface": "Dirt/Sand"
    },
    "Cagnes-sur-Mer": {
        "direction": "Left",
        "width_ratio": 1.6,
        "corner_tightness": 0.70,
        "track_type": "Classic Oval",
        "surface": "Dirt"
    },
    "Milan (San Siro)": {
        "direction": "Left",
        "width_ratio": 1.7,
        "corner_tightness": 0.68,
        "track_type": "Italian Circuit",
        "surface": "Auto"
    },
    "Rome (Capannelle)": {
        "direction": "Left",
        "width_ratio": 1.75,
        "corner_tightness": 0.67,
        "track_type": "Italian Circuit",
        "surface": "Auto"
    },
    "Turin": {
        "direction": "Left",
        "width_ratio": 1.65,
        "corner_tightness": 0.72,
        "track_type": "Classic Oval",
        "surface": "Dirt"
    },
    "Agnano (Naples)": {
        "direction": "Left",
        "width_ratio": 1.7,
        "corner_tightness": 0.69,
        "track_type": "Italian Circuit",
        "surface": "Auto"
    },
    "Cesena": {
        "direction": "Left",
        "width_ratio": 1.6,
        "corner_tightness": 0.71,
        "track_type": "Classic Oval",
        "surface": "Auto"
    },
    "Solvalla (Stockholm)": {
        "direction": "Left",
        "width_ratio": 1.65,
        "corner_tightness": 0.70,
        "track_type": "Swedish Standard",
        "surface": "Auto"
    },
    "Jägersro (Malmö)": {
        "direction": "Left",
        "width_ratio": 1.7,
        "corner_tightness": 0.68,
        "track_type": "Swedish Standard",
        "surface": "Auto"
    },
    "Åby": {
        "direction": "Left",
        "width_ratio": 1.6,
        "corner_tightness": 0.73,
        "track_type": "Swedish Standard",
        "surface": "Auto"
    },
    "Bjerke (Oslo)": {
        "direction": "Left",
        "width_ratio": 1.8,
        "corner_tightness": 0.66,
        "track_type": "Norwegian Circuit",
        "surface": "Auto"
    },
    "Jarlsberg": {
        "direction": "Left",
        "width_ratio": 1.7,
        "corner_tightness": 0.69,
        "track_type": "Norwegian Circuit",
        "surface": "Dirt"
    },
    "Øvrevoll": {
        "direction": "Left",
        "width_ratio": 1.65,
        "corner_tightness": 0.71,
        "track_type": "Norwegian Circuit",
        "surface": "Dirt"
    },
    "Cologne": {
        "direction": "Left",
        "width_ratio": 1.75,
        "corner_tightness": 0.67,
        "track_type": "German Standard",
        "surface": "Auto"
    },
    "Mons": {
        "direction": "Left",
        "width_ratio": 1.6,
        "corner_tightness": 0.72,
        "track_type": "Belgian Circuit",
        "surface": "Auto"
    },
    "Kouvola": {
        "direction": "Left",
        "width_ratio": 1.7,
        "corner_tightness": 0.68,
        "track_type": "Finnish Circuit",
        "surface": "Auto"
    },
    "Woodbine Mohawk Park (Ontario)": {
        "direction": "Left",
        "width_ratio": 1.5,  # Rounder oval (North American style)
        "corner_tightness": 0.75,
        "track_type": "North American",
        "surface": "Auto"
    }
}


class HarnessRaceType(Enum):
    """Harness race distance categories"""
    SHORT = "Short"      # 1000m - 1300m
    MEDIUM = "Medium"    # 1400m - 1700m
    LONG = "Long"        # 1800m - 2200m
    VERY_LONG = "VeryLong"  # 2300m+


class HarnessTrackSurface(Enum):
    """Harness race track surfaces"""
    DIRT = "Dirt"          # Standard dirt
    SAND = "Sand"          # Sand/crushed limestone
    AUTO = "Auto"          # Auto-start (electronic starting gate)


class HarnessRaceFormat(Enum):
    """Race format types in harness racing"""
    STRAIGHT = "Straight"      # Single race, one winner
    HEATS = "Heats"            # Multiple qualifying heats + final
    HANDICAP = "Handicap"      # Horses start from different positions
    CLAIMING = "Claiming"      # Horse can be claimed after race


class HorseType(Enum):
    """Horse racing type in harness racing"""
    TROTTER = "Trotter"    # Trotting gait
    PACER = "Pacer"        # Pacing/lateral gait


class AgeGroup(Enum):
    """Age divisions in harness racing"""
    TWO_YEAR_OLD = "2yo"
    THREE_YEAR_OLD = "3yo"
    FOUR_YEAR_OLD = "4yo"
    OPEN = "Open"  # All ages


@dataclass
class HarnessRace:
    """Represents a harness racing event"""
    id: str
    name: str
    racecourse: HarnessRacecourse
    distance: int                          # Distance in meters
    race_type: HarnessRaceType             # Short/Medium/Long/VeryLong
    surface: HarnessTrackSurface           # Dirt/Sand/Auto
    month: int                             # Month held (1-12)
    
    # Harness-specific attributes
    horse_type: HorseType                  # Trotter or Pacer
    age_group: AgeGroup                    # Eligibility
    format: HarnessRaceFormat              # Race format
    gender: str = "All"                    # "All", "Stallions", "Mares", "Colts", "Fillies"
    prize_money: Optional[int] = None      # Prize in local currency
    country: str = "Europe"                # Country
    
    # Harness racing specifics
    sulky_weight_min: int = 700            # Minimum sulky weight (kg)
    has_heats: bool = False                # Whether race has qualifying heats
    num_heats: int = 3                     # Number of heats if applicable
    track_layout: str = "Oval"             # Track shape
    
    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.racecourse.value})"
    
    @property
    def full_info(self) -> str:
        return (f"{self.name} - {self.distance}m {self.horse_type.value} "
                f"({self.surface.value}) @ {self.racecourse.value}")
    
    @property
    def is_heats_race(self) -> bool:
        return self.has_heats and self.format == HarnessRaceFormat.HEATS


def get_race_type_from_distance(distance: int) -> HarnessRaceType:
    """Determine harness race type from distance"""
    if distance <= 1300:
        return HarnessRaceType.SHORT
    elif distance <= 1700:
        return HarnessRaceType.MEDIUM
    elif distance <= 2200:
        return HarnessRaceType.LONG
    else:
        return HarnessRaceType.VERY_LONG


# ============================================================================
# MAJOR EUROPEAN HARNESS RACES
# ============================================================================

MAJOR_HARNESS_RACES = {
    # ======================== FRANCE (PREMIER LEAGUE) ========================
    
    "prix_d_amerique": HarnessRace(
        id="prix_d_amerique",
        name="Prix d'Amérique",
        racecourse=HarnessRacecourse.PARIS_VINCENNES,
        distance=2700,
        race_type=HarnessRaceType.VERY_LONG,
        surface=HarnessTrackSurface.AUTO,
        month=1,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=1_000_000,
        country="France",
        track_layout="Oval 1000m"
    ),
    
    "prix_de_france": HarnessRace(
        id="prix_de_france",
        name="Prix de France",
        racecourse=HarnessRacecourse.PARIS_VINCENNES,
        distance=2100,
        race_type=HarnessRaceType.LONG,
        surface=HarnessTrackSurface.AUTO,
        month=2,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=550_000,
        country="France",
        has_heats=False
    ),
    
    "criterium_de_vitesse": HarnessRace(
        id="criterium_de_vitesse",
        name="Grand Critérium de Vitesse de la Côte d'Azur",
        racecourse=HarnessRacecourse.CAGNES_SUR_MER,
        distance=1609,
        race_type=HarnessRaceType.MEDIUM,
        surface=HarnessTrackSurface.SAND,
        month=3,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=250_000,
        country="France"
    ),
    
    # ======================== ITALY ========================
    
    "gran_premio_delle_nazioni": HarnessRace(
        id="gran_premio_delle_nazioni",
        name="Grand Premio delle Nazioni",
        racecourse=HarnessRacecourse.MILAN_SAN_SIRO,
        distance=2100,
        race_type=HarnessRaceType.LONG,
        surface=HarnessTrackSurface.AUTO,
        month=10,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=650_000,
        country="Italy"
    ),
    
    "gran_premio_lotteria": HarnessRace(
        id="gran_premio_lotteria",
        name="Gran Premio Lotteria",
        racecourse=HarnessRacecourse.AGNANO,
        distance=1600,
        race_type=HarnessRaceType.MEDIUM,
        surface=HarnessTrackSurface.AUTO,
        month=5,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.HEATS,
        prize_money=830_000,
        country="Italy",
        num_heats=3,
        has_heats=True
    ),
    
    "campionato_europeo": HarnessRace(
        id="campionato_europeo",
        name="Campionato Europeo",
        racecourse=HarnessRacecourse.CESENA,
        distance=2060,
        race_type=HarnessRaceType.LONG,
        surface=HarnessTrackSurface.AUTO,
        month=9,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=350_000,
        country="Italy"
    ),
    
    # ======================== SWEDEN ========================
    
    "elitloppet": HarnessRace(
        id="elitloppet",
        name="Elitloppet",
        racecourse=HarnessRacecourse.SOLVALLA,
        distance=1609,
        race_type=HarnessRaceType.MEDIUM,
        surface=HarnessTrackSurface.AUTO,
        month=5,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=700_000,
        country="Sweden"
    ),
    
    "aby_stora_pris": HarnessRace(
        id="aby_stora_pris",
        name="Åby Stora Pris (Åby World Grand Prix)",
        racecourse=HarnessRacecourse.ÅBY,
        distance=2140,
        race_type=HarnessRaceType.LONG,
        surface=HarnessTrackSurface.AUTO,
        month=8,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=600_000,
        country="Sweden"
    ),
    
    "hugo_abergs_memorial": HarnessRace(
        id="hugo_abergs_memorial",
        name="Hugo Åbergs Memorial",
        racecourse=HarnessRacecourse.JÄGERSRO,
        distance=1609,
        race_type=HarnessRaceType.MEDIUM,
        surface=HarnessTrackSurface.AUTO,
        month=7,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=450_000,
        country="Sweden"
    ),
    
    # ======================== NORWAY ========================
    
    "oslo_grand_prix": HarnessRace(
        id="oslo_grand_prix",
        name="Oslo Grand Prix",
        racecourse=HarnessRacecourse.BJERKE,
        distance=2100,
        race_type=HarnessRaceType.LONG,
        surface=HarnessTrackSurface.AUTO,
        month=6,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=550_000,
        country="Norway"
    ),
    
    "ulf_thoresen_grand_international": HarnessRace(
        id="ulf_thoresen_grand_international",
        name="Ulf Thoresen Grand International",
        racecourse=HarnessRacecourse.JARLSBERG,
        distance=2100,
        race_type=HarnessRaceType.LONG,
        surface=HarnessTrackSurface.AUTO,
        month=7,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=250_000,
        country="Norway"
    ),
    
    # ======================== FINLAND ========================
    
    "kymi_grand_prix": HarnessRace(
        id="kymi_grand_prix",
        name="Kymi Grand Prix",
        racecourse=HarnessRacecourse.KOUVOLA,
        distance=2100,
        race_type=HarnessRaceType.LONG,
        surface=HarnessTrackSurface.AUTO,
        month=6,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=175_000,
        country="Finland"
    ),
    
    # ======================== GERMANY ========================
    
    "union_rennen": HarnessRace(
        id="union_rennen",
        name="Union-Rennen",
        racecourse=HarnessRacecourse.COLOGNE,
        distance=2200,
        race_type=HarnessRaceType.LONG,
        surface=HarnessTrackSurface.AUTO,
        month=6,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=70_000,
        country="Germany"
    ),
    
    # ======================== BELGIUM ========================
    
    "grand_prix_de_wallonie": HarnessRace(
        id="grand_prix_de_wallonie",
        name="Grand Prix de Wallonie",
        racecourse=HarnessRacecourse.MONS,
        distance=2300,
        race_type=HarnessRaceType.VERY_LONG,
        surface=HarnessTrackSurface.AUTO,
        month=9,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.STRAIGHT,
        prize_money=150_000,
        country="Belgium"
    ),
    
    # ======================== CANADA (North American) ========================
    
    "breeders_crown": HarnessRace(
        id="breeders_crown",
        name="The Breeders Crown",
        racecourse=HarnessRacecourse.WOODBINE_MOHAWK,
        distance=1609,
        race_type=HarnessRaceType.MEDIUM,
        surface=HarnessTrackSurface.AUTO,
        month=10,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.OPEN,
        format=HarnessRaceFormat.HEATS,
        prize_money=600_000,
        country="Canada",
        num_heats=2,
        has_heats=True,
        sulky_weight_min=800
    ),
}


# ======================== YOUTH / 2-YEAR-OLD RACES ========================

YOUTH_RACES = {
    "prix_de_hardiesse": HarnessRace(
        id="prix_de_hardiesse",
        name="Prix de Hardiesse",
        racecourse=HarnessRacecourse.PARIS_VINCENNES,
        distance=1800,
        race_type=HarnessRaceType.LONG,
        surface=HarnessTrackSurface.AUTO,
        month=10,
        horse_type=HorseType.TROTTER,
        age_group=AgeGroup.TWO_YEAR_OLD,
        format=HarnessRaceFormat.HEATS,
        prize_money=200_000,
        country="France",
        has_heats=True,
        num_heats=3
    ),
}


# Combined dictionary
ALL_HARNESS_RACES = {**MAJOR_HARNESS_RACES, **YOUTH_RACES}


# ============================================================================
# STAT CATEGORIES FOR HARNESS RACING HORSES
# ============================================================================
# Unlike flat racing, harness racing horses require different stat focus
# due to the nature of pulling a sulky and sustained effort over distance

class HarnessStatCategory(Enum):
    """Harness racing specific stat categories"""
    # Core pulling power
    PULLING_POWER = "Pulling Power"      # Ability to pull sulky (replaces Speed for flat)
    
    # Endurance for sustained trotting
    ENDURANCE = "Endurance"              # Stamina for long distances with sulky
    
    # Consistency in gait
    GAIT_CONSISTENCY = "Gait Consistency"  # Ability to maintain trotting rhythm
    
    # Recovery between heats
    HEAT_RECOVERY = "Heat Recovery"      # Recovery time for multi-heat races
    
    # Acceleration from standing start
    START_ACCELERATION = "Start Acceleration"  # Initial acceleration from gate
    
    # Mental toughness
    TEMPERAMENT = "Temperament"          # Mental toughness and racing aggression
    
    # Weight handling
    SULKY_TOLERANCE = "Sulky Tolerance"  # Efficiency while pulling sulky


# Conversion mapping from Uma Musume stats to Harness stats
STAT_MAPPING = {
    "Speed": HarnessStatCategory.PULLING_POWER,
    "Stamina": HarnessStatCategory.ENDURANCE,
    "Power": HarnessStatCategory.START_ACCELERATION,
    "Guts": HarnessStatCategory.TEMPERAMENT,
    "Wisdom": HarnessStatCategory.GAIT_CONSISTENCY,
}


def print_harness_race_statistics():
    """Print statistics about harness racing database"""
    print(f"{'='*60}")
    print(f"HARNESS RACING DATABASE STATISTICS")
    print(f"{'='*60}")
    
    print(f"\nTotal Harness Races: {len(ALL_HARNESS_RACES)}")
    print(f"  - Major Races: {len(MAJOR_HARNESS_RACES)}")
    print(f"  - Youth Races: {len(YOUTH_RACES)}")
    
    by_type = {}
    by_country = {}
    by_surface = {}
    
    for race in ALL_HARNESS_RACES.values():
        by_type[race.race_type.value] = by_type.get(race.race_type.value, 0) + 1
        by_country[race.country] = by_country.get(race.country, 0) + 1
        by_surface[race.surface.value] = by_surface.get(race.surface.value, 0) + 1
    
    print("\nBy Race Type:")
    for rtype, count in sorted(by_type.items()):
        print(f"  {rtype}: {count}")
    
    print("\nBy Surface:")
    for surface, count in sorted(by_surface.items()):
        print(f"  {surface}: {count}")
    
    print("\nBy Country:")
    for country, count in sorted(by_country.items(), key=lambda x: -x[1]):
        print(f"  {country}: {count}")
    
    print(f"{'='*60}")


if __name__ == "__main__":
    print_harness_race_statistics()
