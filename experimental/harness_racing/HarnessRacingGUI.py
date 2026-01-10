"""
Harness Racing GUI - European Harness Racing Simulation Interface

Enhanced with live race visualization:
- Curved track rendering based on real European harness track layouts
- Live position tracking with F1-style sidebar
- Dynamic commentary system for harness racing events
- Visual indicators for gait breaks, stamina, sulky positioning
- Traditional harness racing margin notation
"""

import sys
import json
import os
import math
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Optional

# Try to import GUI framework (PySide6 preferred, fallback to tkinter)
try:
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
        QPushButton, QLabel, QComboBox, QSpinBox, QCheckBox, QTableWidget, 
        QTableWidgetItem, QMessageBox, QProgressBar, QTextEdit, QLineEdit,
        QFormLayout, QGroupBox, QDoubleSpinBox, QSplitter, QListWidget
    )
    from PySide6.QtCore import Qt, QTimer, Signal, QObject, QPointF, QRectF
    from PySide6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QPainterPath, QPalette
    USE_PYSIDE6 = True
except ImportError:
    USE_PYSIDE6 = False
    print("PySide6 not available, GUI features limited")

from HarnessConfigGenerator import HarnessHorseGenerator, HarnessConfigManager, HarnessHorseProfile
from harness_races import MAJOR_HARNESS_RACES, YOUTH_RACES, ALL_HARNESS_RACES, HARNESS_TRACK_LAYOUTS
from harness_engine import HarnessRaceEngine, SulkyConfiguration, HarnessHorseState
from hybrid_engine import HybridRaceEngine, RacingMode
from harness_commentary import HarnessCommentaryGenerator


from HarnessConfigGenerator import HarnessHorseGenerator, HarnessConfigManager, HarnessHorseProfile
from harness_races import MAJOR_HARNESS_RACES, YOUTH_RACES, ALL_HARNESS_RACES, HARNESS_TRACK_LAYOUTS
from harness_engine import HarnessRaceEngine, SulkyConfiguration, HarnessHorseState
from hybrid_engine import HybridRaceEngine, RacingMode
from harness_commentary import HarnessCommentaryGenerator


class HarnessRaceCanvasWidget(QWidget):
    """
    Canvas widget for drawing curved harness racing track with live race positions
    Adapted from UmaRacingGUI's RaceCanvasWidget for harness-specific features
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        
        # Track configuration
        self.track_path = None
        self.track_length = 0
        self.track_direction = "Left"  # Counter-clockwise (European standard)
        self.width_ratio = 1.7  # Oval elongation
        self.corner_tightness = 0.70  # Harness tracks have tighter corners
        
        # Horse positions on track
        self.horse_positions = []  # List of (horse_id, distance, state)
        self.finished_horses = set()
        
        # Visual settings
        self.track_color = QColor(139, 90, 43)  # Dirt track brown
        self.grass_color = QColor(34, 139, 34)  # Infield grass
        self.finish_line_color = QColor(255, 255, 255)
        
        # Gate colors for horse identification
        self.gate_colors = [
            QColor(255, 0, 0),      # 1: Red
            QColor(0, 0, 255),      # 2: Blue
            QColor(255, 255, 0),    # 3: Yellow
            QColor(0, 255, 0),      # 4: Green
            QColor(255, 165, 0),    # 5: Orange
            QColor(128, 0, 128),    # 6: Purple
            QColor(0, 255, 255),    # 7: Cyan
            QColor(255, 192, 203),  # 8: Pink
            QColor(165, 42, 42),    # 9: Brown
            QColor(128, 128, 128),  # 10: Gray
        ]
        
    def set_track_layout(self, track_name: str):
        """Set track layout based on harness track data"""
        layout = HARNESS_TRACK_LAYOUTS.get(track_name, {})
        
        self.track_direction = layout.get("direction", "Left")
        self.width_ratio = layout.get("width_ratio", 1.7)
        self.corner_tightness = layout.get("corner_tightness", 0.70)
        
        # Generate track path
        self.generate_track_path()
    
    def generate_track_path(self):
        """Generate curved track path as QPainterPath - proper oval shape"""
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # Calculate oval dimensions
        margin = 50
        oval_width = (self.width() - margin * 2) * 0.9
        oval_height = oval_width / self.width_ratio
        
        # Create proper oval track using addEllipse
        path = QPainterPath()
        
        # Draw oval centered in widget
        rect = QRectF(
            center_x - oval_width / 2,
            center_y - oval_height / 2,
            oval_width,
            oval_height
        )
        path.addEllipse(rect)
        
        self.track_path = path
        self.track_length = path.length()
        self.race_distance = 2100  # Store for position calculations
    
    def update_positions(self, positions: List[Tuple[str, float, HarnessHorseState]]):
        """Update horse positions for rendering"""
        self.horse_positions = positions
        self.update()  # Trigger repaint
    
    def set_race_distance(self, distance: int):
        """Set the race distance for position calculations"""
        self.race_distance = distance
    
    def get_position_on_track(self, distance: float, race_distance: float) -> QPointF:
        """Get (x, y) coordinates for horse at given distance"""
        if not self.track_path or self.track_length == 0:
            return QPointF(self.width()/2, self.height()/2)
        
        # Calculate percentage along track
        percent = (distance % race_distance) / race_distance
        
        # Get point along path
        point_percent = min(0.99, max(0.01, percent))
        point = self.track_path.pointAtPercent(point_percent)
        
        return point
    
    def paintEvent(self, event):
        """Draw the race track and horse positions"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Fill background (grass)
        painter.fillRect(self.rect(), self.grass_color)
        
        # Draw track if generated
        if not self.track_path:
            self.generate_track_path()
        
        if self.track_path:
            # Draw dirt track
            painter.setPen(QPen(QColor(80, 50, 20), 3))
            painter.setBrush(QBrush(self.track_color))
            painter.drawPath(self.track_path)
            
            # Draw finish line (at starting position)
            finish_point = self.track_path.pointAtPercent(0.0)
            painter.setPen(QPen(self.finish_line_color, 4))
            painter.drawLine(
                int(finish_point.x() - 20), int(finish_point.y()),
                int(finish_point.x() + 20), int(finish_point.y())
            )
            
            # Draw horses and sulkies
            for idx, (horse_id, distance, state) in enumerate(self.horse_positions):
                gate_number = idx + 1
                color = self.gate_colors[idx % len(self.gate_colors)]
                
                # Get position - use stored race distance
                race_dist = getattr(self, 'race_distance', 2100)
                pos = self.get_position_on_track(distance, race_dist)
                
                # Draw sulky (cart behind horse)
                sulky_offset = -8
                painter.setPen(QPen(QColor(50, 50, 50), 2))
                painter.setBrush(QBrush(QColor(100, 100, 100)))
                painter.drawEllipse(
                    int(pos.x() + sulky_offset - 6), int(pos.y() - 4),
                    12, 8
                )
                
                # Draw horse
                if state and state.is_breaking_gait:
                    # Gait break: red pulsing circle
                    painter.setPen(QPen(QColor(255, 0, 0), 3))
                    painter.setBrush(QBrush(QColor(255, 100, 100, 150)))
                else:
                    painter.setPen(QPen(QColor(0, 0, 0), 2))
                    painter.setBrush(QBrush(color))
                
                painter.drawEllipse(
                    int(pos.x() - 8), int(pos.y() - 8),
                    16, 16
                )
                
                # Draw gate number
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.setFont(QFont("Arial", 10, QFont.Bold))
                painter.drawText(
                    int(pos.x() - 4), int(pos.y() + 4),
                    str(gate_number)
                )
                
                # Draw finish indicator
                if horse_id in self.finished_horses:
                    painter.setPen(QPen(QColor(0, 255, 0), 2))
                    painter.drawText(
                        int(pos.x() + 15), int(pos.y() + 4),
                        "✓"
                    )


class HarnessRaceSimulator:
    """
    Backend simulator for harness racing
    Manages configuration, race execution, and result tracking
    Enhanced with live position tracking and commentary generation
    """
    
    def __init__(self):
        self.horses: dict = {}
        self.selected_race = None
        self.race_results = []
        self.engine = None  # Created when race starts
        self.commentary_generator = HarnessCommentaryGenerator()
        
        # Live tracking
        self.is_running = False
        self.current_positions = []
        self.finished_horses = set()
        self.race_commentary = []
    
    def add_horse(self, horse_profile: HarnessHorseProfile):
        """Add a horse to the racing setup"""
        self.horses[horse_profile.id] = horse_profile
    
    def clear_horses(self):
        """Clear all horses"""
        self.horses = {}
        self.current_positions = []
        self.finished_horses = set()
    
    def select_race(self, race_name: str):
        """Select a race by name"""
        for race_id, race in ALL_HARNESS_RACES.items():
            if race.name == race_name:
                self.selected_race = race
                return True
        return False
    
    def setup_race(self):
        """Setup race engine for simulation"""
        if not self.horses:
            raise ValueError("No horses configured")
        if not self.selected_race:
            raise ValueError("No race selected")
        
        # Convert horse profiles to (id, stats) tuples for engine
        horses_for_engine = [
            (horse_id, profile.stats) 
            for horse_id, profile in self.horses.items()
        ]
        
        # Create new engine instance
        self.engine = HarnessRaceEngine(self.selected_race, horses_for_engine)
        
        # Reset tracking
        self.is_running = False
        self.current_positions = []
        self.finished_horses = set()
        self.race_commentary = []
        self.commentary_generator.reset()
    
    def step_simulation(self) -> bool:
        """
        Advance race simulation by one step (0.1s)
        Returns True if race is still running, False if finished
        """
        if not self.engine:
            return False
        
        # Run one simulation lap
        self.engine.simulate_lap()
        
        # Update positions
        self.update_current_positions()
        
        # Generate commentary
        self.generate_commentary()
        
        # Check if race is complete
        return not self.engine.is_finished
    
    def update_current_positions(self):
        """Update current horse positions from engine state"""
        positions = []
        
        # Get all horse states sorted by distance
        for horse_id, state in self.engine.horse_states.items():
            positions.append((horse_id, state.distance_covered, state))
            
            # Track finished horses
            if hasattr(state, 'is_finished') and state.is_finished:
                self.finished_horses.add(horse_id)
        
        # Sort by distance (descending)
        positions.sort(key=lambda x: x[1], reverse=True)
        self.current_positions = positions
    
    def generate_commentary(self):
        """Generate race commentary based on current state"""
        if not self.engine or not self.current_positions:
            return
        
        # Prepare positions for commentary - use horse NAMES not IDs
        positions_list = [
            (self.horses[horse_id].name if horse_id in self.horses else horse_id, distance) 
            for horse_id, distance, _ in self.current_positions
        ]
        
        # Detect incidents (gait breaks) - use horse names
        incidents = {}
        for horse_id, _, state in self.current_positions:
            if hasattr(state, 'is_breaking_gait') and state.is_breaking_gait:
                horse_name = self.horses[horse_id].name if horse_id in self.horses else horse_id
                incidents[horse_name] = 'gait_break'
        
        # Generate commentary - convert finished horse IDs to names
        finished_names = set()
        for hid in self.finished_horses:
            if hid in self.horses:
                finished_names.add(self.horses[hid].name)
            else:
                finished_names.add(hid)
        
        commentary_lines = self.commentary_generator.get_commentary(
            current_time=self.engine.elapsed_time,
            positions=positions_list,
            race_distance=self.selected_race.distance,
            incidents=incidents if incidents else None,
            finished=finished_names if finished_names else None
        )
        
        # Add to history
        for line in commentary_lines:
            timestamp = f"[{self.engine.elapsed_time:.1f}s]"
            self.race_commentary.append(f"{timestamp} {line}")
    
    def run_race(self):
        """Execute the complete race simulation (non-live)"""
        self.setup_race()
        
        # Run race to completion
        while self.step_simulation():
            pass
        
        # Get final results
        results = self.engine.race_result
        self.race_results = results
        
        return self.get_summary()
    
    def get_summary(self):
        """Get race summary"""
        return {
            "race_name": self.selected_race.name if self.selected_race else "Unknown",
            "distance": self.selected_race.distance if self.selected_race else 0,
            "results": self.race_results if self.race_results else []
        }
    
    def save_results(self, filename: str = None):
        """Save race results to JSON"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"harness_race_results_{timestamp}.json"
        
        results = {
            "race_name": self.selected_race.name if self.selected_race else "Unknown",
            "timestamp": datetime.now().isoformat(),
            "horses": {
                horse_id: {
                    "name": profile.name,
                    "stats": {
                        "pulling_power": profile.stats.pulling_power,
                        "endurance": profile.stats.endurance,
                        "gait_consistency": profile.stats.gait_consistency,
                        "heat_recovery": profile.stats.heat_recovery,
                        "start_acceleration": profile.stats.start_acceleration,
                        "temperament": profile.stats.temperament,
                        "sulky_tolerance": profile.stats.sulky_tolerance,
                    }
                }
                for horse_id, profile in self.horses.items()
            },
            "results": self.race_results,
            "commentary": self.race_commentary[-30:] if self.race_commentary else []
        }
        
        # Create results directory if it doesn't exist
        os.makedirs("results", exist_ok=True)
        filepath = os.path.join("results", filename)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2)
        
        return filepath


if USE_PYSIDE6:
    class HarnessRacingGUI(QMainWindow):
        """
        Harness Racing GUI - Main Application Window
        
        Tabs:
            1. Horse Configuration - Setup harness racing horses
            2. Race Selection - Choose harness race
            3. Simulation - Run race with live updates
            4. Results - View and save results
        """
        
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Harness Racing Simulator - European Edition")
            self.setGeometry(100, 100, 1200, 800)
            
            # Initialize simulator
            self.simulator = HarnessRaceSimulator()
            self.config_manager = HarnessConfigManager()
            self.horse_generator = HarnessHorseGenerator()
            
            # Create UI
            self.init_ui()
        
        def init_ui(self):
            """Initialize user interface"""
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            layout = QVBoxLayout()
            
            # Create tab widget
            tabs = QTabWidget()
            
            # Tab 1: Horse Configuration
            tabs.addTab(self.create_horse_config_tab(), "Horse Configuration")
            
            # Tab 2: Race Selection
            tabs.addTab(self.create_race_selection_tab(), "Race Selection")
            
            # Tab 3: Simulation
            tabs.addTab(self.create_simulation_tab(), "Simulation")
            
            # Tab 4: Results
            tabs.addTab(self.create_results_tab(), "Results")
            
            layout.addWidget(tabs)
            central_widget.setLayout(layout)
        
        def create_horse_config_tab(self) -> QWidget:
            """Create horse configuration tab"""
            widget = QWidget()
            layout = QVBoxLayout()
            
            # Horse generation controls
            controls = QGroupBox("Generate Harness Horses")
            controls_layout = QFormLayout()
            
            self.horse_count_spin = QSpinBox()
            self.horse_count_spin.setValue(3)
            self.horse_count_spin.setMinimum(1)
            self.horse_count_spin.setMaximum(10)
            controls_layout.addRow("Number of Horses:", self.horse_count_spin)
            
            generate_btn = QPushButton("Generate Random Stable")
            generate_btn.clicked.connect(self.generate_random_stable)
            controls_layout.addRow(generate_btn)
            
            controls.setLayout(controls_layout)
            layout.addWidget(controls)
            
            # Horse list
            horses_group = QGroupBox("Harness Racing Stable")
            horses_layout = QVBoxLayout()
            
            self.horses_table = QTableWidget()
            self.horses_table.setColumnCount(8)
            self.horses_table.setHorizontalHeaderLabels([
                "Name", "Age", "Pulling Power", "Endurance", "Gait Const.", 
                "Heat Rec.", "Start Accel.", "Sulky Tol."
            ])
            self.horses_table.resizeColumnsToContents()
            horses_layout.addWidget(self.horses_table)
            
            clear_btn = QPushButton("Clear Stable")
            clear_btn.clicked.connect(self.clear_horses)
            horses_layout.addWidget(clear_btn)
            
            horses_group.setLayout(horses_layout)
            layout.addWidget(horses_group)
            
            widget.setLayout(layout)
            return widget
        
        def create_race_selection_tab(self) -> QWidget:
            """Create race selection tab"""
            widget = QWidget()
            layout = QVBoxLayout()
            
            # Race selection
            race_group = QGroupBox("Select Harness Race")
            race_layout = QFormLayout()
            
            self.race_combo = QComboBox()
            for race_id, race in ALL_HARNESS_RACES.items():
                self.race_combo.addItem(f"{race.name} ({race.distance}m)", race.name)
            
            race_layout.addRow("Race:", self.race_combo)
            race_group.setLayout(race_layout)
            layout.addWidget(race_group)
            
            # Race information
            info_group = QGroupBox("Race Information")
            info_layout = QVBoxLayout()
            
            self.race_info_text = QTextEdit()
            self.race_info_text.setReadOnly(True)
            info_layout.addWidget(self.race_info_text)
            
            info_group.setLayout(info_layout)
            layout.addWidget(info_group)
            
            self.race_combo.currentIndexChanged.connect(self.update_race_info)
            self.update_race_info()
            
            widget.setLayout(layout)
            return widget
        
        def create_simulation_tab(self) -> QWidget:
            """Create simulation/race execution tab with live visualization"""
            widget = QWidget()
            layout = QVBoxLayout()
            
            # Control buttons
            button_layout = QHBoxLayout()
            
            self.run_race_btn = QPushButton("Run Race (Live)")
            self.run_race_btn.clicked.connect(self.run_race_live)
            button_layout.addWidget(self.run_race_btn)
            
            self.run_race_instant_btn = QPushButton("Run Race (Instant)")
            self.run_race_instant_btn.clicked.connect(self.run_race_instant)
            button_layout.addWidget(self.run_race_instant_btn)
            
            button_layout.addStretch()
            layout.addLayout(button_layout)
            
            # Progress
            self.progress_bar = QProgressBar()
            self.progress_bar.setValue(0)
            layout.addWidget(self.progress_bar)
            
            # Main race display: splitter with canvas and positions
            race_splitter = QSplitter(Qt.Horizontal)
            
            # Left: Race canvas with curved track
            self.race_canvas = HarnessRaceCanvasWidget()
            race_splitter.addWidget(self.race_canvas)
            
            # Right: Live positions and commentary
            right_panel = QWidget()
            right_layout = QVBoxLayout()
            
            # Positions list
            positions_label = QLabel("Live Positions:")
            positions_label.setFont(QFont("Arial", 12, QFont.Bold))
            right_layout.addWidget(positions_label)
            
            self.positions_list = QListWidget()
            self.positions_list.setMaximumWidth(300)
            right_layout.addWidget(self.positions_list)
            
            # Commentary display
            commentary_label = QLabel("Race Commentary:")
            commentary_label.setFont(QFont("Arial", 12, QFont.Bold))
            right_layout.addWidget(commentary_label)
            
            self.commentary_output = QTextEdit()
            self.commentary_output.setReadOnly(True)
            self.commentary_output.setMaximumWidth(300)
            right_layout.addWidget(self.commentary_output)
            
            right_panel.setLayout(right_layout)
            race_splitter.addWidget(right_panel)
            
            race_splitter.setSizes([600, 300])
            layout.addWidget(race_splitter)
            
            # Simulation timer for live updates
            self.sim_timer = QTimer()
            self.sim_timer.timeout.connect(self.update_live_race)
            
            widget.setLayout(layout)
            return widget
        
        def create_results_tab(self) -> QWidget:
            """Create results display tab"""
            widget = QWidget()
            layout = QVBoxLayout()
            
            # Results table
            self.results_table = QTableWidget()
            self.results_table.setColumnCount(3)
            self.results_table.setHorizontalHeaderLabels(["Position", "Horse Name", "Stats"])
            layout.addWidget(self.results_table)
            
            # Save results button
            save_btn = QPushButton("Save Results")
            save_btn.clicked.connect(self.save_results)
            layout.addWidget(save_btn)
            
            widget.setLayout(layout)
            return widget
        
        def generate_random_stable(self):
            """Generate random harness racing horses"""
            try:
                count = self.horse_count_spin.value()
                self.simulator.clear_horses()
                
                for i in range(count):
                    horse = self.horse_generator.generate_horse()
                    self.simulator.add_horse(horse)
                
                self.update_horses_table()
                QMessageBox.information(self, "Success", 
                    f"Generated {count} harness racing horses")
            
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        
        def clear_horses(self):
            """Clear all horses from stable"""
            self.simulator.clear_horses()
            self.horses_table.setRowCount(0)
        
        def update_horses_table(self):
            """Update horse list table display"""
            self.horses_table.setRowCount(len(self.simulator.horses))
            
            for row, (horse_id, horse) in enumerate(self.simulator.horses.items()):
                stats = horse.stats
                
                items = [
                    horse.name,
                    str(horse.age),
                    str(stats.pulling_power),
                    str(stats.endurance),
                    str(stats.gait_consistency),
                    str(stats.heat_recovery),
                    str(stats.start_acceleration),
                    str(stats.sulky_tolerance),
                ]
                
                for col, item_text in enumerate(items):
                    self.horses_table.setItem(row, col, QTableWidgetItem(item_text))
        
        def update_race_info(self):
            """Update race information display"""
            race_name = self.race_combo.currentData()
            
            for race_id, race in ALL_HARNESS_RACES.items():
                if race.name == race_name:
                    info = f"""
Race: {race.name}
Distance: {race.distance}m
Track: {race.racecourse.value}
Surface: {race.surface.value}
Race Format: {race.format.value}
Horse Type: {race.horse_type.value}
Age Group: {race.age_group.value}
Prize Money: €{race.prize_money:,}
                    """
                    self.race_info_text.setText(info)
                    self.simulator.select_race(race_name)
                    
                    # Update canvas track layout (if canvas exists)
                    if hasattr(self, 'race_canvas') and self.race_canvas:
                        self.race_canvas.set_track_layout(race.racecourse.value)
                    break
        
        def run_race_live(self):
            """Execute race with live animation"""
            try:
                if not self.simulator.horses:
                    QMessageBox.warning(self, "Error", "Please generate horses first")
                    return
                
                if not self.simulator.selected_race:
                    QMessageBox.warning(self, "Error", "Please select a race")
                    return
                
                # Setup race
                self.simulator.setup_race()
                
                # Set race distance on canvas
                self.race_canvas.set_race_distance(self.simulator.selected_race.distance)
                
                # Clear previous displays
                self.commentary_output.clear()
                self.positions_list.clear()
                self.progress_bar.setValue(0)
                
                # Start commentary
                self.commentary_output.append(f"<b>Race: {self.simulator.selected_race.name}</b>")
                self.commentary_output.append(f"Distance: {self.simulator.selected_race.distance}m")
                self.commentary_output.append(f"Participants: {len(self.simulator.horses)}\n")
                
                # Disable buttons during race
                self.run_race_btn.setEnabled(False)
                self.run_race_instant_btn.setEnabled(False)
                
                # Start simulation timer (30 FPS for smooth animation)
                self.sim_timer.start(33)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
        
        def update_live_race(self):
            """Update live race display (called by timer)"""
            try:
                # Step simulation
                still_running = self.simulator.step_simulation()
                
                # Update canvas with new positions
                self.race_canvas.horse_positions = self.simulator.current_positions
                self.race_canvas.finished_horses = self.simulator.finished_horses
                self.race_canvas.update()
                
                # Update positions list
                self.update_positions_list()
                
                # Update commentary
                self.update_commentary_display()
                
                # Update progress
                if self.simulator.engine and self.simulator.selected_race:
                    leader_distance = self.simulator.current_positions[0][1] if self.simulator.current_positions else 0
                    progress = min(100, int(leader_distance / self.simulator.selected_race.distance * 100))
                    self.progress_bar.setValue(progress)
                
                # Check if race is finished
                if not still_running:
                    self.sim_timer.stop()
                    self.run_race_btn.setEnabled(True)
                    self.run_race_instant_btn.setEnabled(True)
                    
                    # Display final results
                    self.display_results_live()
                    self.commentary_output.append("\n<b>Race Complete!</b>")
                    
            except Exception as e:
                self.sim_timer.stop()
                self.run_race_btn.setEnabled(True)
                self.run_race_instant_btn.setEnabled(True)
                QMessageBox.critical(self, "Error", f"Race error: {str(e)}")
        
        def update_positions_list(self):
            """Update F1-style live positions sidebar"""
            self.positions_list.clear()
            
            for position, (horse_id, distance, state) in enumerate(self.simulator.current_positions, 1):
                horse = self.simulator.horses.get(horse_id)
                if horse:
                    # Format: "1. [Gate 3] Horse Name - 1250m"
                    gate_num = list(self.simulator.horses.keys()).index(horse_id) + 1
                    
                    status = ""
                    if hasattr(state, 'is_breaking_gait') and state.is_breaking_gait:
                        status = " [BREAK!]"
                    elif horse_id in self.simulator.finished_horses:
                        status = " ✓"
                    
                    text = f"{position}. [Gate {gate_num}] {horse.name} - {int(distance)}m{status}"
                    self.positions_list.addItem(text)
        
        def update_commentary_display(self):
            """Update commentary text display with new lines"""
            # Get new commentary lines
            current_count = len(self.simulator.race_commentary)
            
            if not hasattr(self, '_last_commentary_count'):
                self._last_commentary_count = 0
            
            if current_count > self._last_commentary_count:
                new_lines = self.simulator.race_commentary[self._last_commentary_count:]
                for line in new_lines:
                    self.commentary_output.append(line)
                
                # Auto-scroll to bottom
                scrollbar = self.commentary_output.verticalScrollBar()
                scrollbar.setValue(scrollbar.maximum())
                
                self._last_commentary_count = current_count
        
        def run_race_instant(self):
            """Execute the race simulation instantly (no animation)"""
            try:
                if not self.simulator.horses:
                    QMessageBox.warning(self, "Error", "Please generate horses first")
                    return
                
                if not self.simulator.selected_race:
                    QMessageBox.warning(self, "Error", "Please select a race")
                    return
                
                self.commentary_output.clear()
                self.commentary_output.append("Starting harness race simulation (instant)...")
                self.commentary_output.append(f"Race: {self.simulator.selected_race.name}")
                self.commentary_output.append(f"Distance: {self.simulator.selected_race.distance}m")
                self.commentary_output.append(f"Participants: {len(self.simulator.horses)}")
                self.commentary_output.append("\nRunning race...\n")
                
                # Run the race
                summary = self.simulator.run_race()
                
                # Display results
                self.display_results(summary)
                
                self.commentary_output.append("\nRace completed successfully!")
                self.progress_bar.setValue(100)
            
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))
                self.commentary_output.append(f"Error: {str(e)}")
        
        def display_results_live(self):
            """Display race results after live race"""
            if self.simulator.race_results:
                self.display_results({
                    "results": self.simulator.race_results
                })
        
        def display_results(self, summary: dict):
            """Display race results"""
            results_list = summary.get("results", [])
            self.results_table.setRowCount(len(results_list))
            
            for position, horse_id in enumerate(results_list, 1):
                horse = self.simulator.horses.get(horse_id)
                if horse:
                    stats_str = f"PP:{horse.stats.pulling_power} END:{horse.stats.endurance} GC:{horse.stats.gait_consistency}"
                    
                    items = [str(position), horse.name, stats_str]
                    for col, item_text in enumerate(items):
                        self.results_table.setItem(position - 1, col, QTableWidgetItem(item_text))
        
        def save_results(self):
            """Save race results to file"""
            try:
                if not self.simulator.race_results:
                    QMessageBox.warning(self, "No Results", "No race results to save. Please run a race first.")
                    return
                
                filename = self.simulator.save_results()
                QMessageBox.information(self, "Success", f"Results saved to:\n{filename}")
                self.commentary_output.append(f"\nResults saved to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))


def main():
    """Main entry point"""
    if USE_PYSIDE6:
        app = QApplication(sys.argv)
        window = HarnessRacingGUI()
        window.show()
        sys.exit(app.exec())
    else:
        print("PySide6 is required for the GUI")
        print("Install with: pip install PySide6")
        
        # Fallback: Run console interface
        simulator = HarnessRaceSimulator()
        generator = HarnessHorseGenerator()
        
        print("\n=== Harness Racing Simulator (Console Mode) ===\n")
        
        # Generate horses
        print("Generating 3 harness racing horses...")
        for i in range(3):
            horse = generator.generate_horse()
            simulator.add_horse(horse)
            print(f"  {i+1}. {horse.name} - Stats: {horse.stats.total_stats()}")
        
        # Select and run race
        if MAJOR_HARNESS_RACES:
            race = list(MAJOR_HARNESS_RACES.values())[0]
            simulator.selected_race = race
            print(f"\nSelected race: {race.name} ({race.distance}m at {race.racecourse.value})")
            
            print("\nRunning race...")
            summary = simulator.run_race()
            
            print("\nRace Results:")
            for position, horse_id in enumerate(summary['results'], 1):
                horse = simulator.horses[horse_id]
                print(f"  {position}. {horse.name}")
            
            # Save results
            filename = simulator.save_results()
            print(f"\nResults saved to {filename}")


if __name__ == "__main__":
    main()
