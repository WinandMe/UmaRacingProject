import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import json
import os

class UmaConfigGenerator:
    def __init__(self, root):
        self.root = root
        self.root.title("Uma Musume Config Generator")
        self.root.geometry("800x600")

        self.umas = []
        self.current_uma_index = None

        # Hardcoded skills list
        self.skills = [
            
        ]
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
        self.uma_speed = ttk.Scale(stats_frame, from_=0, to=1200, orient=tk.HORIZONTAL, length=150)
        self.uma_speed.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
        self.speed_value = ttk.Label(stats_frame, text="600")
        self.speed_value.grid(row=0, column=3, padx=(5, 0))
        self.uma_speed.config(command=lambda v: [self.speed_value.config(text=str(int(float(v)))), self.speed_var.set(str(int(float(v))))])
        self.uma_speed.set(600)

        ttk.Label(stats_frame, text="Stamina:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.stamina_entry = ttk.Entry(stats_frame, textvariable=self.stamina_var, width=10)
        self.stamina_entry.grid(row=1, column=1, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.uma_stamina = ttk.Scale(stats_frame, from_=0, to=1200, orient=tk.HORIZONTAL, length=150)
        self.uma_stamina.grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.stamina_value = ttk.Label(stats_frame, text="600")
        self.stamina_value.grid(row=1, column=3, padx=(5, 0), pady=(5, 0))
        self.uma_stamina.config(command=lambda v: [self.stamina_value.config(text=str(int(float(v)))), self.stamina_var.set(str(int(float(v))))])
        self.uma_stamina.set(600)

        ttk.Label(stats_frame, text="Power:").grid(row=0, column=4, sticky=tk.W, padx=(20, 0))
        self.power_entry = ttk.Entry(stats_frame, textvariable=self.power_var, width=10)
        self.power_entry.grid(row=0, column=5, sticky=tk.W, padx=(5, 0))
        self.uma_power = ttk.Scale(stats_frame, from_=0, to=1200, orient=tk.HORIZONTAL, length=150)
        self.uma_power.grid(row=0, column=6, sticky=tk.W, padx=(5, 0))
        self.power_value = ttk.Label(stats_frame, text="600")
        self.power_value.grid(row=0, column=7, padx=(5, 0))
        self.uma_power.config(command=lambda v: [self.power_value.config(text=str(int(float(v)))), self.power_var.set(str(int(float(v))))])
        self.uma_power.set(600)

        ttk.Label(stats_frame, text="Guts:").grid(row=1, column=4, sticky=tk.W, padx=(20, 0), pady=(5, 0))
        self.guts_entry = ttk.Entry(stats_frame, textvariable=self.guts_var, width=10)
        self.guts_entry.grid(row=1, column=5, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.uma_guts = ttk.Scale(stats_frame, from_=0, to=1200, orient=tk.HORIZONTAL, length=150)
        self.uma_guts.grid(row=1, column=6, sticky=tk.W, padx=(5, 0), pady=(5, 0))
        self.guts_value = ttk.Label(stats_frame, text="600")
        self.guts_value.grid(row=1, column=7, padx=(5, 0), pady=(5, 0))
        self.uma_guts.config(command=lambda v: [self.guts_value.config(text=str(int(float(v)))), self.guts_var.set(str(int(float(v))))])
        self.uma_guts.set(600)

        ttk.Label(stats_frame, text="Wisdom:").grid(row=0, column=8, sticky=tk.W, padx=(20, 0))
        self.wisdom_entry = ttk.Entry(stats_frame, textvariable=self.wisdom_var, width=10)
        self.wisdom_entry.grid(row=0, column=9, sticky=tk.W, padx=(5, 0))
        self.uma_wisdom = ttk.Scale(stats_frame, from_=0, to=1200, orient=tk.HORIZONTAL, length=150)
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

        # Skills
        skills_frame = ttk.Frame(uma_frame)
        skills_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))

        ttk.Label(skills_frame, text="Skills:").grid(row=0, column=0, sticky=tk.W)
        self.skill_combobox = ttk.Combobox(skills_frame, values=self.skills, width=30)
        self.skill_combobox.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        ttk.Button(skills_frame, text="Add Skill", command=self.add_skill).grid(row=0, column=2, padx=(5, 0))
        ttk.Button(skills_frame, text="Remove Skill", command=self.remove_skill).grid(row=0, column=3, padx=(5, 0))

        self.skill_listbox = tk.Listbox(skills_frame, height=4)
        self.skill_listbox.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(5, 0))

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

    def add_sample_umas(self):
        """Add some sample umas for testing"""
        sample_umas = [
            {
                "name": "King Argentine",
                "running_style": "FR",
                "stats": {"Speed": 1200, "Stamina": 1200, "Power": 1200, "Guts": 1200, "Wit": 1200},
                "distance_aptitude": {"Sprint": "A", "Mile": "A", "Medium": "A", "Long": "A"},
                "surface_aptitude": {"Dirt": "A", "Turf": "A"},
                "skills": []
            },
            {
                "name": "Prince Loupan",
                "running_style": "PC",
                "stats": {"Speed": 1200, "Stamina": 1200, "Power": 1200, "Guts": 1200, "Wit": 1200},
                "distance_aptitude": {"Sprint": "A", "Mile": "A", "Medium": "A", "Long": "A"},
                "surface_aptitude": {"Dirt": "A", "Turf": "A"},
                "skills": []
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

            # Set skills
            self.skill_listbox.delete(0, tk.END)
            for skill in uma.get("skills", []):
                self.skill_listbox.insert(tk.END, skill)

    def add_skill(self):
        """Add selected skill to current uma"""
        skill = self.skill_combobox.get()
        if skill and self.current_uma_index is not None:
            uma = self.umas[self.current_uma_index]
            if skill not in uma["skills"]:
                uma["skills"].append(skill)
                self.skill_listbox.insert(tk.END, skill)

    def remove_skill(self):
        """Remove selected skill from current uma"""
        selection = self.skill_listbox.curselection()
        if selection and self.current_uma_index is not None:
            index = selection[0]
            uma = self.umas[self.current_uma_index]
            skill = self.skill_listbox.get(index)
            uma["skills"].remove(skill)
            self.skill_listbox.delete(index)

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
        self.skill_listbox.delete(0, tk.END)
    
    def generate_config(self):
        """Generate JSON configuration"""
        config = {
            "race": {
                "name": self.race_name.get(),
                "distance": int(self.race_distance.get()),
                "type": self.race_type.get(),
                "surface": self.race_surface.get()
            },
            "umas": self.umas
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
                self.race_name.delete(0, tk.END)
                self.race_name.insert(0, race.get("name", ""))
                self.race_distance.delete(0, tk.END)
                self.race_distance.insert(0, str(race.get("distance", 2500)))
                self.race_type.set(race.get("type", "Long"))
                self.race_surface.set(race.get("surface", "Turf"))
                
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