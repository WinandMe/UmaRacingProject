import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os

# Import skills system
try:
    from skills import (
        SKILLS_DATABASE, get_skill_by_id, get_skill_categories,
        SkillRarity, RunningStyleRequirement
    )
    SKILLS_AVAILABLE = True
except ImportError:
    SKILLS_AVAILABLE = False
    print("Warning: skills.py not found. Skills feature will be disabled.")

# Import races system
try:
    from races import (
        G1_RACES, get_race_by_id, get_race_categories, get_race_season,
        Race, RaceType, Surface, Racecourse, Direction
    )
    RACES_AVAILABLE = True
except ImportError:
    RACES_AVAILABLE = False
    print("Warning: races.py not found. G1 race selection will be disabled.")

class UmaConfigGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Uma Musume Config Generator")
        self.root.geometry("800x600")

        self.umas = []
        self.current_uma_index = None
        
        # Selected skills for current Uma
        self.selected_skills = []

        # Stat variables for precise input
        self.speed_var = tk.StringVar(value="600")
        self.stamina_var = tk.StringVar(value="600")
        self.power_var = tk.StringVar(value="600")
        self.guts_var = tk.StringVar(value="600")
        self.wisdom_var = tk.StringVar(value="600")



        # Add traces to update sliders when entries change
        self.speed_var.trace_add("write", lambda *args: self.update_slider_from_var("speed"))
        self.stamina_var.trace_add("write", lambda *args: self.update_slider_from_var("stamina"))
        self.power_var.trace_add("write", lambda *args: self.update_slider_from_var("power"))
        self.guts_var.trace_add("write", lambda *args: self.update_slider_from_var("guts"))
        self.wisdom_var.trace_add("write", lambda *args: self.update_slider_from_var("wisdom"))

        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Race configuration
        race_frame = ttk.LabelFrame(main_frame, text="Race Configuration", padding="5")
        race_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # G1 Race Selection (if races module available)
        if RACES_AVAILABLE:
            ttk.Label(race_frame, text="G1 Race:").grid(row=0, column=0, sticky=tk.W)
            
            # Race category dropdown
            self.race_category = ttk.Combobox(race_frame, values=list(get_race_categories().keys()), width=18, state="readonly")
            self.race_category.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
            self.race_category.bind("<<ComboboxSelected>>", self.on_race_category_change)
            if get_race_categories():
                self.race_category.set(list(get_race_categories().keys())[2])  # Default to Medium
            
            # Race selection dropdown
            self.race_selection = ttk.Combobox(race_frame, width=35, state="readonly")
            self.race_selection.grid(row=0, column=2, columnspan=2, sticky=tk.W, padx=(5, 0))
            self.race_selection.bind("<<ComboboxSelected>>", self.on_race_select)
            
            # Race info display
            self.race_info_label = ttk.Label(race_frame, text="", foreground="blue")
            self.race_info_label.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=(5, 0))
            
            # Initialize race list
            self.on_race_category_change()
            
            # Hidden variables to store actual values (populated from race selection)
            self.selected_race_id = None
        else:
            # Fallback to manual entry if races module not available
            ttk.Label(race_frame, text="Race Name:").grid(row=0, column=0, sticky=tk.W)
            self.race_name = ttk.Entry(race_frame, width=20)
            self.race_name.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
            self.race_name.insert(0, "Arima Kinen")
            
            ttk.Label(race_frame, text="Distance (m):").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
            self.race_distance = ttk.Entry(race_frame, width=10)
            self.race_distance.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
            self.race_distance.insert(0, "2500")
            
            ttk.Label(race_frame, text="Type:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
            self.race_type = ttk.Combobox(race_frame, values=["Sprint", "Mile", "Medium", "Long"], width=10)
            self.race_type.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))
            self.race_type.set("Long")
            
            ttk.Label(race_frame, text="Surface:").grid(row=1, column=2, sticky=tk.W, padx=(10, 0), pady=(5, 0))
            self.race_surface = ttk.Combobox(race_frame, values=["Turf", "Dirt"], width=10)
            self.race_surface.grid(row=1, column=3, sticky=tk.W, padx=(5, 0), pady=(5, 0))
            self.race_surface.set("Turf")
        
        # Track condition row (always shown)
        row_offset = 2 if RACES_AVAILABLE else 2
        ttk.Label(race_frame, text="Track Condition:").grid(row=row_offset, column=0, sticky=tk.W, pady=(5, 0))
        self.track_condition = ttk.Combobox(race_frame, values=["Firm", "Good", "Soft", "Heavy"], width=10, state="readonly")
        self.track_condition.grid(row=row_offset, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.track_condition.set("Good")
        
        ttk.Label(race_frame, text="Stat Threshold:").grid(row=row_offset, column=2, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        self.stat_threshold = ttk.Entry(race_frame, width=10)
        self.stat_threshold.grid(row=row_offset, column=3, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.stat_threshold.insert(0, "0")
        
        # Tooltip for stat threshold
        ttk.Label(race_frame, text="(0 = none, 300+ gives speed bonus)").grid(row=row_offset, column=4, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        
        # Uma management
        uma_mgmt_frame = ttk.LabelFrame(main_frame, text="Uma Management", padding="5")
        uma_mgmt_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Button(uma_mgmt_frame, text="Add Uma", command=self.add_uma).grid(row=0, column=0, padx=(0, 5))
        ttk.Button(uma_mgmt_frame, text="Remove Uma", command=self.remove_uma).grid(row=0, column=1, padx=(0, 5))
        
        self.uma_listbox = tk.Listbox(uma_mgmt_frame, height=6)
        self.uma_listbox.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(5, 0))
        self.uma_listbox.bind('<<ListboxSelect>>', self.on_uma_select)
        
        # Uma details
        uma_frame = ttk.LabelFrame(main_frame, text="Uma Details", padding="5")
        uma_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Name and running style
        ttk.Label(uma_frame, text="Name:").grid(row=0, column=0, sticky=tk.W)
        self.uma_name = ttk.Entry(uma_frame, width=20)
        self.uma_name.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        
        ttk.Label(uma_frame, text="Running Style:").grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        self.uma_running_style = ttk.Combobox(uma_frame, 
                                            values=["FR - Front Runner", 
                                                   "PC - Pace Chaser", 
                                                   "LS - Late Surger", 
                                                   "EC - End Closer"], 
                                            width=15)
        self.uma_running_style.grid(row=0, column=3, sticky=tk.W, padx=(5, 0))
        self.uma_running_style.set("PC - Pace Chaser")
        
        # Stats
        stats_frame = ttk.Frame(uma_frame)
        stats_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Label(stats_frame, text="Speed:").grid(row=0, column=0, sticky=tk.W)
        self.speed_entry = ttk.Entry(stats_frame, textvariable=self.speed_var, width=10)
        self.speed_entry.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
        self.uma_speed = ttk.Scale(stats_frame, from_=0, to=3500, orient=tk.HORIZONTAL, length=150)
        self.uma_speed.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        self.speed_value = ttk.Label(stats_frame, text="600")
        self.speed_value.grid(row=0, column=3, padx=(5, 0))
        self.uma_speed.config(command=lambda v: [self.speed_value.config(text=str(int(float(v)))), self.speed_var.set(str(int(float(v))))])
        self.uma_speed.set(600)

        ttk.Label(stats_frame, text="Stamina:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.stamina_entry = ttk.Entry(stats_frame, textvariable=self.stamina_var, width=10)
        self.stamina_entry.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.uma_stamina = ttk.Scale(stats_frame, from_=0, to=3500, orient=tk.HORIZONTAL, length=150)
        self.uma_stamina.grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.stamina_value = ttk.Label(stats_frame, text="600")
        self.stamina_value.grid(row=1, column=3, padx=(5, 0), pady=(5, 0))
        self.uma_stamina.config(command=lambda v: [self.stamina_value.config(text=str(int(float(v)))), self.stamina_var.set(str(int(float(v))))])
        self.uma_stamina.set(600)

        ttk.Label(stats_frame, text="Power:").grid(row=0, column=4, sticky=tk.W, padx=(20, 0))
        self.power_entry = ttk.Entry(stats_frame, textvariable=self.power_var, width=10)
        self.power_entry.grid(row=0, column=5, sticky=tk.W, padx=(5, 0))
        self.uma_power = ttk.Scale(stats_frame, from_=0, to=3500, orient=tk.HORIZONTAL, length=150)
        self.uma_power.grid(row=0, column=6, sticky=tk.W, padx=(5, 0))
        self.power_value = ttk.Label(stats_frame, text="600")
        self.power_value.grid(row=0, column=7, padx=(5, 0))
        self.uma_power.config(command=lambda v: [self.power_value.config(text=str(int(float(v)))), self.power_var.set(str(int(float(v))))])
        self.uma_power.set(600)

        ttk.Label(stats_frame, text="Guts:").grid(row=1, column=4, sticky=tk.W, padx=(20, 0), pady=(5, 0))
        self.guts_entry = ttk.Entry(stats_frame, textvariable=self.guts_var, width=10)
        self.guts_entry.grid(row=1, column=5, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.uma_guts = ttk.Scale(stats_frame, from_=0, to=3500, orient=tk.HORIZONTAL, length=150)
        self.uma_guts.grid(row=1, column=6, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.guts_value = ttk.Label(stats_frame, text="600")
        self.guts_value.grid(row=1, column=7, padx=(5, 0), pady=(5, 0))
        self.uma_guts.config(command=lambda v: [self.guts_value.config(text=str(int(float(v)))), self.guts_var.set(str(int(float(v))))])
        self.uma_guts.set(600)

        ttk.Label(stats_frame, text="Wisdom:").grid(row=0, column=8, sticky=tk.W, padx=(20, 0))
        self.wisdom_entry = ttk.Entry(stats_frame, textvariable=self.wisdom_var, width=10)
        self.wisdom_entry.grid(row=0, column=9, sticky=tk.W, padx=(5, 0))
        self.uma_wisdom = ttk.Scale(stats_frame, from_=0, to=3500, orient=tk.HORIZONTAL, length=150)
        self.uma_wisdom.grid(row=0, column=10, sticky=tk.W, padx=(5, 0))
        self.wisdom_value = ttk.Label(stats_frame, text="600")
        self.wisdom_value.grid(row=0, column=11, padx=(5, 0))
        self.uma_wisdom.config(command=lambda v: [self.wisdom_value.config(text=str(int(float(v)))), self.wisdom_var.set(str(int(float(v))))])
        self.uma_wisdom.set(600)
        
        # Aptitudes
        apt_frame = ttk.Frame(uma_frame)
        apt_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Label(apt_frame, text="Distance Aptitude:").grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(apt_frame, text="Sprint:").grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        self.apt_sprint = ttk.Combobox(apt_frame, values=["S", "A", "B", "C", "D", "E", "F", "G"], width=3)
        self.apt_sprint.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        self.apt_sprint.set("B")
        
        ttk.Label(apt_frame, text="Mile:").grid(row=0, column=3, sticky=tk.W, padx=(10, 0))
        self.apt_mile = ttk.Combobox(apt_frame, values=["S", "A", "B", "C", "D", "E", "F", "G"], width=3)
        self.apt_mile.grid(row=0, column=4, sticky=tk.W, padx=(5, 0))
        self.apt_mile.set("B")
        
        ttk.Label(apt_frame, text="Medium:").grid(row=0, column=5, sticky=tk.W, padx=(10, 0))
        self.apt_medium = ttk.Combobox(apt_frame, values=["S", "A", "B", "C", "D", "E", "F", "G"], width=3)
        self.apt_medium.grid(row=0, column=6, sticky=tk.W, padx=(5, 0))
        self.apt_medium.set("B")
        
        ttk.Label(apt_frame, text="Long:").grid(row=0, column=7, sticky=tk.W, padx=(10, 0))
        self.apt_long = ttk.Combobox(apt_frame, values=["S", "A", "B", "C", "D", "E", "F", "G"], width=3)
        self.apt_long.grid(row=0, column=8, sticky=tk.W, padx=(5, 0))
        self.apt_long.set("B")
        
        ttk.Label(apt_frame, text="Surface Aptitude:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        ttk.Label(apt_frame, text="Turf:").grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        self.apt_turf = ttk.Combobox(apt_frame, values=["S", "A", "B", "C", "D", "E", "F", "G"], width=3)
        self.apt_turf.grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.apt_turf.set("B")
        
        ttk.Label(apt_frame, text="Dirt:").grid(row=1, column=3, sticky=tk.W, padx=(10, 0), pady=(5, 0))
        self.apt_dirt = ttk.Combobox(apt_frame, values=["S", "A", "B", "C", "D", "E", "F", "G"], width=3)
        self.apt_dirt.grid(row=1, column=4, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.apt_dirt.set("B")

        # Skills section (only if skills module is available)
        if SKILLS_AVAILABLE:
            skills_frame = ttk.LabelFrame(uma_frame, text="Skills (Max 6)", padding="5")
            skills_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
            
            # Skills category selection
            ttk.Label(skills_frame, text="Category:").grid(row=0, column=0, sticky=tk.W)
            self.skill_category = ttk.Combobox(skills_frame, values=list(get_skill_categories().keys()), width=20)
            self.skill_category.grid(row=0, column=1, sticky=tk.W, padx=(5, 0))
            self.skill_category.bind("<<ComboboxSelected>>", self.on_skill_category_change)
            if get_skill_categories():
                self.skill_category.set(list(get_skill_categories().keys())[0])
            
            # Available skills listbox
            ttk.Label(skills_frame, text="Available:").grid(row=1, column=0, sticky=tk.NW, pady=(5, 0))
            self.available_skills_listbox = tk.Listbox(skills_frame, height=6, width=30, selectmode=tk.SINGLE)
            self.available_skills_listbox.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))
            
            # Add/Remove buttons
            btn_frame = ttk.Frame(skills_frame)
            btn_frame.grid(row=1, column=2, padx=10)
            ttk.Button(btn_frame, text="Add >>", command=self.add_skill).grid(row=0, column=0, pady=2)
            ttk.Button(btn_frame, text="<< Remove", command=self.remove_skill).grid(row=1, column=0, pady=2)
            
            # Selected skills listbox
            ttk.Label(skills_frame, text="Equipped:").grid(row=1, column=3, sticky=tk.NW, pady=(5, 0))
            self.equipped_skills_listbox = tk.Listbox(skills_frame, height=6, width=30, selectmode=tk.SINGLE)
            self.equipped_skills_listbox.grid(row=1, column=4, sticky=tk.W, padx=(5, 0), pady=(5, 0))
            
            # Skill description label
            self.skill_desc_label = ttk.Label(skills_frame, text="", wraplength=500, foreground="gray")
            self.skill_desc_label.grid(row=2, column=0, columnspan=5, sticky=tk.W, pady=(5, 0))
            
            # Bind selection to show description
            self.available_skills_listbox.bind("<<ListboxSelect>>", self.on_skill_select)
            self.equipped_skills_listbox.bind("<<ListboxSelect>>", self.on_equipped_skill_select)
            
            # Initialize available skills list
            self.on_skill_category_change()

        # Save/load buttons
        ttk.Button(uma_frame, text="Save Uma", command=self.save_uma).grid(row=4, column=0, pady=(10, 0))
        ttk.Button(uma_frame, text="Reset Form", command=self.reset_form).grid(row=4, column=1, pady=(10, 0))
        
        # Output and actions
        output_frame = ttk.LabelFrame(main_frame, text="Configuration Output", padding="5")
        output_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.output_text = scrolledtext.ScrolledText(output_frame, height=10)
        self.output_text.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        ttk.Button(output_frame, text="Generate Config", command=self.generate_config).grid(row=1, column=0, pady=(5, 0))
        ttk.Button(output_frame, text="Save to File", command=self.save_to_file).grid(row=1, column=1, pady=(5, 0))
        ttk.Button(output_frame, text="Load from File", command=self.load_from_file).grid(row=1, column=2, pady=(5, 0))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(3, weight=1)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        
        # Add some sample umas
        self.add_sample_umas()

    def update_slider_from_var(self, stat):
        """Update slider position based on entry field value"""
        try:
            if stat == "speed":
                value = int(self.speed_var.get())
                self.uma_speed.set(value)
                self.speed_value.config(text=str(value))
            elif stat == "stamina":
                value = int(self.stamina_var.get())
                self.uma_stamina.set(value)
                self.stamina_value.config(text=str(value))
            elif stat == "power":
                value = int(self.power_var.get())
                self.uma_power.set(value)
                self.power_value.config(text=str(value))
            elif stat == "guts":
                value = int(self.guts_var.get())
                self.uma_guts.set(value)
                self.guts_value.config(text=str(value))
            elif stat == "wisdom":
                value = int(self.wisdom_var.get())
                self.uma_wisdom.set(value)
                self.wisdom_value.config(text=str(value))
        except ValueError:
            pass  # Ignore invalid input

    def on_race_category_change(self, event=None):
        """Update race selection dropdown when category changes"""
        if not RACES_AVAILABLE:
            return
        
        category = self.race_category.get()
        categories = get_race_categories()
        
        if category in categories:
            race_ids = categories[category]
            race_names = []
            for race_id in race_ids:
                race = get_race_by_id(race_id)
                if race:
                    race_names.append(f"{race.name} ({race.distance}m)")
            
            self.race_selection['values'] = race_names
            if race_names:
                self.race_selection.set(race_names[0])
                self.on_race_select()
    
    def on_race_select(self, event=None):
        """Update race info when a race is selected"""
        if not RACES_AVAILABLE:
            return
        
        category = self.race_category.get()
        categories = get_race_categories()
        
        if category in categories:
            selection_idx = self.race_selection.current()
            if selection_idx >= 0 and selection_idx < len(categories[category]):
                race_id = categories[category][selection_idx]
                race = get_race_by_id(race_id)
                if race:
                    self.selected_race_id = race_id
                    season = get_race_season(race)
                    direction = "Right-handed" if race.direction.value == "Right" else "Left-handed"
                    info = f"📍 {race.racecourse.value} | {race.surface.value} | {direction} | {season} | {race.race_type.value}"
                    self.race_info_label.config(text=info)

    def on_skill_category_change(self, event=None):
        """Update available skills list when category changes"""
        if not SKILLS_AVAILABLE:
            return
        
        self.available_skills_listbox.delete(0, tk.END)
        
        category = self.skill_category.get()
        categories = get_skill_categories()
        
        if category in categories:
            for skill_id in categories[category]:
                skill = get_skill_by_id(skill_id)
                if skill:
                    # Show rarity indicator
                    rarity_icon = "◯" if skill.rarity == SkillRarity.WHITE else "◎"
                    self.available_skills_listbox.insert(tk.END, f"{rarity_icon} {skill.name}")
    
    def on_skill_select(self, event=None):
        """Show skill description when selected in available list"""
        if not SKILLS_AVAILABLE:
            return
        
        selection = self.available_skills_listbox.curselection()
        if selection:
            idx = selection[0]
            category = self.skill_category.get()
            categories = get_skill_categories()
            
            if category in categories and idx < len(categories[category]):
                skill_id = categories[category][idx]
                skill = get_skill_by_id(skill_id)
                if skill:
                    self.skill_desc_label.config(text=f"{skill.icon} {skill.description}")
    
    def on_equipped_skill_select(self, event=None):
        """Show skill description when selected in equipped list"""
        if not SKILLS_AVAILABLE:
            return
        
        selection = self.equipped_skills_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.selected_skills):
                skill_id = self.selected_skills[idx]
                skill = get_skill_by_id(skill_id)
                if skill:
                    self.skill_desc_label.config(text=f"{skill.icon} {skill.description}")
    
    def add_skill(self):
        """Add selected skill to equipped list"""
        if not SKILLS_AVAILABLE:
            return
        
        if len(self.selected_skills) >= 6:
            messagebox.showwarning("Limit Reached", "Maximum 6 skills per Uma!")
            return
        
        selection = self.available_skills_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        category = self.skill_category.get()
        categories = get_skill_categories()
        
        if category in categories and idx < len(categories[category]):
            skill_id = categories[category][idx]
            
            # Check if already equipped
            if skill_id in self.selected_skills:
                messagebox.showwarning("Already Equipped", "This skill is already equipped!")
                return
            
            skill = get_skill_by_id(skill_id)
            if skill:
                self.selected_skills.append(skill_id)
                rarity_icon = "◯" if skill.rarity == SkillRarity.WHITE else "◎"
                self.equipped_skills_listbox.insert(tk.END, f"{rarity_icon} {skill.name}")
    
    def remove_skill(self):
        """Remove selected skill from equipped list"""
        if not SKILLS_AVAILABLE:
            return
        
        selection = self.equipped_skills_listbox.curselection()
        if selection:
            idx = selection[0]
            if idx < len(self.selected_skills):
                self.selected_skills.pop(idx)
                self.equipped_skills_listbox.delete(idx)
    
    def update_equipped_skills_display(self):
        """Refresh the equipped skills listbox from selected_skills"""
        if not SKILLS_AVAILABLE:
            return
        
        self.equipped_skills_listbox.delete(0, tk.END)
        for skill_id in self.selected_skills:
            skill = get_skill_by_id(skill_id)
            if skill:
                rarity_icon = "◯" if skill.rarity == SkillRarity.WHITE else "◎"
                self.equipped_skills_listbox.insert(tk.END, f"{rarity_icon} {skill.name}")

    def add_sample_umas(self):
        """Add some sample umas for testing"""
        sample_umas = [
            {
                "name": "King Argentine",
                "running_style": "FR",
                "stats": {"Speed": 3500, "Stamina": 3500, "Power": 3500, "Guts": 3500, "Wit": 3500},
                "distance_aptitude": {"Sprint": "A", "Mile": "A", "Medium": "A", "Long": "A"},
                "surface_aptitude": {"Dirt": "A", "Turf": "A"},
                "skills": ["escape_artist", "taking_the_lead", "breath_of_fresh_air"]
            },
            {
                "name": "Prince Loupan",
                "running_style": "PC",
                "stats": {"Speed": 3500, "Stamina": 3500, "Power": 3500, "Guts": 3500, "Wit": 3500},
                "distance_aptitude": {"Sprint": "A", "Mile": "A", "Medium": "A", "Long": "A"},
                "surface_aptitude": {"Dirt": "A", "Turf": "A"},
                "skills": ["speed_star", "beeline_burst", "in_body_and_mind"]
            }
        ]

        for uma in sample_umas:
            self.umas.append(uma)
            self.uma_listbox.insert(tk.END, uma["name"])
    
    def add_uma(self):
        """Add a new empty uma"""
        new_uma = {
            "name": "New Uma",
            "running_style": "PC",
            "stats": {"Speed": 600, "Stamina": 600, "Power": 600, "Guts": 600, "Wit": 600},
            "distance_aptitude": {"Sprint": "B", "Mile": "B", "Medium": "B", "Long": "B"},
            "surface_aptitude": {"Dirt": "B", "Turf": "B"},
            "skills": []
        }

        self.umas.append(new_uma)
        self.uma_listbox.insert(tk.END, new_uma["name"])
        self.uma_listbox.selection_clear(0, tk.END)
        self.uma_listbox.selection_set(tk.END)
        self.on_uma_select()
    
    def remove_uma(self):
        """Remove selected uma"""
        selection = self.uma_listbox.curselection()
        if selection:
            index = selection[0]
            self.umas.pop(index)
            self.uma_listbox.delete(index)
            self.current_uma_index = None
            self.reset_form()
    
    def on_uma_select(self, event=None):
        """Load selected uma data into form"""
        selection = self.uma_listbox.curselection()
        if selection:
            self.current_uma_index = selection[0]
            uma = self.umas[self.current_uma_index]

            self.uma_name.delete(0, tk.END)
            self.uma_name.insert(0, uma["name"])

            # Set running style
            style_display = {
                "FR": "FR - Front Runner",
                "PC": "PC - Pace Chaser",
                "LS": "LS - Late Surger",
                "EC": "EC - End Closer"
            }
            self.uma_running_style.set(style_display.get(uma["running_style"], "PC - Pace Chaser"))

            # Set stats
            stats = uma["stats"]
            self.uma_speed.set(stats.get("Speed", 600))
            self.uma_stamina.set(stats.get("Stamina", 600))
            self.uma_power.set(stats.get("Power", 600))
            self.uma_guts.set(stats.get("Guts", 600))
            self.uma_wisdom.set(stats.get("Wit", 600))

            # Set aptitudes
            dist_apt = uma["distance_aptitude"]
            self.apt_sprint.set(dist_apt.get("Sprint", "B"))
            self.apt_mile.set(dist_apt.get("Mile", "B"))
            self.apt_medium.set(dist_apt.get("Medium", "B"))
            self.apt_long.set(dist_apt.get("Long", "B"))

            surf_apt = uma["surface_aptitude"]
            self.apt_turf.set(surf_apt.get("Turf", "B"))
            self.apt_dirt.set(surf_apt.get("Dirt", "B"))

            # Load skills
            self.selected_skills = uma.get("skills", []).copy()
            if SKILLS_AVAILABLE:
                self.update_equipped_skills_display()



    def save_uma(self):
        """Save current form data to selected uma"""
        if self.current_uma_index is None:
            messagebox.showerror("Error", "No uma selected")
            return
        
        uma = self.umas[self.current_uma_index]
        
        # Update name
        uma["name"] = self.uma_name.get()
        
        # Update running style (extract code from display)
        style_code = self.uma_running_style.get().split(" - ")[0]
        uma["running_style"] = style_code
        
        # Update stats
        uma["stats"] = {
            "Speed": int(self.uma_speed.get()),
            "Stamina": int(self.uma_stamina.get()),
            "Power": int(self.uma_power.get()),
            "Guts": int(self.uma_guts.get()),
            "Wit": int(self.uma_wisdom.get())
        }
        
        # Update aptitudes
        uma["distance_aptitude"] = {
            "Sprint": self.apt_sprint.get(),
            "Mile": self.apt_mile.get(),
            "Medium": self.apt_medium.get(),
            "Long": self.apt_long.get()
        }
        
        uma["surface_aptitude"] = {
            "Dirt": self.apt_dirt.get(),
            "Turf": self.apt_turf.get()
        }
        
        # Update skills
        uma["skills"] = self.selected_skills.copy()
        
        # Update listbox
        self.uma_listbox.delete(self.current_uma_index)
        self.uma_listbox.insert(self.current_uma_index, uma["name"])
        self.uma_listbox.selection_set(self.current_uma_index)
        
        messagebox.showinfo("Success", "Uma saved successfully")
    
    def reset_form(self):
        """Reset the form to empty values"""
        self.current_uma_index = None
        self.uma_name.delete(0, tk.END)
        self.uma_running_style.set("PC - Pace Chaser")
        self.uma_speed.set(600)
        self.uma_stamina.set(600)
        self.uma_power.set(600)
        self.uma_guts.set(600)
        self.uma_wisdom.set(600)
        self.apt_sprint.set("B")
        self.apt_mile.set("B")
        self.apt_medium.set("B")
        self.apt_long.set("B")
        self.apt_turf.set("B")
        self.apt_dirt.set("B")
        # Reset skills
        self.selected_skills = []
        if SKILLS_AVAILABLE:
            self.update_equipped_skills_display()
            self.skill_desc_label.config(text="")
    
    def generate_config(self):
        """Generate JSON configuration"""
        # Get stat threshold (default to 0 if invalid)
        try:
            stat_threshold_val = int(self.stat_threshold.get())
        except ValueError:
            stat_threshold_val = 0
        
        # Get race data from selected G1 race or manual entry
        if RACES_AVAILABLE and hasattr(self, 'selected_race_id') and self.selected_race_id:
            race = get_race_by_id(self.selected_race_id)
            if race:
                race_config = {
                    "name": race.name,
                    "name_jp": race.name_jp,
                    "distance": race.distance,
                    "type": race.race_type.value,
                    "surface": race.surface.value,
                    "racecourse": race.racecourse.value,
                    "direction": race.direction.value,
                    "track_condition": self.track_condition.get(),
                    "stat_threshold": stat_threshold_val,
                    "season": get_race_season(race),
                    "month": race.month
                }
            else:
                race_config = self._get_manual_race_config(stat_threshold_val)
        else:
            race_config = self._get_manual_race_config(stat_threshold_val)
        
        config = {
            "race": race_config,
            "umas": self.umas
        }
        
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(1.0, json.dumps(config, indent=4, ensure_ascii=False))
    
    def _get_manual_race_config(self, stat_threshold_val):
        """Get race config from manual entry fields (fallback)"""
        return {
            "name": self.race_name.get() if hasattr(self, 'race_name') else "Custom Race",
            "distance": int(self.race_distance.get()) if hasattr(self, 'race_distance') else 2000,
            "type": self.race_type.get() if hasattr(self, 'race_type') else "Medium",
            "surface": self.race_surface.get() if hasattr(self, 'race_surface') else "Turf",
            "track_condition": self.track_condition.get(),
            "stat_threshold": stat_threshold_val
        }
        
        self.output_text.delete(1.0, tk.END)
        self.output_text.insert(1.0, json.dumps(config, indent=4, ensure_ascii=False))
    
    def save_to_file(self):
        """Save configuration to file"""
        if not self.umas:
            messagebox.showerror("Error", "No umas configured")
            return
        
        self.generate_config()
        config_json = self.output_text.get(1.0, tk.END)
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(config_json)
                messagebox.showinfo("Success", f"Configuration saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
    
    def load_from_file(self):
        """Load configuration from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                # Load race config
                race = config.get("race", {})
                
                if RACES_AVAILABLE:
                    # Try to find the race in G1 database by name
                    race_name = race.get("name", "")
                    found_race = None
                    found_category = None
                    
                    for race_id, race_obj in G1_RACES.items():
                        if race_obj.name == race_name:
                            found_race = race_obj
                            # Find the category
                            for cat_name, cat_races in get_race_categories().items():
                                if race_id in cat_races:
                                    found_category = cat_name
                                    break
                            break
                    
                    if found_race and found_category:
                        # Set the category and race selection
                        self.race_category.set(found_category)
                        self.on_race_category_change()
                        
                        # Find and select the race
                        for i, race_id in enumerate(get_race_categories()[found_category]):
                            if race_id == found_race.id:
                                self.race_selection.current(i)
                                self.on_race_select()
                                break
                    
                    # Set track condition
                    self.track_condition.set(race.get("track_condition", "Good"))
                else:
                    # Manual entry mode
                    if hasattr(self, 'race_name'):
                        self.race_name.delete(0, tk.END)
                        self.race_name.insert(0, race.get("name", ""))
                    if hasattr(self, 'race_distance'):
                        self.race_distance.delete(0, tk.END)
                        self.race_distance.insert(0, str(race.get("distance", 2500)))
                    if hasattr(self, 'race_type'):
                        self.race_type.set(race.get("type", "Long"))
                    if hasattr(self, 'race_surface'):
                        self.race_surface.set(race.get("surface", "Turf"))
                    self.track_condition.set(race.get("track_condition", "Good"))
                
                # Set stat threshold
                self.stat_threshold.delete(0, tk.END)
                self.stat_threshold.insert(0, str(race.get("stat_threshold", 0)))
                
                # Load umas
                self.umas = config.get("umas", [])
                self.uma_listbox.delete(0, tk.END)
                for uma in self.umas:
                    self.uma_listbox.insert(tk.END, uma["name"])
                
                # Update output
                self.output_text.delete(1.0, tk.END)
                self.output_text.insert(1.0, json.dumps(config, indent=4, ensure_ascii=False))
                
                messagebox.showinfo("Success", f"Configuration loaded from {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")

if __name__ == "__main__":
    root = tk.Tk()
    app = UmaConfigGenerator(root)
    root.mainloop()