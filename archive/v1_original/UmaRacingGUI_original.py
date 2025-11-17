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
        
        self.title("Uma Musume Racing Simulator")
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
            
            # Convert the config format to simulation format
            self.sim_data = self.convert_config_to_sim_data(config_data)
            
            self.append_output(f"Loaded racing config: {file_path}\n")
            self.append_output(f"Race: {config_data.get('race', {}).get('name', 'Unknown')}\n")
            self.append_output(f"Race distance: {self.sim_data.get('race_distance', 0)}m\n")
            self.append_output(f"Umas: {len(config_data.get('umas', []))}\n")
            
            self.initialize_uma_icons()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load config file:\n{str(e)}")
            self.append_output(f"Error loading config: {str(e)}\n")
    
    def convert_config_to_sim_data(self, config_data):
        """Convert the JSON config format to simulation data format with IMPROVED balance"""
        race_info = config_data.get('race', {})
        umas = config_data.get('umas', [])
        
        race_distance = race_info.get('distance', 2500)
        
        # REALISTIC UMA MUSUME SPEED PARAMETERS - MORE BALANCED
        base_speed = 16.0  # m/s = ~57.6 km/h
        top_speed = 19.0   # m/s = ~68.4 km/h
        sprint_speed = 21.0  # m/s = ~75.6 km/h for final bursts
        
        # Generate positions data
        positions = {}
        
        # Calculate performance with MORE BALANCED STAT WEIGHTS
        uma_stats = {}
        for uma in umas:
            name = uma['name']
            stats = uma['stats']
            running_style = uma.get('running_style', 'PC')
            
            # MORE BALANCED STAT DISTRIBUTION
            base_performance = (
                stats.get('Speed', 0) * 0.30 +
                stats.get('Stamina', 0) * 0.25 +
                stats.get('Power', 0) * 0.20 +
                stats.get('Guts', 0) * 0.15 +
                stats.get('Wit', 0) * 0.10
            )
            
            distance_apt = uma.get('distance_aptitude', {})
            race_type = race_info.get('type', 'Medium')
            surface_apt = uma.get('surface_aptitude', {})
            surface = race_info.get('surface', 'Turf')
            
            apt_multipliers = {
                'S': 1.04, 'A': 1.02, 'B': 1.00, 'C': 0.98,
                'D': 0.96, 'E': 0.94, 'F': 0.92, 'G': 0.90
            }
            
            distance_multiplier = apt_multipliers.get(distance_apt.get(race_type, 'B'), 1.0)
            surface_multiplier = apt_multipliers.get(surface_apt.get(surface, 'B'), 1.0)
            
            # BALANCED RUNNING STYLE MECHANICS
            running_style_bonuses = {
                'FR': {
                    'position_pref': range(1, 3),
                    'early_speed_bonus': 0.06,
                    'mid_speed_bonus': 0.02,
                    'final_speed_penalty': -0.04,
                    'stamina_multiplier': 1.10,
                    'overtake_penalty': 0.08,
                    'lead_bonus': 0.04,
                    'skill_trigger_zones': [0.0, 0.3, 0.6],
                },
                'PC': {
                    'position_pref': range(2, 6),
                    'early_speed_bonus': 0.03,
                    'mid_speed_bonus': 0.04,
                    'final_speed_penalty': 0.00,
                    'stamina_multiplier': 1.0,
                    'overtake_penalty': 0.02,
                    'position_bonus': 0.03,
                    'skill_trigger_zones': [0.2, 0.5, 0.8],
                },
                'LS': {
                    'position_pref': range(4, 8),
                    'early_speed_penalty': -0.03,
                    'mid_speed_bonus': 0.03,
                    'final_speed_bonus': 0.06,
                    'stamina_multiplier': 0.95,
                    'overtake_bonus': 0.06,
                    'comeback_bonus': 0.08,
                    'skill_trigger_zones': [0.4, 0.7, 0.9],
                },
                'EC': {
                    'position_pref': range(6, 12),
                    'early_speed_penalty': -0.05,
                    'mid_speed_penalty': -0.01,
                    'final_speed_bonus': 0.08,
                    'stamina_multiplier': 0.90,
                    'overtake_bonus': 0.08,
                    'final_surge_multiplier': 1.10,
                    'skill_trigger_zones': [0.6, 0.85, 0.95],
                }
            }
            
            style_bonus = running_style_bonuses.get(running_style, running_style_bonuses['PC'])
            
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
            }
        
        # IMPROVED NORMALIZATION - MUCH TIGHTER PERFORMANCE RANGE
        performances = [stats['base_performance'] for stats in uma_stats.values()]
        if performances:
            min_perf = min(performances)
            max_perf = max(performances)
            
            for name in uma_stats:
                if max_perf - min_perf > 0:
                    normalized = (uma_stats[name]['base_performance'] - min_perf) / (max_perf - min_perf)
                    # MUCH TIGHTER RANGE: 0.95 to 1.05
                    compressed = 0.95 + (normalized * 0.10)
                    uma_stats[name]['base_performance'] = compressed
                else:
                    uma_stats[name]['base_performance'] = 1.0
        
        # Generate race progression with NO TIME LIMIT
        max_time = 3000
        time_intervals = list(range(0, max_time + 1, 1))
        
        horse_distances = {name: 0.0 for name in uma_stats.keys()}
        horse_finished = {name: False for name in uma_stats.keys()}
        horse_incidents = {name: {'type': None, 'duration': 0, 'start_time': 0} for name in uma_stats.keys()}
        horse_skills = {name: {'cooldown': 0, 'last_activation': 0, 'active': False} for name in uma_stats.keys()}
        current_positions = {name: 1 for name in uma_stats.keys()}
        horse_fatigue = {name: 0.0 for name in uma_stats.keys()}
        horse_momentum = {name: 1.0 for name in uma_stats.keys()}
        horse_last_position = {name: 1 for name in uma_stats.keys()}
        horse_stamina = {name: 100.0 for name in uma_stats.keys()}
        
        for t in time_intervals:
            frame_positions = []
            
            for name, stats in uma_stats.items():
                if horse_finished[name]:
                    distance_covered = race_distance
                    frame_positions.append((name, distance_covered, None, False))
                    continue
                    
                incident = horse_incidents[name]
                if incident['type'] and t >= incident['start_time'] + incident['duration']:
                    incident['type'] = None
                    horse_momentum[name] = 1.01  # Minimal momentum recovery

                # GREATLY REDUCED INCIDENT FREQUENCY
                incident_chance = 0.0005 - (stats['wisdom'] / 200000.0)
                running_style = stats['running_style']
                
                if running_style == 'FR':
                    incident_chance *= 1.1
                elif running_style == 'EC':
                    incident_chance *= 0.9
                    
                if not incident['type'] and random.random() < incident_chance and t > 20:
                    race_progress = horse_distances[name] / race_distance
                    
                    if race_progress < 0.1:
                        incident_types = [('slow_start', 1, 0.95)]
                    elif race_progress < 0.4:
                        incident_types = [
                            ('stumble', 1, 0.96),
                            ('crowded', 1, 0.95),
                            ('blocked', 1, 0.94)
                        ]
                    elif race_progress < 0.7:
                        incident_types = [
                            ('stamina_drain', 2, 0.97),
                            ('position_loss', 1, 0.98)
                        ]
                    else:
                        incident_types = [
                            ('final_struggle', 1, 0.96),
                            ('exhaustion', 2, 0.92)
                        ]
                    
                    incident_type, duration, speed_mult = random.choice(incident_types)
                    incident['type'] = incident_type
                    incident['duration'] = duration
                    incident['start_time'] = t
                    horse_momentum[name] = 0.92  # Reduced penalty

                skill = horse_skills[name]
                if skill['cooldown'] > 0:
                    skill['cooldown'] -= 1
                    if skill['cooldown'] == 0:
                        skill['active'] = False

                # IMPROVED SKILL ACTIVATION
                base_skill_chance = (stats['wisdom'] / 2000.0) * 0.15
                race_progress = horse_distances[name] / race_distance if race_distance > 0 else 0
                current_pos = current_positions[name]
                
                style_bonus = stats['style_bonus']
                skill_trigger_zones = style_bonus.get('skill_trigger_zones', [0.2, 0.5, 0.8])
                
                skill_multiplier = 1.0
                in_trigger_zone = any(abs(race_progress - zone) < 0.1 for zone in skill_trigger_zones)
                if in_trigger_zone:
                    skill_multiplier *= 1.8
                
                if current_pos in style_bonus['position_pref']:
                    skill_multiplier *= 1.3
                
                if running_style in ['LS', 'EC'] and current_pos >= 6 and race_progress > 0.6:
                    skill_multiplier *= 1.5
                
                if running_style == 'FR' and current_pos <= 2 and race_progress > 0.3:
                    skill_multiplier *= 1.4

                skill_chance = base_skill_chance * skill_multiplier

                if skill['cooldown'] <= 0 and random.random() < skill_chance and t > 10:
                    skill_duration = 5 + min(3, stats['wisdom'] // 400)
                    skill['cooldown'] = skill_duration + random.randint(0, 4)
                    skill['last_activation'] = t
                    skill['active'] = True
                    horse_momentum[name] = 1.08  # Reduced bonus

                perf = stats['base_performance']
                style_bonus = stats['style_bonus']

                if t == 0:
                    distance_covered = 0
                    horse_fatigue[name] = 0.0
                    horse_momentum[name] = 1.0
                    horse_last_position[name] = 1
                    horse_stamina[name] = 100.0
                else:
                    # IMPROVED STAMINA SYSTEM
                    base_stamina_drain = 0.2  # Further reduced drain
                    stamina_multiplier = style_bonus.get('stamina_multiplier', 1.0)
                    
                    if current_positions[name] <= 2 and running_style != 'FR':
                        stamina_multiplier *= 1.05
                    elif current_positions[name] in style_bonus['position_pref']:
                        stamina_multiplier *= 0.98
                    
                    horse_stamina[name] = max(0, horse_stamina[name] - base_stamina_drain * stamina_multiplier)
                    
                    stamina_factor = max(0.90, horse_stamina[name] / 100.0)
                    if horse_stamina[name] < 25:
                        stamina_factor *= 0.98
                    elif horse_stamina[name] < 60:
                        stamina_factor *= 0.99

                    incident_multiplier = 1.0
                    if incident['type']:
                        incident_effects = {
                            'slow_start': 0.95, 'stumble': 0.96, 'crowded': 0.95,
                            'blocked': 0.94, 'stamina_drain': 0.97, 'position_loss': 0.98,
                            'final_struggle': 0.96, 'exhaustion': 0.92
                        }
                        incident_multiplier = incident_effects.get(incident['type'], 1.0)

                    skill_multiplier = 1.0
                    if skill['active']:
                        skill_multiplier = 1.05  # Reduced bonus

                    race_progress = min(1.0, horse_distances[name] / race_distance) if race_distance > 0 else 0

                    # IMPROVED RACE PHASE CALCULATION
                    if race_progress < 0.2:
                        if 'early_speed_bonus' in style_bonus:
                            phase_multiplier = 0.97 + style_bonus['early_speed_bonus']
                        elif 'early_speed_penalty' in style_bonus:
                            phase_multiplier = 0.97 + style_bonus['early_speed_penalty']
                        else:
                            phase_multiplier = 0.97
                        horse_fatigue[name] += 0.001
                        
                    elif race_progress < 0.5:
                        if 'mid_speed_bonus' in style_bonus:
                            phase_multiplier = 0.99 + style_bonus['mid_speed_bonus']
                        elif 'mid_speed_penalty' in style_bonus:
                            phase_multiplier = 0.99 + style_bonus['mid_speed_penalty']
                        else:
                            phase_multiplier = 0.99
                        power_bonus = min(0.04, stats['power'] / 25000.0)
                        phase_multiplier += power_bonus
                        horse_fatigue[name] += 0.0015 * max(0.3, (1 - stats['stamina'] / 3000.0))
                        
                    elif race_progress < 0.8:
                        phase_multiplier = 1.00
                        power_bonus = min(0.03, stats['power'] / 30000.0)
                        phase_multiplier += power_bonus
                        phase_multiplier *= (1 - min(0.05, horse_fatigue[name] * 0.03))
                        
                    else:
                        if 'final_speed_bonus' in style_bonus:
                            phase_multiplier = 1.02 + style_bonus['final_speed_bonus']
                        elif 'final_speed_penalty' in style_bonus:
                            phase_multiplier = 1.02 + style_bonus['final_speed_penalty']
                        else:
                            phase_multiplier = 1.02
                        
                        if running_style == 'EC' and race_progress > 0.9:
                            final_surge = style_bonus.get('final_surge_multiplier', 1.0)
                            phase_multiplier *= final_surge
                            
                        guts_bonus = min(0.10, stats['guts'] / 8000.0)
                        phase_multiplier += guts_bonus
                        fatigue_resistance = 0.4 if stats['running_style'] in ['LS', 'EC'] else 0.5
                        phase_multiplier *= (1 - min(0.08, horse_fatigue[name] * fatigue_resistance))

                    # IMPROVED POSITION BONUSES
                    position_bonus = 1.0
                    ideal_range = style_bonus['position_pref']
                    current_pos = current_positions[name]
                    
                    if current_pos in ideal_range:
                        position_bonus = 1.02 + style_bonus.get('position_bonus', 0.0)
                        horse_momentum[name] = min(1.04, horse_momentum[name] + 0.02)
                    else:
                        position_bonus = 0.99
                        if current_pos < min(ideal_range):
                            overtake_effect = style_bonus.get('overtake_penalty', 0.0)
                            position_bonus -= overtake_effect * 0.3
                        elif current_pos > max(ideal_range):
                            if running_style in ['LS', 'EC'] and race_progress > 0.7:
                                overtake_effect = style_bonus.get('overtake_bonus', 0.0)
                                position_bonus += overtake_effect * 0.5
                        horse_momentum[name] = max(0.96, horse_momentum[name] - 0.01)

                    if running_style == 'FR' and current_pos == 1:
                        position_bonus += style_bonus.get('lead_bonus', 0.0) * 0.5

                    if running_style in ['LS', 'EC'] and horse_last_position[name] > current_pos and race_progress > 0.7:
                        position_bonus += style_bonus.get('comeback_bonus', 0.0) * 0.5

                    if horse_last_position[name] > current_pos:
                        horse_momentum[name] = min(1.06, horse_momentum[name] + 0.03)
                    elif horse_last_position[name] < current_pos:
                        horse_momentum[name] = max(0.94, horse_momentum[name] - 0.02)

                    random_factor = 0.99 + 0.02 * random.random() * horse_momentum[name]

                    speed_multiplier = phase_multiplier * perf * random_factor * incident_multiplier * skill_multiplier * position_bonus * stamina_factor

                    # Apply speed limits
                    current_speed = base_speed * speed_multiplier
                    
                    if race_progress < 0.8:
                        current_speed = min(current_speed, top_speed)
                    else:
                        current_speed = min(current_speed, stats['sprint_speed'])

                    time_delta = 1.0
                    distance_this_interval = current_speed * time_delta

                    distance_covered = horse_distances[name] + distance_this_interval

                if distance_covered >= race_distance:
                    distance_covered = race_distance
                    horse_finished[name] = True

                horse_distances[name] = distance_covered
                horse_incidents[name] = incident
                horse_skills[name] = skill
                horse_last_position[name] = current_positions[name]
                
                frame_positions.append((name, distance_covered, incident['type'], skill['active']))

            frame_positions.sort(key=lambda x: x[1], reverse=True)
            for i, (name, _, _, _) in enumerate(frame_positions):
                current_positions[name] = i + 1

            positions[t] = frame_positions

            # REMOVED TIME LIMIT - only stop when all finish
            if all(horse_finished.values()):
                for remaining_t in range(t + 1, max_time + 1):
                    positions[remaining_t] = frame_positions
                break

        return {
            'race_distance': race_distance,
            'positions': positions,
            'uma_stats': uma_stats
        }

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
            
        positions_data = self.sim_data.get('positions', {})
        if not positions_data:
            self.append_output("Warning: No position data found in config.\n")
            return
            
        first_time = min(positions_data.keys())
        initial_positions = positions_data[first_time]
        
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'cyan', 'magenta', 'darkgreen',
                 'darkred', 'darkblue', 'darkorange', 'darkviolet', 'gold', 'maroon', 'navy', 'teal',
                 'coral', 'lime', 'indigo', 'salmon', 'olive', 'steelblue']
        
        for i, (name, distance, _, _) in enumerate(initial_positions):
            color = colors[i % len(colors)]
            self.uma_colors[name] = color
            
            y_position = 20 + i * self.lane_height
            
            circle = self.canvas.create_oval(0, 0, 0, 0, fill=color, tags=name, outline='black')
            text = self.canvas.create_text(0, 0, text=name, fill='black', anchor=tk.S, font=('Arial', 7, 'bold'))
            speed = self.canvas.create_text(0, 0, text="0 km/h", fill='darkblue', anchor=tk.N, font=('Arial', 6))
            
            self.uma_icons[name] = (circle, text, speed)
            
        self.append_output(f"Initialized {len(initial_positions)} umas on track.\n")
        self._on_frame_configure()

    def start_simulation(self):
        """Start the pre-calculated simulation"""
        if not self.sim_data:
            self.append_output("Error: No simulation data loaded. Please load a racing config first.\n")
            return
            
        if self.sim_running:
            self.append_output("Simulation is already running.\n")
            return
            
        self.sim_running = True
        self.sim_time = 0.0
        self.fired_event_seconds.clear()
        self.finish_times.clear()
        self.incidents_occurred.clear()
        self.overtakes.clear()
        self.skill_activations.clear()
        self.last_commentary_time = 0
        self.previous_positions = {}
        
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        self.append_output("Simulation started!\n")
        
        self._run_sim_tick()
        
    def _run_sim_tick(self):
        """Main simulation tick for pre-calculated simulation"""
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
                    
            frame_dt = 0.05
            self.sim_time += frame_dt * mult
            
            race_distance = self.sim_data.get('race_distance', 2500)
            positions_data = self.sim_data.get('positions', {})
            available_times = sorted(positions_data.keys())
            
            if not available_times:
                self.sim_running = False
                return

            t_int = int(self.sim_time)
            
            lower_time = max([t for t in available_times if t <= t_int], default=available_times[0])
            upper_time = min([t for t in available_times if t >= t_int + 1], default=available_times[-1])
            
            if upper_time == lower_time:
                upper_time = min(lower_time + 1, available_times[-1])
            
            pos_lower_list = positions_data.get(lower_time, [])
            pos_upper_list = positions_data.get(upper_time, pos_lower_list)
            
            pos_lower = {name: (dist, incident, skill) for name, dist, incident, skill in pos_lower_list}
            pos_upper = {name: (dist, incident, skill) for name, dist, incident, skill in pos_upper_list}
            
            if upper_time != lower_time:
                alpha = (self.sim_time - lower_time) / (upper_time - lower_time)
            else:
                alpha = 0.0
            
            current_positions = []
            current_skill_activations = {}
            for name in self.uma_icons.keys():
                lower_data = pos_lower.get(name, (0, None, False))
                upper_data = pos_upper.get(name, lower_data)
                
                lower_dist, lower_incident, lower_skill = lower_data
                upper_dist, upper_incident, upper_skill = upper_data
                
                interp_dist = lower_dist + alpha * (upper_dist - lower_dist)
                current_incident = lower_incident if alpha < 0.5 else upper_incident
                current_skill = lower_skill if alpha < 0.5 else upper_skill
                
                current_positions.append((name, interp_dist, current_incident, current_skill))
                current_skill_activations[name] = current_skill
            
            current_positions.sort(key=lambda x: x[1], reverse=True)
            
            current_incidents = {name: incident for name, _, incident, _ in current_positions if incident}
            
            # Generate commentary
            if self.sim_time - self.last_commentary_time > 2.5:
                leader_dist = current_positions[0][1] if current_positions else 0
                remaining_distance = max(0, race_distance - leader_dist)
                commentaries = self.get_commentary(
                    self.sim_time, current_positions, race_distance, 
                    remaining_distance, current_incidents, set(self.finish_times.keys()),
                    current_skill_activations
                )
                
                for commentary in commentaries[:2]:
                    self.append_output(f"[{self.sim_time:.1f}s] {commentary}\n")
                    self.last_commentary_time = self.sim_time
            
            # Update display
            w = self.canvas.winfo_width() or 800
            start_x = self.track_margin
            finish_x = w - self.track_margin

            leader_name = None
            leader_kmh = 0
            remaining_leader = race_distance
            
            if current_positions:
                leader_name = current_positions[0][0]
                leader_dist = current_positions[0][1]
                remaining_leader = max(0, int(round(race_distance - leader_dist)))
                
                if self.previous_positions and leader_name in self.previous_positions:
                    prev_dist, prev_time = self.previous_positions[leader_name]
                    time_diff = self.sim_time - prev_time
                    if time_diff > 0:
                        leader_inst_mps = (leader_dist - prev_dist) / time_diff
                        leader_kmh = leader_inst_mps * 3.6
                
                if leader_dist >= race_distance and leader_name not in self.finish_times:
                    self.finish_times[leader_name] = self.sim_time
            
            self.remaining_label.config(text=f"Remaining: {remaining_leader}m | Lead: {leader_kmh:.1f} km/h")

            current_previous_positions = self.previous_positions.copy()
            self.previous_positions = {}
            
            for i, (name, distance, incident, skill_active) in enumerate(current_positions):
                self.previous_positions[name] = (distance, self.sim_time)
                
                ratio = min(1.0, float(distance) / race_distance) if race_distance > 0 else 0.0
                x = start_x + ratio * (finish_x - start_x)
                cid, tid, sid = self.uma_icons.get(name, (None, None, None))
                
                if cid:
                    y_position = 20 + i * self.lane_height
                    
                    original_color = self.uma_colors.get(name, 'blue')
                    if skill_active:
                        outline_color = 'gold'
                        outline_width = 3
                    elif incident:
                        outline_color = 'red'
                        outline_width = 2
                    else:
                        outline_color = 'black'
                        outline_width = 1
                    
                    self.canvas.itemconfig(cid, fill=original_color, outline=outline_color, width=outline_width)
                    self.canvas.coords(cid, x-6, y_position-6, x+6, y_position+6)
                    
                if tid:
                    self.canvas.coords(tid, x, y_position-10)
                    
                if sid:
                    speed_text = "0 km/h"
                    if name in current_previous_positions:
                        prev_dist, prev_time = current_previous_positions[name]
                        time_diff = self.sim_time - prev_time
                        if time_diff > 0:
                            inst_mps = (distance - prev_dist) / time_diff
                            inst_kmh = inst_mps * 3.6
                            speed_text = f"{inst_kmh:.1f} km/h"
                    
                    self.canvas.coords(sid, x, y_position+10)
                    self.canvas.itemconfig(sid, text=speed_text)
                
                if distance >= race_distance and name not in self.finish_times:
                    self.finish_times[name] = self.sim_time

            all_finished = len(self.finish_times) == len(self.uma_icons)
            
            # REMOVED TIME LIMIT CHECK - only stop when all finish
            if all_finished:
                self.sim_running = False
                self.start_btn.config(state='normal')
                self.stop_btn.config(state='disabled')
                self.display_final_results()
                return

            self.sim_after_id = self.after(int(frame_dt * 1000 / mult), self._run_sim_tick)
            
        except Exception as e:
            self.append_output(f"Simulation error: {str(e)}\n")
            self.sim_running = False
            self.start_btn.config(state='normal')
            self.stop_btn.config(state='disabled')

    def get_commentary(self, current_time, positions, race_distance, remaining_distance, incidents, finished_umas, skill_activations):
        """Generate realistic uma racing commentary"""
        commentaries = []
        
        active_positions = [p for p in positions if p[0] not in finished_umas]
        
        if not active_positions:
            return commentaries
        
        # Distance-based commentaries
        if remaining_distance > 0:
            if remaining_distance <= 15 and current_time - self.last_commentary_time > 1:
                commentaries.append("FINAL STRETCH! They're charging to the wire!")
            elif remaining_distance <= 40 and current_time - self.last_commentary_time > 2:
                commentaries.append("40 meters to go! The finish line is in sight!")
            elif remaining_distance <= 100 and current_time - self.last_commentary_time > 3:
                commentaries.append("100 meters remaining! This is where champions are made!")
            elif remaining_distance <= 200 and current_time - self.last_commentary_time > 4:
                commentaries.append("Entering the final turn! The pace is electrifying!")
            elif remaining_distance <= 400 and current_time - self.last_commentary_time > 6:
                commentaries.append("Approaching the final 400 meters! The race is heating up!")
        
        # Skill activation commentaries
        for name, is_skill_active in skill_activations.items():
            if is_skill_active and (name, current_time) not in self.skill_activations:
                self.skill_activations.add((name, current_time))
                
                style_commentaries = {
                    'FR': [
                        f"{name} bursts forward with explosive acceleration!",
                        f"{name} shows incredible front-running power!",
                        f"Amazing start from {name} taking the lead!"
                    ],
                    'PC': [
                        f"{name} maintains perfect pace in the middle!",
                        f"{name} times their move perfectly!",
                        f"Great positioning from {name} in the pack!"
                    ],
                    'LS': [
                        f"{name} unleashes a powerful late surge!",
                        f"{name} charges from behind with incredible speed!",
                        f"Watch {name} making up ground rapidly!"
                    ],
                    'EC': [
                        f"{name} shows an explosive final sprint!",
                        f"{name} closes with unbelievable speed!",
                        f"Incredible finishing kick from {name}!"
                    ]
                }
                
                uma_style = None
                if self.sim_data and 'uma_stats' in self.sim_data:
                    uma_style = self.sim_data['uma_stats'].get(name, {}).get('running_style', 'PC')
                
                skill_list = style_commentaries.get(uma_style, [
                    f"{name} activates their special move! Incredible acceleration!",
                    f"{name} uses their unique skill! They're gaining ground!",
                    f"Watch out! {name} shows their true potential!"
                ])
                
                commentaries.append(random.choice(skill_list))
        
        # Position and overtake commentaries
        if len(active_positions) >= 2:
            leader = active_positions[0][0]
            second = active_positions[1][0]
            leader_dist = active_positions[0][1]
            second_dist = active_positions[1][1]
            gap = leader_dist - second_dist
            
            if gap <= 0.05 and current_time - self.last_commentary_time > 2:
                commentaries.append(f"{second} is neck and neck with {leader}! What a battle up front!")
            elif gap <= 0.2 and current_time - self.last_commentary_time > 3:
                commentaries.append(f"{second} is pressing {leader} hard! Intense competition!")
            
            # Multi-horse battle commentary
            if len(active_positions) >= 4:
                third_gap = active_positions[0][1] - active_positions[3][1]
                if third_gap <= 0.8 and current_time - self.last_commentary_time > 5:
                    commentaries.append(f"Four horses in contention! {active_positions[1][0]}, {active_positions[2][0]}, and {active_positions[3][0]} are all challenging!")
            
            # Overtake commentaries
            if len(active_positions) >= 3:
                for i in range(1, len(active_positions)-1):
                    current_uma = active_positions[i][0]
                    behind_uma = active_positions[i+1][0]
                    if (active_positions[i][1] > active_positions[i+1][1] + 0.15 and 
                        (current_uma, behind_uma) not in self.overtakes):
                        self.overtakes.add((current_uma, behind_uma))
                        
                        if i <= 3:
                            commentaries.append(f"{current_uma} overtakes {behind_uma} for a top position!")
                        elif i >= len(active_positions) - 4:
                            commentaries.append(f"{current_uma} moves past {behind_uma} at the back!")
                        else:
                            commentaries.append(f"{current_uma} passes {behind_uma} in the mid-pack!")
        
        # Incident commentaries
        for name, incident_type in incidents.items():
            if (name not in finished_umas and incident_type and 
                (name, incident_type) not in self.incidents_occurred):
                self.incidents_occurred.add((name, incident_type))
                incident_messages = {
                    'slow_start': f"{name} had a slow start from the gates!",
                    'stumble': f"Oh no! {name} stumbles and loses momentum!",
                    'crowded': f"{name} gets crowded and can't find racing room!",
                    'blocked': f"{name} is completely blocked and loses valuable ground!",
                    'stamina_drain': f"{name} is struggling with stamina in the middle stages!",
                    'position_loss': f"{name} loses their ideal racing position!",
                    'final_struggle': f"{name} is having trouble in the final stretch!",
                    'exhaustion': f"{name} looks completely exhausted in the final meters!"
                }
                commentaries.append(incident_messages.get(incident_type, f"{name} encounters trouble!"))
        
        # Running style specific commentaries
        if random.random() < 0.08 and current_time - self.last_commentary_time > 8:
            if active_positions:
                leader_style = None
                if self.sim_data and 'uma_stats' in self.sim_data:
                    leader_style = self.sim_data['uma_stats'].get(active_positions[0][0], {}).get('running_style', 'PC')
                
                style_commentaries = {
                    'FR': "The front runner is setting a blistering pace up front!",
                    'PC': "The pace chaser is perfectly positioned just behind the leaders!",
                    'LS': "The late surger is biding their time, waiting to make a move!",
                    'EC': "The end closer is saving energy for their trademark final sprint!"
                }
                if leader_style in style_commentaries:
                    commentaries.append(style_commentaries[leader_style])
        
        # General race commentaries
        general_commentaries = [
            "The pace is relentless as these umas thunder down the track!",
            "What a magnificent display of uma racing!",
            "The crowd's roar is deafening as the umas approach!",
            "These umas are giving it their all in this prestigious race!",
            "You can feel the tension building with every stride!",
            "This is uma racing at its absolute finest!",
        ]
        
        if random.random() < 0.10 and current_time - self.last_commentary_time > 8:
            commentaries.append(random.choice(general_commentaries))
        
        return commentaries

    def display_final_results(self):
        """Display final race results with IMPROVED distance calculations"""
        self.append_output("\n=== FINAL RESULTS ===\n")
        
        sorted_finish = sorted(self.finish_times.items(), key=lambda x: x[1])
        
        for i, (name, finish_time) in enumerate(sorted_finish, 1):
            pos_str = self.ordinal(i)
            time_str = f"{finish_time:.1f}s"
            
            if i == 1:
                self.append_output(f"{pos_str}: {name} - {time_str}\n")
            else:
                first_time = sorted_finish[0][1]
                prev_time = sorted_finish[i-2][1]
                
                time_behind_first = finish_time - first_time
                time_behind_prev = finish_time - prev_time
                
                # IMPROVED DISTANCE CALCULATION - More realistic speeds
                # Use average speed of ~16 m/s for distance conversion
                dist_behind_first = time_behind_first * 16.0
                dist_behind_prev = time_behind_prev * 16.0
                
                dist_str_first = self.meters_to_horse_racing_distance_improved(dist_behind_first)
                dist_str_prev = self.meters_to_horse_racing_distance_improved(dist_behind_prev)
                
                if i == 2:
                    self.append_output(f"{pos_str}: {name} - {time_str} (+{time_behind_first:.1f}s) - {dist_str_first} behind 1st\n")
                else:
                    self.append_output(f"{pos_str}: {name} - {time_str} (+{time_behind_first:.1f}s/+{time_behind_prev:.1f}s) - {dist_str_first} behind 1st, {dist_str_prev} behind {self.ordinal(i-1)}\n")
        
        self.append_output("\nSimulation completed!\n")

    def meters_to_horse_racing_distance_improved(self, meters):
        """IMPROVED conversion of meters to horse racing distance terminology"""
        lengths = meters / 2.5
        
        if lengths <= 0.05:
            return "nose"
        elif lengths <= 0.1:
            return "short head"
        elif lengths <= 0.2:
            return "head"
        elif lengths <= 0.3:
            return "short neck"
        elif lengths <= 0.4:
            return "neck"
        elif lengths <= 0.6:
            return "half length"
        elif lengths <= 0.8:
            return "3/4 length"
        elif lengths <= 1.0:
            return "1 length"
        elif lengths <= 1.25:
            return "1 1/4 lengths"
        elif lengths <= 1.5:
            return "1 1/2 lengths"
        elif lengths <= 1.75:
            return "1 3/4 lengths"
        elif lengths <= 2.0:
            return "2 lengths"
        elif lengths <= 2.25:
            return "2 1/4 lengths"
        elif lengths <= 2.5:
            return "2 1/2 lengths"
        elif lengths <= 2.75:
            return "2 3/4 lengths"
        elif lengths <= 3.0:
            return "3 lengths"
        elif lengths <= 3.5:
            return "3 1/2 lengths"
        elif lengths <= 4.0:
            return "4 lengths"
        elif lengths <= 4.5:
            return "4 1/2 lengths"
        elif lengths <= 5.0:
            return "5 lengths"
        elif lengths <= 6.0:
            return "6 lengths"
        elif lengths <= 7.0:
            return "7 lengths"
        elif lengths <= 8.0:
            return "8 lengths"
        elif lengths <= 9.0:
            return "9 lengths"
        elif lengths <= 10.0:
            return "10 lengths"
        elif lengths <= 12.0:
            return "12 lengths"
        elif lengths <= 15.0:
            return "15 lengths"
        elif lengths <= 20.0:
            return "20 lengths"
        elif lengths <= 25.0:
            return "25 lengths"
        elif lengths <= 30.0:
            return "30 lengths"
        elif lengths <= 40.0:
            return "40 lengths"
        elif lengths <= 50.0:
            return "50 lengths"
        else:
            # For very large distances, show actual lengths instead of "distance"
            return f"{int(lengths)} lengths"

    def meters_to_horse_racing_distance(self, meters):
        """Convert meters to horse racing distance terminology"""
        lengths = meters / 2.5
        
        if lengths <= 0.05:
            return "nose"
        elif lengths <= 0.1:
            return "short head"
        elif lengths <= 0.2:
            return "head"
        elif lengths <= 0.3:
            return "short neck"
        elif lengths <= 0.4:
            return "neck"
        elif lengths <= 0.6:
            return "half length"
        elif lengths <= 0.8:
            return "3/4 length"
        elif lengths <= 1.0:
            return "1 length"
        elif lengths <= 1.25:
            return "1 1/4 lengths"
        elif lengths <= 1.5:
            return "1 1/2 lengths"
        elif lengths <= 1.75:
            return "1 3/4 lengths"
        elif lengths <= 2.0:
            return "2 lengths"
        elif lengths <= 2.25:
            return "2 1/4 lengths"
        elif lengths <= 2.5:
            return "2 1/2 lengths"
        elif lengths <= 2.75:
            return "2 3/4 lengths"
        elif lengths <= 3.0:
            return "3 lengths"
        elif lengths <= 3.5:
            return "3 1/2 lengths"
        elif lengths <= 4.0:
            return "4 lengths"
        elif lengths <= 4.5:
            return "4 1/2 lengths"
        elif lengths <= 5.0:
            return "5 lengths"
        elif lengths <= 5.5:
            return "5 1/2 lengths"
        elif lengths <= 6.0:
            return "6 lengths"
        elif lengths <= 7.0:
            return "7 lengths"
        elif lengths <= 8.0:
            return "8 lengths"
        elif lengths <= 9.0:
            return "9 lengths"
        elif lengths <= 10.0:
            return "10 lengths"
        elif lengths <= 11.0:
            return "11 lengths"
        elif lengths <= 12.0:
            return "12 lengths"
        else:
            return "distance"

    def ordinal(self, n):
        """Convert number to ordinal (1st, 2nd, 3rd, etc.)"""
        if 11 <= (n % 100) <= 13:
            suffix = 'th'
        else:
            suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
        return str(n) + suffix
        
    def append_output(self, text):
        """Append text to the output area"""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.output_text.update_idletasks()
        
    def stop_simulation(self):
        """Stop the simulation"""
        self.sim_running = False
        if self.sim_after_id:
            self.after_cancel(self.sim_after_id)
            self.sim_after_id = None
        
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.append_output("Simulation stopped by user.\n")

    def reset_simulation(self):
        """Reset the simulation to initial state"""
        self.stop_simulation()
        self.sim_time = 0.0
        self.finish_times.clear()
        self.incidents_occurred.clear()
        self.overtakes.clear()
        self.skill_activations.clear()
        self.last_commentary_time = 0
        self.previous_positions = {}
        self.output_text.delete(1.0, tk.END)
        self.append_output("Simulation reset.\n")
        
        if self.sim_data:
            self.initialize_uma_icons()

    def start_real_time_simulation(self):
        """Placeholder for real-time simulation"""
        self.append_output("Real-time simulation not yet implemented. Using standard simulation.\n")
        self.start_simulation()

if __name__ == '__main__':
    app = UmaRacingGUI()
    app.mainloop()