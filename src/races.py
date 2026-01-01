"""
Uma Musume Racing Simulation - Complete Race Database

Contains all races from Uma Musume game including:
- G1, G2, G3 JRA races  
- International prestigious races (Prix de l'Arc de Triomphe, etc.)
- Pre-G1 classification (OP, L races)

Race information includes:
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
    """Racecourses including JRA, NAR, and International"""
    # JRA Racecourses
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
    # NAR Racecourses
    OHI = "Ohi"
    KAWASAKI = "Kawasaki"
    FUNABASHI = "Funabashi"
    MORIOKA = "Morioka"
    KASAMATSU = "Kasamatsu"
    SONODA = "Sonoda"
    URAWA = "Urawa"
    # International Racecourses
    LONGCHAMP = "Longchamp"  # France - Prix de l'Arc de Triomphe
    CHANTILLY = "Chantilly"  # France
    DEAUVILLE = "Deauville"  # France
    SAINT_CLOUD = "Saint-Cloud"  # France
    ASCOT = "Ascot"  # UK
    EPSOM = "Epsom"  # UK
    NEWMARKET = "Newmarket"  # UK
    GOODWOOD = "Goodwood"  # UK
    YORK = "York"  # UK
    SANTA_ANITA = "Santa Anita"  # USA
    DEL_MAR = "Del Mar"  # USA
    KEENELAND = "Keeneland"  # USA
    CHURCHILL_DOWNS = "Churchill Downs"  # USA
    BELMONT = "Belmont Park"  # USA
    GULFSTREAM = "Gulfstream Park"  # USA
    MEYDAN = "Meydan"  # UAE - Dubai
    SHA_TIN = "Sha Tin"  # Hong Kong
    HAPPY_VALLEY = "Happy Valley"  # Hong Kong
    FLEMINGTON = "Flemington"  # Australia
    MOONEE_VALLEY = "Moonee Valley"  # Australia
    RANDWICK = "Randwick"  # Australia
    MEYDAN_SAUDI = "King Abdulaziz"  # Saudi Arabia - Saudi Cup
    SERI_KENANGAN = "Selangor Turf Club"  # Malaysia - Merdeka Cup
    DONCASTER = "Doncaster"  # UK
    SANDOWN = "Sandown"  # UK
    PIMLICO = "Pimlico"  # USA
    SARATOGA = "Saratoga"  # USA
    ZARZUELA = "Zarzuela"  # Spain
    SAN_SEBASTIAN = "San Sebastian"  # Spain
    SANTA_ROSA = "Santa Rosa Park"  # Philippines


# Racecourse track directions
RACECOURSE_DIRECTIONS = {
    # JRA
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
    # NAR
    Racecourse.OHI: Direction.RIGHT,
    Racecourse.KAWASAKI: Direction.LEFT,
    Racecourse.FUNABASHI: Direction.RIGHT,
    Racecourse.MORIOKA: Direction.LEFT,
    Racecourse.KASAMATSU: Direction.LEFT,
    Racecourse.SONODA: Direction.RIGHT,
    Racecourse.URAWA: Direction.LEFT,
    # International
    Racecourse.LONGCHAMP: Direction.RIGHT,
    Racecourse.CHANTILLY: Direction.RIGHT,
    Racecourse.DEAUVILLE: Direction.RIGHT,
    Racecourse.SAINT_CLOUD: Direction.LEFT,
    Racecourse.ASCOT: Direction.RIGHT,
    Racecourse.EPSOM: Direction.LEFT,
    Racecourse.NEWMARKET: Direction.RIGHT,
    Racecourse.GOODWOOD: Direction.RIGHT,
    Racecourse.YORK: Direction.LEFT,
    Racecourse.SANTA_ANITA: Direction.LEFT,
    Racecourse.DEL_MAR: Direction.LEFT,
    Racecourse.KEENELAND: Direction.LEFT,
    Racecourse.CHURCHILL_DOWNS: Direction.LEFT,
    Racecourse.BELMONT: Direction.LEFT,
    Racecourse.GULFSTREAM: Direction.LEFT,
    Racecourse.MEYDAN: Direction.LEFT,
    Racecourse.SHA_TIN: Direction.RIGHT,
    Racecourse.HAPPY_VALLEY: Direction.RIGHT,
    Racecourse.FLEMINGTON: Direction.LEFT,
    Racecourse.MOONEE_VALLEY: Direction.LEFT,
    Racecourse.RANDWICK: Direction.LEFT,
    Racecourse.MEYDAN_SAUDI: Direction.LEFT,
    Racecourse.SERI_KENANGAN: Direction.LEFT,
    Racecourse.DONCASTER: Direction.LEFT,
    Racecourse.SANDOWN: Direction.RIGHT,
    Racecourse.PIMLICO: Direction.LEFT,
    Racecourse.SARATOGA: Direction.LEFT,
    Racecourse.ZARZUELA: Direction.RIGHT,
    Racecourse.SAN_SEBASTIAN: Direction.RIGHT,
    Racecourse.SANTA_ROSA: Direction.LEFT,
}


@dataclass
class Race:
    """Represents a horse race"""
    id: str                          # Unique identifier
    name: str                        # Official race name
    name_jp: str                     # Japanese name
    distance: int                    # Distance in meters
    race_type: RaceType              # Sprint/Mile/Medium/Long
    surface: Surface                 # Turf/Dirt
    racecourse: Racecourse           # Where the race is held
    direction: Direction             # Track direction
    month: int                       # Month when typically held (1-12)
    grade: str = "G1"                # Grade level (G1, G2, G3, OP, L, etc.)
    eligibility: str = "3yo+"        # Age/sex eligibility
    prize_money: Optional[int] = None  # Prize money in local currency (optional)
    country: str = "Japan"           # Country where race is held
    
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
# JRA G2 RACES DATABASE
# ============================================================================

G2_RACES = {
    # ======================== JANUARY ========================
    "american_jockey_club_cup": Race(
        id="american_jockey_club_cup",
        name="American Jockey Club Cup",
        name_jp="アメリカジョッキークラブカップ",
        distance=2200,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=1,
        grade="G2",
        eligibility="4yo+",
        prize_money=57_000_000
    ),
    
    "kyoto_kinen": Race(
        id="kyoto_kinen",
        name="Kyoto Kinen",
        name_jp="京都記念",
        distance=2200,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=2,
        grade="G2",
        eligibility="4yo+",
        prize_money=62_000_000
    ),
    
    # ======================== FEBRUARY ========================
    "nakayama_kinen": Race(
        id="nakayama_kinen",
        name="Nakayama Kinen",
        name_jp="中山記念",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=2,
        grade="G2",
        eligibility="4yo+",
        prize_money=62_000_000
    ),
    
    # ======================== MARCH ========================
    "kinko_sho": Race(
        id="kinko_sho",
        name="Kinko Sho",
        name_jp="金鯱賞",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.CHUKYO,
        direction=Direction.LEFT,
        month=3,
        grade="G2",
        eligibility="4yo+",
        prize_money=62_000_000
    ),
    
    "hochi_hai_yayoi_sho": Race(
        id="hochi_hai_yayoi_sho",
        name="Yayoi Sho",
        name_jp="弥生賞ディープインパクト記念",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=3,
        grade="G2",
        eligibility="3yo",
        prize_money=53_000_000
    ),
    
    "tulip_sho": Race(
        id="tulip_sho",
        name="Tulip Sho",
        name_jp="チューリップ賞",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=3,
        grade="G2",
        eligibility="3yo fillies",
        prize_money=53_000_000
    ),
    
    "fillies_revue": Race(
        id="fillies_revue",
        name="Fillies' Revue",
        name_jp="フィリーズレビュー",
        distance=1400,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=3,
        grade="G2",
        eligibility="3yo fillies",
        prize_money=53_000_000
    ),
    
    "spring_stakes": Race(
        id="spring_stakes",
        name="Spring Stakes",
        name_jp="スプリングステークス",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=3,
        grade="G2",
        eligibility="3yo",
        prize_money=53_000_000
    ),
    
    "nikkei_sho": Race(
        id="nikkei_sho",
        name="Nikkei Sho",
        name_jp="日経賞",
        distance=2500,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=3,
        grade="G2",
        eligibility="4yo+",
        prize_money=57_000_000
    ),
    
    "hanshin_daishoten": Race(
        id="hanshin_daishoten",
        name="Hanshin Daishoten",
        name_jp="阪神大賞典",
        distance=3000,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=3,
        grade="G2",
        eligibility="4yo+",
        prize_money=57_000_000
    ),
    
    # ======================== APRIL ========================
    "sankei_sho_flora_stakes": Race(
        id="sankei_sho_flora_stakes",
        name="Flora Stakes",
        name_jp="フローラステークス",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=4,
        grade="G2",
        eligibility="3yo fillies",
        prize_money=53_000_000
    ),
    
    "aoba_sho": Race(
        id="aoba_sho",
        name="Aoba Sho",
        name_jp="青葉賞",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=4,
        grade="G2",
        eligibility="3yo",
        prize_money=53_000_000
    ),
    
    # ======================== MAY ========================
    "kyoto_shimbun_hai": Race(
        id="kyoto_shimbun_hai",
        name="Kyoto Shimbun Hai",
        name_jp="京都新聞杯",
        distance=2200,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=5,
        grade="G2",
        eligibility="3yo",
        prize_money=53_000_000
    ),
    
    # ======================== JUNE ========================
    "mermaid_stakes": Race(
        id="mermaid_stakes",
        name="Mermaid Stakes",
        name_jp="マーメイドステークス",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=6,
        grade="G3",
        eligibility="3yo+ fillies & mares",
        prize_money=43_000_000
    ),
    
    # ======================== AUGUST ========================
    "sapporo_kinen": Race(
        id="sapporo_kinen",
        name="Sapporo Kinen",
        name_jp="札幌記念",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.SAPPORO,
        direction=Direction.RIGHT,
        month=8,
        grade="G2",
        eligibility="3yo+",
        prize_money=62_000_000
    ),
    
    "niigata_kinen": Race(
        id="niigata_kinen",
        name="Niigata Kinen",
        name_jp="新潟記念",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.NIIGATA,
        direction=Direction.LEFT,
        month=8,
        grade="G3",
        eligibility="3yo+",
        prize_money=43_000_000
    ),
    
    "keeneland_cup": Race(
        id="keeneland_cup",
        name="Keeneland Cup",
        name_jp="キーンランドカップ",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.SAPPORO,
        direction=Direction.RIGHT,
        month=8,
        grade="G3",
        eligibility="3yo+",
        prize_money=43_000_000
    ),
    
    # ======================== SEPTEMBER ========================
    "keisei_hai_autumn_handicap": Race(
        id="keisei_hai_autumn_handicap",
        name="Keisei Hai Autumn Handicap",
        name_jp="京成杯オータムハンデキャップ",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=9,
        grade="G3",
        eligibility="3yo+",
        prize_money=43_000_000
    ),
    
    "all_comers": Race(
        id="all_comers",
        name="All Comers",
        name_jp="オールカマー",
        distance=2200,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=9,
        grade="G2",
        eligibility="3yo+",
        prize_money=57_000_000
    ),
    
    "kobe_shimbun_hai": Race(
        id="kobe_shimbun_hai",
        name="Kobe Shimbun Hai",
        name_jp="神戸新聞杯",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=9,
        grade="G2",
        eligibility="3yo",
        prize_money=57_000_000
    ),
    
    "rose_stakes": Race(
        id="rose_stakes",
        name="Rose Stakes",
        name_jp="ローズステークス",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=9,
        grade="G2",
        eligibility="3yo fillies",
        prize_money=53_000_000
    ),
    
    "saint_lite_kinen": Race(
        id="saint_lite_kinen",
        name="St. Lite Kinen",
        name_jp="セントライト記念",
        distance=2200,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=9,
        grade="G2",
        eligibility="3yo",
        prize_money=57_000_000
    ),
    
    # ======================== OCTOBER ========================
    "mainichi_okan": Race(
        id="mainichi_okan",
        name="Mainichi Okan",
        name_jp="毎日王冠",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=10,
        grade="G2",
        eligibility="3yo+",
        prize_money=62_000_000
    ),
    
    "fuji_stakes": Race(
        id="fuji_stakes",
        name="Fuji Stakes",
        name_jp="富士ステークス",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=10,
        grade="G2",
        eligibility="3yo+",
        prize_money=57_000_000
    ),
    
    "swan_stakes": Race(
        id="swan_stakes",
        name="Swan Stakes",
        name_jp="スワンステークス",
        distance=1400,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=10,
        grade="G2",
        eligibility="3yo+",
        prize_money=57_000_000
    ),
    
    # ======================== NOVEMBER ========================
    "argentina_kyowakoku_hai": Race(
        id="argentina_kyowakoku_hai",
        name="Argentina Kyowakoku Hai",
        name_jp="アルゼンチン共和国杯",
        distance=2500,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=11,
        grade="G2",
        eligibility="3yo+",
        prize_money=57_000_000
    ),
    
    "stayers_stakes": Race(
        id="stayers_stakes",
        name="Stayers Stakes",
        name_jp="ステイヤーズステークス",
        distance=3600,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=12,
        grade="G2",
        eligibility="3yo+",
        prize_money=43_000_000
    ),
    
    "kyoto_himba_stakes": Race(
        id="kyoto_himba_stakes",
        name="Kyoto Himba Stakes",
        name_jp="京都牝馬ステークス",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=2,
        grade="G3",
        eligibility="4yo+ fillies & mares",
        prize_money=43_000_000
    ),
    
    # ======================== DECEMBER ========================
    "hanshin_cup": Race(
        id="hanshin_cup",
        name="Hanshin Cup",
        name_jp="阪神カップ",
        distance=1400,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=12,
        grade="G2",
        eligibility="3yo+",
        prize_money=62_000_000
    ),
}


# ============================================================================
# JRA G3 RACES DATABASE
# ============================================================================

G3_RACES = {
    # ======================== JANUARY ========================
    "fairy_stakes": Race(
        id="fairy_stakes",
        name="Fairy Stakes",
        name_jp="フェアリーステークス",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=1,
        grade="G3",
        eligibility="3yo fillies",
        prize_money=38_000_000
    ),
    
    "shinzan_kinen": Race(
        id="shinzan_kinen",
        name="Shinzan Kinen",
        name_jp="シンザン記念",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=1,
        grade="G3",
        eligibility="3yo",
        prize_money=38_000_000
    ),
    
    "nenga_hai": Race(
        id="nenga_hai",
        name="Tokai Stakes",
        name_jp="東海ステークス",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.DIRT,
        racecourse=Racecourse.CHUKYO,
        direction=Direction.LEFT,
        month=1,
        grade="G2",
        eligibility="4yo+",
        prize_money=53_000_000
    ),
    
    "negishi_stakes": Race(
        id="negishi_stakes",
        name="Negishi Stakes",
        name_jp="根岸ステークス",
        distance=1400,
        race_type=RaceType.SPRINT,
        surface=Surface.DIRT,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=1,
        grade="G3",
        eligibility="4yo+",
        prize_money=43_000_000
    ),
    
    # ======================== FEBRUARY ========================
    "queen_cup": Race(
        id="queen_cup",
        name="Queen Cup",
        name_jp="クイーンカップ",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=2,
        grade="G3",
        eligibility="3yo fillies",
        prize_money=38_000_000
    ),
    
    "kisaragi_sho": Race(
        id="kisaragi_sho",
        name="Kisaragi Sho",
        name_jp="きさらぎ賞",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=2,
        grade="G3",
        eligibility="3yo",
        prize_money=38_000_000
    ),
    
    "kyodo_news_hai": Race(
        id="kyodo_news_hai",
        name="Kyodo News Hai",
        name_jp="共同通信杯",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=2,
        grade="G3",
        eligibility="3yo",
        prize_money=43_000_000
    ),
    
    # ======================== MARCH ========================
    "ocean_stakes": Race(
        id="ocean_stakes",
        name="Ocean Stakes",
        name_jp="オーシャンステークス",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=3,
        grade="G3",
        eligibility="4yo+",
        prize_money=38_000_000
    ),
    
    "flower_cup": Race(
        id="flower_cup",
        name="Flower Cup",
        name_jp="フラワーカップ",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=3,
        grade="G3",
        eligibility="3yo fillies",
        prize_money=38_000_000
    ),
    
    "falcon_stakes": Race(
        id="falcon_stakes",
        name="Falcon Stakes",
        name_jp="ファルコンステークス",
        distance=1400,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.CHUKYO,
        direction=Direction.LEFT,
        month=3,
        grade="G3",
        eligibility="3yo",
        prize_money=38_000_000
    ),
    
    # ======================== APRIL ========================
    "dandelion_sho": Race(
        id="dandelion_sho",
        name="Dandelion Sho",
        name_jp="葵ステークス",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=5,
        grade="G3",
        eligibility="3yo",
        prize_money=38_000_000
    ),
    
    "new_zealand_trophy": Race(
        id="new_zealand_trophy",
        name="New Zealand Trophy",
        name_jp="ニュージーランドトロフィー",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=4,
        grade="G2",
        eligibility="3yo",
        prize_money=53_000_000
    ),
    
    "arlington_cup": Race(
        id="arlington_cup",
        name="Arlington Cup",
        name_jp="アーリントンカップ",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.HANSHIN,
        direction=Direction.RIGHT,
        month=4,
        grade="G3",
        eligibility="3yo",
        prize_money=38_000_000
    ),
    
    # ======================== MAY ========================
    "niigata_daishoten": Race(
        id="niigata_daishoten",
        name="Niigata Daishoten",
        name_jp="新潟大賞典",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.NIIGATA,
        direction=Direction.LEFT,
        month=5,
        grade="G3",
        eligibility="4yo+",
        prize_money=38_000_000
    ),
    
    # ======================== JUNE ========================
    "epsom_cup": Race(
        id="epsom_cup",
        name="Epsom Cup",
        name_jp="エプソムカップ",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=6,
        grade="G3",
        eligibility="3yo+",
        prize_money=43_000_000
    ),
    
    "hakodate_sprint_stakes": Race(
        id="hakodate_sprint_stakes",
        name="Hakodate Sprint Stakes",
        name_jp="函館スプリントステークス",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.HAKODATE,
        direction=Direction.RIGHT,
        month=6,
        grade="G3",
        eligibility="3yo+",
        prize_money=38_000_000
    ),
    
    "unicorn_stakes": Race(
        id="unicorn_stakes",
        name="Unicorn Stakes",
        name_jp="ユニコーンステークス",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.DIRT,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=6,
        grade="G3",
        eligibility="3yo",
        prize_money=38_000_000
    ),
    
    # ======================== JULY ========================
    "cbc_sho": Race(
        id="cbc_sho",
        name="CBC Sho",
        name_jp="CBC賞",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.CHUKYO,
        direction=Direction.LEFT,
        month=7,
        grade="G3",
        eligibility="3yo+",
        prize_money=43_000_000
    ),
    
    "tanabata_sho": Race(
        id="tanabata_sho",
        name="Tanabata Sho",
        name_jp="七夕賞",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.FUKUSHIMA,
        direction=Direction.RIGHT,
        month=7,
        grade="G3",
        eligibility="3yo+",
        prize_money=38_000_000
    ),
    
    "procyon_stakes": Race(
        id="procyon_stakes",
        name="Procyon Stakes",
        name_jp="プロキオンステークス",
        distance=1400,
        race_type=RaceType.SPRINT,
        surface=Surface.DIRT,
        racecourse=Racecourse.CHUKYO,
        direction=Direction.LEFT,
        month=7,
        grade="G3",
        eligibility="3yo+",
        prize_money=38_000_000
    ),
    
    "hakodate_kinen": Race(
        id="hakodate_kinen",
        name="Hakodate Kinen",
        name_jp="函館記念",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.HAKODATE,
        direction=Direction.RIGHT,
        month=7,
        grade="G3",
        eligibility="3yo+",
        prize_money=43_000_000
    ),
    
    "ibis_summer_dash": Race(
        id="ibis_summer_dash",
        name="Ibis Summer Dash",
        name_jp="アイビスサマーダッシュ",
        distance=1000,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.NIIGATA,
        direction=Direction.LEFT,
        month=7,
        grade="G3",
        eligibility="3yo+",
        prize_money=38_000_000
    ),
    
    # ======================== AUGUST ========================
    "cluster_cup": Race(
        id="cluster_cup",
        name="Cluster Cup",
        name_jp="クラスターカップ",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.DIRT,
        racecourse=Racecourse.MORIOKA,
        direction=Direction.LEFT,
        month=8,
        grade="JpnG3",
        eligibility="3yo+",
        prize_money=30_000_000
    ),
    
    "kokura_kinen": Race(
        id="kokura_kinen",
        name="Kokura Kinen",
        name_jp="小倉記念",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.KOKURA,
        direction=Direction.RIGHT,
        month=8,
        grade="G3",
        eligibility="3yo+",
        prize_money=43_000_000
    ),
    
    # ======================== SEPTEMBER ========================
    "shion_stakes": Race(
        id="shion_stakes",
        name="Shion Stakes",
        name_jp="紫苑ステークス",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=9,
        grade="G2",
        eligibility="3yo fillies",
        prize_money=53_000_000
    ),
    
    # ======================== OCTOBER ========================
    "samurai_dash": Race(
        id="samurai_dash",
        name="Samurai Dash",
        name_jp="サムライダッシュ",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.FUKUSHIMA,
        direction=Direction.RIGHT,
        month=10,
        grade="OP",
        eligibility="3yo+",
        prize_money=30_000_000
    ),
    
    # ======================== NOVEMBER ========================
    "fantasy_stakes": Race(
        id="fantasy_stakes",
        name="Fantasy Stakes",
        name_jp="ファンタジーステークス",
        distance=1400,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=11,
        grade="G3",
        eligibility="2yo fillies",
        prize_money=38_000_000
    ),
    
    "artemis_stakes": Race(
        id="artemis_stakes",
        name="Artemis Stakes",
        name_jp="アルテミスステークス",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.TOKYO,
        direction=Direction.LEFT,
        month=10,
        grade="G3",
        eligibility="2yo fillies",
        prize_money=38_000_000
    ),
    
    "sports_nippon_sho_kyoto_2_year_old_stakes": Race(
        id="sports_nippon_sho_kyoto_2_year_old_stakes",
        name="Sports Nippon Sho Kyoto 2-Year-Old Stakes",
        name_jp="スポニチ賞京都２歳ステークス",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=11,
        grade="G3",
        eligibility="2yo",
        prize_money=38_000_000
    ),
    
    "daily_hai_2_year_old_stakes": Race(
        id="daily_hai_2_year_old_stakes",
        name="Daily Hai Nisai Stakes",
        name_jp="デイリー杯２歳ステークス",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.KYOTO,
        direction=Direction.RIGHT,
        month=11,
        grade="G2",
        eligibility="2yo",
        prize_money=53_000_000
    ),
    
    # ======================== DECEMBER ========================
    "capella_stakes": Race(
        id="capella_stakes",
        name="Capella Stakes",
        name_jp="カペラステークス",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.DIRT,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=12,
        grade="G3",
        eligibility="3yo+",
        prize_money=38_000_000
    ),
    
    "turquoise_stakes": Race(
        id="turquoise_stakes",
        name="Turquoise Stakes",
        name_jp="ターコイズステークス",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=12,
        grade="G3",
        eligibility="3yo+ fillies & mares",
        prize_money=43_000_000
    ),
    
    "nakayama_grand_jump": Race(
        id="nakayama_grand_jump",
        name="Nakayama Grand Jump",
        name_jp="中山グランドジャンプ",
        distance=4250,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.NAKAYAMA,
        direction=Direction.RIGHT,
        month=4,
        grade="J-G1",
        eligibility="4yo+",
        prize_money=60_000_000
    ),
}


# ============================================================================
# INTERNATIONAL RACES DATABASE
# ============================================================================

INTERNATIONAL_RACES = {
    # ======================== FRANCE ========================
    "prix_de_larc_de_triomphe": Race(
        id="prix_de_larc_de_triomphe",
        name="Prix de l'Arc de Triomphe",
        name_jp="凱旋門賞",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.LONGCHAMP,
        direction=Direction.RIGHT,
        month=10,
        grade="G1",
        eligibility="3yo+",
        prize_money=500_000_000,  # approx in JPY
        country="France"
    ),
    
    "prix_du_jockey_club": Race(
        id="prix_du_jockey_club",
        name="Prix du Jockey Club",
        name_jp="仏ダービー",
        distance=2100,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.CHANTILLY,
        direction=Direction.RIGHT,
        month=6,
        grade="G1",
        eligibility="3yo colts & fillies",
        prize_money=180_000_000,
        country="France"
    ),
    
    "prix_de_diane": Race(
        id="prix_de_diane",
        name="Prix de Diane",
        name_jp="仏オークス",
        distance=2100,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.CHANTILLY,
        direction=Direction.RIGHT,
        month=6,
        grade="G1",
        eligibility="3yo fillies",
        prize_money=120_000_000,
        country="France"
    ),
    
    "prix_ganay": Race(
        id="prix_ganay",
        name="Prix Ganay",
        name_jp="ガネー賞",
        distance=2100,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.LONGCHAMP,
        direction=Direction.RIGHT,
        month=4,
        grade="G1",
        eligibility="4yo+",
        prize_money=60_000_000,
        country="France"
    ),
    
    "poule_dessai_des_poulains": Race(
        id="poule_dessai_des_poulains",
        name="Poule d'Essai des Poulains",
        name_jp="仏2000ギニー",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.LONGCHAMP,
        direction=Direction.RIGHT,
        month=5,
        grade="G1",
        eligibility="3yo colts",
        prize_money=60_000_000,
        country="France"
    ),
    
    "poule_dessai_des_pouliches": Race(
        id="poule_dessai_des_pouliches",
        name="Poule d'Essai des Pouliches",
        name_jp="仏1000ギニー",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.LONGCHAMP,
        direction=Direction.RIGHT,
        month=5,
        grade="G1",
        eligibility="3yo fillies",
        prize_money=60_000_000,
        country="France"
    ),
    
    "prix_vermeille": Race(
        id="prix_vermeille",
        name="Prix Vermeille",
        name_jp="ヴェルメイユ賞",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.LONGCHAMP,
        direction=Direction.RIGHT,
        month=9,
        grade="G1",
        eligibility="3yo+ fillies & mares",
        prize_money=50_000_000,
        country="France"
    ),
    
    "prix_foy": Race(
        id="prix_foy",
        name="Prix Foy",
        name_jp="フォワ賞",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.LONGCHAMP,
        direction=Direction.RIGHT,
        month=9,
        grade="G2",
        eligibility="3yo+",
        prize_money=25_000_000,
        country="France"
    ),
    
    "prix_niel": Race(
        id="prix_niel",
        name="Prix Niel",
        name_jp="ニエル賞",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.LONGCHAMP,
        direction=Direction.RIGHT,
        month=9,
        grade="G2",
        eligibility="3yo",
        prize_money=25_000_000,
        country="France"
    ),
    
    # ======================== UNITED KINGDOM ========================
    "epsom_derby": Race(
        id="epsom_derby",
        name="Epsom Derby",
        name_jp="英ダービー",
        distance=2414,  # 1 mile 4 furlongs
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.EPSOM,
        direction=Direction.LEFT,
        month=6,
        grade="G1",
        eligibility="3yo colts & fillies",
        prize_money=200_000_000,
        country="United Kingdom"
    ),
    
    "epsom_oaks": Race(
        id="epsom_oaks",
        name="Epsom Oaks",
        name_jp="英オークス",
        distance=2414,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.EPSOM,
        direction=Direction.LEFT,
        month=6,
        grade="G1",
        eligibility="3yo fillies",
        prize_money=100_000_000,
        country="United Kingdom"
    ),
    
    "king_george_vi_and_queen_elizabeth_stakes": Race(
        id="king_george_vi_and_queen_elizabeth_stakes",
        name="King George VI and Queen Elizabeth Stakes",
        name_jp="キングジョージⅥ世&クイーンエリザベスS",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.ASCOT,
        direction=Direction.RIGHT,
        month=7,
        grade="G1",
        eligibility="3yo+",
        prize_money=150_000_000,
        country="United Kingdom"
    ),
    
    "royal_ascot_gold_cup": Race(
        id="royal_ascot_gold_cup",
        name="Ascot Gold Cup",
        name_jp="ゴールドカップ",
        distance=4014,  # 2 miles 4 furlongs
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.ASCOT,
        direction=Direction.RIGHT,
        month=6,
        grade="G1",
        eligibility="4yo+",
        prize_money=75_000_000,
        country="United Kingdom"
    ),
    
    "two_thousand_guineas": Race(
        id="two_thousand_guineas",
        name="2000 Guineas",
        name_jp="英2000ギニー",
        distance=1609,  # 1 mile
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NEWMARKET,
        direction=Direction.RIGHT,
        month=5,
        grade="G1",
        eligibility="3yo colts",
        prize_money=75_000_000,
        country="United Kingdom"
    ),
    
    "one_thousand_guineas": Race(
        id="one_thousand_guineas",
        name="1000 Guineas",
        name_jp="英1000ギニー",
        distance=1609,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NEWMARKET,
        direction=Direction.RIGHT,
        month=5,
        grade="G1",
        eligibility="3yo fillies",
        prize_money=60_000_000,
        country="United Kingdom"
    ),
    
    "st_leger": Race(
        id="st_leger",
        name="St Leger",
        name_jp="セントレジャー",
        distance=2921,  # 1 mile 6 furlongs 115 yards
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.YORK,
        direction=Direction.LEFT,
        month=9,
        grade="G1",
        eligibility="3yo",
        prize_money=70_000_000,
        country="United Kingdom"
    ),
    
    "sussex_stakes": Race(
        id="sussex_stakes",
        name="Sussex Stakes",
        name_jp="サセックスステークス",
        distance=1609,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.GOODWOOD,
        direction=Direction.RIGHT,
        month=7,
        grade="G1",
        eligibility="3yo+",
        prize_money=100_000_000,
        country="United Kingdom"
    ),
    
    "champion_stakes_uk": Race(
        id="champion_stakes_uk",
        name="Champion Stakes",
        name_jp="チャンピオンステークス（英）",
        distance=2011,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.ASCOT,
        direction=Direction.RIGHT,
        month=10,
        grade="G1",
        eligibility="3yo+",
        prize_money=150_000_000,
        country="United Kingdom"
    ),
    
    # ======================== UNITED STATES ========================
    "kentucky_derby": Race(
        id="kentucky_derby",
        name="Kentucky Derby",
        name_jp="ケンタッキーダービー",
        distance=2012,  # 1 1/4 miles
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.CHURCHILL_DOWNS,
        direction=Direction.LEFT,
        month=5,
        grade="G1",
        eligibility="3yo",
        prize_money=500_000_000,
        country="United States"
    ),
    
    "preakness_stakes": Race(
        id="preakness_stakes",
        name="Preakness Stakes",
        name_jp="プリークネスステークス",
        distance=1911,  # 1 3/16 miles
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.CHURCHILL_DOWNS,  # Actually Pimlico
        direction=Direction.LEFT,
        month=5,
        grade="G1",
        eligibility="3yo",
        prize_money=200_000_000,
        country="United States"
    ),
    
    "belmont_stakes": Race(
        id="belmont_stakes",
        name="Belmont Stakes",
        name_jp="ベルモントステークス",
        distance=2414,  # 1 1/2 miles
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.BELMONT,
        direction=Direction.LEFT,
        month=6,
        grade="G1",
        eligibility="3yo",
        prize_money=200_000_000,
        country="United States"
    ),
    
    "breeders_cup_classic": Race(
        id="breeders_cup_classic",
        name="Breeders' Cup Classic",
        name_jp="ブリーダーズカップクラシック",
        distance=2000,  # 1 1/4 miles
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.SANTA_ANITA,  # Varies each year
        direction=Direction.LEFT,
        month=11,
        grade="G1",
        eligibility="3yo+",
        prize_money=700_000_000,
        country="United States"
    ),
    
    "breeders_cup_turf": Race(
        id="breeders_cup_turf",
        name="Breeders' Cup Turf",
        name_jp="ブリーダーズカップターフ",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.SANTA_ANITA,
        direction=Direction.LEFT,
        month=11,
        grade="G1",
        eligibility="3yo+",
        prize_money=500_000_000,
        country="United States"
    ),
    
    "breeders_cup_mile": Race(
        id="breeders_cup_mile",
        name="Breeders' Cup Mile",
        name_jp="ブリーダーズカップマイル",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.SANTA_ANITA,
        direction=Direction.LEFT,
        month=11,
        grade="G1",
        eligibility="3yo+",
        prize_money=300_000_000,
        country="United States"
    ),
    
    "breeders_cup_sprint": Race(
        id="breeders_cup_sprint",
        name="Breeders' Cup Sprint",
        name_jp="ブリーダーズカップスプリント",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.DIRT,
        racecourse=Racecourse.SANTA_ANITA,
        direction=Direction.LEFT,
        month=11,
        grade="G1",
        eligibility="3yo+",
        prize_money=200_000_000,
        country="United States"
    ),
    
    "breeders_cup_distaff": Race(
        id="breeders_cup_distaff",
        name="Breeders' Cup Distaff",
        name_jp="ブリーダーズカップディスタフ",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.DIRT,
        racecourse=Racecourse.SANTA_ANITA,
        direction=Direction.LEFT,
        month=11,
        grade="G1",
        eligibility="3yo+ fillies & mares",
        prize_money=300_000_000,
        country="United States"
    ),
    
    "santa_anita_handicap": Race(
        id="santa_anita_handicap",
        name="Santa Anita Handicap",
        name_jp="サンタアニタハンデキャップ",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.SANTA_ANITA,
        direction=Direction.LEFT,
        month=3,
        grade="G1",
        eligibility="4yo+",
        prize_money=100_000_000,
        country="United States"
    ),
    
    "pacific_classic": Race(
        id="pacific_classic",
        name="Pacific Classic",
        name_jp="パシフィッククラシック",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.DEL_MAR,
        direction=Direction.LEFT,
        month=8,
        grade="G1",
        eligibility="3yo+",
        prize_money=150_000_000,
        country="United States"
    ),
    
    # ======================== UAE (DUBAI) ========================
    "dubai_world_cup": Race(
        id="dubai_world_cup",
        name="Dubai World Cup",
        name_jp="ドバイワールドカップ",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.MEYDAN,
        direction=Direction.LEFT,
        month=3,
        grade="G1",
        eligibility="4yo+",
        prize_money=1_500_000_000,  # $12 million
        country="UAE"
    ),
    
    "dubai_sheema_classic": Race(
        id="dubai_sheema_classic",
        name="Dubai Sheema Classic",
        name_jp="ドバイシーマクラシック",
        distance=2410,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.MEYDAN,
        direction=Direction.LEFT,
        month=3,
        grade="G1",
        eligibility="4yo+",
        prize_money=750_000_000,
        country="UAE"
    ),
    
    "dubai_turf": Race(
        id="dubai_turf",
        name="Dubai Turf",
        name_jp="ドバイターフ",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.MEYDAN,
        direction=Direction.LEFT,
        month=3,
        grade="G1",
        eligibility="4yo+",
        prize_money=600_000_000,
        country="UAE"
    ),
    
    "dubai_golden_shaheen": Race(
        id="dubai_golden_shaheen",
        name="Dubai Golden Shaheen",
        name_jp="ドバイゴールデンシャヒーン",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.DIRT,
        racecourse=Racecourse.MEYDAN,
        direction=Direction.LEFT,
        month=3,
        grade="G1",
        eligibility="3yo+",
        prize_money=300_000_000,
        country="UAE"
    ),
    
    # ======================== SAUDI ARABIA ========================
    "saudi_cup": Race(
        id="saudi_cup",
        name="Saudi Cup",
        name_jp="サウジカップ",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.DIRT,
        racecourse=Racecourse.MEYDAN_SAUDI,
        direction=Direction.LEFT,
        month=2,
        grade="G1",
        eligibility="4yo+",
        prize_money=2_500_000_000,  # $20 million - richest race
        country="Saudi Arabia"
    ),
    
    # ======================== HONG KONG ========================
    "hong_kong_cup": Race(
        id="hong_kong_cup",
        name="Hong Kong Cup",
        name_jp="香港カップ",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.SHA_TIN,
        direction=Direction.RIGHT,
        month=12,
        grade="G1",
        eligibility="3yo+",
        prize_money=400_000_000,
        country="Hong Kong"
    ),
    
    "hong_kong_mile": Race(
        id="hong_kong_mile",
        name="Hong Kong Mile",
        name_jp="香港マイル",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.SHA_TIN,
        direction=Direction.RIGHT,
        month=12,
        grade="G1",
        eligibility="3yo+",
        prize_money=350_000_000,
        country="Hong Kong"
    ),
    
    "hong_kong_sprint": Race(
        id="hong_kong_sprint",
        name="Hong Kong Sprint",
        name_jp="香港スプリント",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.SHA_TIN,
        direction=Direction.RIGHT,
        month=12,
        grade="G1",
        eligibility="3yo+",
        prize_money=300_000_000,
        country="Hong Kong"
    ),
    
    "hong_kong_vase": Race(
        id="hong_kong_vase",
        name="Hong Kong Vase",
        name_jp="香港ヴァーズ",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.SHA_TIN,
        direction=Direction.RIGHT,
        month=12,
        grade="G1",
        eligibility="3yo+",
        prize_money=300_000_000,
        country="Hong Kong"
    ),
    
    "qeii_cup_hk": Race(
        id="qeii_cup_hk",
        name="Queen Elizabeth II Cup (HK)",
        name_jp="クイーンエリザベス２世カップ（香港）",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.SHA_TIN,
        direction=Direction.RIGHT,
        month=4,
        grade="G1",
        eligibility="4yo+",
        prize_money=350_000_000,
        country="Hong Kong"
    ),
    
    "champions_mile_hk": Race(
        id="champions_mile_hk",
        name="Champions Mile",
        name_jp="チャンピオンズマイル",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.SHA_TIN,
        direction=Direction.RIGHT,
        month=5,
        grade="G1",
        eligibility="4yo+",
        prize_money=300_000_000,
        country="Hong Kong"
    ),
    
    # ======================== AUSTRALIA ========================
    "melbourne_cup": Race(
        id="melbourne_cup",
        name="Melbourne Cup",
        name_jp="メルボルンカップ",
        distance=3200,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.FLEMINGTON,
        direction=Direction.LEFT,
        month=11,
        grade="G1",
        eligibility="3yo+",
        prize_money=1_000_000_000,
        country="Australia"
    ),
    
    "cox_plate": Race(
        id="cox_plate",
        name="Cox Plate",
        name_jp="コックスプレート",
        distance=2040,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.MOONEE_VALLEY,
        direction=Direction.LEFT,
        month=10,
        grade="G1",
        eligibility="3yo+",
        prize_money=600_000_000,
        country="Australia"
    ),
    
    "caulfield_cup": Race(
        id="caulfield_cup",
        name="Caulfield Cup",
        name_jp="コーフィールドカップ",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.RANDWICK,
        direction=Direction.LEFT,
        month=10,
        grade="G1",
        eligibility="3yo+",
        prize_money=500_000_000,
        country="Australia"
    ),
    
    "the_everest": Race(
        id="the_everest",
        name="The Everest",
        name_jp="ジ・エベレスト",
        distance=1200,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.RANDWICK,
        direction=Direction.LEFT,
        month=10,
        grade="G1",
        eligibility="3yo+",
        prize_money=1_800_000_000,
        country="Australia"
    ),
    
    # ======================== MALAYSIA ========================
    "merdeka_cup": Race(
        id="merdeka_cup",
        name="Merdeka Cup",
        name_jp="ムルデカカップ",
        distance=1400,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.SERI_KENANGAN,
        direction=Direction.LEFT,
        month=8,
        grade="G3",
        eligibility="3yo+",
        prize_money=15_000_000,
        country="Malaysia"
    ),
    
    "coronation_cup_my": Race(
        id="coronation_cup_my",
        name="Coronation Cup (MY)",
        name_jp="コロネーションカップ（マレーシア）",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.SERI_KENANGAN,
        direction=Direction.LEFT,
        month=6,
        grade="G3",
        eligibility="3yo+",
        prize_money=20_000_000,
        country="Malaysia"
    ),
    
    "piala_emas_sultan_selangor": Race(
        id="piala_emas_sultan_selangor",
        name="Piala Emas Sultan Selangor",
        name_jp="スルタンセランゴールゴールドカップ",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.SERI_KENANGAN,
        direction=Direction.LEFT,
        month=12,
        grade="G2",
        eligibility="3yo+",
        prize_money=30_000_000,
        country="Malaysia"
    ),
    
    # ======================== IRELAND ========================
    "irish_derby": Race(
        id="irish_derby",
        name="Irish Derby",
        name_jp="愛ダービー",
        distance=2414,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.EPSOM,  # Actually Curragh
        direction=Direction.RIGHT,
        month=6,
        grade="G1",
        eligibility="3yo",
        prize_money=120_000_000,
        country="Ireland"
    ),
    
    "irish_champion_stakes": Race(
        id="irish_champion_stakes",
        name="Irish Champion Stakes",
        name_jp="アイリッシュチャンピオンステークス",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.EPSOM,  # Actually Leopardstown
        direction=Direction.LEFT,
        month=9,
        grade="G1",
        eligibility="3yo+",
        prize_money=150_000_000,
        country="Ireland"
    ),
    
    # ======================== GERMANY ========================
    "grosser_preis_von_baden": Race(
        id="grosser_preis_von_baden",
        name="Grosser Preis von Baden",
        name_jp="バーデン大賞",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.EPSOM,  # Actually Baden-Baden
        direction=Direction.LEFT,
        month=9,
        grade="G1",
        eligibility="3yo+",
        prize_money=40_000_000,
        country="Germany"
    ),
    
    # ======================== ITALY ========================
    "premio_roma": Race(
        id="premio_roma",
        name="Premio Roma",
        name_jp="ローマ賞",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.EPSOM,  # Actually Capannelle
        direction=Direction.RIGHT,
        month=11,
        grade="G1",
        eligibility="3yo+",
        prize_money=30_000_000,
        country="Italy"
    ),
    
    # ======================== FRANCE (ADDITIONAL) ========================
    "prix_de_diane": Race(
        id="prix_de_diane",
        name="Prix de Diane",
        name_jp="プリ・ド・ディアーヌ",
        distance=2145,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.CHANTILLY,
        direction=Direction.RIGHT,
        month=6,
        grade="G1",
        eligibility="3yo fillies",
        prize_money=300_000_000,
        country="France"
    ),
    
    "prix_saint_george": Race(
        id="prix_saint_george",
        name="Prix Saint-George",
        name_jp="プリ・サンジョルジュ",
        distance=1400,
        race_type=RaceType.SPRINT,
        surface=Surface.TURF,
        racecourse=Racecourse.SAINT_CLOUD,
        direction=Direction.LEFT,
        month=5,
        grade="G3",
        eligibility="3yo+",
        prize_money=80_000_000,
        country="France"
    ),
    
    "grand_prix_de_deauville": Race(
        id="grand_prix_de_deauville",
        name="Grand Prix de Deauville",
        name_jp="グランプリ・ド・ドーヴィル",
        distance=2100,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.DEAUVILLE,
        direction=Direction.RIGHT,
        month=8,
        grade="G2",
        eligibility="3yo+",
        prize_money=150_000_000,
        country="France"
    ),
    
    # ======================== UNITED KINGDOM (ADDITIONAL) ========================
    "2000_guineas": Race(
        id="2000_guineas",
        name="2000 Guineas",
        name_jp="2000ギニー",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NEWMARKET,
        direction=Direction.RIGHT,
        month=5,
        grade="G1",
        eligibility="3yo colts",
        prize_money=180_000_000,
        country="United Kingdom"
    ),
    
    "1000_guineas": Race(
        id="1000_guineas",
        name="1000 Guineas",
        name_jp="1000ギニー",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.NEWMARKET,
        direction=Direction.RIGHT,
        month=5,
        grade="G1",
        eligibility="3yo fillies",
        prize_money=180_000_000,
        country="United Kingdom"
    ),
    
    "epsom_derby": Race(
        id="epsom_derby",
        name="Epsom Derby",
        name_jp="エプソムダービー",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.EPSOM,
        direction=Direction.LEFT,
        month=6,
        grade="G1",
        eligibility="3yo colts & fillies",
        prize_money=250_000_000,
        country="United Kingdom"
    ),
    
    "epsom_oaks": Race(
        id="epsom_oaks",
        name="Epsom Oaks",
        name_jp="オークス",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.EPSOM,
        direction=Direction.LEFT,
        month=6,
        grade="G1",
        eligibility="3yo fillies",
        prize_money=200_000_000,
        country="United Kingdom"
    ),
    
    "st_leger_stakes": Race(
        id="st_leger_stakes",
        name="St Leger Stakes",
        name_jp="セントレジャー",
        distance=2830,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.DONCASTER,  # Need to add Doncaster to enum
        direction=Direction.LEFT,
        month=9,
        grade="G1",
        eligibility="3yo",
        prize_money=180_000_000,
        country="United Kingdom"
    ),
    
    "eclipse_stakes": Race(
        id="eclipse_stakes",
        name="Eclipse Stakes",
        name_jp="エクリプスステークス",
        distance=2002,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.SANDOWN,  # Need to add Sandown to enum
        direction=Direction.RIGHT,
        month=7,
        grade="G1",
        eligibility="3yo+",
        prize_money=140_000_000,
        country="United Kingdom"
    ),
    
    "king_george_iv_queen_elizabeth_ii_stakes": Race(
        id="king_george_iv_queen_elizabeth_ii_stakes",
        name="King George IV & Queen Elizabeth II Stakes",
        name_jp="キングジョージ4世・クイーンエリザベス2世ステークス",
        distance=2406,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.ASCOT,
        direction=Direction.RIGHT,
        month=7,
        grade="G1",
        eligibility="3yo+",
        prize_money=210_000_000,
        country="United Kingdom"
    ),
    
    "royal_ascot_gold_cup": Race(
        id="royal_ascot_gold_cup",
        name="Royal Ascot Gold Cup",
        name_jp="アスコット・ゴールドカップ",
        distance=4000,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.ASCOT,
        direction=Direction.RIGHT,
        month=6,
        grade="G1",
        eligibility="3yo+",
        prize_money=200_000_000,
        country="United Kingdom"
    ),
    
    # ======================== UNITED STATES (ADDITIONAL) ========================
    "preakness_stakes": Race(
        id="preakness_stakes",
        name="Preakness Stakes",
        name_jp="プリークネスステークス",
        distance=1900,
        race_type=RaceType.MILE,
        surface=Surface.DIRT,
        racecourse=Racecourse.PIMLICO,  # Need to add Pimlico
        direction=Direction.LEFT,
        month=5,
        grade="G1",
        eligibility="3yo",
        prize_money=190_000_000,
        country="USA"
    ),
    
    "belmont_stakes": Race(
        id="belmont_stakes",
        name="Belmont Stakes",
        name_jp="ベルモントステークス",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.BELMONT,
        direction=Direction.LEFT,
        month=6,
        grade="G1",
        eligibility="3yo",
        prize_money=250_000_000,
        country="USA"
    ),
    
    "travers_stakes": Race(
        id="travers_stakes",
        name="Travers Stakes",
        name_jp="トラバースステークス",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.SARATOGA,  # Need to add Saratoga
        direction=Direction.LEFT,
        month=8,
        grade="G1",
        eligibility="3yo",
        prize_money=160_000_000,
        country="USA"
    ),
    
    "breeders_cup_classic": Race(
        id="breeders_cup_classic",
        name="Breeders' Cup Classic",
        name_jp="ブリーダーズカップクラシック",
        distance=2011,
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.KEENELAND,
        direction=Direction.LEFT,
        month=11,
        grade="G1",
        eligibility="3yo+",
        prize_money=980_000_000,
        country="USA"
    ),
    
    "breeders_cup_turf": Race(
        id="breeders_cup_turf",
        name="Breeders' Cup Turf",
        name_jp="ブリーダーズカップターフ",
        distance=2410,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.KEENELAND,
        direction=Direction.LEFT,
        month=11,
        grade="G1",
        eligibility="3yo+",
        prize_money=700_000_000,
        country="USA"
    ),
    
    "breeders_cup_mile": Race(
        id="breeders_cup_mile",
        name="Breeders' Cup Mile",
        name_jp="ブリーダーズカップマイル",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.KEENELAND,
        direction=Direction.LEFT,
        month=11,
        grade="G1",
        eligibility="3yo+",
        prize_money=280_000_000,
        country="USA"
    ),
    
    "breeders_cup_juvenile": Race(
        id="breeders_cup_juvenile",
        name="Breeders' Cup Juvenile",
        name_jp="ブリーダーズカップジュベナイル",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.DIRT,
        racecourse=Racecourse.KEENELAND,
        direction=Direction.LEFT,
        month=11,
        grade="G1",
        eligibility="2yo",
        prize_money=280_000_000,
        country="USA"
    ),
    
    "pegasus_world_cup": Race(
        id="pegasus_world_cup",
        name="Pegasus World Cup",
        name_jp="ペガサスワールドカップ",
        distance=1800,
        race_type=RaceType.MILE,
        surface=Surface.DIRT,
        racecourse=Racecourse.GULFSTREAM,
        direction=Direction.LEFT,
        month=1,
        grade="G1",
        eligibility="3yo+",
        prize_money=875_000_000,
        country="USA"
    ),
    
    "santa_anita_derby": Race(
        id="santa_anita_derby",
        name="Santa Anita Derby",
        name_jp="サンタアニタダービー",
        distance=1810,
        race_type=RaceType.MILE,
        surface=Surface.DIRT,
        racecourse=Racecourse.SANTA_ANITA,
        direction=Direction.LEFT,
        month=3,
        grade="G1",
        eligibility="3yo",
        prize_money=88_000_000,
        country="USA"
    ),
    
    # ======================== SPAIN ========================
    "gran_premio_cimera": Race(
        id="gran_premio_cimera",
        name="Gran Premio Cimera (Poule de Potros)",
        name_jp="グランプレミオシメラ",
        distance=1600,
        race_type=RaceType.MILE,
        surface=Surface.TURF,
        racecourse=Racecourse.ZARZUELA,  # Need to add Zarzuela
        direction=Direction.RIGHT,
        month=4,
        grade="G3",
        eligibility="3yo",
        prize_money=30_000_000,
        country="Spain"
    ),
    
    "gran_premio_villapediana": Race(
        id="gran_premio_villapediana",
        name="Gran Premio Villapediana (Spanish Derby)",
        name_jp="グランプレミオビヤペディアナ",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.ZARZUELA,
        direction=Direction.RIGHT,
        month=6,
        grade="G2",
        eligibility="3yo",
        prize_money=35_000_000,
        country="Spain"
    ),
    
    "copa_de_oro_san_sebastian": Race(
        id="copa_de_oro_san_sebastian",
        name="Copa de Oro de San Sebastián",
        name_jp="コパデオロ・デ・サンセバスチャン",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.SAN_SEBASTIAN,  # Need to add
        direction=Direction.RIGHT,
        month=8,
        grade="G2",
        eligibility="3yo+",
        prize_money=35_000_000,
        country="Spain"
    ),
    
    # ======================== AUSTRALIA (ADDITIONAL) ========================
    "sydney_cup": Race(
        id="sydney_cup",
        name="Sydney Cup",
        name_jp="シドニーカップ",
        distance=3200,
        race_type=RaceType.LONG,
        surface=Surface.TURF,
        racecourse=Racecourse.RANDWICK,
        direction=Direction.LEFT,
        month=2,
        grade="G1",
        eligibility="3yo+",
        prize_money=200_000_000,
        country="Australia"
    ),
    
    "caulfield_cup": Race(
        id="caulfield_cup",
        name="Caulfield Cup",
        name_jp="コーフィールドカップ",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.MOONEE_VALLEY,
        direction=Direction.LEFT,
        month=10,
        grade="G1",
        eligibility="3yo+",
        prize_money=245_000_000,
        country="Australia"
    ),
    
    # ======================== HONG KONG (ADDITIONAL) ========================
    "hong_kong_vase": Race(
        id="hong_kong_vase",
        name="Hong Kong Vase",
        name_jp="香港ヴェイズ",
        distance=2400,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.SHA_TIN,
        direction=Direction.RIGHT,
        month=12,
        grade="G1",
        eligibility="3yo+",
        prize_money=380_000_000,
        country="Hong Kong"
    ),
    
    "queen_elizabeth_ii_cup_hk": Race(
        id="queen_elizabeth_ii_cup_hk",
        name="Queen Elizabeth II Cup (HK)",
        name_jp="クイーンエリザベス2世カップ",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.TURF,
        racecourse=Racecourse.SHA_TIN,
        direction=Direction.RIGHT,
        month=4,
        grade="G1",
        eligibility="4yo+",
        prize_money=300_000_000,
        country="Hong Kong"
    ),
    
    # ======================== PHILIPPINES ========================
    "pcso_presidential_gold_cup": Race(
        id="pcso_presidential_gold_cup",
        name="PCSO Presidential Gold Cup",
        name_jp="PCSO大統領杯",
        distance=2000,
        race_type=RaceType.MEDIUM,
        surface=Surface.DIRT,
        racecourse=Racecourse.SANTA_ROSA,  # Need to add
        direction=Direction.LEFT,
        month=12,
        grade="G1",
        eligibility="3yo+",
        prize_money=100_000_000,
        country="Philippines"
    ),
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Combined dictionary of all races for easy lookup
ALL_RACES = {**G1_RACES, **G2_RACES, **G3_RACES, **INTERNATIONAL_RACES}


def get_race_by_id(race_id: str) -> Optional[Race]:
    """Get a race by its ID from any category"""
    return ALL_RACES.get(race_id)


def get_all_races() -> dict[str, Race]:
    """Get all races (G1, G2, G3, and International)"""
    return ALL_RACES.copy()


def get_all_g1_races() -> dict[str, Race]:
    """Get all G1 races only"""
    return G1_RACES.copy()


def get_all_g2_races() -> dict[str, Race]:
    """Get all G2 races only"""
    return G2_RACES.copy()


def get_all_g3_races() -> dict[str, Race]:
    """Get all G3 races only"""
    return G3_RACES.copy()


def get_all_international_races() -> dict[str, Race]:
    """Get all international races"""
    return INTERNATIONAL_RACES.copy()


def get_races_by_grade(grade: str) -> list[Race]:
    """Get all races of a specific grade"""
    return [race for race in ALL_RACES.values() if race.grade == grade]


def get_races_by_type(race_type: RaceType) -> list[Race]:
    """Get all races of a specific type"""
    return [race for race in ALL_RACES.values() if race.race_type == race_type]


def get_races_by_surface(surface: Surface) -> list[Race]:
    """Get all races on a specific surface"""
    return [race for race in ALL_RACES.values() if race.surface == surface]


def get_races_by_racecourse(racecourse: Racecourse) -> list[Race]:
    """Get all races at a specific racecourse"""
    return [race for race in ALL_RACES.values() if race.racecourse == racecourse]


def get_races_by_month(month: int) -> list[Race]:
    """Get all races held in a specific month"""
    return [race for race in ALL_RACES.values() if race.month == month]


def get_races_by_country(country: str) -> list[Race]:
    """Get all races held in a specific country"""
    return [race for race in ALL_RACES.values() if race.country == country]


def get_race_list_for_dropdown(grade_filter: Optional[str] = None) -> list[tuple[str, str]]:
    """Get list of (race_id, display_name) tuples for dropdown menus"""
    races = ALL_RACES.values()
    if grade_filter:
        races = [r for r in races if r.grade == grade_filter]
    # Sort by grade, then month, then name
    sorted_races = sorted(races, key=lambda r: (r.grade, r.month, r.name))
    return [(race.id, f"[{race.grade}] {race.name} ({race.distance}m {race.surface.value})") for race in sorted_races]


def get_races_grouped_by_month() -> dict[int, list[Race]]:
    """Get races grouped by month"""
    grouped = {}
    for race in ALL_RACES.values():
        if race.month not in grouped:
            grouped[race.month] = []
        grouped[race.month].append(race)
    
    # Sort races within each month
    for month in grouped:
        grouped[month].sort(key=lambda r: (r.grade, r.name))
    
    return grouped


def get_races_grouped_by_grade() -> dict[str, list[Race]]:
    """Get races grouped by grade"""
    grouped = {}
    for race in ALL_RACES.values():
        if race.grade not in grouped:
            grouped[race.grade] = []
        grouped[race.grade].append(race)
    
    # Sort races within each grade
    for grade in grouped:
        grouped[grade].sort(key=lambda r: r.name)
    
    return grouped


def get_race_categories() -> dict[str, list[str]]:
    """Get races grouped by category for UI display"""
    categories = {
        "Sprint (1000-1400m)": [],
        "Mile (1401-1800m)": [],
        "Medium (1801-2400m)": [],
        "Long (2401m+)": [],
    }
    
    for race_id, race in ALL_RACES.items():
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
    """Print statistics about all races database"""
    print(f"{'='*60}")
    print(f"UMA MUSUME RACES DATABASE STATISTICS")
    print(f"{'='*60}")
    
    print(f"\nTotal Races: {len(ALL_RACES)}")
    print(f"  - G1 Races: {len(G1_RACES)}")
    print(f"  - G2 Races: {len(G2_RACES)}")
    print(f"  - G3 Races: {len(G3_RACES)}")
    print(f"  - International Races: {len(INTERNATIONAL_RACES)}")
    
    by_type = {}
    by_surface = {}
    by_country = {}
    
    for race in ALL_RACES.values():
        by_type[race.race_type.value] = by_type.get(race.race_type.value, 0) + 1
        by_surface[race.surface.value] = by_surface.get(race.surface.value, 0) + 1
        by_country[race.country] = by_country.get(race.country, 0) + 1
    
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
    # Print statistics when run directly
    print_race_statistics()
    
    print("\nAll Races by Grade and Month:")
    print("-" * 60)
    grouped = get_races_grouped_by_month()
    month_names = ["", "January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    
    for month in sorted(grouped.keys()):
        print(f"\n{month_names[month]}:")
        for race in grouped[month]:
            season = get_race_season(race)
            print(f"  - [{race.grade}] {race.name}: {race.distance}m {race.surface.value} @ {race.racecourse.value}")
