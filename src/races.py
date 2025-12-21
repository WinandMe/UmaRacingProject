"""
Japan G1 Horse Racing Database for Uma Musume Racing Simulation

Contains all JRA G1 races with their official data including:
- Distance and race type category (Sprint/Mile/Medium/Long)
- Racecourse location
- Surface type (Turf/Dirt)
- Track direction (Right/Left)
- Month when typically held
- Eligible participants

Race Type Categories (Uma Musume):
- Sprint: 1000m - 1400m
- Mile: 1401m - 1800m
- Medium: 1801m - 2400m
- Long: 2401m+
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RaceType(Enum):
    """Race distance categories as used in Uma Musume"""
    SPRINT = "Sprint"      # 1000m - 1400m
    MILE = "Mile"          # 1401m - 1800m
    MEDIUM = "Medium"      # 1801m - 2400m
    LONG = "Long"          # 2401m+


class Surface(Enum):
    """Track surface type"""
    TURF = "Turf"
    DIRT = "Dirt"


class Direction(Enum):
    """Track direction"""
    RIGHT = "Right"   # Right-handed (clockwise)
    LEFT = "Left"     # Left-handed (counter-clockwise)


class Racecourse(Enum):
    """JRA Racecourses"""
    TOKYO = "Tokyo"
    NAKAYAMA = "Nakayama"
    HANSHIN = "Hanshin"
    KYOTO = "Kyoto"
    CHUKYO = "Chukyo"
    SAPPORO = "Sapporo"
    HAKODATE = "Hakodate"
    FUKUSHIMA = "Fukushima"
    NIIGATA = "Niigata"
    KOKURA = "Kokura"
    OHI = "Ohi"  # NAR (for Tokyo Daishoten)


# Racecourse track directions
RACECOURSE_DIRECTIONS = {
    Racecourse.TOKYO: Direction.LEFT,
    Racecourse.NAKAYAMA: Direction.RIGHT,
    Racecourse.HANSHIN: Direction.RIGHT,
    Racecourse.KYOTO: Direction.RIGHT,
    Racecourse.CHUKYO: Direction.LEFT,
    Racecourse.SAPPORO: Direction.RIGHT,
    Racecourse.HAKODATE: Direction.RIGHT,
    Racecourse.FUKUSHIMA: Direction.RIGHT,
    Racecourse.NIIGATA: Direction.LEFT,
    Racecourse.KOKURA: Direction.RIGHT,
    Racecourse.OHI: Direction.RIGHT,
}


@dataclass
class Race:
    """Represents a G1 horse race"""
    id: str                          # Unique identifier
    name: str                        # Official race name
    name_jp: str                     # Japanese name
    distance: int                    # Distance in meters
    race_type: RaceType              # Sprint/Mile/Medium/Long
    surface: Surface                 # Turf/Dirt
    racecourse: Racecourse           # Where the race is held
    direction: Direction             # Track direction
    month: int                       # Month when typically held (1-12)
    grade: str = "G1"                # Grade level
    eligibility: str = "3yo+"        # Age/sex eligibility
    prize_money: Optional[int] = None  # Prize money in JPY (optional)
    
    @property
    def display_name(self) -> str:
        """Display name with racecourse"""
        return f"{self.name} ({self.racecourse.value})"
    
    @property
    def full_info(self) -> str:
        """Full race information string"""
        return f"{self.name} - {self.distance}m {self.surface.value} @ {self.racecourse.value}"


def get_race_type_from_distance(distance: int) -> RaceType:
    """Determine race type category from distance"""
    if distance <= 1400:
        return RaceType.SPRINT
    elif distance <= 1800:
        return RaceType.MILE
    elif distance <= 2400:
        return RaceType.MEDIUM
    else:
        return RaceType.LONG


# ============================================================================
# JRA G1 RACES DATABASE
# ============================================================================

G1_RACES = {
    # ======================== FEBRUARY ========================
    "february_stakes": Race(
        id="february_stakes",
        name="February Stakes",
        name_jp="フェブラリーステークス",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.DIRT,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=2,
        eligibility="4yo+",
        prize_money=120_000_000
    ),
    
    # ======================== MARCH ========================
    "takamatsunomiya_kinen": Race(
        id="takamatsunomiya_kinen",
        name="Takamatsunomiya Kinen",
        name_jp="高松宮記念",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.CHUKYO,
        direction=Direction.LEFT,
        month=3,
        eligibility="4yo+",
        prize_money=170_000_000
    ),
    
    "osaka_hai": Race(
        id="osaka_hai",
        name="Osaka Hai",
        name_jp="大阪杯",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=3,
        eligibility="4yo+",
        prize_money=300_000_000
    ),
    
    # ======================== APRIL ========================
    "oka_sho": Race(
        id="oka_sho",
        name="Oka Sho",
        name_jp="桜花賞",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=4,
        eligibility="3yo fillies",
        prize_money=140_000_000
    ),
    
    "satsuki_sho": Race(
        id="satsuki_sho",
        name="Satsuki Sho",
        name_jp="皐月賞",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=4,
        eligibility="3yo colts & fillies",
        prize_money=200_000_000
    ),
    
    "tenno_sho_spring": Race(
        id="tenno_sho_spring",
        name="Tenno Sho (Spring)",
        name_jp="天皇賞（春）",
        distance=3200,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=4,
        eligibility="4yo+",
        prize_money=300_000_000
    ),
    
    # ======================== MAY ========================
    "nhk_mile_cup": Race(
        id="nhk_mile_cup",
        name="NHK Mile Cup",
        name_jp="NHKマイルカップ",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=5,
        eligibility="3yo colts & fillies",
        prize_money=130_000_000
    ),
    
    "victoria_mile": Race(
        id="victoria_mile",
        name="Victoria Mile",
        name_jp="ヴィクトリアマイル",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=5,
        eligibility="4yo+ fillies & mares",
        prize_money=130_000_000
    ),
    
    "yushun_himba": Race(
        id="yushun_himba",
        name="Yushun Himba",
        name_jp="優駿牝馬（オークス）",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=5,
        eligibility="3yo fillies",
        prize_money=150_000_000
    ),
    
    "tokyo_yushun": Race(
        id="tokyo_yushun",
        name="Tokyo Yushun",
        name_jp="東京優駿（日本ダービー）",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=5,
        eligibility="3yo colts & fillies",
        prize_money=300_000_000
    ),
    
    # ======================== JUNE ========================
    "yasuda_kinen": Race(
        id="yasuda_kinen",
        name="Yasuda Kinen",
        name_jp="安田記念",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=6,
        eligibility="3yo+",
        prize_money=180_000_000
    ),
    
    "takarazuka_kinen": Race(
        id="takarazuka_kinen",
        name="Takarazuka Kinen",
        name_jp="宝塚記念",
        distance=2200,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=6,
        eligibility="3yo+",
        prize_money=300_000_000
    ),
    
    # ======================== SEPTEMBER ========================
    "sprinters_stakes": Race(
        id="sprinters_stakes",
        name="Sprinters Stakes",
        name_jp="スプリンターズステークス",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=9,
        eligibility="3yo+",
        prize_money=170_000_000
    ),
    
    # ======================== OCTOBER ========================
    "shuka_sho": Race(
        id="shuka_sho",
        name="Shuka Sho",
        name_jp="秋華賞",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=10,
        eligibility="3yo fillies",
        prize_money=110_000_000
    ),
    
    "kikuka_sho": Race(
        id="kikuka_sho",
        name="Kikuka Sho",
        name_jp="菊花賞",
        distance=3000,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=10,
        eligibility="3yo colts & fillies",
        prize_money=200_000_000
    ),
    
    "tenno_sho_autumn": Race(
        id="tenno_sho_autumn",
        name="Tenno Sho (Autumn)",
        name_jp="天皇賞（秋）",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=10,
        eligibility="3yo+",
        prize_money=300_000_000
    ),
    
    # ======================== NOVEMBER ========================
    "queen_elizabeth_ii_cup": Race(
        id="queen_elizabeth_ii_cup",
        name="Queen Elizabeth II Cup",
        name_jp="エリザベス女王杯",
        distance=2200,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=11,
        eligibility="3yo+ fillies & mares",
        prize_money=130_000_000
    ),
    
    "mile_championship": Race(
        id="mile_championship",
        name="Mile Championship",
        name_jp="マイルチャンピオンシップ",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=11,
        eligibility="3yo+",
        prize_money=180_000_000
    ),
    
    "japan_cup": Race(
        id="japan_cup",
        name="Japan Cup",
        name_jp="ジャパンカップ",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=11,
        eligibility="3yo+",
        prize_money=500_000_000
    ),
    
    # ======================== DECEMBER ========================
    "champions_cup": Race(
        id="champions_cup",
        name="Champions Cup",
        name_jp="チャンピオンズカップ",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.DIRT,
        racecourse=Racecourse.CHUKYO,
        direction=Direction.LEFT,
        month=12,
        eligibility="3yo+",
        prize_money=120_000_000
    ),
    
    "hanshin_juvenile_fillies": Race(
        id="hanshin_juvenile_fillies",
        name="Hanshin Juvenile Fillies",
        name_jp="阪神ジュベナイルフィリーズ",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=12,
        eligibility="2yo fillies",
        prize_money=65_000_000
    ),
    
    "asahi_hai_futurity_stakes": Race(
        id="asahi_hai_futurity_stakes",
        name="Asahi Hai Futurity Stakes",
        name_jp="朝日杯フューチュリティステークス",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=12,
        eligibility="2yo colts & fillies",
        prize_money=70_000_000
    ),
    
    "arima_kinen": Race(
        id="arima_kinen",
        name="Arima Kinen",
        name_jp="有馬記念",
        distance=2500,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=12,
        eligibility="3yo+",
        prize_money=500_000_000
    ),
    
    "hopeful_stakes": Race(
        id="hopeful_stakes",
        name="Hopeful Stakes",
        name_jp="ホープフルステークス",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=12,
        eligibility="2yo colts & fillies",
        prize_money=70_000_000
    ),
    
    "tokyo_daishoten": Race(
        id="tokyo_daishoten",
        name="Tokyo Daishoten",
        name_jp="東京大賞典",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.OHI,
        direction=Direction.RIGHT,
        month=12,
        eligibility="3yo+",
        prize_money=100_000_000
    ),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_race_by_id(race_id: str) -> Optional[Race]:
    """Get a race by its ID"""
    return G1_RACES.get(race_id)


def get_all_races() -> dict[str, Race]:
    """Get all G1 races"""
    return G1_RACES.copy()


def get_races_by_type(race_type: RaceType) -> list[Race]:
    """Get all races of a specific type"""
    return [race for race in G1_RACES.values() if race.race_type == race_type]


def get_races_by_surface(surface: Surface) -> list[Race]:
    """Get all races on a specific surface"""
    return [race for race in G1_RACES.values() if race.surface == surface]


def get_races_by_racecourse(racecourse: Racecourse) -> list[Race]:
    """Get all races at a specific racecourse"""
    return [race for race in G1_RACES.values() if race.racecourse == racecourse]


def get_races_by_month(month: int) -> list[Race]:
    """Get all races held in a specific month"""
    return [race for race in G1_RACES.values() if race.month == month]


def get_race_list_for_dropdown() -> list[tuple[str, str]]:
    """Get list of (race_id, display_name) tuples for dropdown menus"""
    # Sort by month, then by name
    sorted_races = sorted(G1_RACES.values(), key=lambda r: (r.month, r.name))
    return [(race.id, f"{race.name} ({race.distance}m {race.surface.value})") for race in sorted_races]


def get_races_grouped_by_month() -> dict[int, list[Race]]:
    """Get races grouped by month"""
    grouped = {}
    for race in G1_RACES.values():
        if race.month not in grouped:
            grouped[race.month] = []
        grouped[race.month].append(race)
    
    # Sort races within each month
    for month in grouped:
        grouped[month].sort(key=lambda r: r.name)
    
    return grouped


def get_race_categories() -> dict[str, list[str]]:
    """Get races grouped by category for UI display"""
    categories = {
        "Sprint (1000-1400m)": [],
        "Mile (1401-1800m)": [],
        "Medium (1801-2400m)": [],
        "Long (2401m+)": [],
    }
    
    for race_id, race in G1_RACES.items():
        if race.race_type == RaceType.SPRINT:
            categories["Sprint (1000-1400m)"].append(race_id)
        elif race.race_type == RaceType.MILE:
            categories["Mile (1401-1800m)"].append(race_id)
        elif race.race_type == RaceType.MEDIUM:
            categories["Medium (1801-2400m)"].append(race_id)
        elif race.race_type == RaceType.LONG:
            categories["Long (2401m+)"].append(race_id)
    
    return categories


# ============================================================================
# SEASON MAPPING (for skill triggers)
# ============================================================================

MONTH_TO_SEASON = {
    1: "Winter",
    2: "Winter",
    3: "Spring",
    4: "Spring",
    5: "Spring",
    6: "Summer",
    7: "Summer",
    8: "Summer",
    9: "Fall",
    10: "Fall",
    11: "Fall",
    12: "Winter",
}


def get_race_season(race: Race) -> str:
    """Get the season when a race is held"""
    return MONTH_TO_SEASON.get(race.month, "Unknown")


# ============================================================================
# STATISTICS
# ============================================================================

def print_race_statistics():
    """Print statistics about the G1 races database"""
    total = len(G1_RACES)
    
    by_type = {}
    by_surface = {}
    by_racecourse = {}
    
    for race in G1_RACES.values():
        by_type[race.race_type.value] = by_type.get(race.race_type.value, 0) + 1
        by_surface[race.surface.value] = by_surface.get(race.surface.value, 0) + 1
        by_racecourse[race.racecourse.value] = by_racecourse.get(race.racecourse.value, 0) + 1
    
    print(f"{'='*50}")
    print(f"G1 RACES DATABASE STATISTICS")
    print(f"{'='*50}")
    print(f"Total G1 Races: {total}")
    print()
    print("By Race Type:")
    for rtype, count in sorted(by_type.items()):
        print(f"  {rtype}: {count}")
    print()
    print("By Surface:")
    for surface, count in sorted(by_surface.items()):
        print(f"  {surface}: {count}")
    print()
    print("By Racecourse:")
    for course, count in sorted(by_racecourse.items(), key=lambda x: -x[1]):
        print(f"  {course}: {count}")
    print(f"{'='*50}")


if __name__ == "__main__":
    # Print statistics when run directly
    print_race_statistics()
    
    print("\nAll G1 Races by Month:")
    print("-" * 50)
    grouped = get_races_grouped_by_month()
    month_names = ["", "January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    
    for month in sorted(grouped.keys()):
        print(f"\n{month_names[month]}:")
        for race in grouped[month]:
            season = get_race_season(race)
            print(f"  - {race.name}: {race.distance}m {race.surface.value} @ {race.racecourse.value} ({season})")
