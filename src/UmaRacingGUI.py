import json
import math
import random
from datetime import datetime
from pathlib import Path

from race_engine import (
    RaceEngine, RacePhase, RunningStyle, UmaStats, UmaState,
    create_race_engine_from_config, PHASE_CONFIGS, STYLE_CONFIGS
)


# =============================================================================
# HORSE RACING MARGIN CONVERSION
# =============================================================================
# In horse racing, gaps between horses are measured in traditional units:
# - Nose: ~0.05 lengths (very close photo finish)
# - Short Head: ~0.1 lengths
# - Head: ~0.2 lengths  
# - Neck: ~0.3 lengths
# - Half a length: 0.5 lengths
# - 3/4 length: 0.75 lengths
# - 1 length, 1.5 lengths, 2 lengths, etc.
# - Distance: 20+ lengths (very far behind)
#
# One horse "length" ≈ 2.4 meters (average horse body length)
# At racing speeds (~17 m/s), 1 length ≈ 0.14 seconds
# =============================================================================

HORSE_LENGTH_METERS = 2.4  # Average horse body length in meters

def time_gap_to_margin(time_gap: float, avg_speed: float = 17.0) -> str:
    """
    Convert a time gap between horses to traditional racing margin notation.
    
    Args:
        time_gap: Time difference in seconds
        avg_speed: Average race speed in m/s (default ~17 m/s for turf)
    
    Returns:
        Human-readable margin string (e.g., "1 1/4", "Neck", "Nose")
    """
    if time_gap <= 0:
        return "-"  # Winner or same time
    
    # Convert time to distance, then to lengths
    distance_meters = time_gap * avg_speed
    lengths = distance_meters / HORSE_LENGTH_METERS
    
    # Traditional margin notation
    if lengths < 0.05:
        return "Dead Heat"
    elif lengths < 0.1:
        return "Nose"
    elif lengths < 0.15:
        return "Short Head"
    elif lengths < 0.25:
        return "Head"
    elif lengths < 0.4:
        return "Neck"
    elif lengths < 0.6:
        return "1/2"
    elif lengths < 0.85:
        return "3/4"
    elif lengths < 1.15:
        return "1"
    elif lengths < 1.4:
        return "1 1/4"
    elif lengths < 1.6:
        return "1 1/2"
    elif lengths < 1.85:
        return "1 3/4"
    elif lengths < 2.15:
        return "2"
    elif lengths < 2.6:
        return "2 1/2"
    elif lengths < 3.15:
        return "3"
    elif lengths < 3.6:
        return "3 1/2"
    elif lengths < 4.15:
        return "4"
    elif lengths < 4.6:
        return "4 1/2"
    elif lengths < 5.15:
        return "5"
    elif lengths < 6.0:
        return "5+"
    elif lengths < 7.0:
        return "6"
    elif lengths < 8.0:
        return "7"
    elif lengths < 9.0:
        return "8"
    elif lengths < 10.0:
        return "9"
    elif lengths < 15.0:
        return f"{int(lengths)}"
    elif lengths < 20.0:
        return "Large"  # ~15-20 lengths, large gap
    else:
        return "Distance"  # 20+ lengths, essentially out of contention


from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLabel, QFileDialog, QTextEdit, QSplitter,
    QFrame, QMessageBox, QListWidget, QListWidgetItem, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QSize, QPoint, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush, QPainterPath


# ============================================================================
# RACECOURSE TRACK LAYOUTS
# Each layout defines the track shape using normalized control points
# Direction: "Right" = clockwise, "Left" = counter-clockwise  
# All tracks are ovals, but differ in aspect ratio and corner tightness
# Based on GameTora data: All JRA tracks have 4 corners, differ in straight length
# ============================================================================

# G1 RACE COURSE CONFIGURATIONS (from GameTora)
# Format: "racecourse_distance_surface_variant": { corners, straights, etc }
# Positions are in meters, will be normalized to progress (0-1)
G1_COURSE_DATA = {
    # Arima Kinen - Nakayama 2500m Turf Inner (Right-handed)
    "Nakayama_2500_Turf_Inner": {
        "corners": [
            {"name": "C1", "start": 350, "end": 540},
            {"name": "C2", "start": 540, "end": 730},
            {"name": "C3", "start": 1580, "end": 1880},
            {"name": "C4", "start": 1880, "end": 2180},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 350},      # Home straight (start)
            {"name": "S2", "start": 730, "end": 1580},   # Backstretch
            {"name": "S3", "start": 2180, "end": 2500},  # Home straight (finish)
        ],
        "spurt_start": 1667,
    },
    # Japan Cup - Tokyo 2400m Turf (Left-handed)
    "Tokyo_2400_Turf": {
        "corners": [
            {"name": "C1", "start": 350, "end": 550},
            {"name": "C2", "start": 550, "end": 750},
            {"name": "C3", "start": 1300, "end": 1650},
            {"name": "C4", "start": 1650, "end": 2000},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 350},
            {"name": "S2", "start": 750, "end": 1300},
            {"name": "S3", "start": 2000, "end": 2400},  # Famous long home straight
        ],
        "spurt_start": 1600,
    },
    # Tokyo Yushun (Derby) - Tokyo 2400m Turf (same as Japan Cup)
    "Tokyo_2400_Turf_Derby": {
        "corners": [
            {"name": "C1", "start": 350, "end": 550},
            {"name": "C2", "start": 550, "end": 750},
            {"name": "C3", "start": 1300, "end": 1650},
            {"name": "C4", "start": 1650, "end": 2000},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 350},
            {"name": "S2", "start": 750, "end": 1300},
            {"name": "S3", "start": 2000, "end": 2400},
        ],
        "spurt_start": 1600,
    },
    # Tenno Sho Spring - Kyoto 3200m Turf Outer (Right-handed)
    "Kyoto_3200_Turf_Outer": {
        "corners": [
            {"name": "C3", "start": 370, "end": 720},
            {"name": "C4", "start": 720, "end": 1070},
            {"name": "C1", "start": 1520, "end": 1710},
            {"name": "C2", "start": 1710, "end": 1900},
            {"name": "C3b", "start": 2250, "end": 2550},
            {"name": "C4b", "start": 2550, "end": 2850},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 370},
            {"name": "S2", "start": 1070, "end": 1520},
            {"name": "S3", "start": 1900, "end": 2250},
            {"name": "S4", "start": 2850, "end": 3200},
        ],
        "spurt_start": 2133,
    },
    # Tenno Sho Autumn - Tokyo 2000m Turf (Left-handed)
    "Tokyo_2000_Turf": {
        "corners": [
            {"name": "C1", "start": 150, "end": 350},
            {"name": "C2", "start": 350, "end": 550},
            {"name": "C3", "start": 1100, "end": 1400},
            {"name": "C4", "start": 1400, "end": 1700},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 150},
            {"name": "S2", "start": 550, "end": 1100},
            {"name": "S3", "start": 1700, "end": 2000},
        ],
        "spurt_start": 1333,
    },
    # Takarazuka Kinen - Hanshin 2200m Turf Inner (Right-handed)
    "Hanshin_2200_Turf_Inner": {
        "corners": [
            {"name": "C1", "start": 520, "end": 710},
            {"name": "C2", "start": 710, "end": 900},
            {"name": "C3", "start": 1250, "end": 1550},
            {"name": "C4", "start": 1550, "end": 1850},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 520},
            {"name": "S2", "start": 900, "end": 1250},
            {"name": "S3", "start": 1850, "end": 2200},
        ],
        "spurt_start": 1467,
    },
    # Osaka Hai - Hanshin 2000m Turf Inner (Right-handed)
    "Hanshin_2000_Turf_Inner": {
        "corners": [
            {"name": "C1", "start": 370, "end": 560},
            {"name": "C2", "start": 560, "end": 750},
            {"name": "C3", "start": 1050, "end": 1350},
            {"name": "C4", "start": 1350, "end": 1650},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 370},
            {"name": "S2", "start": 750, "end": 1050},
            {"name": "S3", "start": 1650, "end": 2000},
        ],
        "spurt_start": 1333,
    },
    # Oka Sho - Hanshin 1600m Turf Outer (Right-handed)
    "Hanshin_1600_Turf_Outer": {
        "corners": [
            {"name": "C3", "start": 450, "end": 800},
            {"name": "C4", "start": 800, "end": 1150},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 450},
            {"name": "S2", "start": 1150, "end": 1600},
        ],
        "spurt_start": 1067,
    },
    # Satsuki Sho - Nakayama 2000m Turf Inner (Right-handed)
    "Nakayama_2000_Turf_Inner": {
        "corners": [
            {"name": "C1", "start": 130, "end": 320},
            {"name": "C2", "start": 320, "end": 510},
            {"name": "C3", "start": 1060, "end": 1360},
            {"name": "C4", "start": 1360, "end": 1660},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 130},
            {"name": "S2", "start": 510, "end": 1060},
            {"name": "S3", "start": 1660, "end": 2000},
        ],
        "spurt_start": 1333,
    },
    # Kikuka Sho - Kyoto 3000m Turf Outer (Right-handed)
    "Kyoto_3000_Turf_Outer": {
        "corners": [
            {"name": "C3", "start": 170, "end": 520},
            {"name": "C4", "start": 520, "end": 870},
            {"name": "C1", "start": 1320, "end": 1510},
            {"name": "C2", "start": 1510, "end": 1700},
            {"name": "C3b", "start": 2050, "end": 2350},
            {"name": "C4b", "start": 2350, "end": 2650},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 170},
            {"name": "S2", "start": 870, "end": 1320},
            {"name": "S3", "start": 1700, "end": 2050},
            {"name": "S4", "start": 2650, "end": 3000},
        ],
        "spurt_start": 2000,
    },
    # Shuka Sho - Kyoto 2000m Turf Inner (Right-handed)
    "Kyoto_2000_Turf_Inner": {
        "corners": [
            {"name": "C3", "start": 350, "end": 550},
            {"name": "C4", "start": 550, "end": 750},
            {"name": "C1", "start": 1100, "end": 1350},
            {"name": "C2", "start": 1350, "end": 1600},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 350},
            {"name": "S2", "start": 750, "end": 1100},
            {"name": "S3", "start": 1600, "end": 2000},
        ],
        "spurt_start": 1333,
    },
    # Queen Elizabeth II Cup - Kyoto 2200m Turf Outer (Right-handed)
    "Kyoto_2200_Turf_Outer": {
        "corners": [
            {"name": "C3", "start": 350, "end": 600},
            {"name": "C4", "start": 600, "end": 850},
            {"name": "C1", "start": 1200, "end": 1450},
            {"name": "C2", "start": 1450, "end": 1700},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 350},
            {"name": "S2", "start": 850, "end": 1200},
            {"name": "S3", "start": 1700, "end": 2200},
        ],
        "spurt_start": 1467,
    },
    # Mile Championship - Kyoto 1600m Turf Outer (Right-handed)
    "Kyoto_1600_Turf_Outer": {
        "corners": [
            {"name": "C3", "start": 350, "end": 600},
            {"name": "C4", "start": 600, "end": 850},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 350},
            {"name": "S2", "start": 850, "end": 1600},
        ],
        "spurt_start": 1067,
    },
    # Sprinters Stakes - Nakayama 1200m Turf Outer (Right-handed)
    "Nakayama_1200_Turf_Outer": {
        "corners": [
            {"name": "C3", "start": 300, "end": 550},
            {"name": "C4", "start": 550, "end": 800},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 300},
            {"name": "S2", "start": 800, "end": 1200},
        ],
        "spurt_start": 800,
    },
    # NHK Mile Cup / Yasuda Kinen / Victoria Mile - Tokyo 1600m Turf (Left-handed)
    "Tokyo_1600_Turf": {
        "corners": [
            {"name": "C3", "start": 300, "end": 550},
            {"name": "C4", "start": 550, "end": 800},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 300},
            {"name": "S2", "start": 800, "end": 1600},  # Very long final straight
        ],
        "spurt_start": 1067,
    },
    # February Stakes - Tokyo 1600m Dirt (Left-handed)
    "Tokyo_1600_Dirt": {
        "corners": [
            {"name": "C3", "start": 350, "end": 600},
            {"name": "C4", "start": 600, "end": 850},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 350},
            {"name": "S2", "start": 850, "end": 1600},
        ],
        "spurt_start": 1067,
    },
    # Takamatsunomiya Kinen - Chukyo 1200m Turf (Left-handed)
    "Chukyo_1200_Turf": {
        "corners": [
            {"name": "C3", "start": 250, "end": 500},
            {"name": "C4", "start": 500, "end": 750},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 250},
            {"name": "S2", "start": 750, "end": 1200},
        ],
        "spurt_start": 800,
    },
    # Champions Cup - Chukyo 1800m Dirt (Left-handed)
    "Chukyo_1800_Dirt": {
        "corners": [
            {"name": "C1", "start": 230, "end": 430},
            {"name": "C2", "start": 430, "end": 630},
            {"name": "C3", "start": 880, "end": 1130},
            {"name": "C4", "start": 1130, "end": 1380},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 230},
            {"name": "S2", "start": 630, "end": 880},
            {"name": "S3", "start": 1380, "end": 1800},
        ],
        "spurt_start": 1200,
    },
    # Hopeful Stakes - Nakayama 2000m Turf Inner (same as Satsuki Sho)
    "Nakayama_2000_Turf_Inner_Hopeful": {
        "corners": [
            {"name": "C1", "start": 130, "end": 320},
            {"name": "C2", "start": 320, "end": 510},
            {"name": "C3", "start": 1060, "end": 1360},
            {"name": "C4", "start": 1360, "end": 1660},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 130},
            {"name": "S2", "start": 510, "end": 1060},
            {"name": "S3", "start": 1660, "end": 2000},
        ],
        "spurt_start": 1333,
    },
    # Hanshin JF / Asahi Hai Futurity - Hanshin 1600m Turf Outer
    "Hanshin_1600_Turf_Outer_JF": {
        "corners": [
            {"name": "C3", "start": 450, "end": 800},
            {"name": "C4", "start": 800, "end": 1150},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 450},
            {"name": "S2", "start": 1150, "end": 1600},
        ],
        "spurt_start": 1067,
    },
    # Yushun Himba (Oaks) - Tokyo 2400m Turf (same as Japan Cup)
    "Tokyo_2400_Turf_Oaks": {
        "corners": [
            {"name": "C1", "start": 350, "end": 550},
            {"name": "C2", "start": 550, "end": 750},
            {"name": "C3", "start": 1300, "end": 1650},
            {"name": "C4", "start": 1650, "end": 2000},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 350},
            {"name": "S2", "start": 750, "end": 1300},
            {"name": "S3", "start": 2000, "end": 2400},
        ],
        "spurt_start": 1600,
    },
    # Tokyo Daishoten - Ohi 2000m Dirt (Right-handed)
    "Ohi_2000_Dirt": {
        "corners": [
            {"name": "C1", "start": 300, "end": 500},
            {"name": "C2", "start": 500, "end": 700},
            {"name": "C3", "start": 1100, "end": 1350},
            {"name": "C4", "start": 1350, "end": 1600},
        ],
        "straights": [
            {"name": "S1", "start": 0, "end": 300},
            {"name": "S2", "start": 700, "end": 1100},
            {"name": "S3", "start": 1600, "end": 2000},
        ],
        "spurt_start": 1333,
    },
}

# Map race configurations to course data keys
RACE_TO_COURSE_KEY = {
    "arima_kinen": "Nakayama_2500_Turf_Inner",
    "japan_cup": "Tokyo_2400_Turf",
    "tokyo_yushun": "Tokyo_2400_Turf_Derby",
    "tenno_sho_spring": "Kyoto_3200_Turf_Outer",
    "tenno_sho_autumn": "Tokyo_2000_Turf",
    "takarazuka_kinen": "Hanshin_2200_Turf_Inner",
    "osaka_hai": "Hanshin_2000_Turf_Inner",
    "oka_sho": "Hanshin_1600_Turf_Outer",
    "satsuki_sho": "Nakayama_2000_Turf_Inner",
    "kikuka_sho": "Kyoto_3000_Turf_Outer",
    "shuka_sho": "Kyoto_2000_Turf_Inner",
    "queen_elizabeth_ii_cup": "Kyoto_2200_Turf_Outer",
    "mile_championship": "Kyoto_1600_Turf_Outer",
    "sprinters_stakes": "Nakayama_1200_Turf_Outer",
    "nhk_mile_cup": "Tokyo_1600_Turf",
    "yasuda_kinen": "Tokyo_1600_Turf",
    "victoria_mile": "Tokyo_1600_Turf",
    "yushun_himba": "Tokyo_2400_Turf_Oaks",
    "february_stakes": "Tokyo_1600_Dirt",
    "takamatsunomiya_kinen": "Chukyo_1200_Turf",
    "champions_cup": "Chukyo_1800_Dirt",
    "hopeful_stakes": "Nakayama_2000_Turf_Inner_Hopeful",
    "hanshin_juvenile_fillies": "Hanshin_1600_Turf_Outer_JF",
    "asahi_hai_futurity_stakes": "Hanshin_1600_Turf_Outer_JF",
    "tokyo_daishoten": "Ohi_2000_Dirt",
}

RACECOURSE_LAYOUTS = {
    # Tokyo - Left-handed, LARGE oval, very long home straight (525m), 2083m turf
    # Famous for: Wide sweeping turns, long straights
    "Tokyo": {
        "direction": "Left",
        "width_ratio": 2.2,      # Very elongated (long straights)
        "corner_tightness": 0.9, # Gentle wide corners
    },
    
    # Nakayama - Right-handed, 1840m outer, tight turn 4
    # Famous for: Notoriously tight final turn, undulating terrain
    # Corners are sharper compared to Tokyo
    "Nakayama": {
        "direction": "Right",
        "width_ratio": 1.5,      # More compact than Tokyo
        "corner_tightness": 0.7, # Tighter corners, especially turn 4
    },
    
    # Hanshin - Right-handed, dual course (outer 2089m), relatively flat
    # Famous for: A/B courses, renovated in 2006
    "Hanshin": {
        "direction": "Right",
        "width_ratio": 1.8,
        "corner_tightness": 0.85,
    },
    
    # Kyoto - Right-handed, dual course (outer 1894m), famous hill on backstretch
    # Famous for: 3-4 corner hill (淀の坂), downhill finish
    "Kyoto": {
        "direction": "Right",
        "width_ratio": 1.7,
        "corner_tightness": 0.8,
    },
    
    # Chukyo - Left-handed, medium size (1705m), slightly undulating
    "Chukyo": {
        "direction": "Left",
        "width_ratio": 1.5,
        "corner_tightness": 0.75,
    },
    
    # Sapporo - Right-handed, small (1641m), 洋芝 (Western grass)
    # Corners 1-4 fairly evenly spaced
    "Sapporo": {
        "direction": "Right",
        "width_ratio": 1.3,
        "corner_tightness": 0.7,
    },
    
    # Hakodate - Right-handed, smallest JRA track (1477m), very tight
    "Hakodate": {
        "direction": "Right",
        "width_ratio": 1.2,
        "corner_tightness": 0.6,   # Tightest corners
    },
    
    # Fukushima - Right-handed, small (1600m), spiral course
    "Fukushima": {
        "direction": "Right",
        "width_ratio": 1.35,
        "corner_tightness": 0.65,
    },
    
    # Niigata - Left-handed, HUGE (2223m), famous 1000m straight course
    # Famous for: Longest straight course in Japan, very few corners
    # GameTora shows only Corner 3 & 4 for most races - extremely long straights
    "Niigata": {
        "direction": "Left",
        "width_ratio": 2.5,       # Extremely elongated
        "corner_tightness": 0.95, # Very gentle corners
    },
    
    # Kokura - Right-handed, small (1615m), flat, summer venue
    "Kokura": {
        "direction": "Right",
        "width_ratio": 1.4,
        "corner_tightness": 0.7,
    },
    
    # Ohi - Right-handed, NAR dirt track (1400m), tight turns
    "Ohi": {
        "direction": "Right",
        "width_ratio": 1.25,
        "corner_tightness": 0.55,  # Very tight (dirt track)
    },
}

# Default layout for unknown racecourses
DEFAULT_LAYOUT = {
    "direction": "Right",
    "width_ratio": 1.6,
    "corner_tightness": 0.75,
}


class RaceCanvasWidget(QWidget):
    """Custom widget for rendering race track and umas with curved racecourse layouts"""
    
    def __init__(self):
        super().__init__()
        self.sim_data = None
        self.uma_distances = {}
        self.track_margin = 5  # Minimal margin for maximum track size
        self.uma_finished = {}
        self.uma_dnf = {}
        self.uma_incidents = {}
        self.uma_colors = {}
        self.gate_numbers = {}
        # Mechanic state indicators
        self.duel_participants = set()      # Red - dueling
        self.rushing_participants = set()   # Orange - rushing
        self.temptation_participants = set()  # Yellow-Orange - temptation (かかり)
        self.spot_struggle_participants = set()  # Magenta - spot struggle
        self.skill_active_participants = set()  # Cyan glow - skill active
        
        # Track layout data
        self.racecourse = None
        self.direction = "Right"
        self.track_path = None
        self.track_points = []  # List of (x, y, progress) points along the track
        self.path_length = 0
        
    def set_racecourse(self, racecourse_name, direction=None):
        """Set the racecourse layout to use"""
        self.racecourse = racecourse_name
        if direction:
            self.direction = direction
        elif racecourse_name in RACECOURSE_LAYOUTS:
            self.direction = RACECOURSE_LAYOUTS[racecourse_name]["direction"]
        self.track_path = None  # Force regeneration
        self.track_points = []
        
    def generate_track_path(self, width, height):
        """Generate the track path based on racecourse layout"""
        layout = RACECOURSE_LAYOUTS.get(self.racecourse, DEFAULT_LAYOUT)
        
        # Track dimensions with minimal padding
        padding = self.track_margin
        track_width = width - 2 * padding
        track_height = height - 2 * padding
        
        # Center of the track area
        cx = width / 2
        cy = height / 2
        
        # Get layout parameters
        width_ratio = layout.get("width_ratio", 1.6)
        corner_tightness = layout.get("corner_tightness", 0.75)
        direction = layout.get("direction", "Right")
        
        # Calculate the maximum track size that fits while maintaining aspect ratio
        # The track's width/height ratio must match width_ratio
        canvas_ratio = track_width / track_height
        
        if canvas_ratio > width_ratio:
            # Canvas is wider than track aspect ratio - height is the constraint
            # Use full height, calculate width
            oval_height = track_height
            oval_width = oval_height * width_ratio
        else:
            # Canvas is taller than track aspect ratio - width is the constraint
            # Use full width, calculate height
            oval_width = track_width
            oval_height = oval_width / width_ratio
        
        # Debug output
        print(f"Canvas: {width}x{height}, Track area: {track_width}x{track_height}")
        print(f"width_ratio: {width_ratio}, canvas_ratio: {canvas_ratio:.2f}")
        print(f"Final oval: {oval_width:.0f}x{oval_height:.0f}")
        
        # Direction multiplier: 1 for Right (clockwise), -1 for Left (counter-clockwise)
        dir_mult = 1 if direction == "Right" else -1
        
        # Generate path points - use unified rounded rectangle approach
        path = QPainterPath()
        self.track_points = []
        
        num_points = 360  # One point per degree
        
        # Generate the track using a rounded rectangle (stadium) shape
        # All JRA tracks are basically ovals - they differ in aspect ratio and corner radius
        self._generate_rounded_track(cx, cy, oval_width, oval_height, corner_tightness, dir_mult, num_points)
        
        # Build the QPainterPath from track points
        for i, (x, y, t) in enumerate(self.track_points):
            if i == 0:
                path.moveTo(x, y)
            else:
                path.lineTo(x, y)
        
        path.closeSubpath()
        self.track_path = path
        
        # Calculate path length
        self.path_length = sum(
            math.sqrt((self.track_points[i][0] - self.track_points[i-1][0])**2 + 
                     (self.track_points[i][1] - self.track_points[i-1][1])**2)
            for i in range(1, len(self.track_points))
        )
        
        return path
    
    def _generate_rounded_track(self, cx, cy, width, height, corner_tightness, dir_mult, num_points):
        """Generate a rounded rectangle track (stadium shape)
        
        This creates a track with:
        - Two straight sections (top and bottom)  
        - Two curved ends (left and right semicircles)
        
        corner_tightness controls the corner radius relative to track height:
        - 1.0 = semicircle radius equals half height (pure stadium)
        - Lower values = smaller corner radius, more rectangular appearance
        
        The track starts at the finish line (top-center for Right-handed)
        and goes clockwise (Right) or counter-clockwise (Left)
        """
        half_w = width / 2
        half_h = height / 2
        
        # Corner radius is based on track height and tightness
        # For a proper stadium, corners should be semicircles with radius = half_h
        corner_radius = half_h * corner_tightness
        
        # Straight section length = total width minus the two corner diameters
        straight_length = max(0, width - 2 * corner_radius)
        
        # Centers of the semicircular ends
        left_center_x = cx - straight_length / 2
        right_center_x = cx + straight_length / 2
        
        # IMPORTANT: The Y position of straights must match the corner radius!
        # Otherwise there's a gap between straights and curves
        top_y = cy - corner_radius
        bottom_y = cy + corner_radius
        
        for i in range(num_points):
            t = i / num_points  # Progress 0 to 1 around the track
            
            if dir_mult > 0:  # Right-handed (clockwise)
                if t < 0.25:
                    # TOP STRAIGHT: going right (toward turn 1-2)
                    local_t = t / 0.25
                    x = left_center_x + local_t * straight_length
                    y = top_y
                elif t < 0.5:
                    # RIGHT CURVE (Turn 1-2): semicircle on right side
                    local_t = (t - 0.25) / 0.25
                    angle = -math.pi/2 + local_t * math.pi  # -90° to +90°
                    x = right_center_x + corner_radius * math.cos(angle)
                    y = cy + corner_radius * math.sin(angle)
                elif t < 0.75:
                    # BOTTOM STRAIGHT: going left (backstretch)
                    local_t = (t - 0.5) / 0.25
                    x = right_center_x - local_t * straight_length
                    y = bottom_y
                else:
                    # LEFT CURVE (Turn 3-4): semicircle on left side
                    local_t = (t - 0.75) / 0.25
                    angle = math.pi/2 + local_t * math.pi  # +90° to +270°
                    x = left_center_x + corner_radius * math.cos(angle)
                    y = cy + corner_radius * math.sin(angle)
            else:  # Left-handed (counter-clockwise)
                if t < 0.25:
                    # TOP STRAIGHT: going left (toward turn 1-2)
                    local_t = t / 0.25
                    x = right_center_x - local_t * straight_length
                    y = top_y
                elif t < 0.5:
                    # LEFT CURVE (Turn 1-2): semicircle on left side
                    local_t = (t - 0.25) / 0.25
                    angle = -math.pi/2 - local_t * math.pi  # -90° to -270°
                    x = left_center_x + corner_radius * math.cos(angle)
                    y = cy + corner_radius * math.sin(angle)
                elif t < 0.75:
                    # BOTTOM STRAIGHT: going right (backstretch)
                    local_t = (t - 0.5) / 0.25
                    x = left_center_x + local_t * straight_length
                    y = bottom_y
                else:
                    # RIGHT CURVE (Turn 3-4): semicircle on right side
                    local_t = (t - 0.75) / 0.25
                    angle = math.pi/2 - local_t * math.pi  # +90° to -90°
                    x = right_center_x + corner_radius * math.cos(angle)
                    y = cy + corner_radius * math.sin(angle)
            
            self.track_points.append((x, y, t))
    
    def get_position_on_track(self, progress):
        """Get (x, y) position on track for a given progress (0 to 1)"""
        if not self.track_points:
            return (self.track_margin, self.height() / 2)
        
        # Clamp progress
        progress = max(0, min(1, progress))
        
        # Find the two points to interpolate between
        idx = int(progress * (len(self.track_points) - 1))
        idx = min(idx, len(self.track_points) - 2)
        
        t = progress * (len(self.track_points) - 1) - idx
        
        p1 = self.track_points[idx]
        p2 = self.track_points[idx + 1]
        
        x = p1[0] + (p2[0] - p1[0]) * t
        y = p1[1] + (p2[1] - p1[1]) * t
        
        return (x, y)
    
    def get_track_direction_at(self, progress):
        """Get the direction angle (in radians) at a given progress point"""
        if not self.track_points or len(self.track_points) < 2:
            return 0
        
        idx = int(progress * (len(self.track_points) - 1))
        idx = min(idx, len(self.track_points) - 2)
        
        p1 = self.track_points[idx]
        p2 = self.track_points[idx + 1]
        
        return math.atan2(p2[1] - p1[1], p2[0] - p1[0])
    
    def get_course_data(self):
        """Get course segment data for current race"""
        if not self.sim_data:
            return None
        
        # Try race_id first
        race_id = self.sim_data.get('race_id', '')
        course_key = RACE_TO_COURSE_KEY.get(race_id)
        
        if course_key and course_key in G1_COURSE_DATA:
            return G1_COURSE_DATA.get(course_key)
        
        # Fallback: try to construct course key from racecourse, distance, surface
        racecourse = self.sim_data.get('racecourse', '')
        race_distance = self.sim_data.get('race_distance', 0)
        surface = self.sim_data.get('race_surface', 'Turf')
        
        if racecourse and race_distance:
            # Try various key formats
            possible_keys = [
                f"{racecourse}_{race_distance}_{surface}",
                f"{racecourse}_{race_distance}_{surface}_Inner",
                f"{racecourse}_{race_distance}_{surface}_Outer",
            ]
            
            for key in possible_keys:
                if key in G1_COURSE_DATA:
                    return G1_COURSE_DATA.get(key)
        
        return None
    
    def draw_corner_markers(self, painter, race_distance):
        """Draw corner position markers on the track"""
        course_data = self.get_course_data()
        if not course_data or not self.track_points:
            return
        
        w = self.width()
        h = self.height()
        cx, cy = w / 2, h / 2
        
        # Draw corners as colored arcs/zones on track outer edge
        corners = course_data.get('corners', [])
        for corner in corners:
            start_progress = corner['start'] / race_distance
            end_progress = corner['end'] / race_distance
            
            # Draw corner zone highlight
            start_idx = int(start_progress * (len(self.track_points) - 1))
            end_idx = int(end_progress * (len(self.track_points) - 1))
            start_idx = max(0, min(start_idx, len(self.track_points) - 1))
            end_idx = max(0, min(end_idx, len(self.track_points) - 1))
            
            # Create path for corner zone (line only, no fill)
            corner_path = QPainterPath()
            first_point = True
            for i in range(start_idx, end_idx + 1):
                x, y, _ = self.track_points[i]
                # Scale slightly outward to show on track edge
                ox = cx + (x - cx) * 1.05
                oy = cy + (y - cy) * 1.05
                if first_point:
                    corner_path.moveTo(ox, oy)
                    first_point = False
                else:
                    corner_path.lineTo(ox, oy)
            
            # Draw corner highlight (stroke only, no fill)
            pen = QPen(QColor('#FF6B35'), 4)  # Orange for corners
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)  # No fill!
            painter.drawPath(corner_path)
            
            # Draw corner label at midpoint
            mid_progress = (start_progress + end_progress) / 2
            mid_x, mid_y = self.get_position_on_track(mid_progress)
            # Offset label toward inside
            label_x = cx + (mid_x - cx) * 0.65
            label_y = cy + (mid_y - cy) * 0.65
            
            font = QFont("Arial", 10)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(QColor('#FF6B35')))
            painter.drawText(int(label_x - 8), int(label_y + 4), corner['name'])
    
    def draw_spurt_marker(self, painter, race_distance):
        """Draw the spurt start marker"""
        course_data = self.get_course_data()
        if not course_data or not self.track_points:
            return
        
        spurt_start = course_data.get('spurt_start')
        if not spurt_start:
            return
        
        spurt_progress = spurt_start / race_distance
        spurt_x, spurt_y = self.get_position_on_track(spurt_progress)
        track_angle = self.get_track_direction_at(spurt_progress)
        
        # Draw spurt marker (perpendicular line across track)
        perp_angle = track_angle + math.pi / 2
        line_length = 25
        
        pen = QPen(QColor('#00FFFF'), 3)  # Cyan for spurt
        painter.setPen(pen)
        painter.drawLine(
            int(spurt_x - line_length * math.cos(perp_angle)),
            int(spurt_y - line_length * math.sin(perp_angle)),
            int(spurt_x + line_length * math.cos(perp_angle)),
            int(spurt_y + line_length * math.sin(perp_angle))
        )
        
        # Label
        font = QFont("Arial", 8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QPen(QColor('#00FFFF')))
        label_x = spurt_x + 30 * math.cos(perp_angle)
        label_y = spurt_y + 30 * math.sin(perp_angle)
        painter.drawText(int(label_x - 20), int(label_y + 4), "SPURT")
    
    def draw_distance_markers(self, painter, race_distance):
        """Draw distance markers every 500m"""
        if not self.track_points:
            return
        
        # Draw markers every 500m
        marker_interval = 500
        for distance in range(marker_interval, int(race_distance), marker_interval):
            progress = distance / race_distance
            x, y = self.get_position_on_track(progress)
            track_angle = self.get_track_direction_at(progress)
            
            # Draw small tick mark perpendicular to track
            perp_angle = track_angle + math.pi / 2
            tick_length = 10
            
            pen = QPen(QColor('#AAAAAA'), 2)
            painter.setPen(pen)
            painter.drawLine(
                int(x - tick_length * math.cos(perp_angle)),
                int(y - tick_length * math.sin(perp_angle)),
                int(x + tick_length * math.cos(perp_angle)),
                int(y + tick_length * math.sin(perp_angle))
            )
            
            # Distance label (positioned inside track)
            font = QFont("Arial", 7)
            painter.setFont(font)
            painter.setPen(QPen(QColor('#CCCCCC')))
            label_x = x + 18 * math.cos(perp_angle)
            label_y = y + 18 * math.sin(perp_angle)
            painter.drawText(int(label_x - 12), int(label_y + 4), f"{distance}m")
    
    def paintEvent(self, event):
        """Paint the race track with curved layout"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        if w <= 1:
            w = 800
        if h <= 1:
            h = 300
        
        # Generate track path if needed
        if self.track_path is None or not self.track_points:
            self.generate_track_path(w, h)
        
        # Draw track background (grass/dirt area)
        if self.sim_data:
            surface = self.sim_data.get('surface', 'Turf')
            if surface == 'Dirt':
                bg_color = QColor('#8B7355')  # Brown for dirt
            else:
                bg_color = QColor('#2d5016')  # Dark green for turf
        else:
            bg_color = QColor('#2d5016')
        
        painter.fillRect(0, 0, w, h, bg_color)
        
        # Draw track infield (lighter color)
        if self.track_path:
            infield_color = QColor('#1a3d0c') if self.sim_data and self.sim_data.get('surface') != 'Dirt' else QColor('#6B5344')
            painter.setBrush(QBrush(infield_color))
            painter.setPen(Qt.PenStyle.NoPen)
            
            # Scale down the path for infield
            infield_path = QPainterPath()
            cx, cy = w / 2, h / 2
            scale = 0.7
            
            for i, (x, y, _) in enumerate(self.track_points):
                # Scale towards center
                ix = cx + (x - cx) * scale
                iy = cy + (y - cy) * scale
                if i == 0:
                    infield_path.moveTo(ix, iy)
                else:
                    infield_path.lineTo(ix, iy)
            infield_path.closeSubpath()
            painter.drawPath(infield_path)
        
        # Draw outer track edge
        if self.track_path:
            outer_path = QPainterPath()
            cx, cy = w / 2, h / 2
            scale = 1.08
            
            for i, (x, y, _) in enumerate(self.track_points):
                ox = cx + (x - cx) * scale
                oy = cy + (y - cy) * scale
                if i == 0:
                    outer_path.moveTo(ox, oy)
                else:
                    outer_path.lineTo(ox, oy)
            outer_path.closeSubpath()
            
            # Draw track surface between outer and inner
            painter.setBrush(QBrush(QColor('#c4a87c') if self.sim_data and self.sim_data.get('surface') == 'Dirt' else QColor('#90b070')))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(outer_path)
            painter.drawPath(infield_path)
        
        # Draw the main track line (racing line)
        if self.track_path:
            # Track outline
            pen = QPen(QColor('#ffffff'), 3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self.track_path)
            
            # Inner rail
            inner_path = QPainterPath()
            cx, cy = w / 2, h / 2
            for i, (x, y, _) in enumerate(self.track_points):
                ix = cx + (x - cx) * 0.85
                iy = cy + (y - cy) * 0.85
                if i == 0:
                    inner_path.moveTo(ix, iy)
                else:
                    inner_path.lineTo(ix, iy)
            inner_path.closeSubpath()
            
            pen = QPen(QColor('#ffffff'), 2)
            painter.setPen(pen)
            painter.drawPath(inner_path)
        
        # Draw START and FINISH markers
        if self.track_points:
            # Start position (0% progress)
            start_x, start_y = self.get_position_on_track(0.0)
            # Finish position (100% progress / 0% on oval)
            finish_x, finish_y = self.get_position_on_track(0.98)
            
            # Draw finish line
            font = QFont("Arial", 10)
            font.setBold(True)
            painter.setFont(font)
            
            # Finish flag pattern
            painter.setPen(QPen(QColor('#ffffff'), 2))
            finish_angle = self.get_track_direction_at(0.98)
            
            # Draw checkered pattern at finish
            for i in range(4):
                offset = (i - 1.5) * 8
                fx = finish_x + offset * math.cos(finish_angle + math.pi/2)
                fy = finish_y + offset * math.sin(finish_angle + math.pi/2)
                color = QColor('#ffffff') if i % 2 == 0 else QColor('#000000')
                painter.setBrush(QBrush(color))
                painter.drawRect(int(fx - 4), int(fy - 4), 8, 8)
            
            # Labels
            painter.setPen(QPen(QColor('#ffff00')))
            painter.drawText(int(start_x - 25), int(start_y - 25), "START")
            painter.setPen(QPen(QColor('#ff0000')))
            painter.drawText(int(finish_x - 25), int(finish_y + 20), "FINISH")
        
        # Draw racecourse name
        if self.racecourse:
            font = QFont("Arial", 14)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(QColor('#ffffff')))
            direction_text = "↻" if self.direction == "Right" else "↺"
            painter.drawText(10, 25, f"{self.racecourse} {direction_text}")
        
        # Draw course segment markers (corners, spurt, distance markers)
        if self.sim_data and self.track_points:
            race_distance = self.sim_data.get('race_distance', 2500)
            self.draw_corner_markers(painter, race_distance)
            self.draw_spurt_marker(painter, race_distance)
            self.draw_distance_markers(painter, race_distance)
        
        # Draw umas if data available
        if self.sim_data and self.uma_distances and self.track_points:
            race_distance = self.sim_data.get('race_distance', 2500)
            num_umas = len(self.uma_distances)
            
            # Ball size based on number of participants
            if num_umas > 18:
                ball_radius = 10
            elif num_umas > 12:
                ball_radius = 12
            else:
                ball_radius = 14
            
            # Sort umas by distance (leader first)
            sorted_umas = sorted(self.uma_distances.items(), key=lambda x: x[1], reverse=True)
            
            # Calculate positions with realistic lane blocking
            assigned_positions = {}
            
            # Track width for lane spreading (inner to outer rail)
            # Keep smaller to prevent going outside track
            track_width = 28  # Reduced from 45 to keep within track
            num_lanes = min(4, max(3, num_umas // 5))  # 3-4 virtual lanes
            lane_width = track_width / num_lanes
            
            # Keep track of occupied positions to prevent overlap
            # Key: (progress_bucket, lane), Value: uma_name
            occupied_slots = {}
            
            for name, distance in sorted_umas:
                if race_distance > 0:
                    progress = min(distance / race_distance, 1.0)
                else:
                    progress = 0
                
                base_x, base_y = self.get_position_on_track(progress)
                track_angle = self.get_track_direction_at(progress)
                perp_angle = track_angle + math.pi / 2
                
                # Progress bucket for collision detection (finer granularity)
                # Each bucket represents ~1% of race distance
                progress_bucket = int(progress * 100)
                
                # Find an available lane (prefer middle lanes, then spread out)
                # Lane preference order: 2, 1, 3, 0, 4 (middle first)
                lane_preference = [num_lanes // 2]
                for i in range(1, (num_lanes + 1) // 2 + 1):
                    if num_lanes // 2 + i < num_lanes:
                        lane_preference.append(num_lanes // 2 + i)
                    if num_lanes // 2 - i >= 0:
                        lane_preference.append(num_lanes // 2 - i)
                
                assigned_lane = num_lanes // 2  # Default to middle
                
                # Check nearby buckets for collisions (current and adjacent)
                for lane in lane_preference:
                    is_free = True
                    for bucket_offset in range(-2, 3):  # Check ±2 buckets
                        check_bucket = progress_bucket + bucket_offset
                        if (check_bucket, lane) in occupied_slots:
                            is_free = False
                            break
                    if is_free:
                        assigned_lane = lane
                        break
                
                # Mark this slot as occupied
                occupied_slots[(progress_bucket, assigned_lane)] = name
                
                # Calculate actual position based on lane
                # Lane 0 = inner rail, Lane num_lanes-1 = outer rail
                lane_offset = (assigned_lane - (num_lanes - 1) / 2) * lane_width
                
                lane_x = base_x + lane_offset * math.cos(perp_angle)
                lane_y = base_y + lane_offset * math.sin(perp_angle)
                
                assigned_positions[name] = (lane_x, lane_y)
            
            # Draw all Uma
            for name, distance in sorted_umas:
                x_pos, y_pos = assigned_positions.get(name, self.get_position_on_track(0))
                
                # Determine color based on status (priority order)
                if self.uma_finished.get(name, False):
                    color = QColor('#FFD700')  # Gold for finished
                    outline = QColor('white')
                elif self.uma_dnf.get(name, {}).get('dnf', False):
                    color = QColor('#333333')  # Dark gray for DNF
                    outline = QColor('white')
                elif name in self.duel_participants:
                    color = QColor('#FF0000')  # RED - Dueling (追い比べ)
                    outline = QColor('#FFFFFF')
                elif name in self.temptation_participants:
                    color = QColor('#FFCC00')  # YELLOW-ORANGE - Temptation (かかり)
                    outline = QColor('#FF6600')
                elif name in self.rushing_participants:
                    color = QColor('#FF6600')  # ORANGE - Rushing (掛かり)
                    outline = QColor('#FFFFFF')
                elif name in self.spot_struggle_participants:
                    color = QColor('#FF00FF')  # MAGENTA - Spot Struggle (位置取り争い)
                    outline = QColor('#FFFFFF')
                elif self.uma_incidents.get(name, {}).get('type'):
                    color = QColor('#FFAA00')  # Light orange for incident
                    outline = QColor('white')
                else:
                    color = QColor(self.uma_colors.get(name, '#fdbf24'))
                    # Check for active skills - cyan outline if skill is active
                    if name in self.skill_active_participants:
                        outline = QColor('#00FFFF')  # Cyan outline for skill active
                    else:
                        outline = QColor('#c89600')
                
                # Draw uma circle
                painter.setBrush(QBrush(color))
                painter.setPen(QPen(outline, 2))
                painter.drawEllipse(int(x_pos - ball_radius), int(y_pos - ball_radius), 
                                   ball_radius * 2, ball_radius * 2)
                
                # Draw participant number inside circle
                gate_num = self.gate_numbers.get(name, '?')
                font = QFont("Arial", max(6, ball_radius - 2))
                font.setBold(True)
                painter.setFont(font)
                painter.setPen(QPen(QColor('black')))
                painter.drawText(int(x_pos - ball_radius), int(y_pos - ball_radius), 
                                ball_radius * 2, ball_radius * 2, 
                                Qt.AlignmentFlag.AlignCenter, str(gate_num))
    
    def resizeEvent(self, event):
        """Regenerate track path when widget is resized"""
        super().resizeEvent(event)
        # Force track path regeneration
        self.track_path = None
        self.track_points = []
        self.update()
        
    def update_display(self, sim_data, uma_distances, uma_finished, uma_dnf, 
                      uma_incidents, uma_colors, gate_numbers, track_margin, 
                      duel_participants=None, rushing_participants=None, 
                      temptation_participants=None,
                      spot_struggle_participants=None, skill_active_participants=None):
        """Update display data"""
        self.sim_data = sim_data
        self.uma_distances = uma_distances
        self.uma_finished = uma_finished
        self.uma_dnf = uma_dnf
        self.uma_incidents = uma_incidents
        self.uma_colors = uma_colors
        self.gate_numbers = gate_numbers
        self.track_margin = track_margin
        # Update mechanic indicators
        if duel_participants is not None:
            self.duel_participants = duel_participants
        if rushing_participants is not None:
            self.rushing_participants = rushing_participants
        if temptation_participants is not None:
            self.temptation_participants = temptation_participants
        if spot_struggle_participants is not None:
            self.spot_struggle_participants = spot_struggle_participants
            self.duel_participants = duel_participants
        if skill_active_participants is not None:
            self.skill_active_participants = skill_active_participants
        self.update()


class UmaRacingGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        # Initialize simulation variables
        self.sim_running = False
        self.sim_data = None
        self.config_data = None  # Store original config for engine creation
        self.race_engine: RaceEngine = None  # NEW: Core race simulation engine
        self.sim_time = 0.0
        self.fired_event_seconds = set()
        self.uma_icons = {}
        self.track_margin = 80
        self.lane_height = 20
        self.finish_times = {}
        self.incidents_occurred = set()
        self.overtakes = set()
        self.commentary_cooldown = 0
        self.last_commentary_time = 0
        self.previous_positions = {}
        self.uma_colors = {}
        self.real_time_data = None

        # Real-time simulation variables (synced from engine)
        self.uma_distances = {}
        self.uma_finished = {}
        self.uma_incidents = {}
        self.current_positions = {}
        self.uma_fatigue = {}
        self.uma_momentum = {}
        self.uma_last_position = {}
        self.uma_stamina = {}
        self.uma_dnf = {}
        
        # Dueling variables (visual feature)
        self.duel_active = False
        self.duel_participants = set()
        self.rushing_participants = set()
        self.temptation_participants = set()  # Track Uma in temptation state
        self.spot_struggle_participants = set()
        self.skill_active_participants = set()  # Track Uma with active skills
        self.duel_start_time = 0
        self.duel_commentary_made = False
        self.duel_guts_used = {}
        self.duel_stamina_boost_used = {}

        # Commentary tracking
        self.distance_callouts_made = set()
        self.last_incident_commentary = 0
        self.last_position_commentary = 0
        self.last_phase_commentary = 0
        self.last_speed_commentary = 0
        self.last_dnf_commentary = 0
        self.dnf_commented = set()
        self.finish_commented = set()
        self.commentary_history = []
        
        # === BARU: Komentar dueling ===
        self.duel_commentary_lines = [
            "And now we have dueling between {name1} and {name2}!",
            "What a battle! {name1} and {name2} are going head to head!",
            "Incredible! {name1} and {name2} are locked in combat!",
            "The crowd goes wild as {name1} and {name2} duel for position!",
            "A thrilling duel between {name1} and {name2}!",
            "This is intense! {name1} and {name2} are pushing each other to the limit!",
            "A magnificent battle between {name1} and {name2}!",
            "The duel is on! {name1} versus {name2}!"
        ]
        
        self.duel_multi_commentary_lines = [
            "What a spectacle! Multiple runners are dueling for position!",
            "An epic multi-uma battle is unfolding!",
            "The pack is breaking apart as several runners duel for supremacy!",
            "Multiple contenders are locked in combat! What a race!",
            "A fierce multi-uma duel has erupted!"
        ]

        # Gate numbers for visual display
        self.gate_numbers = {}

        # === BARU: Lacak penanda jarak yang digambar ===
        self.distance_markers_drawn = {}

        self.setWindowTitle("Uma Musume Racing Simulator - REAL TIME")
        self.setGeometry(100, 100, 1200, 700)
        self.setup_ui()
        
        # Timer for simulation loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.run_simulation_frame)
        self.timer.start(50)  # ~20 FPS for smooth animation


        
    def setup_ui(self):
        """Setup PySide6 UI"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # Control panel
        control_layout = QHBoxLayout()
        
        # Load button
        self.load_btn = QPushButton("Load Racing Config")
        self.load_btn.clicked.connect(self.load_racing_config)
        control_layout.addWidget(self.load_btn)
        
        # Start button
        self.start_btn = QPushButton("Start Simulation")
        self.start_btn.clicked.connect(self.start_simulation)
        control_layout.addWidget(self.start_btn)
        
        # Stop button
        self.stop_btn = QPushButton("Stop Simulation")
        self.stop_btn.clicked.connect(self.stop_simulation)
        control_layout.addWidget(self.stop_btn)
        
        # Reset button
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.clicked.connect(self.reset_simulation)
        control_layout.addWidget(self.reset_btn)
        
        # Stat Priorities button
        self.priorities_btn = QPushButton("Stat Priorities")
        self.priorities_btn.clicked.connect(self.show_stat_priorities)
        control_layout.addWidget(self.priorities_btn)
        
        # Speed label and combobox
        control_layout.addWidget(QLabel("Speed:"))
        self.speed_cb = QComboBox()
        self.speed_cb.addItems(["0.5x", "1x", "2x", "5x", "10x"])
        self.speed_cb.setCurrentText("1x")
        self.speed_cb.setMaximumWidth(70)
        control_layout.addWidget(self.speed_cb)
        
        # Remaining distance label
        self.remaining_label = QLabel("Remaining: -- | Lead: -- km/h")
        control_layout.addWidget(self.remaining_label)
        
        # Real-time indicator
        self.realtime_label = QLabel("REAL-TIME MODE")
        self.realtime_label.setStyleSheet("color: red; font-weight: bold; font-size: 11px;")
        control_layout.addWidget(self.realtime_label)
        
        control_layout.addStretch()
        main_layout.addLayout(control_layout)
        
        # Splitter for canvas and output
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # Horizontal layout for canvas + positions sidebar
        canvas_sidebar_widget = QWidget()
        canvas_sidebar_layout = QHBoxLayout(canvas_sidebar_widget)
        canvas_sidebar_layout.setContentsMargins(0, 0, 0, 0)
        canvas_sidebar_layout.setSpacing(5)
        
        # Canvas frame - larger for curved track display
        self.canvas_frame = QFrame()
        self.canvas_frame.setStyleSheet("background-color: #3a665a;")
        self.canvas_frame.setMinimumHeight(450)  # Larger canvas for better track visibility
        canvas_layout = QVBoxLayout(self.canvas_frame)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        
        # Use a custom painter-based canvas
        self.race_canvas = RaceCanvasWidget()
        self.race_canvas.setStyleSheet("background-color: #3a665a;")
        self.race_canvas.setMinimumHeight(440)  # Ensure canvas doesn't shrink
        canvas_layout.addWidget(self.race_canvas)
        
        canvas_sidebar_layout.addWidget(self.canvas_frame, stretch=4)
        
        # === F1-STYLE POSITIONS SIDEBAR ===
        self.positions_frame = QFrame()
        self.positions_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a2e;
                border: 2px solid #16213e;
                border-radius: 5px;
            }
        """)
        self.positions_frame.setMinimumWidth(180)
        self.positions_frame.setMaximumWidth(220)
        positions_layout = QVBoxLayout(self.positions_frame)
        positions_layout.setContentsMargins(5, 5, 5, 5)
        positions_layout.setSpacing(2)
        
        # Header
        positions_header = QLabel("🏁 LIVE POSITIONS")
        positions_header.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-weight: bold;
                font-size: 11px;
                padding: 5px;
                background-color: #0f3460;
                border-radius: 3px;
            }
        """)
        positions_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        positions_layout.addWidget(positions_header)
        
        # Positions list
        self.positions_list = QListWidget()
        self.positions_list.setStyleSheet("""
            QListWidget {
                background-color: #1a1a2e;
                border: none;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10px;
            }
            QListWidget::item {
                padding: 3px 5px;
                border-bottom: 1px solid #16213e;
            }
            QListWidget::item:selected {
                background-color: #16213e;
            }
        """)
        positions_layout.addWidget(self.positions_list)
        
        canvas_sidebar_layout.addWidget(self.positions_frame, stretch=0)
        
        splitter.addWidget(canvas_sidebar_widget)
        
        # Output text area
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background-color: #0a0a0a; color: #00ff00; font-family: Courier; font-size: 9pt;")
        self.output_text.setMaximumHeight(150)  # Smaller output area
        splitter.addWidget(self.output_text)
        
        splitter.setStretchFactor(0, 4)  # Canvas gets more space
        splitter.setStretchFactor(1, 1)
        
        main_layout.addWidget(splitter, 1)
        
    def draw_track(self):
        """Draw track on canvas"""
        self.race_canvas.update_display(
            self.sim_data, self.uma_distances, 
            self.uma_finished, self.uma_dnf,
            self.uma_incidents, self.uma_colors,
            {}, self.track_margin
        )
    
    def run_simulation_frame(self):
        """Run one frame of simulation"""
        if self.sim_running and self.race_engine:
            self._run_real_time_tick()

    def load_racing_config(self):
        """Load racing configuration from JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Racing Config File",
            "",
            "JSON files (*.json);;All files (*.*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Store original config for engine creation
            self.config_data = config_data
            
            # Create the race engine
            self.race_engine = create_race_engine_from_config(config_data)
            
            # Also prepare legacy sim_data for UI compatibility
            self.sim_data = self.prepare_real_time_simulation(config_data)
            
            race_config = config_data.get('race', {})
            self.append_output(f"Loaded racing config: {file_path}\n")
            self.append_output(f"Race: {race_config.get('name', 'Unknown')}\n")
            
            # Show Japanese name if available
            if race_config.get('name_jp'):
                self.append_output(f"  ({race_config.get('name_jp')})\n")
            
            self.append_output(f"Race distance: {self.race_engine.race_distance}m\n")
            self.append_output(f"Race type: {self.race_engine.race_type}\n")
            self.append_output(f"Terrain: {self.race_engine.terrain.value.capitalize()}\n")
            
            # Show racecourse and direction if available (G1 race)
            if race_config.get('racecourse'):
                direction = race_config.get('direction', '')
                dir_text = f" ({direction}-handed)" if direction else ""
                self.append_output(f"Racecourse: {race_config.get('racecourse')}{dir_text}\n")
                # Set racecourse on the canvas for curved track rendering
                self.race_canvas.set_racecourse(race_config.get('racecourse'), direction)
            else:
                # Default to Tokyo if no racecourse specified
                self.race_canvas.set_racecourse("Tokyo", "Left")
            
            # Show season if available
            if race_config.get('season'):
                self.append_output(f"Season: {race_config.get('season')}\n")
            
            self.append_output(f"Track Condition: {self.race_engine.track_condition.value.capitalize()}\n")
            if self.race_engine.stat_threshold > 0:
                self.append_output(f"Stat Threshold: {self.race_engine.stat_threshold}\n")
            self.append_output(f"Umas: {len(config_data.get('umas', []))}\n")
            self.append_output("REAL-TIME SIMULATION MODE READY (New Engine)\n")
            
            self.initialize_uma_icons()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load config file:\n{str(e)}")
            self.append_output(f"Error loading config: {str(e)}\n")
    
    def prepare_real_time_simulation(self, config_data):
        """Prepare simulation data for real-time execution"""
        race_info = config_data.get('race', {})
        umas = config_data.get('umas', [])

        race_distance = race_info.get('distance', 2500)
        race_type = race_info.get('type', 'Medium')
        surface = race_info.get('surface', 'Turf')

        speed_params = {
            'Sprint': {'base_speed': 16.5, 'top_speed': 17.5, 'sprint_speed': 18.0},
            'Mile': {'base_speed': 16.2, 'top_speed': 17.2, 'sprint_speed': 17.7},
            'Medium': {'base_speed': 16.0, 'top_speed': 17.0, 'sprint_speed': 17.5},
            'Long': {'base_speed': 15.8, 'top_speed': 16.8, 'sprint_speed': 17.3}
        }

        params = speed_params.get(race_type, speed_params['Medium'])
        base_speed = params['base_speed']
        top_speed = params['top_speed']
        sprint_speed = params['sprint_speed']

        stat_weights = {
            'Sprint': {'Speed': 0.45, 'Stamina': 0.15, 'Power': 0.20, 'Guts': 0.12, 'Wit': 0.08},
            'Mile': {'Speed': 0.35, 'Stamina': 0.25, 'Power': 0.18, 'Guts': 0.14, 'Wit': 0.08},
            'Medium': {'Speed': 0.30, 'Stamina': 0.35, 'Power': 0.15, 'Guts': 0.12, 'Wit': 0.08},
            'Long': {'Speed': 0.25, 'Stamina': 0.40, 'Power': 0.15, 'Guts': 0.12, 'Wit': 0.08}
        }

        weights = stat_weights.get(race_type, stat_weights['Medium'])

        # Stat priority multipliers for each running style
        stat_priorities = {
            'FR': ['Speed', 'Wit', 'Power', 'Guts', 'Stamina'],
            'PC': ['Speed', 'Power', 'Wit', 'Guts', 'Stamina'],
            'LS': ['Speed', 'Power', 'Wit', 'Stamina', 'Guts'],
            'EC': ['Speed', 'Power', 'Wit', 'Stamina', 'Guts']
        }

        # Priority multipliers: higher priority stats get boosted
        priority_multipliers = [1.2, 1.15, 1.1, 1.05, 1.0]

        uma_stats = {}
        for uma in umas:
            name = uma['name']
            stats = uma['stats']
            running_style = uma.get('running_style', 'PC')

            # Get stat priorities for this running style
            style_priorities = stat_priorities.get(running_style, stat_priorities['PC'])

            # Create stat contribution with priority multipliers
            stat_contributions = {}
            for i, stat_name in enumerate(style_priorities):
                multiplier = priority_multipliers[i]
                if stat_name == 'Speed':
                    stat_contributions['Speed'] = stats.get('Speed', 0) * weights['Speed'] * multiplier
                elif stat_name == 'Stamina':
                    stat_contributions['Stamina'] = stats.get('Stamina', 0) * weights['Stamina'] * multiplier
                elif stat_name == 'Power':
                    stat_contributions['Power'] = stats.get('Power', 0) * weights['Power'] * multiplier
                elif stat_name == 'Guts':
                    stat_contributions['Guts'] = stats.get('Guts', 0) * weights['Guts'] * multiplier
                elif stat_name == 'Wit':
                    stat_contributions['Wit'] = stats.get('Wit', 0) * weights['Wit'] * multiplier

            base_performance = sum(stat_contributions.values())

            distance_apt = uma.get('distance_aptitude', {})
            surface_apt = uma.get('surface_aptitude', {})

            apt_multipliers = {
                'Sprint': {'S': 1.12, 'A': 1.06, 'B': 1.00, 'C': 0.94, 'D': 0.88, 'E': 0.82, 'F': 0.76, 'G': 0.70},
                'Mile': {'S': 1.10, 'A': 1.05, 'B': 1.00, 'C': 0.95, 'D': 0.90, 'E': 0.85, 'F': 0.80, 'G': 0.75},
                'Medium': {'S': 1.08, 'A': 1.04, 'B': 1.00, 'C': 0.96, 'D': 0.92, 'E': 0.88, 'F': 0.84, 'G': 0.80},
                'Long': {'S': 1.15, 'A': 1.08, 'B': 1.00, 'C': 0.92, 'D': 0.85, 'E': 0.78, 'F': 0.72, 'G': 0.65}
            }

            distance_multipliers = apt_multipliers.get(race_type, apt_multipliers['Medium'])
            surface_multipliers = apt_multipliers.get(race_type, apt_multipliers['Medium'])

            distance_multiplier = distance_multipliers.get(distance_apt.get(race_type, 'B'), 1.0)
            surface_multiplier = surface_multipliers.get(surface_apt.get(surface, 'B'), 1.0)

            running_style_bonuses = {
                'Sprint': {
                    'FR': {'early_speed_bonus': 0.20, 'mid_speed_bonus': 0.10, 'final_speed_bonus': 0.05},
                    'PC': {'early_speed_bonus': 0.08, 'mid_speed_bonus': 0.12, 'final_speed_bonus': 0.08},
                    'LS': {'early_speed_penalty': -0.05, 'mid_speed_bonus': 0.08, 'final_speed_bonus': 0.10},
                    'EC': {'early_speed_penalty': -0.10, 'mid_speed_penalty': -0.05, 'final_speed_bonus': 0.15}
                },
                'Mile': {
                    'FR': {'early_speed_bonus': 0.15, 'mid_speed_bonus': 0.08, 'final_speed_penalty': -0.05},
                    'PC': {'early_speed_bonus': 0.06, 'mid_speed_bonus': 0.10, 'final_speed_bonus': 0.06},
                    'LS': {'early_speed_penalty': -0.06, 'mid_speed_bonus': 0.06, 'final_speed_bonus': 0.12},
                    'EC': {'early_speed_penalty': -0.12, 'mid_speed_penalty': -0.06, 'final_speed_bonus': 0.18}
                },
                'Medium': {
                    'FR': {'early_speed_bonus': 0.12, 'mid_speed_bonus': 0.06, 'final_speed_penalty': -0.08},
                    'PC': {'early_speed_bonus': 0.04, 'mid_speed_bonus': 0.08, 'final_speed_bonus': 0.05},
                    'LS': {'early_speed_penalty': -0.07, 'mid_speed_bonus': 0.05, 'final_speed_bonus': 0.14},
                    'EC': {'early_speed_penalty': -0.14, 'mid_speed_penalty': -0.07, 'final_speed_bonus': 0.20}
                },
                'Long': {
                    'FR': {'early_speed_bonus': 0.10, 'mid_speed_penalty': -0.05, 'final_speed_penalty': -0.15},
                    'PC': {'early_speed_bonus': 0.03, 'mid_speed_bonus': 0.06, 'final_speed_bonus': 0.04},
                    'LS': {'early_speed_penalty': -0.08, 'mid_speed_bonus': 0.04, 'final_speed_bonus': 0.15},
                    'EC': {'early_speed_penalty': -0.15, 'mid_speed_penalty': -0.08, 'final_speed_bonus': 0.25}
                }
            }

            style_bonus_config = running_style_bonuses.get(race_type, running_style_bonuses['Medium'])
            style_bonus = style_bonus_config.get(running_style, style_bonus_config['PC'])

            final_performance = base_performance * distance_multiplier * surface_multiplier

            uma_stats[name] = {
                'base_performance': final_performance,
                'running_style': running_style,
                'style_bonus': style_bonus,
                'base_speed': base_speed,
                'top_speed': top_speed,
                'sprint_speed': sprint_speed,
                'stamina': stats.get('Stamina', 0),
                'guts': stats.get('Guts', 0),
                'wisdom': stats.get('Wit', 0),
                'power': stats.get('Power', 0),
                'speed': stats.get('Speed', 0),
                'distance_aptitude': distance_apt.get(race_type, 'B'),
                'surface_aptitude': surface_apt.get(surface, 'B'),
                'race_type': race_type
            }

        performances = [stats['base_performance'] for stats in uma_stats.values()]
        if performances:
            min_perf = min(performances)
            max_perf = max(performances)

            normalization_ranges = {
                'Sprint': (0.82, 0.30),
                'Mile': (0.80, 0.33),
                'Medium': (0.78, 0.36),
                'Long': (0.76, 0.40)
            }

            base_range, range_size = normalization_ranges.get(race_type, (0.78, 0.36))

            for name in uma_stats:
                if max_perf - min_perf > 0:
                    normalized = (uma_stats[name]['base_performance'] - min_perf) / (max_perf - min_perf)
                    compressed = base_range + (normalized * range_size)
                    uma_stats[name]['base_performance'] = compressed
                else:
                    uma_stats[name]['base_performance'] = 1.0

        return {
            'race_distance': race_distance,
            'race_type': race_type,
            'race_surface': surface,
            'race_id': race_info.get('id', ''),  # Add race_id for course segment lookup
            'racecourse': race_info.get('racecourse', ''),
            'direction': race_info.get('direction', ''),
            'uma_stats': uma_stats
        }

    def initialize_real_time_simulation(self):
        """Initialize all real-time simulation variables and reset the race engine."""
        if not self.sim_data:
            return
            
        uma_stats = self.sim_data.get('uma_stats', {})
        
        # Initialize GUI tracking variables
        self.uma_distances = {name: 0.0 for name in uma_stats.keys()}
        self.uma_finished = {name: False for name in uma_stats.keys()}
        self.uma_incidents = {name: {'type': None, 'duration': 0, 'start_time': 0} for name in uma_stats.keys()}
        self.current_positions = {name: 1 for name in uma_stats.keys()}
        self.uma_fatigue = {name: 0.0 for name in uma_stats.keys()}
        self.uma_momentum = {name: 1.0 for name in uma_stats.keys()}
        self.uma_last_position = {name: 1 for name in uma_stats.keys()}
        self.uma_stamina = {name: 100.0 for name in uma_stats.keys()}
        self.uma_dnf = {name: {'dnf': False, 'reason': '', 'dnf_time': 0, 'dnf_distance': 0} for name in uma_stats.keys()}
        
        # Dueling variables (visual feature)
        self.duel_active = False
        self.duel_participants = set()
        self.duel_start_time = 0
        self.duel_commentary_made = False
        self.duel_guts_used = {name: False for name in uma_stats.keys()}
        self.duel_stamina_boost_used = {name: False for name in uma_stats.keys()}
        
        # Mechanic tracking for visual indicators
        self.rushing_participants = set()
        self.temptation_participants = set()
        self.spot_struggle_participants = set()
        self._rushing_announced = set()
        self._temptation_announced = set()
        self._spot_struggle_announced = set()

        self.sim_time = 0.0
        self.finish_times.clear()
        self.incidents_occurred.clear()
        self.overtakes.clear()
        self.last_commentary_time = 0
        self.previous_positions.clear()

        self.distance_callouts_made.clear()
        self.last_incident_commentary = 0
        self.last_position_commentary = 0
        self.last_phase_commentary = 0
        self.last_speed_commentary = 0
        self.commentary_history.clear()

        # === BARU: Hapus penanda jarak lama ===
        self.distance_markers_drawn.clear()

    def calculate_dnf_chance(self, uma_name, uma_stats):
        """Calculate DNF chance based on stats and aptitudes"""
        # Base stats (100-150) should have virtually no DNF chance
        base_chance = 0.00001  # Extremely low base

        stat_penalty = 0
        for stat_name, stat_value in [('Speed', uma_stats['speed']),
                                     ('Stamina', uma_stats['stamina']),
                                     ('Power', uma_stats['power']),
                                     ('Guts', uma_stats['guts']),
                                     ('Wit', uma_stats['wisdom'])]:
            # Only heavily penalize critically low stats (below 100)
            if stat_value < 100:
                stat_penalty += (100 - stat_value) * 0.000001

        distance_apt = uma_stats['distance_aptitude']
        surface_apt = uma_stats['surface_aptitude']

        apt_multiplier = 1.0
        # Only penalize worst aptitudes
        if distance_apt == 'G':
            apt_multiplier += 0.001
        if surface_apt == 'G':
            apt_multiplier += 0.001

        # Only extreme cases get multiplier boost
        if (uma_stats['stamina'] < 80 or
            uma_stats['guts'] < 80):
            apt_multiplier += 0.002

        final_chance = (base_chance + stat_penalty) * apt_multiplier
        return min(final_chance, 0.005)  # Very low max chance

    def check_dnf(self, uma_name, uma_stats, current_distance, race_distance):
        """Check if uma suffers DNF during race"""
        if self.uma_dnf[uma_name]['dnf']:
            return True, self.uma_dnf[uma_name]['reason']
            
        race_progress = current_distance / race_distance
        # Only check during middle portion of race
        if race_progress < 0.4 or race_progress > 0.85:
            return False, ""
        
        dnf_chance = self.calculate_dnf_chance(uma_name, uma_stats)
        
        # Reduced check frequency
        if random.random() < 0.05:
            if random.random() < dnf_chance:
                reasons = []
                # Only extremely low stats cause DNF
                if uma_stats['stamina'] < 80:
                    reasons.append("exhaustion")
                if uma_stats['guts'] < 80:
                    reasons.append("loss of will")
                if uma_stats['distance_aptitude'] == 'G':
                    reasons.append("unsuitable distance")
                if uma_stats['surface_aptitude'] == 'G':
                    reasons.append("unsuitable surface")
                
                # Base stats should rarely reach here
                if not reasons:
                    return False, ""
                
                reason = ", ".join(reasons)
                
                self.uma_dnf[uma_name] = {
                    'dnf': True,
                    'reason': reason,
                    'dnf_time': self.sim_time,
                    'dnf_distance': current_distance
                }
                
                return True, reason
        
        return False, ""

    def initialize_uma_icons(self):
        """Initialize Uma Musume style visual icons"""
        self.uma_icons.clear()
        self.uma_colors.clear()
        self.gate_numbers.clear()
        
        if not self.sim_data:
            return
            
        uma_stats = self.sim_data.get('uma_stats', {})
        if not uma_stats:
            self.append_output("Warning: No uma stats found in config.\n")
            return
        
        colors = [
            '#FF6B9D', '#4FC3F7', '#81C784', '#FFB74D', '#BA68C8', '#A1887F',
            '#F06292', '#4DD0E1', '#9575CD', '#4DB6AC', '#E57373', '#64B5F6',
            '#AED581', '#FFD54F', '#CE93D8', '#FF8A65', '#90CAF9', '#C5E1A5'
        ]
        
        # Try to get gate numbers from config, fallback to sequential
        config_umas = self.config_data.get('umas', []) if self.config_data else []
        uma_gate_map = {}
        for uma_data in config_umas:
            uma_name = uma_data.get('name', '')
            gate = uma_data.get('gate_number', 0)
            if uma_name and gate:
                uma_gate_map[uma_name] = gate
        
        for i, name in enumerate(uma_stats.keys()):
            # Use gate from config if available, otherwise use index + 1
            gate_number = uma_gate_map.get(name, i + 1)
            self.gate_numbers[name] = gate_number
            color = colors[i % len(colors)]
            self.uma_colors[name] = color
            self.uma_icons[name] = (None, None, None)  # Placeholder for PySide6
        
        # Initialize positions sidebar with starting positions (by gate number)
        starting_positions = [(name, 0) for name in uma_stats.keys()]
        # Sort by gate number for initial display
        starting_positions.sort(key=lambda x: self.gate_numbers.get(x[0], 999))
        self.update_positions_sidebar(starting_positions)
            
        self.append_output(f"Initialized {len(uma_stats)} umas on track.\n")

    def start_simulation(self):
        """Start the real-time simulation"""
        if not self.sim_data:
            self.append_output("Error: No simulation data loaded. Please load a racing config first.\n")
            return
            
        if self.sim_running:
            self.append_output("Simulation is already running.\n")
            return
            
        self.sim_running = True
        self.initialize_real_time_simulation()
        
        # Reset the race engine
        if self.race_engine:
            self.race_engine.reset()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.append_output("REAL-TIME SIMULATION started! (New Engine)\n")
        
        self._run_real_time_tick()
        
    def _run_real_time_tick(self):
        """Main simulation tick using the new RaceEngine"""
        if not self.sim_running or not self.race_engine:
            return
            
        try:
            # Get speed multiplier from UI
            speed_text = self.speed_cb.currentText()
            mult = 1.0
            if speed_text.endswith('x'):
                try:
                    mult = float(speed_text[:-1])
                except Exception:
                    mult = 1.0
                    
            frame_dt = 0.05 * mult
            
            # ===== NEW ENGINE TICK =====
            engine_states = self.race_engine.tick(frame_dt)
            self.sim_time = self.race_engine.current_time
            
            # Sync engine state to GUI variables
            self._sync_engine_state_to_gui(engine_states)
            
            race_distance = self.race_engine.race_distance
            
            # Build frame positions from engine state
            current_frame_positions = [
                (name, state.distance) 
                for name, state in engine_states.items()
            ]
            current_frame_positions.sort(key=lambda x: x[1], reverse=True)

            # Calculate remaining distance
            remaining_distance = race_distance
            if current_frame_positions:
                leader_dist = current_frame_positions[0][1]
                remaining_distance = max(0, race_distance - leader_dist)

                # Distance markers
                markers_to_show = [1000, 800, 600, 400, 200]
                for marker in markers_to_show:
                    if remaining_distance <= marker and marker not in self.distance_markers_drawn:
                        self.draw_distance_marker(marker, race_distance)
                        self.distance_markers_drawn[marker] = True
            
            # Check and trigger dueling (visual feature)
            if not self.duel_active and 400 <= remaining_distance <= 1200:
                self.check_and_trigger_dueling(
                    self.sim_data.get('uma_stats', {}), 
                    current_frame_positions, 
                    race_distance
                )

            # Build incidents dict for commentary
            current_incidents = {
                name: self.uma_incidents[name]['type'] 
                for name in self.uma_incidents.keys() 
                if self.uma_incidents[name]['type'] 
                and not self.uma_finished.get(name, False) 
                and not self.uma_dnf.get(name, {}).get('dnf', False)
            }

            # Filter active positions
            active_positions = [
                p for p in current_frame_positions 
                if not self.uma_finished.get(p[0], False) 
                and not self.uma_dnf.get(p[0], {}).get('dnf', False)
            ]

            # Commentary
            if self.sim_time - self.last_commentary_time > 1.8:
                leader_dist = active_positions[0][1] if active_positions else (
                    current_frame_positions[0][1] if current_frame_positions else 0
                )
                remaining_distance = max(0, race_distance - leader_dist)
            commentaries = self.get_enhanced_commentary(
                    self.sim_time, active_positions, race_distance,
                    remaining_distance, current_incidents, set(self.finish_times.keys())
                )
                
            for commentary in commentaries:
                    if commentary not in self.commentary_history[-5:]:
                        self.append_output(f"[{self.sim_time:.1f}s] {commentary}\n")
                        self.commentary_history.append(commentary)
                        self.last_commentary_time = self.sim_time
                        if len(self.commentary_history) > 20:
                            self.commentary_history.pop(0)
            
            self.update_display(current_frame_positions, race_distance)
            
            # Check if race is finished (via engine)
            if self.race_engine.is_finished:
                self.sim_running = False
                self.start_btn.setEnabled(True)
                self.stop_btn.setEnabled(False)
                self.display_final_results()
                return
            
        except Exception as e:
            import traceback
            self.append_output(f"Simulation error: {str(e)}\n")
            self.append_output(f"Traceback: {traceback.format_exc()}\n")
            self.sim_running = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)

    def _sync_engine_state_to_gui(self, engine_states: dict):
        """Sync RaceEngine state to GUI variables for display and commentary."""
        # Track mechanic states for indicators
        new_duel_participants = set()
        new_rushing_participants = set()
        new_temptation_participants = set()
        new_spot_struggle_participants = set()
        new_skill_active_participants = set()
        
        for name, state in engine_states.items():
            # Sync distance
            self.uma_distances[name] = state.distance
            
            # Sync finished status
            if state.is_finished and not self.uma_finished.get(name, False):
                self.uma_finished[name] = True
                self.finish_times[name] = state.finish_time
            
            # Sync DNF status
            if state.is_dnf and not self.uma_dnf.get(name, {}).get('dnf', False):
                self.uma_dnf[name] = {
                    'dnf': True,
                    'reason': state.dnf_reason,
                    'dnf_time': self.sim_time,
                    'dnf_distance': state.distance
                }
                self.append_output(f"[{self.sim_time:.1f}s] {name} DNF! Reason: {state.dnf_reason}\n")
            
            # Sync stamina and fatigue
            self.uma_stamina[name] = state.stamina
            self.uma_fatigue[name] = state.fatigue
            
            # Track position changes for overtake detection
            new_position = state.position
            if name in self.previous_positions:
                old_position = self.previous_positions[name]
                if old_position > new_position:  # Overtake happened
                    self.overtakes.add((name, old_position, new_position, self.sim_time))
            self.previous_positions[name] = new_position
            
            # Track mechanic states for visual indicators
            if state.is_in_duel:
                new_duel_participants.add(name)
            if state.is_rushing:
                new_rushing_participants.add(name)
            if hasattr(state, 'is_tempted') and state.is_tempted:
                new_temptation_participants.add(name)
            if state.is_in_spot_struggle:
                new_spot_struggle_participants.add(name)
            
            # Track if Uma has active skills
            if hasattr(state, 'active_skills') and state.active_skills:
                new_skill_active_participants.add(name)
            
            # Skills: Check for newly activated skills
            if hasattr(state, 'skills_activated_log') and state.skills_activated_log:
                gate = self.gate_numbers.get(name, '?')
                for skill_name in state.skills_activated_log:
                    self.append_output(f"[{self.sim_time:.1f}s] ✨ [{gate}]{name} activated {skill_name}!\n")
                # Clear the log after processing
                state.skills_activated_log.clear()
        
        # Commentary for mechanic changes
        # Dueling commentary
        new_duelers = new_duel_participants - self.duel_participants
        for name in new_duelers:
            partner = engine_states[name].duel_partner if name in engine_states else ""
            if partner:
                gate1 = self.gate_numbers.get(name, '?')
                gate2 = self.gate_numbers.get(partner, '?')
                self.append_output(f"[{self.sim_time:.1f}s] 🔥 DUEL! [{gate1}]{name} vs [{gate2}]{partner} in an intense battle!\n")
        
        # Rushing commentary (only first time)
        if not hasattr(self, '_rushing_announced'):
            self._rushing_announced = set()
        new_rushers = new_rushing_participants - self._rushing_announced
        for name in new_rushers:
            self._rushing_announced.add(name)
            gate = self.gate_numbers.get(name, '?')
            self.append_output(f"[{self.sim_time:.1f}s] ⚡ [{gate}]{name} is RUSHING! Burning extra stamina!\n")
        
        # Spot struggle commentary (only first time)
        if not hasattr(self, '_spot_struggle_announced'):
            self._spot_struggle_announced = set()
        new_strugglers = new_spot_struggle_participants - self._spot_struggle_announced
        for name in new_strugglers:
            self._spot_struggle_announced.add(name)
            gate = self.gate_numbers.get(name, '?')
            self.append_output(f"[{self.sim_time:.1f}s] 💥 [{gate}]{name} enters SPOT STRUGGLE!\n")
        
        # Temptation commentary (かかり - losing control)
        if not hasattr(self, '_temptation_announced'):
            self._temptation_announced = set()
        new_tempted = new_temptation_participants - self._temptation_announced
        for name in new_tempted:
            self._temptation_announced.add(name)
            gate = self.gate_numbers.get(name, '?')
            self.append_output(f"[{self.sim_time:.1f}s] 😤 [{gate}]{name} is losing control! (TEMPTATION)\n")
        # Clear announced when temptation ends (so it can announce again)
        ended_temptation = self._temptation_announced - new_temptation_participants
        for name in ended_temptation:
            self._temptation_announced.discard(name)
        
        # Update indicator sets
        self.duel_participants = new_duel_participants
        self.rushing_participants = new_rushing_participants
        self.temptation_participants = new_temptation_participants
        self.spot_struggle_participants = new_spot_struggle_participants
        self.skill_active_participants = new_skill_active_participants

    def calculate_real_time_positions(self, time_delta):
        """Legacy method - kept for compatibility but engine handles this now."""
        # This method is now mostly unused, but kept for any legacy code paths
        race_distance = self.sim_data.get('race_distance', 2500)
        race_type = self.sim_data.get('race_type', 'Medium')
        uma_stats = self.sim_data.get('uma_stats', {})
        
        frame_positions = []
        
        for uma_name in uma_stats.keys():
            # Kuda yang sudah finish/DNF tetap dimasukkan ke frame_positions
            if self.uma_finished[uma_name] or self.uma_dnf[uma_name]['dnf']:
                frame_positions.append((uma_name, self.uma_distances[uma_name]))
                continue
                
            uma_stat = uma_stats[uma_name]
            
            dnf, dnf_reason = self.check_dnf(uma_name, uma_stat, self.uma_distances[uma_name], race_distance)
            if dnf:
                self.uma_dnf[uma_name]['dnf'] = True
                self.uma_dnf[uma_name]['reason'] = dnf_reason
                self.uma_dnf[uma_name]['dnf_time'] = self.sim_time
                self.uma_dnf[uma_name]['dnf_distance'] = self.uma_distances[uma_name]
                self.append_output(f"[{self.sim_time:.1f}s] {uma_name} DNF! Reason: {dnf_reason}\n")
                frame_positions.append((uma_name, self.uma_distances[uma_name]))
                continue
            
            if self.uma_incidents[uma_name]['type']:
                incident_time = self.sim_time - self.uma_incidents[uma_name]['start_time']
                if incident_time >= self.uma_incidents[uma_name]['duration']:
                    self.uma_incidents[uma_name]['type'] = None
                else:
                    speed_multiplier = 0.3
                    if self.uma_incidents[uma_name]['type'] == 'stumble':
                        speed_multiplier = 0.1
                    elif self.uma_incidents[uma_name]['type'] == 'blocked':
                        speed_multiplier = 0.5

                    current_speed = self.calculate_current_speed(uma_name, uma_stat, race_distance, race_type)
                    distance_covered = current_speed * time_delta * speed_multiplier
                    self.uma_distances[uma_name] += distance_covered

                    if self.uma_distances[uma_name] >= race_distance:
                        self.uma_finished[uma_name] = True
                        self.finish_times[uma_name] = self.sim_time

                    frame_positions.append((uma_name, self.uma_distances[uma_name]))
                    continue

            current_speed = self.calculate_current_speed(uma_name, uma_stat, race_distance, race_type)
            
            # === BARU: Apply duel speed boost ===
            if self.duel_active and uma_name in self.duel_participants:
                # High guts umas get surgical speed precision
                if uma_stat['guts'] > 800:
                    speed_boost = 0.15
                elif uma_stat['guts'] > 600:
                    speed_boost = 0.10
                elif uma_stat['guts'] > 400:
                    speed_boost = 0.05
                else:
                    speed_boost = 0.02
                
                current_speed *= (1.0 + speed_boost)
            
            current_speed *= self.uma_momentum[uma_name]
            distance_covered = current_speed * time_delta
            self.uma_distances[uma_name] += distance_covered

            if self.uma_distances[uma_name] >= race_distance:
                self.uma_finished[uma_name] = True
                self.finish_times[uma_name] = self.sim_time
            
            frame_positions.append((uma_name, self.uma_distances[uma_name]))
        
        frame_positions.sort(key=lambda x: x[1], reverse=True)
        
        for i, (name, distance) in enumerate(frame_positions):
            position = i + 1
            if name in self.previous_positions and self.previous_positions[name] != position:
                old_pos = self.previous_positions[name]
                if old_pos > position:
                    self.overtakes.add((name, old_pos, position, self.sim_time))
            self.previous_positions[name] = position
        
        return frame_positions

    def draw_distance_marker(self, marker_distance, race_distance):
        """Draw a distance marker on the track (placeholder for PySide6)"""
        # This is a visual marker for important distance callouts
        # In the simple track design, we just announce via commentary
        pass

    def check_and_activate_skills(self, uma_name, uma_stat, race_distance, race_type):
        """Check and activate skills based on race phase, cooldown, and chance"""
        current_distance = self.uma_distances[uma_name]
        race_progress = current_distance / race_distance

        # Determine current phase
        if race_type == 'Sprint':
            phases = {'start': (0.0, 0.2), 'mid': (0.2, 0.7), 'final': (0.7, 0.9), 'sprint': (0.9, 1.0)}
        elif race_type == 'Mile':
            phases = {'start': (0.0, 0.15), 'mid': (0.15, 0.6), 'final': (0.6, 0.85), 'sprint': (0.85, 1.0)}
        elif race_type == 'Medium':
            phases = {'start': (0.0, 0.1), 'mid': (0.1, 0.5), 'final': (0.5, 0.8), 'sprint': (0.8, 1.0)}
        else:
            phases = {'start': (0.0, 0.05), 'mid': (0.05, 0.4), 'final': (0.4, 0.7), 'sprint': (0.7, 1.0)}

        current_phase = 'start'
        for phase, (start, end) in phases.items():
            if start <= race_progress < end:
                current_phase = phase
                break

        # Check each skill
        for skill_name in self.uma_skills[uma_name]:
            skill_data = self.uma_skills[uma_name][skill_name]
            skill_effect = self.skill_effects.get(skill_name, {})

            # Skip if skill is already active
            if skill_data['active']:
                # Check if duration has expired
                if self.sim_time - skill_data['last_activation'] >= skill_effect.get('duration', 0):
                    skill_data['active'] = False
                    skill_data['duration_left'] = 0
                    skill_data['effect'] = None
                    # Remove persistent effects
                    effect_type = skill_effect.get('type')
                    value = skill_effect.get('value', 0)
                    if effect_type == 'momentum_boost':
                        self.uma_momentum[uma_name] = max(1.0, self.uma_momentum[uma_name] - value)
                continue

            # Check cooldown
            if self.sim_time - skill_data['last_activation'] < skill_effect.get('cooldown', 0):
                continue

            # Check phase
            if skill_effect.get('phase', 'mid') != current_phase:
                continue

            # Check activation chance
            if random.random() > skill_effect.get('chance', 0.5):
                continue

            # Activate skill
            skill_data['active'] = True
            skill_data['last_activation'] = self.sim_time
            skill_data['duration_left'] = skill_effect.get('duration', 0)
            skill_data['effect'] = skill_effect

            # Apply immediate or persistent effects
            effect_type = skill_effect.get('type')
            value = skill_effect.get('value', 0)
            if effect_type == 'stamina_recovery':
                self.uma_stamina[uma_name] = min(100.0, self.uma_stamina[uma_name] + value)
            elif effect_type == 'momentum_boost':
                self.uma_momentum[uma_name] += value

            # Skill activated (used for commentary tracking if needed)

    def calculate_current_speed(self, uma_name, uma_stat, race_distance, race_type):
        """Calculate current speed with distance-specific phase mechanics"""
        current_distance = self.uma_distances[uma_name]
        race_progress = current_distance / race_distance

        base_speed = uma_stat['base_speed']
        top_speed = uma_stat['top_speed']
        sprint_speed = uma_stat['sprint_speed']
        style_bonus = uma_stat['style_bonus']

        if race_type == 'Sprint':
            phases = {'start': (0.0, 0.2), 'mid': (0.2, 0.7), 'final': (0.7, 0.9), 'sprint': (0.9, 1.0)}
        elif race_type == 'Mile':
            phases = {'start': (0.0, 0.15), 'mid': (0.15, 0.6), 'final': (0.6, 0.85), 'sprint': (0.85, 1.0)}
        elif race_type == 'Medium':
            phases = {'start': (0.0, 0.1), 'mid': (0.1, 0.5), 'final': (0.5, 0.8), 'sprint': (0.8, 1.0)}
        else:
            phases = {'start': (0.0, 0.05), 'mid': (0.05, 0.4), 'final': (0.4, 0.7), 'sprint': (0.7, 1.0)}

        current_phase = 'start'
        for phase, (start, end) in phases.items():
            if start <= race_progress < end:
                current_phase = phase
                break

        if current_phase == 'start':
            target_speed = base_speed
        elif current_phase == 'mid':
            target_speed = top_speed
        elif current_phase == 'final':
            target_speed = top_speed * 1.02
        else:
            target_speed = sprint_speed

        if current_phase == 'start':
            if 'early_speed_bonus' in style_bonus:
                target_speed += target_speed * style_bonus['early_speed_bonus']
            if 'early_speed_penalty' in style_bonus:
                target_speed += target_speed * style_bonus['early_speed_penalty']
        elif current_phase == 'mid':
            if 'mid_speed_bonus' in style_bonus:
                target_speed += target_speed * style_bonus['mid_speed_bonus']
            if 'mid_speed_penalty' in style_bonus:
                target_speed += target_speed * style_bonus['mid_speed_penalty']
        elif current_phase == 'final' or current_phase == 'sprint':
            if 'final_speed_bonus' in style_bonus:
                target_speed += target_speed * style_bonus['final_speed_bonus']
            if 'final_speed_penalty' in style_bonus:
                target_speed += target_speed * style_bonus['final_speed_penalty']

        target_speed *= uma_stat['base_performance']
        
        # Stamina-based speed adjustments
        stamina_ratio = self.uma_stamina[uma_name] / 100.0
        if stamina_ratio > 0.8:
            # High stamina: slight boost
            target_speed *= 1.02
        elif stamina_ratio > 0.6:
            # Good stamina: normal speed
            target_speed *= 1.00
        elif stamina_ratio > 0.4:
            # Moderate stamina: slight penalty
            target_speed *= 0.98
        elif stamina_ratio > 0.2:
            # Low stamina: moderate penalty
            target_speed *= 0.95
        else:
            # Critical stamina: severe penalty
            target_speed *= 0.90
        
        fatigue_penalty = self.uma_fatigue[uma_name] * 0.04
        target_speed *= (1.0 - min(fatigue_penalty, 0.15))

        stamina_ratio = self.uma_stamina[uma_name] / 100.0
        guts_efficiency = uma_stat['guts'] / 1000.0
        effective_stamina = stamina_ratio * (0.7 + 0.3 * guts_efficiency)

        if effective_stamina < 0.1:
            target_speed *= 0.90
        elif effective_stamina < 0.3:
            target_speed *= 0.94
        elif effective_stamina < 0.5:
            target_speed *= 0.97
        elif effective_stamina < 0.7:
            target_speed *= 0.99

        self.update_fatigue_and_stamina(uma_name, uma_stat, race_progress, current_phase)

        variation = 1.0 + (random.random() * 0.04 - 0.02)
        target_speed *= variation

        return max(target_speed, base_speed * 0.85)

    def update_fatigue_and_stamina(self, uma_name, uma_stat, race_progress, current_phase):
        """Update fatigue and stamina with distance-specific mechanics"""
        fatigue_rates = {
            'Sprint': {'start': 0.0015, 'mid': 0.002, 'final': 0.003, 'sprint': 0.004},
            'Mile': {'start': 0.002, 'mid': 0.0025, 'final': 0.004, 'sprint': 0.005},
            'Medium': {'start': 0.0025, 'mid': 0.003, 'final': 0.004, 'sprint': 0.006},
            'Long': {'start': 0.003, 'mid': 0.004, 'final': 0.005, 'sprint': 0.007}
        }
        
        race_type = uma_stat['race_type']
        rates = fatigue_rates.get(race_type, fatigue_rates['Medium'])
        fatigue_rate = rates.get(current_phase, 0.003)
        
        # Base stamina bonus helps a lot (even 100 stamina helps)
        stamina_bonus = uma_stat['stamina'] / 500.0  # More generous scaling
        fatigue_rate *= max(0.3, 1.0 - stamina_bonus * 0.5)  # Minimum 30% fatigue rate
        
        self.uma_fatigue[uma_name] += fatigue_rate
        
        base_stamina_drain = 0.03  # Reduced from 0.08
        phase_multipliers = {'start': 0.6, 'mid': 0.8, 'final': 1.0, 'sprint': 1.2}  # Reduced
        stamina_depletion = base_stamina_drain * phase_multipliers.get(current_phase, 0.8)
        stamina_depletion += (self.uma_fatigue[uma_name] * 0.08)  # Reduced from 0.15
        
        # Guts reduces stamina drain significantly!
        guts_bonus = uma_stat['guts'] / 600.0  # Guts plays BIG role in stamina conservation
        stamina_depletion *= max(0.4, 1.0 - guts_bonus * 0.6)  # Minimum 40% drain with high Guts
        
        self.uma_stamina[uma_name] = max(0.0, self.uma_stamina[uma_name] - stamina_depletion)

    # === FUNGSI BARU: Mekanisme dueling ===
    def check_and_trigger_dueling(self, uma_stats, frame_positions, race_distance):
        """Check and trigger dueling mechanism during final spurt"""
        remaining_distance = race_distance - frame_positions[0][1]
        
        # Only trigger dueling when 400-1200 meters remaining
        if not (400 <= remaining_distance <= 1200):
            return
        
        # Check if dueling is already active
        if self.duel_active:
            # Check if duel should end (too close to finish or participants finished)
            if remaining_distance < 100 or not self.duel_participants:
                self.duel_active = False
                self.duel_participants.clear()
                self.append_output(f"[{self.sim_time:.1f}s] The duel has concluded!\n")
            return
        
        # Find potential duel participants (active umas that are close together)
        active_umas = [(name, dist) for name, dist in frame_positions 
                        if not self.uma_finished[name] and not self.uma_dnf[name]['dnf']]
        
        if len(active_umas) < 2:
            return
        
        # Group umas by proximity (within 5 meters of each other)
        duel_groups = []
        current_group = [active_umas[0]]
        
        for i in range(1, len(active_umas)):
            prev_name, prev_dist = active_umas[i-1]
            curr_name, curr_dist = active_umas[i]
            
            if abs(prev_dist - curr_dist) <= 5.0:
                current_group.append(active_umas[i])
            else:
                if len(current_group) >= 2:
                    duel_groups.append(current_group)
                current_group = [active_umas[i]]
        
        if len(current_group) >= 2:
            duel_groups.append(current_group)
        
        # Check for duel triggers based on guts and position
        for group in duel_groups:
            if len(group) >= 2:
                # Check if any uma in the group has high guts and wants to initiate duel
                for name, dist in group:
                    uma_stat = uma_stats[name]
                    guts_value = uma_stat['guts']
                    
                    # High guts umas are more likely to initiate duels
                    guts_chance = min(0.7, guts_value / 200.0)  # Up to 70% chance for high guts
                    
                    # Additional chance if uma is blocked or in middle of pack
                    position_idx = [frame_positions.index((n, d)) for n, d in frame_positions if n == name][0]
                    total_umas = len(frame_positions)
                    
                    # umas in middle positions are more likely to want to break out
                    position_factor = 1.0
                    if 0.3 <= (position_idx / total_umas) <= 0.7:
                        position_factor = 1.5
                    
                    final_chance = guts_chance * position_factor * 0.1  # 10% base chance
                    
                    if random.random() < final_chance and not self.duel_guts_used[name]:
                        # This uma initiates a duel!
                        self.duel_active = True
                        self.duel_start_time = self.sim_time
                        
                        # Add this uma and nearby umas to duel participants
                        for duel_name, duel_dist in group:
                            if duel_name not in self.duel_participants:
                                self.duel_participants.add(duel_name)
                        
                        # Apply duel bonuses based on guts
                        for participant in self.duel_participants:
                            participant_stat = uma_stats[participant]
                            participant_guts = participant_stat['guts']
                            
                            # Guts-based stamina boost (acts as backup stamina)
                            guts_stamina_boost = min(20.0, participant_guts / 10.0)  # Up to 20% stamina boost
                            
                            if not self.duel_stamina_boost_used[participant]:
                                self.uma_stamina[participant] = min(100.0, self.uma_stamina[participant] + guts_stamina_boost)
                                self.duel_stamina_boost_used[participant] = True
                                self.append_output(f"[{self.sim_time:.1f}s] {participant}'s guts provides {guts_stamina_boost:.1f}% stamina backup!\n")
                            
                            # Speed boost for high guts umas during duel
                            if participant_guts > 800:  # Very high guts
                                speed_boost = 0.15
                                self.uma_momentum[participant] += speed_boost
                                self.append_output(f"[{self.sim_time:.1f}s] {participant}'s incredible guts provides a speed surge!\n")
                            elif participant_guts > 600:  # High guts
                                speed_boost = 0.10
                                self.uma_momentum[participant] += speed_boost
                            elif participant_guts > 400:  # Medium guts
                                speed_boost = 0.05
                                self.uma_momentum[participant] += speed_boost
                        
                        self.duel_guts_used[name] = True
                        self.append_output(f"[{self.sim_time:.1f}s] {name} initiates a duel using their guts!\n")
                        return

    # === FUNGSI BARU: Komentar dueling ===
    def get_duel_commentary(self):
        """Generate commentary for dueling situations"""
        if not self.duel_active or self.duel_commentary_made:
            return ""
        
        participants = list(self.duel_participants)
        if len(participants) == 0:
            return ""
        
        self.duel_commentary_made = True
        
        if len(participants) == 2:
            commentary = random.choice(self.duel_commentary_lines)
            return commentary.format(name1=participants[0], name2=participants[1])
        elif len(participants) > 2:
            # For multi-uma duels, mention top 2
            if len(participants) >= 2:
                commentary = random.choice(self.duel_commentary_lines)
                return commentary.format(name1=participants[0], name2=participants[1])
            else:
                return random.choice(self.duel_multi_commentary_lines)
        
        return ""

    def get_enhanced_commentary(self, current_time, positions, race_distance, remaining_distance, incidents, finished):
        """Enhanced commentary system with dueling"""
        commentaries = []
        
        if not positions:
            return commentaries
            
        leader_name, leader_distance = positions[0]
        race_progress = leader_distance / race_distance
        
        # === BARU: Tambahkan komentar dueling ===
        duel_commentary = self.get_duel_commentary()
        if duel_commentary:
            commentaries.append(duel_commentary)
        
        distance_markers = [1800, 1600, 1400, 1200, 1000, 800, 600, 400, 200, 100, 50]
        for marker in distance_markers:
            if remaining_distance <= marker and marker not in self.distance_callouts_made:
                self.distance_callouts_made.add(marker)
                commentary = self.get_distance_callout(marker, leader_name, positions)
                if commentary:
                    commentaries.append(commentary)
                    break
        
        if self.sim_time - self.last_position_commentary > 3.0:
            recent_overtakes = [o for o in self.overtakes if o[3] > current_time - 3.0]
            if recent_overtakes:
                overtake = random.choice(recent_overtakes)
                commentary = self.get_overtake_commentary(overtake, positions)
                if commentary:
                    commentaries.append(commentary)
                    self.last_position_commentary = self.sim_time
        
        if incidents and self.sim_time - self.last_incident_commentary > 4.0:
            for name, incident_type in incidents.items():
                if incident_type:
                    commentary = self.get_incident_commentary(name, incident_type, positions)
                    if commentary:
                        commentaries.append(commentary)
                        self.last_incident_commentary = self.sim_time
                        break
        
        if not commentaries and self.sim_time - self.last_phase_commentary > 10.0:
            phase_commentary = self.get_phase_commentary(race_progress, leader_name, positions, remaining_distance)
            if phase_commentary:
                commentaries.append(phase_commentary)
                self.last_phase_commentary = self.sim_time
        
        if self.sim_time - self.last_speed_commentary > 5.0 and not commentaries:
            speed_commentary = self.get_speed_position_commentary(positions, race_distance)
            if speed_commentary:
                commentaries.append(speed_commentary)
                self.last_speed_commentary = self.sim_time
        
        finish_commentary = self.get_finish_commentary(finished, positions, race_progress)
        if finish_commentary:
            commentaries.append(finish_commentary)

        dnf_commentary = self.get_dnf_commentary(positions, race_progress)
        if dnf_commentary:
            commentaries.append(dnf_commentary)
        
        return commentaries[:2]

    def get_distance_callout(self, remaining, leader, positions):
        """Distance-specific callouts"""
        gate_num = self.gate_numbers.get(leader, "?")
        callouts = {
            1800: [f"{remaining}m to go! The number {gate_num} {leader} leads the pack!", f"We're at the {remaining} meter mark with the number {gate_num} {leader} in front!"],
            1600: [f"{remaining}m remaining! The field is tightening up!", f"At {remaining}m, the number {gate_num} {leader} maintains the advantage!"],
            1400: [f"{remaining}m to go! The race is heating up!", f"At {remaining}m, positioning becomes critical!"],
            1200: [f"{remaining}m remaining! Into the crucial phase!", f"The {remaining} meter mark! The number {gate_num} {leader} needs to hold on!"],
            1000: [f"The final {remaining} meters! The number {gate_num} {leader} leads the charge!", f"One thousand meters to go! This is where races are won!"],
            800: [f"{remaining}m to go! The home stretch approaches!", f"At {remaining}m, the number {gate_num} {leader} is fighting hard!"],
            600: [f"{remaining}m to the finish! The number {gate_num} {leader} is giving everything!", f"At {remaining}m! The final push is on!"],
            400: [f"Just {remaining}m remaining! The number {gate_num} {leader} is being hunted!", f"{remaining} meters to go! The finish line is in sight!"],
            200: [f"Only {remaining}m to go! The number {gate_num} {leader} is sprinting for glory!", f"{remaining} meters! The finish line beckons!"],
            100: [f"The final {remaining} meters! The number {gate_num} {leader} is so close!", f"Only {remaining}m left! The number {gate_num} {leader} is giving everything!"],
            50: [f"Just {remaining} meters! The number {gate_num} {leader} is almost there!", f"{remaining}m to the line! The number {gate_num} {leader} can see victory!"]
        }
        return random.choice(callouts.get(remaining, []))

    def get_overtake_commentary(self, overtake, positions):
        """Overtaking moment commentary"""
        name, old_pos, new_pos, time = overtake
        position_gained = old_pos - new_pos

        overtaken = []
        for pos_name, distance in positions:
            current_pos = positions.index((pos_name, distance)) + 1
            if current_pos == new_pos + 1 and pos_name != name:  # Exclude self-overtake
                overtaken.append(pos_name)

        overtaken_name = overtaken[0] if overtaken else "a rival"
        gate_num = self.gate_numbers.get(name, "?")
        overtaken_gate_num = self.gate_numbers.get(overtaken_name, "?") if overtaken_name != "a rival" else ""

        if overtaken_name == "a rival":
            overtaken_display = "a rival"
        else:
            overtaken_display = f"the number {overtaken_gate_num} {overtaken_name}"

        if position_gained == 1:
            lines = [f"The number {gate_num} {name} makes a bold move past {overtaken_display}!", f"And here comes the number {gate_num} {name}! Overtaking {overtaken_display}!"]
        elif position_gained == 2:
            lines = [f"Incredible! The number {gate_num} {name} jumps two positions!", f"The number {gate_num} {name} with a surge! Up two spots!"]
        else:
            lines = [f"Spectacular! The number {gate_num} {name} rockets from {old_pos}th to {new_pos}th!", f"The number {gate_num} {name} is on fire! Gaining {position_gained} positions!"]

        return random.choice(lines)

    def get_incident_commentary(self, name, incident_type, positions):
        """Incident commentary"""
        if incident_type == 'stumble':
            lines = [f"Oh no! {name} stumbles badly!", f"Disaster for {name}! A stumble at the worst possible time!"]
        elif incident_type == 'blocked':
            lines = [f"{name} gets blocked! No room to maneuver!", f"Traffic problems for {name}! Blocked in!"]
        else:
            lines = [f"{name} encounters trouble!", f"Problems for {name}!"]
        
        return random.choice(lines)

    def get_phase_commentary(self, race_progress, leader, positions, remaining):
        """Phase-based general commentary"""
        if race_progress < 0.1:
            lines = [f"And they're off! {leader} takes the early lead!", f"The gates open and {leader} breaks quickly!"]
        elif race_progress < 0.25:
            lines = [f"The early pace is strong!", f"{leader} settles into the lead with {remaining:.0f}m to go!"]
        elif race_progress < 0.5:
            if len(positions) > 1:
                second = positions[1][0]
                lines = [f"{leader} leads at the midway point!", f"{leader} and {second} are the main protagonists!"]
            else:
                lines = [f"{leader} continues to lead at halfway!"]
        elif race_progress < 0.75:
            lines = [f"Into the business end! {leader} still leads!", f"The race is getting serious! {leader} out front!"]
        elif race_progress < 0.9:
            lines = [f"{leader} is being pressed by challengers!", f"The final stretch! {leader} versus the chasers!"]
        else:
            lines = [f"The finish line looms! {leader} is straining!", f"Final meters! {leader} is giving everything!"]
        
        return random.choice(lines)

    def get_speed_position_commentary(self, positions, race_distance):
        """Commentary about speed and positions"""
        if len(positions) < 2:
            return ""
        
        leader = positions[0][0]
        second = positions[1][0]
        gap = positions[0][1] - positions[1][1]
        
        if gap < 1.0:
            lines = [f"{leader} and {second} are virtually inseparable!", f"Nothing between {leader} and {second}!"]
        elif gap < 3.0:
            lines = [f"{leader} has a narrow lead over {second}!", f"{second} is within striking distance!"]
        else:
            lines = [f"{leader} is pulling away! {gap:.1f}m clear!", f"{leader} has established a commanding lead!"]
        
        return random.choice(lines)

    def get_finish_commentary(self, finished, positions, race_progress):
        """Commentary for umas crossing the finish line"""
        if not finished or race_progress < 0.85:
            return ""

        newly_finished = [name for name in finished if name not in self.finish_commented]

        if not newly_finished:
            return ""

        name = newly_finished[0]
        finished_sorted = sorted(finished, key=lambda x: self.finish_times[x])
        finish_position = finished_sorted.index(name) + 1

        self.finish_commented.add(name)

        if finish_position == 1:
            lines = [f"{name} crosses the line! Victory!", f"And {name} wins it!", f"{name} victorious!"]
        elif finish_position == 2:
            lines = [f"{name} finishes second!", f"{name} takes second place!"]
        elif finish_position == 3:
            lines = [f"{name} claims third!", f"Third for {name}!"]
        else:
            lines = [f"{name} crosses in {finish_position}th!", f"{name} finishes {finish_position}th!"]

        return random.choice(lines)

    def get_dnf_commentary(self, positions, race_progress):
        """Commentary for umas that DNF"""
        if self.sim_time - self.last_dnf_commentary < 5.0:
            return ""

        newly_dnf = [name for name, dnf_data in self.uma_dnf.items()
                    if dnf_data['dnf'] and name not in self.dnf_commented]

        if not newly_dnf:
            return ""

        name = newly_dnf[0]
        reason = self.uma_dnf[name]['reason']
        dnf_distance = self.uma_dnf[name]['dnf_distance']

        self.dnf_commented.add(name)
        self.last_dnf_commentary = self.sim_time

        if "exhaustion" in reason:
            lines = [f"{name} is exhausted and drops out!", f"{name} can't continue - exhaustion!", f"{name} fades away due to exhaustion!"]
        elif "loss of will" in reason:
            lines = [f"{name} loses the will to continue!", f"{name} gives up the fight!", f"{name} succumbs to the pressure!"]
        elif "unsuitable distance" in reason:
            lines = [f"{name} is out of their comfort zone!", f"{name} struggles with the distance!", f"{name} can't handle this race length!"]
        elif "unsuitable surface" in reason:
            lines = [f"{name} doesn't like this surface!", f"{name} is uncomfortable on this ground!", f"{name} can't adapt to the surface!"]
        else:
            lines = [f"{name} has to drop out!", f"{name} is forced to retire!", f"{name} can't continue!"]

        return random.choice(lines)
    
    def update_positions_sidebar(self, frame_positions):
        """Update the F1-style positions sidebar with current race standings"""
        self.positions_list.clear()
        
        if not frame_positions:
            return
        
        # Separate finished, DNF, and still-racing participants
        finished_umas = []
        racing_umas = []
        dnf_umas = []
        
        for name, distance in frame_positions:
            if self.uma_finished.get(name, False):
                finish_time = self.finish_times.get(name, float('inf'))
                finished_umas.append((name, distance, finish_time))
            elif self.uma_dnf.get(name, {}).get('dnf', False):
                dnf_umas.append((name, distance))
            else:
                racing_umas.append((name, distance))
        
        # Sort finished umas by finish time (fastest first)
        finished_umas.sort(key=lambda x: x[2])
        
        # Sort racing umas by distance (furthest first)  
        racing_umas.sort(key=lambda x: x[1], reverse=True)
        
        # Combine: finished first (by time), then racing (by distance), then DNF
        sorted_positions = []
        for name, distance, _ in finished_umas:
            sorted_positions.append((name, distance))
        for name, distance in racing_umas:
            sorted_positions.append((name, distance))
        for name, distance in dnf_umas:
            sorted_positions.append((name, distance))
        
        # Calculate leader distance (for gap calculation of racing umas)
        # Leader is either the last finished uma's distance or the furthest racing uma
        if racing_umas:
            leader_distance = racing_umas[0][1]
        elif sorted_positions:
            leader_distance = sorted_positions[0][1]
        else:
            leader_distance = 0
        
        # Get winner time for finished gap calculation
        winner_time = finished_umas[0][2] if finished_umas else None
        
        for i, (name, distance) in enumerate(sorted_positions):
            position = i + 1
            gate = self.gate_numbers.get(name, '?')
            color = self.uma_colors.get(name, '#ffffff')
            
            # Calculate gap
            gap_text = ""
            status = ""
            
            if self.uma_finished.get(name, False):
                status = " 🏁"
                # Show time gap from winner
                if winner_time is not None:
                    finish_time = self.finish_times.get(name, 0)
                    time_gap = finish_time - winner_time
                    if time_gap > 0:
                        gap_text = f" +{time_gap:.2f}s"
            elif self.uma_dnf.get(name, {}).get('dnf', False):
                status = " ❌"
                gap_text = " DNF"
            else:
                # Still racing - show distance gap from leader
                gap_meters = leader_distance - distance
                if gap_meters <= 0:
                    gap_text = ""
                elif gap_meters < 2.4:
                    gap_text = f" +{gap_meters:.1f}m"
                else:
                    lengths = gap_meters / 2.4
                    gap_text = f" +{lengths:.1f}L"
                
                # Status indicators for racing umas
                if name in getattr(self, 'duel_participants', set()):
                    status = " 🔥"
                elif name in getattr(self, 'rushing_participants', set()):
                    status = " ⚡"
                elif name in getattr(self, 'temptation_participants', set()):
                    status = " 😤"
                elif name in getattr(self, 'skill_active_participants', set()):
                    status = " ✨"
            
            # Format: "1: Name (G5) +2.3L 🏁"
            item_text = f"{position:2d}: {name} (G{gate}){gap_text}{status}"
            
            item = QListWidgetItem(item_text)
            item.setForeground(QColor(color))
            
            # Highlight top 3
            if position == 1:
                item.setBackground(QColor(255, 215, 0, 40))  # Gold tint
            elif position == 2:
                item.setBackground(QColor(192, 192, 192, 40))  # Silver tint  
            elif position == 3:
                item.setBackground(QColor(205, 127, 50, 40))  # Bronze tint
            
            self.positions_list.addItem(item)
    
    def update_display(self, frame_positions, race_distance):
        """Update display - update the canvas widget"""
        if not self.sim_data:
            return
        
        # Update the canvas widget with new data
        self.race_canvas.update_display(
            self.sim_data, 
            self.uma_distances, 
            self.uma_finished,
            self.uma_dnf,
            self.uma_incidents,
            self.uma_colors,
            self.gate_numbers,
            self.track_margin,
            duel_participants=getattr(self, 'duel_participants', set()),
            rushing_participants=getattr(self, 'rushing_participants', set()),
            temptation_participants=getattr(self, 'temptation_participants', set()),
            spot_struggle_participants=getattr(self, 'spot_struggle_participants', set()),
            skill_active_participants=getattr(self, 'skill_active_participants', set())
        )
        
        # Update F1-style positions sidebar
        self.update_positions_sidebar(frame_positions)
        
        # Update status labels
        if frame_positions:
            leader_dist = frame_positions[0][1]
            remaining = max(0, race_distance - leader_dist)
            
            leader_name = frame_positions[0][0]
            # Get speed from engine state if available
            if self.race_engine and leader_name in self.race_engine.uma_states:
                current_speed = self.race_engine.uma_states[leader_name].current_speed
            else:
                uma_stat = self.sim_data['uma_stats'][leader_name]
                current_speed = self.calculate_current_speed(leader_name, uma_stat, race_distance, self.sim_data['race_type'])
            speed_kmh = current_speed * 3.6
            
            # Display status including dueling and final spurt
            status_text = f"Remaining: {remaining:.0f}m | Lead: {speed_kmh:.1f} km/h"
            if self.duel_active:
                status_text += " | DUEL ACTIVE!"
            self.remaining_label.setText(status_text)

    def stop_simulation(self):
        """Stop the simulation"""
        self.sim_running = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.append_output("Simulation stopped.\n")

    def reset_simulation(self):
        """Reset the simulation"""
        self.stop_simulation()
        
        # Reset race engine
        if self.race_engine:
            self.race_engine.reset()
        
        self.sim_time = 0.0
        self.finish_times.clear()
        self.incidents_occurred.clear()
        self.overtakes.clear()
        self.last_commentary_time = 0
        self.previous_positions.clear()
        
        self.uma_distances.clear()
        self.uma_finished.clear()
        self.uma_incidents.clear()
        self.current_positions.clear()
        self.uma_fatigue.clear()
        self.uma_momentum.clear()
        self.uma_last_position.clear()
        self.uma_stamina.clear()
        self.uma_dnf.clear()
        
        # Reset dueling variables
        self.duel_active = False
        self.duel_participants.clear()
        self.duel_start_time = 0
        self.duel_commentary_made = False
        self.duel_guts_used.clear()
        self.duel_stamina_boost_used.clear()
        
        self.distance_callouts_made.clear()
        self.last_incident_commentary = 0
        self.last_position_commentary = 0
        self.last_phase_commentary = 0
        self.last_speed_commentary = 0
        self.commentary_history.clear()
        
        self.output_text.clear()
        self.remaining_label.setText("Remaining: -- | Lead: -- km/h")
        
        if self.sim_data:
            self.initialize_uma_icons()
        
        # === BARU: Hapus penanda jarak saat reset ===
        self.distance_markers_drawn.clear()
        
        self.draw_track()
        self.append_output("Simulation reset.\n")

    def display_final_results(self):
        """Display final race results with traditional horse racing margins"""
        if not self.finish_times and not any(dnf['dnf'] for dnf in self.uma_dnf.values()):
            self.append_output("No results to display.\n")
            return
        
        # Update sidebar with final standings (sorted by finish time)
        final_positions = []
        finished = [(name, time) for name, time in self.finish_times.items()]
        finished.sort(key=lambda x: x[1])
        for name, _ in finished:
            final_positions.append((name, self.uma_distances.get(name, 0)))
        # Add DNF umas at the end
        for name in self.uma_distances.keys():
            if name not in self.finish_times and self.uma_dnf.get(name, {}).get('dnf', False):
                final_positions.append((name, self.uma_distances.get(name, 0)))
        self.update_positions_sidebar(final_positions)
            
        self.append_output("\n" + "="*60 + "\n")
        self.append_output("FINAL RACE RESULTS\n")
        self.append_output("="*60 + "\n")
        
        # Calculate average speed for margin conversion
        avg_speed = 17.0  # Default
        if self.race_engine:
            avg_speed = self.race_engine.base_speed
        
        # Use engine's get_final_results if available
        if self.race_engine:
            results = self.race_engine.get_final_results()
            winner_time = None
            prev_time = None
            
            for pos, name, time_or_dist, status in results:
                gate_num = self.gate_numbers.get(name, "?")
                
                if status == "FIN":
                    # Track winner time for margins
                    if winner_time is None:
                        winner_time = time_or_dist
                        prev_time = time_or_dist
                        self.append_output(f"{pos:2d}. [{gate_num:>2}] {name:20s}  {time_or_dist:7.2f}s\n")
                    else:
                        # Calculate margin from previous horse
                        margin_from_prev = time_gap_to_margin(time_or_dist - prev_time, avg_speed)
                        prev_time = time_or_dist
                        self.append_output(f"{pos:2d}. [{gate_num:>2}] {name:20s}  {time_or_dist:7.2f}s  [{margin_from_prev}]\n")
                else:
                    self.append_output(f"{pos:2d}. [{gate_num:>2}] {name:20s}  {status} at {time_or_dist:.0f}m\n")
        else:
            # Legacy fallback
            finished_umas = sorted(self.finish_times.items(), key=lambda x: x[1])
            prev_time = None
            for i, (name, time) in enumerate(finished_umas):
                gate_num = self.gate_numbers.get(name, "?")
                if prev_time is None:
                    self.append_output(f"{i+1:2d}. [{gate_num:>2}] {name:20s}  {time:7.2f}s\n")
                else:
                    margin = time_gap_to_margin(time - prev_time, avg_speed)
                    self.append_output(f"{i+1:2d}. [{gate_num:>2}] {name:20s}  {time:7.2f}s  [{margin}]\n")
                prev_time = time
        
        dnf_umas = [(name, dnf_data) for name, dnf_data in self.uma_dnf.items() if dnf_data.get('dnf', False)]
        if dnf_umas:
            self.append_output("\nDNF (Did Not Finish):\n")
            for name, dnf_data in dnf_umas:
                gate_num = self.gate_numbers.get(name, "?")
                self.append_output(f"- [{gate_num}] {name} (DNF at {dnf_data['dnf_distance']:.0f}m - {dnf_data['reason']})\n")
        
        total_starters = len(self.uma_icons)
        total_finished = len(self.finish_times)
        total_dnf = len(dnf_umas)
        
        if self.finish_times:
            finished_umas = sorted(self.finish_times.items(), key=lambda x: x[1])
            winning_time = finished_umas[0][1]
            if len(finished_umas) > 1:
                time_gap = finished_umas[-1][1] - winning_time
            else:
                time_gap = 0.0
        else:
            winning_time = 0.0
            time_gap = 0.0
        
        self.append_output(f"\nSUMMARY: {total_finished}/{total_starters} finished, {total_dnf} DNF\n")
        if self.finish_times:
            self.append_output(f"Winning time: {winning_time:.2f}s\n")
            if len(finished_umas) > 1:
                # Show margin in lengths for total gap
                total_margin = time_gap_to_margin(time_gap, avg_speed if self.race_engine else 17.0)
                self.append_output(f"Gap (1st to last): {time_gap:.2f}s ({total_margin})\n")
        self.append_output("="*60 + "\n")

    def show_stat_priorities(self):
        """Display stat priorities for each running style"""
        self.output_text.clear()
        self.append_output("UMA MUSUME STAT PRIORITIES BY RUNNING STYLE\n")
        self.append_output("="*50 + "\n\n")

        priorities = {
            'FR (Front Runner)': ['Speed', 'Wisdom', 'Power', 'Guts', 'Stamina'],
            'PC (Pace Chaser)': ['Speed', 'Power', 'Wisdom', 'Guts', 'Stamina'],
            'LS (Late Surger)': ['Speed', 'Power', 'Wisdom', 'Stamina', 'Guts'],
            'EC (End Closer)': ['Speed', 'Power', 'Wisdom', 'Stamina', 'Guts']
        }

        style_descriptions = {
            'FR (Front Runner)': {
                'role': 'Leads the race from the start',
                'needs': 'High Speed to stay ahead, Wisdom for skill timing and cornering',
                'lacking': 'Low Speed → gets overtaken early; Low Wisdom → poor pacing, late skill triggers, risk of burnout'
            },
            'PC (Pace Chaser)': {
                'role': 'Stays behind FR, ready to surge mid-race',
                'needs': 'High Speed and Power for mid-race acceleration',
                'lacking': 'Low Power → can\'t catch up during middle phase; Low Speed → falls behind FR and can\'t contest lead'
            },
            'LS (Late Surger)': {
                'role': 'Holds back early, surges in final stretch',
                'needs': 'High Speed, Power, and decent Wisdom',
                'lacking': 'Low Power → weak final burst; Low Wisdom → poor positioning, blocked during surge'
            },
            'EC (End Closer)': {
                'role': 'Stays at the back, launches powerful last-minute sprint',
                'needs': 'High Speed, Power, and enough Stamina to survive',
                'lacking': 'Low Stamina → burns out before final phase; Low Power → can\'t accelerate fast enough to close gap'
            }
        }

        for style, stats in priorities.items():
            desc = style_descriptions.get(style, {})
            self.append_output(f"{style}:\n")
            self.append_output(f"  Role: {desc.get('role', '')}\n")
            self.append_output(f"  Key Stats: {desc.get('needs', '')}\n")
            self.append_output("  Priorities:\n")
            for i, stat in enumerate(stats):
                if i < 3:
                    self.append_output(f"    {i+1}. {stat} (VITAL)\n")
                else:
                    self.append_output(f"    {i+1}. {stat}\n")
            self.append_output(f"  If lacking: {desc.get('lacking', '')}\n")
            self.append_output("\n")

        self.append_output("NOTE: Top 3 stats are vital - lacking any can severely decrease performance.\n")
        self.append_output("Guts plays a special role in duels - high Guts umas can use it as stamina backup\n")
        self.append_output("during last spurt duels (around 400-1200 meters remaining) and break from crowded packs.\n")
        self.append_output("These priorities are now applied to simulation calculations for realistic performance.\n")

    def append_output(self, text):
        """Append text to output area"""
        self.output_text.append(text.rstrip('\n'))


if __name__ == "__main__":
    app = QApplication([])
    window = UmaRacingGUI()
    window.show()
    app.exec()