import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import json
import math
import random
from datetime import datetime

class UmaRacingGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # Initialize simulation variables
        self.sim_running = False
        self.sim_data = None
        self.sim_time = 0.0
        self.sim_after_id = None
        self.fired_event_seconds = set()
        self.uma_icons = {}
        self.track_margin = 50
        self.lane_height = 20
        self.finish_times = {}
        self.incidents_occurred = set()
        self.overtakes = set()
        self.commentary_cooldown = 0
        self.last_commentary_time = 0
        self.previous_positions = {}
        self.skill_activations = set()
        self.uma_colors = {}
        self.real_time_data = None
        
        # Real-time simulation variables
        self.horse_distances = {}
        self.horse_finished = {}
        self.horse_incidents = {}
        self.horse_skills = {}
        self.current_positions = {}
        self.horse_fatigue = {}
        self.horse_momentum = {}
        self.horse_last_position = {}
        self.horse_stamina = {}
        self.horse_dnf = {}
        
        # Commentary tracking
        self.distance_callouts_made = set()
        self.last_incident_commentary = 0
        self.last_position_commentary = 0
        self.last_speed_commentary = 0
        self.commentary_history = []
        
        self.title("Uma Musume Racing Simulator - REAL TIME")
        self.geometry("900x700")
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Load button
        self.load_btn = ttk.Button(control_frame, text="Load Racing Config", command=self.load_racing_config)
        self.load_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Start button
        self.start_btn = ttk.Button(control_frame, text="Start Simulation", command=self.start_simulation)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Stop button
        self.stop_btn = ttk.Button(control_frame, text="Stop Simulation", command=self.stop_simulation)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Reset button
        self.reset_btn = ttk.Button(control_frame, text="Reset", command=self.reset_simulation)
        self.reset_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Speed combobox
        ttk.Label(control_frame, text="Speed:").pack(side=tk.LEFT, padx=(0, 5))
        self.speed_cb = ttk.Combobox(control_frame, values=["0.5x", "1x", "2x", "5x", "10x"], width=5)
        self.speed_cb.set("1x")
        self.speed_cb.pack(side=tk.LEFT, padx=(0, 10))
        
        # Remaining distance label
        self.remaining_label = ttk.Label(control_frame, text="Remaining: -- | Lead: -- km/h")
        self.remaining_label.pack(side=tk.LEFT)
        
        # Real-time indicator
        self.realtime_label = ttk.Label(control_frame, text="REAL-TIME MODE", foreground="red", font=('Arial', 10, 'bold'))
        self.realtime_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Scrollable frame for track
        track_container = ttk.Frame(main_frame)
        track_container.pack(fill=tk.X, pady=(0, 10))
        
        # Add scrollbar for track
        track_scrollbar = ttk.Scrollbar(track_container, orient=tk.VERTICAL)
        track_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Canvas for race track with scrollbar
        self.canvas = tk.Canvas(track_container, bg='white', height=300, yscrollcommand=track_scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        track_scrollbar.config(command=self.canvas.yview)
        
        # Frame to hold all track elements
        self.track_frame = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.track_frame, anchor="nw")
        
        # Output text area
        output_frame = ttk.LabelFrame(main_frame, text="Simulation Output")
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=12)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Bind events for proper scrolling
        self.track_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Draw initial track
        self.draw_track()
        
    def _on_frame_configure(self, event=None):
        """Update scroll region when track frame size changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        
    def _on_canvas_configure(self, event=None):
        """Update canvas window size when canvas is resized"""
        self.canvas.itemconfig(self.canvas_window, width=event.width)
        
    def draw_track(self):
        """Draw the race track"""
        self.canvas.delete("track")
        w = self.canvas.winfo_width() or 800
        
        # Draw start line
        self.canvas.create_line(
            self.track_margin, 20, 
            self.track_margin, 280, 
            fill="red", width=2, tags="track"
        )
        
        # Draw finish line
        self.canvas.create_line(
            w - self.track_margin, 20, 
            w - self.track_margin, 280, 
            fill="green", width=2, tags="track"
        )
        
        # Draw track center line
        self.canvas.create_line(
            self.track_margin, 150, 
            w - self.track_margin, 150, 
            fill="gray", dash=(5, 5), tags="track"
        )
        
    def load_racing_config(self):
        """Load racing configuration from JSON file"""
        file_path = filedialog.askopenfilename(
            title="Select Racing Config File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Store the config data for real-time simulation
            self.sim_data = self.prepare_real_time_simulation(config_data)
            
            self.append_output(f"Loaded racing config: {file_path}\n")
            self.append_output(f"Race: {config_data.get('race', {}).get('name', 'Unknown')}\n")
            self.append_output(f"Race distance: {self.sim_data.get('race_distance', 0)}m\n")
            self.append_output(f"Race type: {self.sim_data.get('race_type', 'Unknown')}\n")
            self.append_output(f"Umas: {len(config_data.get('umas', []))}\n")
            self.append_output("REAL-TIME SIMULATION MODE READY\n")
            
            self.initialize_uma_icons()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config file:\n{str(e)}")
            self.append_output(f"Error loading config: {str(e)}\n")
    
    def prepare_real_time_simulation(self, config_data):
        """Prepare simulation data for real-time execution with distance-specific mechanics"""
        race_info = config_data.get('race', {})
        umas = config_data.get('umas', [])
        
        race_distance = race_info.get('distance', 2500)
        race_type = race_info.get('type', 'Medium')
        surface = race_info.get('surface', 'Turf')
        
        # REALISTIC SPEED PARAMETERS FOR ~60-65 KM/H RANGE (16.5-18.0 m/s)
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
        
        # DISTANCE-SPECIFIC STAT WEIGHTINGS
        stat_weights = {
            'Sprint': {
                'Speed': 0.45,
                'Stamina': 0.15,
                'Power': 0.20,
                'Guts': 0.12,
                'Wit': 0.08
            },
            'Mile': {
                'Speed': 0.35,
                'Stamina': 0.25,
                'Power': 0.18,
                'Guts': 0.14,
                'Wit': 0.08
            },
            'Medium': {
                'Speed': 0.30,
                'Stamina': 0.35,
                'Power': 0.15,
                'Guts': 0.12,
                'Wit': 0.08
            },
            'Long': {
                'Speed': 0.25,
                'Stamina': 0.40,
                'Power': 0.15,
                'Guts': 0.12,
                'Wit': 0.08
            }
        }
        
        weights = stat_weights.get(race_type, stat_weights['Medium'])
        
        # Calculate performance stats for each uma with distance-specific weightings
        uma_stats = {}
        for uma in umas:
            name = uma['name']
            stats = uma['stats']
            running_style = uma.get('running_style', 'PC')
            
            base_performance = (
                stats.get('Speed', 0) * weights['Speed'] +
                stats.get('Stamina', 0) * weights['Stamina'] +
                stats.get('Power', 0) * weights['Power'] +
                stats.get('Guts', 0) * weights['Guts'] +
                stats.get('Wit', 0) * weights['Wit']
            )
            
            distance_apt = uma.get('distance_aptitude', {})
            surface_apt = uma.get('surface_aptitude', {})
            
            # DISTANCE-SPECIFIC APTITUDE MULTIPLIERS
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
            
            # DISTANCE-SPECIFIC RUNNING STYLE MECHANICS
            running_style_bonuses = {
                'Sprint': {
                    'FR': {
                        'position_pref': range(1, 2),
                        'early_speed_bonus': 0.20,
                        'mid_speed_bonus': 0.10,
                        'final_speed_bonus': 0.05,
                        'stamina_multiplier': 1.10,
                        'skill_trigger_zones': [0.0, 0.3, 0.6],
                        'lead_bonus': 0.04,
                    },
                    'PC': {
                        'position_pref': range(2, 4),
                        'early_speed_bonus': 0.08,
                        'mid_speed_bonus': 0.12,
                        'final_speed_bonus': 0.08,
                        'stamina_multiplier': 1.00,
                        'skill_trigger_zones': [0.2, 0.5, 0.8],
                    },
                    'LS': {
                        'position_pref': range(3, 6),
                        'early_speed_penalty': -0.05,
                        'mid_speed_bonus': 0.08,
                        'final_speed_bonus': 0.10,
                        'stamina_multiplier': 0.95,
                        'skill_trigger_zones': [0.4, 0.7, 0.9],
                    },
                    'EC': {
                        'position_pref': range(5, 21),
                        'early_speed_penalty': -0.10,
                        'mid_speed_penalty': -0.05,
                        'final_speed_bonus': 0.15,
                        'stamina_multiplier': 0.90,
                        'skill_trigger_zones': [0.6, 0.8, 0.95],
                    }
                },
                'Mile': {
                    'FR': {
                        'position_pref': range(1, 3),
                        'early_speed_bonus': 0.15,
                        'mid_speed_bonus': 0.08,
                        'final_speed_penalty': -0.05,
                        'stamina_multiplier': 1.20,
                        'skill_trigger_zones': [0.0, 0.3, 0.6],
                        'lead_bonus': 0.03,
                    },
                    'PC': {
                        'position_pref': range(2, 5),
                        'early_speed_bonus': 0.06,
                        'mid_speed_bonus': 0.10,
                        'final_speed_bonus': 0.06,
                        'stamina_multiplier': 1.00,
                        'skill_trigger_zones': [0.2, 0.5, 0.8],
                    },
                    'LS': {
                        'position_pref': range(3, 7),
                        'early_speed_penalty': -0.06,
                        'mid_speed_bonus': 0.06,
                        'final_speed_bonus': 0.12,
                        'stamina_multiplier': 0.92,
                        'skill_trigger_zones': [0.4, 0.7, 0.9],
                    },
                    'EC': {
                        'position_pref': range(6, 21),
                        'early_speed_penalty': -0.12,
                        'mid_speed_penalty': -0.06,
                        'final_speed_bonus': 0.18,
                        'stamina_multiplier': 0.85,
                        'skill_trigger_zones': [0.6, 0.8, 0.95],
                    }
                },
                'Medium': {
                    'FR': {
                        'position_pref': range(1, 3),
                        'early_speed_bonus': 0.12,
                        'mid_speed_bonus': 0.06,
                        'final_speed_penalty': -0.08,
                        'stamina_multiplier': 1.30,
                        'skill_trigger_zones': [0.0, 0.3, 0.6],
                        'lead_bonus': 0.02,
                    },
                    'PC': {
                        'position_pref': range(2, 6),
                        'early_speed_bonus': 0.04,
                        'mid_speed_bonus': 0.08,
                        'final_speed_bonus': 0.05,
                        'stamina_multiplier': 1.00,
                        'skill_trigger_zones': [0.2, 0.5, 0.8],
                    },
                    'LS': {
                        'position_pref': range(4, 8),
                        'early_speed_penalty': -0.07,
                        'mid_speed_bonus': 0.05,
                        'final_speed_bonus': 0.14,
                        'stamina_multiplier': 0.88,
                        'skill_trigger_zones': [0.4, 0.7, 0.9],
                    },
                    'EC': {
                        'position_pref': range(7, 21),
                        'early_speed_penalty': -0.14,
                        'mid_speed_penalty': -0.07,
                        'final_speed_bonus': 0.20,
                        'stamina_multiplier': 0.80,
                        'skill_trigger_zones': [0.6, 0.8, 0.95],
                    }
                },
                'Long': {
                    'FR': {
                        'position_pref': range(1, 3),
                        'early_speed_bonus': 0.10,
                        'mid_speed_penalty': -0.05,
                        'final_speed_penalty': -0.15,
                        'stamina_multiplier': 1.40,
                        'skill_trigger_zones': [0.0, 0.2, 0.4],
                        'lead_bonus': 0.01,
                    },
                    'PC': {
                        'position_pref': range(2, 6),
                        'early_speed_bonus': 0.03,
                        'mid_speed_bonus': 0.06,
                        'final_speed_bonus': 0.04,
                        'stamina_multiplier': 1.05,
                        'skill_trigger_zones': [0.3, 0.5, 0.7],
                    },
                    'LS': {
                        'position_pref': range(4, 8),
                        'early_speed_penalty': -0.08,
                        'mid_speed_bonus': 0.04,
                        'final_speed_bonus': 0.15,
                        'stamina_multiplier': 0.85,
                        'skill_trigger_zones': [0.5, 0.7, 0.9],
                    },
                    'EC': {
                        'position_pref': range(6, 21),
                        'early_speed_penalty': -0.15,
                        'mid_speed_penalty': -0.08,
                        'final_speed_bonus': 0.25,
                        'stamina_multiplier': 0.75,
                        'skill_trigger_zones': [0.6, 0.8, 0.95],
                    }
                }
            }
            
            style_bonus_config = running_style_bonuses.get(race_type, running_style_bonuses['Medium'])
            style_bonus = style_bonus_config.get(running_style, style_bonus_config['PC'])
            
            # Apply aptitude multipliers
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
        
        # BALANCED NORMALIZATION - not too compressed, not too wide
        performances = [stats['base_performance'] for stats in uma_stats.values()]
        if performances:
            min_perf = min(performances)
            max_perf = max(performances)
            
            # ADJUSTED: Wider ranges for more stat impact, but still balanced
            normalization_ranges = {
                'Sprint': (0.82, 0.30),  # 0.82 to 1.12 (30% difference)
                'Mile': (0.80, 0.33),    # 0.80 to 1.13 (33% difference)
                'Medium': (0.78, 0.36),  # 0.78 to 1.14 (36% difference)
                'Long': (0.76, 0.40)     # 0.76 to 1.16 (40% difference)
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
            'uma_stats': uma_stats
        }

    def initialize_real_time_simulation(self):
        """Initialize all real-time simulation variables"""
        if not self.sim_data:
            return
            
        uma_stats = self.sim_data.get('uma_stats', {})
        
        # Initialize real-time simulation state
        self.horse_distances = {name: 0.0 for name in uma_stats.keys()}
        self.horse_finished = {name: False for name in uma_stats.keys()}
        self.horse_incidents = {name: {'type': None, 'duration': 0, 'start_time': 0} for name in uma_stats.keys()}
        self.horse_skills = {name: {'cooldown': 0, 'last_activation': 0, 'active': False, 'failed_skill': False} for name in uma_stats.keys()}
        self.current_positions = {name: 1 for name in uma_stats.keys()}
        self.horse_fatigue = {name: 0.0 for name in uma_stats.keys()}
        self.horse_momentum = {name: 1.0 for name in uma_stats.keys()}
        self.horse_last_position = {name: 1 for name in uma_stats.keys()}
        self.horse_stamina = {name: 100.0 for name in uma_stats.keys()}
        self.horse_dnf = {name: {'dnf': False, 'reason': '', 'dnf_time': 0, 'dnf_distance': 0} for name in uma_stats.keys()}
        
        self.sim_time = 0.0
        self.finish_times.clear()
        self.incidents_occurred.clear()
        self.overtakes.clear()
        self.skill_activations.clear()
        self.last_commentary_time = 0
        self.previous_positions.clear()
        
        # Reset commentary tracking
        self.distance_callouts_made.clear()
        self.last_incident_commentary = 0
        self.last_position_commentary = 0
        self.last_speed_commentary = 0
        self.commentary_history.clear()

    def calculate_dnf_chance(self, uma_name, uma_stats):
        """Calculate DNF chance based on stats and aptitudes"""
        base_chance = 0.0005
        
        # Increase chance for low stats
        stat_penalty = 0
        for stat_name, stat_value in [('Speed', uma_stats['speed']), 
                                     ('Stamina', uma_stats['stamina']),
                                     ('Power', uma_stats['power']),
                                     ('Guts', uma_stats['guts']),
                                     ('Wit', uma_stats['wisdom'])]:
            if stat_value < 500:
                stat_penalty += (500 - stat_value) * 0.00001
        
        # Increase chance for poor aptitudes
        distance_apt = uma_stats['distance_aptitude']
        surface_apt = uma_stats['surface_aptitude']
        
        apt_multiplier = 1.0
        if distance_apt in ['D', 'E', 'F', 'G']:
            apt_multiplier += 0.005
        if surface_apt in ['D', 'E', 'F', 'G']:
            apt_multiplier += 0.005
        
        # Very high chance for extremely poor horses
        if (uma_stats['stamina'] < 400 or 
            uma_stats['guts'] < 300 or 
            distance_apt == 'G' or 
            surface_apt == 'G'):
            apt_multiplier += 0.01
        
        final_chance = (base_chance + stat_penalty) * apt_multiplier
        return min(final_chance, 0.05)

    def check_dnf(self, uma_name, uma_stats, current_distance, race_distance):
        """Check if uma suffers DNF during race"""
        if self.horse_dnf[uma_name]['dnf']:
            return True, self.horse_dnf[uma_name]['reason']
            
        # Only check for DNF in middle phase of the race (30%-70% distance)
        race_progress = current_distance / race_distance
        if race_progress < 0.3 or race_progress > 0.7:
            return False, ""
            
        dnf_chance = self.calculate_dnf_chance(uma_name, uma_stats)
        
        # Make DNF even rarer by only checking occasionally
        if random.random() < 0.1:
            if random.random() < dnf_chance:
                # Determine DNF reason
                reasons = []
                if uma_stats['stamina'] < 500:
                    reasons.append("exhaustion")
                if uma_stats['guts'] < 400:
                    reasons.append("loss of will")
                if uma_stats['distance_aptitude'] in ['E', 'F', 'G']:
                    reasons.append("unsuitable distance")
                if uma_stats['surface_aptitude'] in ['E', 'F', 'G']:
                    reasons.append("unsuitable surface")
                
                if not reasons:
                    reasons.append("unexpected incident")
                
                reason = ", ".join(reasons)
                
                # Record DNF details
                self.horse_dnf[uma_name] = {
                    'dnf': True,
                    'reason': reason,
                    'dnf_time': self.sim_time,
                    'dnf_distance': current_distance
                }
                
                return True, reason
        
        return False, ""

    def initialize_uma_icons(self):
        """Initialize the visual icons for each uma on the track"""
        for name, (circle, text, speed) in self.uma_icons.items():
            if circle: self.canvas.delete(circle)
            if text: self.canvas.delete(text)
            if speed: self.canvas.delete(speed)
        self.uma_icons.clear()
        self.uma_colors.clear()
        
        if not self.sim_data:
            return
            
        uma_stats = self.sim_data.get('uma_stats', {})
        if not uma_stats:
            self.append_output("Warning: No uma stats found in config.\n")
            return
        
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'cyan', 'magenta', 'darkgreen',
                 'darkred', 'darkblue', 'darkorange', 'darkviolet', 'gold', 'maroon', 'navy', 'teal',
                 'coral', 'lime', 'indigo', 'salmon', 'olive', 'steelblue']
        
        for i, name in enumerate(uma_stats.keys()):
            color = colors[i % len(colors)]
            self.uma_colors[name] = color
            
            y_position = 20 + i * self.lane_height
            
            circle = self.canvas.create_oval(0, 0, 0, 0, fill=color, tags=name, outline='black', width=1)
            text = self.canvas.create_text(0, 0, text=name, fill='black', anchor=tk.S, font=('Arial', 7, 'bold'))
            speed = self.canvas.create_text(0, 0, text="0 km/h", fill='darkblue', anchor=tk.N, font=('Arial', 6))
            
            self.uma_icons[name] = (circle, text, speed)
            
        self.append_output(f"Initialized {len(uma_stats)} umas on track.\n")
        self._on_frame_configure()

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
        
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        self.append_output("REAL-TIME SIMULATION started!\n")
        
        self._run_real_time_tick()
        
    def _run_real_time_tick(self):
        """Main simulation tick for real-time simulation"""
        if not self.sim_running or not self.sim_data:
            return
            
        try:
            speed_text = self.speed_cb.get()
            mult = 1.0
            if speed_text.endswith('x'):
                try:
                    mult = float(speed_text[:-1])
                except Exception:
                    mult = 1.0
                    
            frame_dt = 0.05  # 50ms per frame
            self.sim_time += frame_dt * mult
            
            race_distance = self.sim_data.get('race_distance', 2500)
            uma_stats = self.sim_data.get('uma_stats', {})
            
            # Calculate new positions in real-time
            current_frame_positions = self.calculate_real_time_positions(frame_dt * mult)
            
            current_skill_activations = {name: self.horse_skills[name]['active'] for name in uma_stats.keys()}
            current_incidents = {name: self.horse_incidents[name]['type'] for name in uma_stats.keys() if self.horse_incidents[name]['type']}
            
            # Generate commentary with enhanced system
            if self.sim_time - self.last_commentary_time > 1.8:  # More frequent commentary
                leader_dist = current_frame_positions[0][1] if current_frame_positions else 0
                remaining_distance = max(0, race_distance - leader_dist)
                commentaries = self.get_enhanced_commentary(
                    self.sim_time, current_frame_positions, race_distance, 
                    remaining_distance, current_incidents, set(self.finish_times.keys()),
                    current_skill_activations
                )
                
                for commentary in commentaries:
                    if commentary not in self.commentary_history[-5:]:  # Avoid recent repeats
                        self.append_output(f"[{self.sim_time:.1f}s] {commentary}\n")
                        self.commentary_history.append(commentary)
                        self.last_commentary_time = self.sim_time
                        if len(self.commentary_history) > 20:
                            self.commentary_history.pop(0)
            
            # Update display
            self.update_display(current_frame_positions, race_distance)
            
            # Check if all finished (including DNF)
            all_finished = len(self.finish_times) + len([d for d in self.horse_dnf.values() if d['dnf']]) == len(self.uma_icons)
            
            if all_finished:
                self.sim_running = False
                self.start_btn.config(state='normal')
                self.stop_btn.config(state='disabled')
                self.display_final_results()
                return

            self.sim_after_id = self.after(int(frame_dt * 1000 / mult), self._run_real_time_tick)
            
        except Exception as e:
            self.append_output(f"Simulation error: {str(e)}\n")
            self.sim_running = False
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')

    def calculate_real_time_positions(self, time_delta):
        """Calculate new positions with distance-specific mechanics"""
        race_distance = self.sim_data.get('race_distance', 2500)
        race_type = self.sim_data.get('race_type', 'Medium')
        uma_stats = self.sim_data.get('uma_stats', {})
        
        frame_positions = []
        
        for uma_name in uma_stats.keys():
            if self.horse_finished[uma_name] or self.horse_dnf[uma_name]['dnf']:
                continue
                
            uma_stat = uma_stats[uma_name]
            style_bonus = uma_stat['style_bonus']
            
            # Check for DNF first - only in middle phase
            dnf, dnf_reason = self.check_dnf(uma_name, uma_stat, self.horse_distances[uma_name], race_distance)
            if dnf:
                self.horse_dnf[uma_name]['dnf'] = True
                self.horse_dnf[uma_name]['reason'] = dnf_reason
                self.horse_dnf[uma_name]['dnf_time'] = self.sim_time
                self.horse_dnf[uma_name]['dnf_distance'] = self.horse_distances[uma_name]
                self.append_output(f"[{self.sim_time:.1f}s] {uma_name} DNF! Reason: {dnf_reason}\n")
                continue
            
            # Handle incidents
            if self.horse_incidents[uma_name]['type']:
                incident_time = self.sim_time - self.horse_incidents[uma_name]['start_time']
                if incident_time >= self.horse_incidents[uma_name]['duration']:
                    self.horse_incidents[uma_name]['type'] = None
                else:
                    # Slow down during incident
                    speed_multiplier = 0.3
                    if self.horse_incidents[uma_name]['type'] == 'stumble':
                        speed_multiplier = 0.1
                    elif self.horse_incidents[uma_name]['type'] == 'blocked':
                        speed_multiplier = 0.5
                    
                    # Apply speed reduction
                    current_speed = self.calculate_current_speed(uma_name, uma_stat, race_distance, race_type)
                    distance_covered = current_speed * time_delta * speed_multiplier
                    self.horse_distances[uma_name] += distance_covered
                    
                    if self.horse_distances[uma_name] >= race_distance:
                        self.horse_finished[uma_name] = True
                        self.finish_times[uma_name] = self.sim_time
                    
                    frame_positions.append((uma_name, self.horse_distances[uma_name]))
                    continue
            
            # Calculate current speed based on race phase and conditions
            current_speed = self.calculate_current_speed(uma_name, uma_stat, race_distance, race_type)
            
            # Apply momentum effects
            current_speed *= self.horse_momentum[uma_name]
            
            # Calculate distance covered this frame
            distance_covered = current_speed * time_delta
            
            # Update distance
            self.horse_distances[uma_name] += distance_covered
            
            # Check for finish
            if self.horse_distances[uma_name] >= race_distance:
                self.horse_finished[uma_name] = True
                self.finish_times[uma_name] = self.sim_time
            
            frame_positions.append((uma_name, self.horse_distances[uma_name]))
        
        # Sort by distance (descending) for positions
        frame_positions.sort(key=lambda x: x[1], reverse=True)
        
        # Update positions and detect overtakes
        for i, (name, distance) in enumerate(frame_positions):
            position = i + 1
            if name in self.previous_positions and self.previous_positions[name] != position:
                old_pos = self.previous_positions[name]
                if old_pos > position:
                    self.overtakes.add((name, old_pos, position, self.sim_time))
            self.previous_positions[name] = position
        
        return frame_positions

    def calculate_current_speed(self, uma_name, uma_stat, race_distance, race_type):
        """Calculate current speed with distance-specific phase mechanics"""
        current_distance = self.horse_distances[uma_name]
        race_progress = current_distance / race_distance
        
        base_speed = uma_stat['base_speed']
        top_speed = uma_stat['top_speed']
        sprint_speed = uma_stat['sprint_speed']
        running_style = uma_stat['running_style']
        style_bonus = uma_stat['style_bonus']
        
        # DISTANCE-SPECIFIC RACE PHASES
        if race_type == 'Sprint':
            phases = {
                'start': (0.0, 0.2),
                'mid': (0.2, 0.7),
                'final': (0.7, 0.9),
                'sprint': (0.9, 1.0)
            }
        elif race_type == 'Mile':
            phases = {
                'start': (0.0, 0.15),
                'mid': (0.15, 0.6),
                'final': (0.6, 0.85),
                'sprint': (0.85, 1.0)
            }
        elif race_type == 'Medium':
            phases = {
                'start': (0.0, 0.1),
                'mid': (0.1, 0.5),
                'final': (0.5, 0.8),
                'sprint': (0.8, 1.0)
            }
        else:  # Long
            phases = {
                'start': (0.0, 0.05),
                'mid': (0.05, 0.4),
                'final': (0.4, 0.7),
                'sprint': (0.7, 1.0)
            }
        
        # Determine current phase
        current_phase = 'start'
        for phase, (start, end) in phases.items():
            if start <= race_progress < end:
                current_phase = phase
                break
        
        # Base speed for phase
        if current_phase == 'start':
            target_speed = base_speed
        elif current_phase == 'mid':
            target_speed = top_speed
        elif current_phase == 'final':
            target_speed = top_speed * 1.02
        else:  # sprint
            target_speed = sprint_speed
        
        # Apply running style bonuses/penalties
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
        
        # Apply performance scaling
        target_speed *= uma_stat['base_performance']
        
        # Apply fatigue effects
        fatigue_penalty = self.horse_fatigue[uma_name] * 0.08
        target_speed *= (1.0 - min(fatigue_penalty, 0.25))
        
        # Apply stamina effects with Guts integration
        stamina_ratio = self.horse_stamina[uma_name] / 100.0
        guts_efficiency = uma_stat['guts'] / 1000.0
        effective_stamina = stamina_ratio * (0.7 + 0.3 * guts_efficiency)
        
        # Progressive stamina penalties
        if effective_stamina < 0.1:
            target_speed *= 0.80
        elif effective_stamina < 0.3:
            target_speed *= 0.88
        elif effective_stamina < 0.5:
            target_speed *= 0.93
        elif effective_stamina < 0.7:
            target_speed *= 0.97
        
        # Update fatigue and stamina
        self.update_fatigue_and_stamina(uma_name, uma_stat, race_progress, current_phase)
        
        # Random variation (±2%)
        variation = 1.0 + (random.random() * 0.04 - 0.02)
        target_speed *= variation
        
        return max(target_speed, base_speed * 0.85)

    def update_fatigue_and_stamina(self, uma_name, uma_stat, race_progress, current_phase):
        """Update fatigue and stamina with distance-specific mechanics"""
        # Distance-specific fatigue rates
        fatigue_rates = {
            'Sprint': {'start': 0.003, 'mid': 0.005, 'final': 0.008, 'sprint': 0.012},
            'Mile': {'start': 0.004, 'mid': 0.006, 'final': 0.010, 'sprint': 0.015},
            'Medium': {'start': 0.005, 'mid': 0.008, 'final': 0.012, 'sprint': 0.018},
            'Long': {'start': 0.006, 'mid': 0.010, 'final': 0.015, 'sprint': 0.022}
        }
        
        race_type = uma_stat['race_type']
        rates = fatigue_rates.get(race_type, fatigue_rates['Medium'])
        fatigue_rate = rates.get(current_phase, 0.008)
        
        # Stamina-based fatigue resistance
        stamina_bonus = uma_stat['stamina'] / 1000.0
        fatigue_rate *= (1.0 - stamina_bonus * 0.4)
        
        # Update fatigue
        self.horse_fatigue[uma_name] += fatigue_rate
        
        # Stamina depletion rates
        base_stamina_drain = 0.08
        
        # Phase-specific stamina consumption
        phase_multipliers = {
            'start': 0.8,
            'mid': 1.0,
            'final': 1.3,
            'sprint': 1.8
        }
        
        stamina_depletion = base_stamina_drain * phase_multipliers.get(current_phase, 1.0)
        
        # Add fatigue impact on stamina drain
        stamina_depletion += (self.horse_fatigue[uma_name] * 0.15)
        
        # Guts helps maintain stamina
        guts_bonus = uma_stat['guts'] / 1000.0
        stamina_depletion *= (1.0 - guts_bonus * 0.3)
        
        self.horse_stamina[uma_name] = max(0.0, self.horse_stamina[uma_name] - stamina_depletion)

    def get_enhanced_commentary(self, current_time, positions, race_distance, remaining_distance, incidents, finished, skill_activations):
        """Enhanced commentary system with 300+ unique lines"""
        commentaries = []
        
        if not positions:
            return commentaries
            
        leader_name, leader_distance = positions[0]
        race_progress = leader_distance / race_distance
        
        # DISTANCE CALLOUTS - Check specific meter markers
        distance_markers = [1800, 1600, 1400, 1200, 1000, 800, 600, 400, 200, 100, 50]
        for marker in distance_markers:
            if remaining_distance <= marker and marker not in self.distance_callouts_made:
                self.distance_callouts_made.add(marker)
                commentary = self.get_distance_callout(marker, leader_name, positions)
                if commentary:
                    commentaries.append(commentary)
                    break  # Only one distance callout per tick
        
        # OVERTAKE COMMENTARY - Check for recent overtakes
        if self.sim_time - self.last_position_commentary > 3.0:
            recent_overtakes = [o for o in self.overtakes if o[3] > current_time - 3.0]
            if recent_overtakes:
                overtake = random.choice(recent_overtakes)
                commentary = self.get_overtake_commentary(overtake, positions)
                if commentary:
                    commentaries.append(commentary)
                    self.last_position_commentary = self.sim_time
        
        # INCIDENT COMMENTARY
        if incidents and self.sim_time - self.last_incident_commentary > 4.0:
            for name, incident_type in incidents.items():
                if incident_type:
                    commentary = self.get_incident_commentary(name, incident_type, positions)
                    if commentary:
                        commentaries.append(commentary)
                        self.last_incident_commentary = self.sim_time
                        break
        
        # PHASE-BASED COMMENTARY
        if not commentaries:  # Fill with phase commentary if no special events
            phase_commentary = self.get_phase_commentary(race_progress, leader_name, positions, remaining_distance)
            if phase_commentary:
                commentaries.append(phase_commentary)
        
        # SPEED AND POSITION COMMENTARY
        if self.sim_time - self.last_speed_commentary > 5.0 and not commentaries:
            speed_commentary = self.get_speed_position_commentary(positions, race_distance)
            if speed_commentary:
                commentaries.append(speed_commentary)
                self.last_speed_commentary = self.sim_time
        
        # FINISH LINE COMMENTARY
        finish_commentary = self.get_finish_commentary(finished, positions, race_progress)
        if finish_commentary:
            commentaries.append(finish_commentary)
        
        return commentaries[:2]  # Return up to 2 comments per tick

    def get_distance_callout(self, remaining, leader, positions):
        """Distance-specific callouts with variety"""
        callouts = {
            1800: [
                f"{remaining}m to go! {leader} leads the pack!",
                f"We're at the {remaining} meter mark with {leader} in front!",
                f"{remaining} meters remaining! {leader} is showing the way!",
                f"Entering the final {remaining} meters! {leader} controls the pace!",
            ],
            1600: [
                f"{remaining}m remaining! The field is tightening up!",
                f"At {remaining}m, {leader} maintains the advantage!",
                f"{remaining} meters to the wire! Who will make their move?",
                f"The {remaining} meter pole! {leader} still in command!",
            ],
            1400: [
                f"{remaining}m to go! The race is heating up!",
                f"At {remaining}m, positioning becomes critical!",
                f"{remaining} meters left! {leader} under pressure now!",
                f"We're at {remaining}m! The final battle is about to begin!",
            ],
            1200: [
                f"{remaining}m remaining! Into the crucial phase!",
                f"The {remaining} meter mark! {leader} needs to hold on!",
                f"{remaining}m to go! The challengers are gathering!",
                f"At {remaining}m, every meter counts now!",
            ],
            1000: [
                f"The final {remaining} meters! {leader} leads the charge!",
                f"One thousand meters to go! This is where races are won!",
                f"{remaining}m remaining! {leader} is being chased down!",
                f"The final kilometer! {leader} must dig deep!",
                f"At the {remaining}m pole! The sprint is on!",
            ],
            800: [
                f"{remaining}m to go! The home stretch approaches!",
                f"At {remaining}m, {leader} is fighting hard!",
                f"{remaining} meters remaining! Who has the stamina?",
                f"The {remaining} meter mark! {leader} under intense pressure!",
            ],
            600: [
                f"{remaining}m to the finish! {leader} is giving everything!",
                f"At {remaining}m! The final push is on!",
                f"{remaining} meters! {leader} tries to hold them off!",
                f"The {remaining} meter pole! It's a desperate fight!",
            ],
            400: [
                f"Just {remaining}m remaining! {leader} is being hunted!",
                f"{remaining} meters to go! The finish line is in sight!",
                f"At {remaining}m! Who will find that extra gear?",
                f"The final {remaining} meters! {leader} is in survival mode!",
                f"{remaining}m left! This is where champions are made!",
            ],
            200: [
                f"Only {remaining}m to go! {leader} is sprinting for glory!",
                f"{remaining} meters! The finish line beckons!",
                f"The final {remaining}! {leader} is pouring it all out!",
                f"{remaining}m remaining! It's all or nothing now!",
                f"Just {remaining} meters! {leader} can almost taste victory!",
            ],
            100: [
                f"The final {remaining} meters! {leader} is so close!",
                f"Only {remaining}m left! {leader} is giving everything!",
                f"{remaining} meters to glory! {leader} in full flight!",
                f"The last {remaining}m! {leader} must hold on!",
            ],
            50: [
                f"Just {remaining} meters! {leader} is almost there!",
                f"{remaining}m to the line! {leader} can see victory!",
                f"The final {remaining}! {leader} is lunging for the win!",
            ]
        }
        
        return random.choice(callouts.get(remaining, []))

    def get_overtake_commentary(self, overtake, positions):
        """Overtaking moment commentary with dramatic flair"""
        name, old_pos, new_pos, time = overtake
        position_gained = old_pos - new_pos
        
        # Find who was overtaken
        overtaken = []
        for pos_name, distance in positions:
            current_pos = positions.index((pos_name, distance)) + 1
            if current_pos == new_pos + 1:
                overtaken.append(pos_name)
        
        overtaken_name = overtaken[0] if overtaken else "a rival"
        
        if position_gained == 1:
            lines = [
                f"{name} makes a bold move past {overtaken_name}!",
                f"And here comes {name}! Overtaking {overtaken_name} on the outside!",
                f"{name} finds an opening and slips past {overtaken_name}!",
                f"Watch {name} go! Flying past {overtaken_name}!",
                f"{name} with a brilliant tactical move past {overtaken_name}!",
                f"There it is! {name} overtakes {overtaken_name}!",
                f"{name} is not to be denied! Past {overtaken_name}!",
                f"A gutsy move by {name}! {overtaken_name} has been passed!",
                f"{name} accelerates past {overtaken_name}!",
                f"Beautiful running from {name}! Past {overtaken_name} and moving up!",
            ]
        elif position_gained == 2:
            lines = [
                f"Incredible! {name} jumps two positions from {old_pos} to {new_pos}!",
                f"{name} with a surge! Up two spots!",
                f"What a move by {name}! From {old_pos}th to {new_pos}th in one go!",
                f"{name} is flying! Gains two positions!",
                f"Amazing acceleration from {name}! Two horses passed!",
                f"{name} unleashes a powerful burst! Up to {new_pos}th!",
            ]
        else:  # 3+ positions
            lines = [
                f"Spectacular! {name} rockets from {old_pos}th to {new_pos}th!",
                f"{name} is on fire! Gaining {position_gained} positions in one incredible surge!",
                f"Unbelievable speed from {name}! From {old_pos}th to {new_pos}th!",
                f"{name} with a devastating move! Multiple horses passed!",
                f"Look at {name} go! That's a {position_gained}-position gain!",
                f"{name} is unstoppable! Charging through the field!",
            ]
        
        return random.choice(lines)

    def get_incident_commentary(self, name, incident_type, positions):
        """Incident commentary with drama"""
        if incident_type == 'stumble':
            lines = [
                f"Oh no! {name} stumbles badly!",
                f"Disaster for {name}! A stumble at the worst possible time!",
                f"{name} has hit trouble! A stumble costs precious momentum!",
                f"Bad luck for {name}! They've stumbled!",
                f"{name} nearly goes down! A serious stumble!",
                f"That's going to hurt! {name} stumbles!",
                f"{name} loses balance! What a setback!",
                f"A nightmare moment for {name}! They stumbled!",
            ]
        elif incident_type == 'blocked':
            lines = [
                f"{name} gets blocked! No room to maneuver!",
                f"Traffic problems for {name}! Blocked in!",
                f"{name} is boxed! Can't find a way through!",
                f"Bad positioning for {name}! Completely blocked!",
                f"{name} has nowhere to go! Trapped behind horses!",
                f"Oh that's unfortunate! {name} is stuck!",
                f"{name} needs to find space! Currently blocked!",
                f"Racing luck! {name} is hemmed in!",
            ]
        else:
            lines = [
                f"{name} encounters trouble!",
                f"Problems for {name}!",
                f"An incident for {name}!",
                f"{name} faces an obstacle!",
            ]
        
        return random.choice(lines)

    def get_phase_commentary(self, race_progress, leader, positions, remaining):
        """Phase-based general commentary"""
        if race_progress < 0.1:
            lines = [
                f"And they're off! {leader} takes the early lead!",
                f"The gates open and {leader} breaks quickly!",
                f"Clean start! {leader} is first to show!",
                f"Here we go! {leader} leads them away!",
                f"{leader} is keen early! Takes the front position!",
                f"Good beginning for {leader}! Out in front!",
            ]
        elif race_progress < 0.25:
            lines = [
                f"The early pace is {random.choice(['honest', 'strong', 'moderate', 'solid'])}!",
                f"{leader} settles into the lead with {remaining:.0f}m to go!",
                f"The field is {random.choice(['bunched', 'spread out', 'compact', 'stretching'])} behind {leader}!",
                f"{leader} dictates the tempo in these early stages!",
                f"Still plenty of time, but {leader} controls things!",
            ]
        elif race_progress < 0.5:
            if len(positions) > 1:
                second = positions[1][0]
                gap = positions[0][1] - positions[1][1]
                lines = [
                    f"{leader} leads {second} by {gap:.1f} meters at the midway point!",
                    f"Halfway through and {leader} is in command!",
                    f"{leader} and {second} are the main protagonists so far!",
                    f"The race is developing with {leader} in front!",
                    f"{second} tracks {leader} closely at the halfway mark!",
                ]
            else:
                lines = [f"{leader} continues to lead at halfway!"]
        elif race_progress < 0.75:
            lines = [
                f"Into the business end! {leader} still leads!",
                f"The race is getting serious! {leader} out front!",
                f"{leader} tries to maintain the advantage!",
                f"Pressure is mounting on {leader}!",
                f"The challenges are coming for {leader}!",
                f"{leader} must respond to the pressure!",
            ]
        elif race_progress < 0.9:
            if len(positions) > 2:
                lines = [
                    f"{leader} is being pressed by multiple challengers!",
                    f"The final stretch! {leader} versus the chasers!",
                    f"{leader} is fighting for every meter!",
                    f"This is intense! {leader} trying to hold on!",
                    f"{leader} and the field are locked in battle!",
                    f"Down to the wire! {leader} is under siege!",
                ]
            else:
                lines = [f"{leader} in the final stretch!"]
        else:
            lines = [
                f"The finish line looms! {leader} is straining!",
                f"Final meters! {leader} is giving everything!",
                f"{leader} can almost touch the line!",
                f"The wire approaches! {leader} in front!",
            ]
        
        return random.choice(lines)

    def get_speed_position_commentary(self, positions, race_distance):
        """Commentary about speed and relative positions"""
        if len(positions) < 2:
            return ""
        
        leader = positions[0][0]
        second = positions[1][0]
        gap = positions[0][1] - positions[1][1]
        
        if gap < 1.0:
            lines = [
                f"{leader} and {second} are virtually inseparable!",
                f"Nothing between {leader} and {second}!",
                f"{leader} and {second} are nose to nose!",
                f"It's tight at the front! {leader} just ahead of {second}!",
                f"{leader} marginally ahead of {second}!",
            ]
        elif gap < 3.0:
            lines = [
                f"{leader} has a narrow lead over {second}!",
                f"{second} is within striking distance of {leader}!",
                f"{leader} holds a slim advantage over {second}!",
                f"Close racing! {leader} {gap:.1f}m ahead of {second}!",
            ]
        elif gap < 5.0:
            lines = [
                f"{leader} has opened up {gap:.1f}m on {second}!",
                f"{second} trails {leader} by {gap:.1f} meters!",
                f"{leader} has some breathing room from {second}!",
                f"A gap of {gap:.1f}m between {leader} and {second}!",
            ]
        else:
            lines = [
                f"{leader} is pulling away! {gap:.1f}m clear of {second}!",
                f"{leader} has established a commanding lead over {second}!",
                f"Dominant from {leader}! {gap:.1f}m ahead of {second}!",
                f"{second} has work to do! {gap:.1f}m behind {leader}!",
            ]
        
        # Add 3-way battles
        if len(positions) > 2:
            third = positions[2][0]
            gap_to_third = positions[1][1] - positions[2][1]
            if gap_to_third < 2.0:
                three_way_lines = [
                    f"A three-way battle! {leader}, {second}, and {third}!",
                    f"{leader}, {second}, and {third} are locked together!",
                    f"Triple threat! {leader}, {second}, {third} all in contention!",
                ]
                return random.choice(three_way_lines)
        
        return random.choice(lines)

    def get_finish_commentary(self, finished, positions, race_progress):
        """Commentary for horses crossing the finish line"""
        if not finished or race_progress < 0.85:
            return ""
        
        newly_finished = [name for name in finished if name not in [c.split()[0] for c in self.commentary_history[-3:]]]
        
        if not newly_finished:
            return ""
        
        name = newly_finished[0]
        finish_position = len(finished)
        
        if finish_position == 1:
            lines = [
                f"{name} crosses the line! Victory!",
                f"And {name} wins it!",
                f"{name} takes the prize! What a performance!",
                f"They've done it! {name} wins!",
                f"{name} victorious! A brilliant run!",
                f"Winner! {name} claims glory!",
                f"{name} powers home to win!",
                f"Triumph for {name}!",
            ]
        elif finish_position == 2:
            lines = [
                f"{name} finishes second! A strong showing!",
                f"{name} takes second place!",
                f"Runner-up spot for {name}!",
                f"{name} in second! Fought hard!",
            ]
        elif finish_position == 3:
            lines = [
                f"{name} claims third! On the podium!",
                f"{name} finishes in third place!",
                f"Third for {name}! A solid effort!",
            ]
        else:
            lines = [
                f"{name} crosses the line in {finish_position}th!",
                f"{name} finishes {finish_position}th!",
                f"{name} completes the race!",
            ]
        
        return random.choice(lines)

    def update_display(self, frame_positions, race_distance):
        """Update the visual display with current positions"""
        if not self.sim_data:
            return
            
        w = self.canvas.winfo_width() or 800
        track_width = w - 2 * self.track_margin
        
        # Update remaining distance and lead speed
        if frame_positions:
            leader_dist = frame_positions[0][1]
            remaining = max(0, race_distance - leader_dist)
            
            # Calculate lead speed in km/h
            leader_name = frame_positions[0][0]
            uma_stat = self.sim_data['uma_stats'][leader_name]
            current_speed = self.calculate_current_speed(leader_name, uma_stat, race_distance, self.sim_data['race_type'])
            speed_kmh = current_speed * 3.6
            
            self.remaining_label.config(text=f"Remaining: {remaining:.0f}m | Lead: {speed_kmh:.1f} km/h")
        
        # Update uma positions
        for name, (circle, text, speed_text) in self.uma_icons.items():
            if name not in [pos[0] for pos in frame_positions] and not self.horse_finished[name] and not self.horse_dnf[name]['dnf']:
                continue
                
            # Find position index
            position = 1
            distance = 0
            for i, (n, d) in enumerate(frame_positions):
                if n == name:
                    position = i + 1
                    distance = d
                    break
            
            # Calculate x position on track
            progress = min(1.0, distance / race_distance)
            x_pos = self.track_margin + (progress * track_width)
            
            # Calculate y position based on lane
            y_pos = 20 + (position - 1) * self.lane_height
            
            # Update circle position
            self.canvas.coords(circle, x_pos-8, y_pos-8, x_pos+8, y_pos+8)
            
            # Update name text position
            self.canvas.coords(text, x_pos, y_pos-10)
            
            # Update speed text
            if name in self.sim_data['uma_stats']:
                uma_stat = self.sim_data['uma_stats'][name]
                current_speed = self.calculate_current_speed(name, uma_stat, race_distance, self.sim_data['race_type'])
                speed_kmh = current_speed * 3.6
                self.canvas.coords(speed_text, x_pos, y_pos+10)
                self.canvas.itemconfig(speed_text, text=f"{speed_kmh:.1f} km/h")
            
            # Color coding for status
            if self.horse_finished[name]:
                self.canvas.itemconfig(circle, fill='gold')
            elif self.horse_dnf[name]['dnf']:
                self.canvas.itemconfig(circle, fill='black')
            elif self.horse_skills[name]['active']:
                self.canvas.itemconfig(circle, fill='yellow')
            elif self.horse_incidents[name]['type']:
                self.canvas.itemconfig(circle, fill='orange')
            else:
                self.canvas.itemconfig(circle, fill=self.uma_colors[name])
        
        self.canvas.update()

    def stop_simulation(self):
        """Stop the simulation"""
        if self.sim_after_id:
            self.after_cancel(self.sim_after_id)
            self.sim_after_id = None
            
        self.sim_running = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.append_output("Simulation stopped.\n")

    def reset_simulation(self):
        """Reset the simulation to initial state"""
        self.stop_simulation()
        
        self.sim_time = 0.0
        self.finish_times.clear()
        self.incidents_occurred.clear()
        self.overtakes.clear()
        self.skill_activations.clear()
        self.last_commentary_time = 0
        self.previous_positions.clear()
        
        # Clear real-time data
        self.horse_distances.clear()
        self.horse_finished.clear()
        self.horse_incidents.clear()
        self.horse_skills.clear()
        self.current_positions.clear()
        self.horse_fatigue.clear()
        self.horse_momentum.clear()
        self.horse_last_position.clear()
        self.horse_stamina.clear()
        self.horse_dnf.clear()
        
        # Reset commentary tracking
        self.distance_callouts_made.clear()
        self.last_incident_commentary = 0
        self.last_position_commentary = 0
        self.last_speed_commentary = 0
        self.commentary_history.clear()
        
        self.output_text.delete(1.0, tk.END)
        self.remaining_label.config(text="Remaining: -- | Lead: -- km/h")
        
        # Reset uma icons to start
        if self.sim_data:
            self.initialize_uma_icons()
        
        self.append_output("Simulation reset.\n")

    def display_final_results(self):
        """Display final race results including DNFs"""
        if not self.finish_times and not any(dnf['dnf'] for dnf in self.horse_dnf.values()):
            self.append_output("No results to display.\n")
            return
            
        self.append_output("\n" + "="*50 + "\n")
        self.append_output("FINAL RACE RESULTS\n")
        self.append_output("="*50 + "\n")
        
        # Sort finished umas by time
        finished_umas = sorted(self.finish_times.items(), key=lambda x: x[1])
        
        # Display finished umas
        for i, (name, time) in enumerate(finished_umas):
            self.append_output(f"{i+1}. {name} - {time:.2f}s\n")
        
        # Display DNF umas
        dnf_umas = [(name, dnf_data) for name, dnf_data in self.horse_dnf.items() if dnf_data['dnf']]
        if dnf_umas:
            self.append_output("\nDNF (Did Not Finish):\n")
            for name, dnf_data in dnf_umas:
                self.append_output(f"- {name} (DNF at {dnf_data['dnf_distance']:.0f}m - {dnf_data['reason']})\n")
        
        # Calculate statistics
        total_starters = len(self.uma_icons)
        total_finished = len(finished_umas)
        total_dnf = len(dnf_umas)
        
        if finished_umas:
            winning_time = finished_umas[0][1]
            if len(finished_umas) > 1:
                last_time = finished_umas[-1][1]
                time_gap = last_time - winning_time
            else:
                time_gap = 0.0
        else:
            winning_time = 0.0
            time_gap = 0.0
        
        self.append_output(f"\nSUMMARY: {total_finished}/{total_starters} finished, {total_dnf} DNF\n")
        if finished_umas:
            self.append_output(f"Winning time: {winning_time:.2f}s\n")
            self.append_output(f"Time gap: {time_gap:.2f}s\n")
        self.append_output("="*50 + "\n")

    def append_output(self, text):
        """Append text to output area"""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.update()

if __name__ == "__main__":
    app = UmaRacingGUI()
    app.mainloop()