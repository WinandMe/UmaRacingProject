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

        # Real-time simulation variables
        self.uma_distances = {}
        self.uma_finished = {}
        self.uma_incidents = {}
        self.current_positions = {}
        self.uma_fatigue = {}
        self.uma_momentum = {}
        self.uma_last_position = {}
        self.uma_stamina = {}
        self.uma_dnf = {}
        
        # === BARU: Variabel dueling ===
        self.duel_active = False
        self.duel_participants = set()
        self.duel_start_time = 0
        self.duel_commentary_made = False
        self.duel_guts_used = {}  # Track who used guts for dueling
        self.duel_stamina_boost_used = {}  # Track stamina boosts

        # Commentary tracking
        self.distance_callouts_made = set()
        self.last_incident_commentary = 0
        self.last_position_commentary = 0
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

        self.title("Uma Musume Racing Simulator - REAL TIME")
        self.geometry("900x700")
        self.setup_ui()

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_rowconfigure(2, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        # Control panel
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=0, sticky='ew')

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

        # Stat Priorities button
        self.priorities_btn = ttk.Button(control_frame, text="Stat Priorities", command=self.show_stat_priorities)
        self.priorities_btn.pack(side=tk.LEFT, padx=(0, 10))

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

        # === PERUBAHAN VISUAL KANVAS (Meniru Video) ===
        # Latar belakang hijau tua, tanpa border, expands to fill half height
        self.canvas = tk.Canvas(main_frame, bg='#3a665a', highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky='nsew')

        # Output text area
        output_frame = ttk.LabelFrame(main_frame, text="Simulation Output")
        output_frame.grid(row=2, column=0, sticky='nsew')

        self.output_text = scrolledtext.ScrolledText(output_frame)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Bind canvas configure to redraw
        self.canvas.bind("<Configure>", lambda e: self.draw_track())

        # Draw initial track
        self.after(100, self.draw_track())

    def draw_track(self):
        """Draw Uma Musume style race track (Meniru Video)"""
        self.canvas.delete("track")
        w = self.canvas.winfo_width()
        if w <= 1:
            w = 800
        # Dapatkan tinggi kanvas yang sebenarnya
        h = self.canvas.winfo_height()
        if h <= 1:
            h = 80
        
        track_y = h // 2
        
        # === PERUBAHAN VISUAL GARIS (Meniru Video) ===
        # Garis biru muda, lebih tebal
        self.canvas.create_line(
            self.track_margin, track_y,
            w - self.track_margin, track_y,
            fill='#a0d8e0', width=4, tags="track"
        )
        
        # === PERUBAHAN VISUAL TEKS (Meniru Video) ===
        # Teks START (Putih)
        self.canvas.create_text(
            self.track_margin - 30, track_y,
            text="START", fill='white', font=('Arial', 12, 'bold'),
            tags="track"
        )
        
        # Teks FINISH (Putih)
        self.canvas.create_text(
            w - self.track_margin + 35, track_y,
            text="FINISH", fill='white', font=('Arial', 12, 'bold'),
            tags="track"
        )
        
        # Hapus semua garis start/finish/tengah yang lama
        
    # === FUNGSI BARU: Menggambar penanda jarak ===
    def draw_distance_marker(self, marker_distance, race_distance):
        w = self.canvas.winfo_width()
        if w <= 1: w = 800
        h = self.canvas.winfo_height()
        if h <= 1: h = 80
        track_y = h // 2
        track_width = w - 2 * self.track_margin
        
        # Hitung posisi X dari penanda
        progress = (race_distance - marker_distance) / race_distance
        x_pos = self.track_margin + (progress * track_width)
        
        text = f"{marker_distance}>"
        
        # Gambar teks di atas garis
        self.canvas.create_text(
            x_pos, track_y - 25, 
            text=text, fill='white', font=('Arial', 10, 'bold'),
            tags="distance_marker",
            anchor=tk.N 
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
            'uma_stats': uma_stats
        }

    def initialize_real_time_simulation(self):
        """Initialize all real-time simulation variables"""
        if not self.sim_data:
            return
            
        uma_stats = self.sim_data.get('uma_stats', {})
        
        self.uma_distances = {name: 0.0 for name in uma_stats.keys()}
        self.uma_finished = {name: False for name in uma_stats.keys()}
        self.uma_incidents = {name: {'type': None, 'duration': 0, 'start_time': 0} for name in uma_stats.keys()}
        self.current_positions = {name: 1 for name in uma_stats.keys()}
        self.uma_fatigue = {name: 0.0 for name in uma_stats.keys()}
        self.uma_momentum = {name: 1.0 for name in uma_stats.keys()}
        self.uma_last_position = {name: 1 for name in uma_stats.keys()}
        self.uma_stamina = {name: 100.0 for name in uma_stats.keys()}
        self.uma_dnf = {name: {'dnf': False, 'reason': '', 'dnf_time': 0, 'dnf_distance': 0} for name in uma_stats.keys()}
        
        # === BARU: Inisialisasi variabel dueling ===
        self.duel_active = False
        self.duel_participants = set()
        self.duel_start_time = 0
        self.duel_commentary_made = False
        self.duel_guts_used = {name: False for name in uma_stats.keys()}
        self.duel_stamina_boost_used = {name: False for name in uma_stats.keys()}

        self.sim_time = 0.0
        self.finish_times.clear()
        self.incidents_occurred.clear()
        self.overtakes.clear()
        self.last_commentary_time = 0
        self.previous_positions.clear()

        self.distance_callouts_made.clear()
        self.last_incident_commentary = 0
        self.last_position_commentary = 0
        self.last_speed_commentary = 0
        self.commentary_history.clear()

        # === BARU: Hapus penanda jarak lama ===
        self.distance_markers_drawn.clear()
        self.canvas.delete("distance_marker")

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
        for name, (circle, number_text, name_text) in self.uma_icons.items():
            if circle: self.canvas.delete(circle)
            if number_text: self.canvas.delete(number_text)
            if name_text: self.canvas.delete(name_text)
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
        
        for i, name in enumerate(uma_stats.keys()):
            gate_number = i + 1
            self.gate_numbers[name] = gate_number
            color = colors[i % len(colors)]
            self.uma_colors[name] = color
            
            circle = self.canvas.create_oval(0, 0, 0, 0, fill=color, outline='white', width=2, tags=name)
            number_text = self.canvas.create_text(0, 0, text=str(gate_number), fill='white', font=('Arial', 10, 'bold'), tags=name)
            name_text = self.canvas.create_text(0, 0, text="", fill='black', font=('Arial', 7), tags=name)
            
            self.uma_icons[name] = (circle, number_text, name_text)
            
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
                    
            frame_dt = 0.05
            self.sim_time += frame_dt * mult
            
            race_distance = self.sim_data.get('race_distance', 2500)
            uma_stats = self.sim_data.get('uma_stats', {})
            
            current_frame_positions = self.calculate_real_time_positions(frame_dt * mult)

            # Initialize remaining_distance
            remaining_distance = race_distance
            # === BARU: Logika untuk menggambar penanda jarak ===
            if current_frame_positions:
                leader_dist = current_frame_positions[0][1]
                remaining_distance = max(0, race_distance - leader_dist)

                # Penanda yang ingin ditampilkan (dalam meter tersisa)
                markers_to_show = [1000, 800, 600, 400, 200]
                for marker in markers_to_show:
                    if remaining_distance <= marker and marker not in self.distance_markers_drawn:
                        self.draw_distance_marker(marker, race_distance)
                        self.distance_markers_drawn[marker] = True
            
            # === BARU: Check and trigger dueling mechanism ===
            if not self.duel_active and 400 <= remaining_distance <= 1200:
                self.check_and_trigger_dueling(uma_stats, current_frame_positions, race_distance)

            current_incidents = {name: self.uma_incidents[name]['type'] for name in uma_stats.keys() if self.uma_incidents[name]['type'] and not self.uma_finished[name] and not self.uma_dnf[name]['dnf']}

            # Filter positions to only active (non-finished, non-DNF) umas
            active_positions = [p for p in current_frame_positions if not self.uma_finished[p[0]] and not self.uma_dnf[p[0]]['dnf']]

            if self.sim_time - self.last_commentary_time > 1.8:
                leader_dist = active_positions[0][1] if active_positions else current_frame_positions[0][1] if current_frame_positions else 0
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
            
            all_finished = len(self.finish_times) + len([d for d in self.uma_dnf.values() if d['dnf']]) == len(self.uma_icons)
            
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
            # === PERBAIKAN BUG 1 ===
            # Kuda yang sudah finish/DNF tetap dimasukkan ke frame_positions
            # agar .index() tidak error. Tapi kita lewati kalkulasi untuk mereka.
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

            # Add to skill activations for commentary
            self.skill_activations.add((uma_name, skill_name, self.sim_time))

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
        
        # === DIKURANGI BANYAK: Fatigue penalty sangat dikurangi ===
        fatigue_penalty = self.uma_fatigue[uma_name] * 0.01  # Reduced from 0.04 to 0.01
        target_speed *= (1.0 - min(fatigue_penalty, 0.05))  # Max penalty reduced to 5% from 15%

        stamina_ratio = self.uma_stamina[uma_name] / 100.0
        guts_efficiency = uma_stat['guts'] / 1000.0
        effective_stamina = stamina_ratio * (0.7 + 0.3 * guts_efficiency)

        # === DIKURANGI BANYAK: Speed penalties from low stamina reduced ===
        if effective_stamina < 0.1:
            target_speed *= 0.97  # Reduced from 0.90
        elif effective_stamina < 0.3:
            target_speed *= 0.98  # Reduced from 0.94
        elif effective_stamina < 0.5:
            target_speed *= 0.99  # Reduced from 0.97
        elif effective_stamina < 0.7:
            target_speed *= 0.995  # Reduced from 0.99

        self.update_fatigue_and_stamina(uma_name, uma_stat, race_progress, current_phase)

        variation = 1.0 + (random.random() * 0.04 - 0.02)
        target_speed *= variation

        return max(target_speed, base_speed * 0.92)  # Increased minimum from 85% to 92%

    def update_fatigue_and_stamina(self, uma_name, uma_stat, race_progress, current_phase):
        """Update fatigue and stamina with distance-specific mechanics - SIGNIFICANTLY REDUCED"""
        # === DIKURANGI BANYAK: Fatigue rates reduced by 80-90% ===
        fatigue_rates = {
            'Sprint': {'start': 0.0003, 'mid': 0.0004, 'final': 0.0006, 'sprint': 0.0008},  # Reduced by ~80%
            'Mile': {'start': 0.0004, 'mid': 0.0005, 'final': 0.0008, 'sprint': 0.0010},    # Reduced by ~80%
            'Medium': {'start': 0.0005, 'mid': 0.0006, 'final': 0.0008, 'sprint': 0.0012},  # Reduced by ~80%
            'Long': {'start': 0.0006, 'mid': 0.0008, 'final': 0.0010, 'sprint': 0.0014}     # Reduced by ~80%
        }
        
        race_type = uma_stat['race_type']
        rates = fatigue_rates.get(race_type, fatigue_rates['Medium'])
        fatigue_rate = rates.get(current_phase, 0.0006)  # Reduced from 0.003
        
        # Base stamina bonus helps a lot (even 100 stamina helps)
        stamina_bonus = uma_stat['stamina'] / 500.0  # More generous scaling
        fatigue_rate *= max(0.1, 1.0 - stamina_bonus * 0.8)  # Minimum 10% fatigue rate (was 30%)
        
        self.uma_fatigue[uma_name] += fatigue_rate
        
        # === DIKURANGI BANYAK: Stamina depletion reduced by 70-80% ===
        base_stamina_drain = 0.006  # Reduced from 0.03 (80% reduction)
        phase_multipliers = {'start': 0.3, 'mid': 0.4, 'final': 0.5, 'sprint': 0.6}  # Reduced from 0.6-1.2
        stamina_depletion = base_stamina_drain * phase_multipliers.get(current_phase, 0.4)
        stamina_depletion += (self.uma_fatigue[uma_name] * 0.016)  # Reduced from 0.08 (80% reduction)
        
        guts_bonus = uma_stat['guts'] / 800.0  # More generous scaling
        stamina_depletion *= max(0.2, 1.0 - guts_bonus * 0.8)  # Minimum 20% drain (was 50%)
        
        # Prevent stamina from going too low
        if self.uma_stamina[uma_name] > 10.0:  # Only drain if above 10%
            self.uma_stamina[uma_name] = max(10.0, self.uma_stamina[uma_name] - stamina_depletion)
        else:
            # Very slow drain when already low
            self.uma_stamina[uma_name] = max(5.0, self.uma_stamina[uma_name] - stamina_depletion * 0.1)

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
        
        if not commentaries:
            phase_commentary = self.get_phase_commentary(race_progress, leader_name, positions, remaining_distance)
            if phase_commentary:
                commentaries.append(phase_commentary)
        
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
            if current_pos == new_pos + 1:
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
    
    def update_display(self, frame_positions, race_distance):
        """Update Uma Musume style display"""
        if not self.sim_data:
            return
            
        w = self.canvas.winfo_width()
        if w <= 1:
            w = 800
        h = self.canvas.winfo_height()
        if h <= 1:
            h = 80
        track_y = h // 2
        track_width = w - 2 * self.track_margin
        
        if frame_positions:
            leader_dist = frame_positions[0][1]
            remaining = max(0, race_distance - leader_dist)
            
            leader_name = frame_positions[0][0]
            uma_stat = self.sim_data['uma_stats'][leader_name]
            current_speed = self.calculate_current_speed(leader_name, uma_stat, race_distance, self.sim_data['race_type'])
            speed_kmh = current_speed * 3.6
            
            # === BARU: Tampilkan status dueling ===
            status_text = f"Remaining: {remaining:.0f}m | Lead: {speed_kmh:.1f} km/h"
            if self.duel_active:
                status_text += " | DUEL ACTIVE!"
            self.remaining_label.config(text=status_text)
        
        # Group umas by x position to calculate vertical stacking
        position_groups = {}
        ball_radius = 10 if len(self.uma_icons) > 10 else 14
        
        # === PERBAIKAN BUG 1 (Bagian 1) ===
        # Buat daftar nama yang ada di frame_positions untuk pengecekan cepat
        names_in_frame = [pos[0] for pos in frame_positions]
        
        for name, (circle, number_text, name_text) in self.uma_icons.items():
            # Jika kuda tidak ada di frame_positions (seharusnya tidak terjadi lagi, tapi sebagai pengaman)
            if name not in names_in_frame:
                self.canvas.coords(circle, -100, -100, -100, -100)
                self.canvas.coords(number_text, -100, -100)
                self.canvas.coords(name_text, -100, -100)
                continue
            
            distance = 0
            for n, d in frame_positions:
                if n == name:
                    distance = d
                    break
            
            # Kuda yang finish/DNF akan memiliki progress >= 1.0
            progress = min(1.0, distance / race_distance)
            x_pos = self.track_margin + (progress * track_width)
            
            # Group by x position
            x_key = round(x_pos / 5) * 5
            if x_key not in position_groups:
                position_groups[x_key] = []
            position_groups[x_key].append((name, x_pos))
        
        # Now position each uma with proper vertical spacing
        for name, (circle, number_text, name_text) in self.uma_icons.items():
            if name not in names_in_frame:
                continue
            
            distance = 0
            position_in_race = 0
            # === PERBAIKAN BUG 1 (Bagian 2) ===
            # Kita bisa mengandalkan frame_positions untuk mendapatkan jarak
            # dan posisi, karena sekarang SELALU berisi SEMUA kuda.
            for i, (n, d) in enumerate(frame_positions):
                if n == name:
                    distance = d
                    position_in_race = i
                    break
            
            progress = min(1.0, distance / race_distance)
            x_pos = self.track_margin + (progress * track_width)
            x_key = round(x_pos / 5) * 5
            
            # Calculate vertical offset based on position in the group
            group = position_groups.get(x_key, [])
            y_offset = 0
            
            # === PERBAIKAN BUG 1 (Bagian 3) ===
            # Logika .index() sekarang aman karena frame_positions berisi semua nama
            group_sorted = sorted(group, key=lambda x: names_in_frame.index(x[0]))
            
            if name in [g[0] for g in group_sorted]:
                idx = [g[0] for g in group_sorted].index(name)
                if len(group_sorted) == 1:
                    y_offset = 0
                else:
                    total_height = (len(group_sorted) - 1) * (ball_radius * 2 + 6)
                    y_offset = (idx * (ball_radius * 2 + 6)) - (total_height / 2)
            
            y_pos = track_y + y_offset
            
            self.canvas.coords(circle, x_pos - ball_radius, y_pos - ball_radius, x_pos + ball_radius, y_pos + ball_radius)
            self.canvas.coords(number_text, x_pos, y_pos)
            
            # === PERUBAHAN VISUAL (Meniru Video) ===
            # Hapus label nama untuk Top 3, karena tidak ada di video
            self.canvas.coords(name_text, -100, -100)
            
            # Color coding based on status
            if self.uma_finished[name]:
                self.canvas.itemconfig(circle, fill='#FFD700', outline='white')
            elif self.uma_dnf[name]['dnf']:
                self.canvas.itemconfig(circle, fill='#333333', outline='white')
            elif self.uma_incidents[name]['type']:
                self.canvas.itemconfig(circle, fill='#FF6600', outline='white')
            elif name in self.duel_participants and self.duel_active:
                # === BARU: Warna khusus untuk peserta dueling ===
                self.canvas.itemconfig(circle, fill='#FF0000', outline='white')  # Merah untuk dueling
            else:
                self.canvas.itemconfig(circle, fill=self.uma_colors[name], outline='white')
        
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
        """Reset the simulation"""
        self.stop_simulation()
        
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
        
        # === BARU: Reset variabel dueling ===
        self.duel_active = False
        self.duel_participants.clear()
        self.duel_start_time = 0
        self.duel_commentary_made = False
        self.duel_guts_used.clear()
        self.duel_stamina_boost_used.clear()
        
        self.distance_callouts_made.clear()
        self.last_incident_commentary = 0
        self.last_position_commentary = 0
        self.last_speed_commentary = 0
        self.commentary_history.clear()
        
        self.output_text.delete(1.0, tk.END)
        self.remaining_label.config(text="Remaining: -- | Lead: -- km/h")
        
        if self.sim_data:
            self.initialize_uma_icons()
        
        # === BARU: Hapus penanda jarak saat reset ===
        self.distance_markers_drawn.clear()
        self.canvas.delete("distance_marker")
        
        self.draw_track()
        self.append_output("Simulation reset.\n")

    def display_final_results(self):
        """Display final race results"""
        if not self.finish_times and not any(dnf['dnf'] for dnf in self.uma_dnf.values()):
            self.append_output("No results to display.\n")
            return
            
        self.append_output("\n" + "="*50 + "\n")
        self.append_output("FINAL RACE RESULTS\n")
        self.append_output("="*50 + "\n")
        
        finished_umas = sorted(self.finish_times.items(), key=lambda x: x[1])
        
        for i, (name, time) in enumerate(finished_umas):
            gate_num = self.gate_numbers.get(name, "?")
            self.append_output(f"{i+1}. [{gate_num}] {name} - {time:.2f}s\n")
        
        dnf_umas = [(name, dnf_data) for name, dnf_data in self.uma_dnf.items() if dnf_data['dnf']]
        if dnf_umas:
            self.append_output("\nDNF (Did Not Finish):\n")
            for name, dnf_data in dnf_umas:
                gate_num = self.gate_numbers.get(name, "?")
                self.append_output(f"- [{gate_num}] {name} (DNF at {dnf_data['dnf_distance']:.0f}m - {dnf_data['reason']})\n")
        
        total_starters = len(self.uma_icons)
        total_finished = len(finished_umas)
        total_dnf = len(dnf_umas)
        
        if finished_umas:
            winning_time = finished_umas[0][1]
            if len(finished_umas) > 1:
                time_gap = finished_umas[-1][1] - winning_time
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

    def show_stat_priorities(self):
        """Display stat priorities for each running style"""
        self.output_text.delete(1.0, tk.END)
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
        self.append_output("The remaining 2 stats provide slight performance boosts if sufficiently high.\n")
        self.append_output("These priorities are now applied to simulation calculations for realistic performance.\n")

    def append_output(self, text):
        """Append text to output area"""
        self.output_text.insert(tk.END, text)
        self.output_text.see(tk.END)
        self.update()

if __name__ == "__main__":
    app = UmaRacingGUI()
    app.mainloop()