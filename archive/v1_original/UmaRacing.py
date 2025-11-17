import random

class Uma:
    def __init__(self, name, stats, running_style, distance_apt, surface_apt):
        self.name = name
        self.stats = stats  # dictionary with Speed, Stamina, Power, Guts, Wit
        self.running_style = running_style
        self.distance_apt = distance_apt  # dictionary with Sprint, Mile, Medium, Long
        self.surface_apt = surface_apt  # dictionary with Dirt, Turf

def get_stat_rank(value):
    if value < 0 or value > 1200:
        return "Invalid"
    elif value == 1200:
        return "SS"
    elif 1100 <= value <= 1199:
        return "S+"
    elif 1000 <= value <= 1099:
        return "S"
    elif 900 <= value <= 999:
        return "A+"
    elif 800 <= value <= 899:
        return "A"
    elif 700 <= value <= 799:
        return "B+"
    elif 600 <= value <= 699:
        return "B"
    elif 500 <= value <= 599:
        return "C+"
    elif 400 <= value <= 499:
        return "C"
    elif 350 <= value <= 399:
        return "D+"
    elif 300 <= value <= 349:
        return "D"
    elif 250 <= value <= 299:
        return "E+"
    elif 200 <= value <= 249:
        return "E"
    elif 150 <= value <= 199:
        return "F+"
    elif 100 <= value <= 149:
        return "F"
    elif 51 <= value <= 99:
        return "G+"
    else:
        return "G"

def get_input_stat(stat_name):
    while True:
        try:
            value = int(input(f"Enter {stat_name} (0-1200): "))
            if 0 <= value <= 1200:
                return value
            print("Value must be between 0 and 1200")
        except ValueError:
            print("Please enter a valid integer")

def get_input_aptitude(apt_type):
    valid_ranks = ['S', 'A', 'B', 'C', 'D', 'E', 'F', 'G']
    while True:
        rank = input(f"Enter {apt_type} aptitude rank (S/A/B/C/D/E/F/G): ").upper()
        if rank in valid_ranks:
            return rank
        print("Invalid rank. Please enter S, A, B, C, D, E, F, or G")

def get_race_score(uma, race_distance, race_surface):
    # Base score from stats based on running style
    style_weights = {
        'FR': {'Speed': 1.0, 'Stamina': 0.9, 'Power': 0.8, 'Wit': 0.6, 'Guts': 0.5},
        'PC': {'Speed': 1.0, 'Stamina': 0.9, 'Wit': 0.8, 'Power': 0.6, 'Guts': 0.5},
        'LS': {'Speed': 1.0, 'Power': 0.9, 'Stamina': 0.8, 'Wit': 0.6, 'Guts': 0.5},
        'EC': {'Speed': 1.0, 'Power': 0.9, 'Wit': 0.8, 'Stamina': 0.6, 'Guts': 0.5}
    }

    # Calculate base score from weighted stats
    base_score = sum(uma.stats[stat] * weight 
                    for stat, weight in style_weights[uma.running_style].items())

    # Distance aptitude multiplier
    distance_type = ""
    if 1000 <= race_distance <= 1400:
        distance_type = "Sprint"
    elif 1500 <= race_distance <= 1800:
        distance_type = "Mile"
    elif 1900 <= race_distance <= 2200:
        distance_type = "Medium"
    else:
        distance_type = "Long"

    # Convert aptitude rank to multiplier
    apt_multipliers = {'S': 1.5, 'A': 1.3, 'B': 1.1, 'C': 1.0, 
                      'D': 0.9, 'E': 0.8, 'F': 0.7, 'G': 0.6}
    
    distance_multiplier = apt_multipliers[uma.distance_apt[distance_type]]
    surface_multiplier = apt_multipliers[uma.surface_apt[race_surface]]

    # Apply distance and running style bonuses
    style_distance_bonus = 1.0
    if distance_type == "Sprint" and uma.running_style in ["FR", "PC"]:
        style_distance_bonus = 1.2
    elif distance_type == "Mile" and uma.running_style in ["FR", "LS"]:
        style_distance_bonus = 1.2
    elif distance_type == "Long" and uma.running_style in ["FR", "PC"]:
        style_distance_bonus = 1.1

    # Calculate final score with some randomness
    final_score = (base_score * distance_multiplier * surface_multiplier * 
                  style_distance_bonus * random.uniform(0.9, 1.1))
    
    return final_score

def main():
    # Get number of Umas
    while True:
        try:
            num_umas = int(input("Enter the number of Umas participating: "))
            if num_umas > 0:
                break
            print("Please enter a positive number")
        except ValueError:
            print("Please enter a valid integer")

    umas = []

    # Input Uma details
    for i in range(num_umas):
        print(f"\nEntering details for Uma #{i+1}")
        name = input("Enter Uma name: ")
        
        # Get stats
        stats = {}
        for stat in ['Speed', 'Stamina', 'Power', 'Guts', 'Wit']:
            stats[stat] = get_input_stat(stat)
            print(f"Rank: {get_stat_rank(stats[stat])}")

        # Get running style
        while True:
            style = input("Enter running style (FR/PC/LS/EC): ").upper()
            if style in ['FR', 'PC', 'LS', 'EC']:
                break
            print("Invalid running style. Please enter FR, PC, LS, or EC")

        # Get distance aptitudes
        distance_apt = {}
        print("\nDistance Aptitudes:")
        for distance in ['Sprint', 'Mile', 'Medium', 'Long']:
            distance_apt[distance] = get_input_aptitude(distance)

        # Get surface aptitudes
        surface_apt = {}
        print("\nSurface Aptitudes:")
        for surface in ['Dirt', 'Turf']:
            surface_apt[surface] = get_input_aptitude(surface)

        uma = Uma(name, stats, style, distance_apt, surface_apt)
        umas.append(uma)

    # Get race details
    print("\nRace Setup")
    race_name = input("Enter race name: ")
    
    while True:
        try:
            race_distance = int(input("Enter race distance (1000-3600): "))
            if 1000 <= race_distance <= 3600:
                break
            print("Distance must be between 1000 and 3600")
        except ValueError:
            print("Please enter a valid integer")

    while True:
        race_surface = input("Enter race surface (Dirt/Turf): ").capitalize()
        if race_surface in ['Dirt', 'Turf']:
            break
        print("Invalid surface. Please enter Dirt or Turf")

    # Calculate race results
    results = []
    for uma in umas:
        score = get_race_score(uma, race_distance, race_surface)
        results.append((uma, score))

    # Sort results by score in descending order
    results.sort(key=lambda x: x[1], reverse=True)

    # Display results
    print(f"\nResults for {race_name}")
    print(f"Distance: {race_distance}m, Surface: {race_surface}")
    print("\nFinal Standings:")
    for position, (uma, score) in enumerate(results, 1):
        print(f"{position}. {uma.name}")

if __name__ == "__main__":
    main()
