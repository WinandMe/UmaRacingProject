"""
Harness Racing Commentary Generator

Generates realistic commentary for European harness racing events,
adapted for trotter-specific mechanics (sulky, gait breaks, heats, etc.)
"""

import random
from typing import List, Tuple, Dict, Set


class HarnessCommentaryGenerator:
    """Generate live commentary for harness racing"""
    
    # Harness racing specific terms
    GAIT_BREAK_LINES = [
        "{horse} breaks stride! Losing valuable momentum!",
        "Oh no! {horse} breaks into a gallop - that's going to cost time!",
        "{horse} loses the trot! The driver works to regain control!",
        "Disaster for {horse}! A break in stride at the worst time!",
        "{horse} is off stride! Critical moment in the race!",
    ]
    
    SULKY_LINES = [
        "{horse} is pulling the sulky beautifully!",
        "Perfect sulky control from {horse}!",
        "{horse} shows excellent equipment handling!",
    ]
    
    START_LINES = [
        "And they're off from the auto-start gate!",
        "The gates open and the trotters burst forward!",
        "Perfect start! All horses away cleanly!",
        "The auto-start releases - they're racing!",
    ]
    
    POSITION_LINES_LEADER = [
        "{horse} takes command at the front!",
        "{horse} grabs the early lead!",
        "{horse} shows impressive gate speed to lead!",
        "{horse} is out front and trotting smoothly!",
    ]
    
    POSITION_LINES_CHALLENGING = [
        "{horse} is moving up on the outside!",
        "{horse} makes a bold move forward!",
        "{horse} is angling for position!",
        "Here comes {horse} with a strong move!",
    ]
    
    FINISH_LINES_WINNER = [
        "{horse} crosses the line! Victory in the harness!",
        "{horse} wins it! A commanding performance!",
        "{horse} takes the honors! What a trot!",
        "Victory to {horse}! Magnificent driving!",
    ]
    
    FINISH_LINES_PLACE = [
        "{horse} claims {position} place!",
        "{horse} finishes in {position}!",
        "A solid {position} for {horse}!",
    ]
    
    def __init__(self):
        self.last_commentary_time = 0
        self.commentary_history = []
        self.distance_callouts_made = set()
        self.last_incident_time = 0
        self.last_position_time = 0
        self.last_phase_time = 0
        self.gait_breaks_commented = set()
        
    def get_commentary(self, current_time: float, positions: List[Tuple[str, float]], 
                      race_distance: float, incidents: Dict[str, str] = None,
                      finished: Set[str] = None) -> List[str]:
        """
        Get commentary for current race state
        
        Args:
            current_time: Elapsed time in seconds
            positions: List of (horse_id, distance) tuples sorted by position
            race_distance: Total race distance in meters
            incidents: Dict of horse_id -> incident type ('gait_break', etc.)
            finished: Set of horse_ids that have finished
            
        Returns:
            List of commentary lines to display
        """
        commentaries = []
        
        if not positions:
            return commentaries
        
        leader_name, leader_distance = positions[0]
        remaining_distance = max(0, race_distance - leader_distance)
        race_progress = leader_distance / race_distance
        
        # Cooldown check
        if current_time - self.last_commentary_time < 1.5:
            return commentaries
        
        # === START COMMENTARY ===
        if race_progress < 0.05 and not self.commentary_history:
            commentaries.append(random.choice(self.START_LINES))
            self.last_commentary_time = current_time
        
        # === DISTANCE MARKERS ===
        distance_markers = [2000, 1600, 1200, 1000, 800, 600, 400, 200, 100]
        for marker in distance_markers:
            if remaining_distance <= marker and marker not in self.distance_callouts_made:
                self.distance_callouts_made.add(marker)
                commentary = self._get_distance_callout(marker, leader_name, remaining_distance)
                if commentary:
                    commentaries.append(commentary)
                    self.last_commentary_time = current_time
                    break
        
        # === GAIT BREAK INCIDENTS ===
        if incidents and current_time - self.last_incident_time > 3.0:
            for horse_id, incident_type in incidents.items():
                if incident_type == 'gait_break' and horse_id not in self.gait_breaks_commented:
                    commentary = random.choice(self.GAIT_BREAK_LINES).format(horse=horse_id)
                    commentaries.append(commentary)
                    self.gait_breaks_commented.add(horse_id)
                    self.last_incident_time = current_time
                    self.last_commentary_time = current_time
                    break
        
        # === POSITION CHANGES ===
        if not commentaries and current_time - self.last_position_time > 4.0:
            if len(positions) >= 2:
                second = positions[1][0]
                gap = positions[0][1] - positions[1][1]
                
                if gap < 5.0:  # Within 5 meters
                    lines = [
                        f"{leader_name} and {second} are locked together!",
                        f"Tight racing between {leader_name} and {second}!",
                        f"{second} is breathing down the leader's neck!",
                    ]
                    commentaries.append(random.choice(lines))
                    self.last_position_time = current_time
                    self.last_commentary_time = current_time
        
        # === PHASE COMMENTARY ===
        if not commentaries and current_time - self.last_phase_time > 8.0:
            phase_commentary = self._get_phase_commentary(race_progress, leader_name, positions)
            if phase_commentary:
                commentaries.append(phase_commentary)
                self.last_phase_time = current_time
                self.last_commentary_time = current_time
        
        # === FINISH COMMENTARY ===
        if finished:
            finish_commentary = self._get_finish_commentary(finished, positions)
            if finish_commentary:
                commentaries.append(finish_commentary)
                self.last_commentary_time = current_time
        
        # Update history
        for commentary in commentaries:
            if commentary not in self.commentary_history[-5:]:
                self.commentary_history.append(commentary)
                if len(self.commentary_history) > 20:
                    self.commentary_history.pop(0)
        
        return commentaries[:2]  # Limit to 2 lines at once
    
    def _get_distance_callout(self, marker: int, leader: str, remaining: float) -> str:
        """Get distance-specific callout"""
        callouts = {
            2000: [
                f"{int(remaining)}m to go! {leader} leads the field!",
                f"At the 2000 meter mark with {leader} in front!",
            ],
            1600: [
                f"{int(remaining)}m remaining! The pace is solid!",
                f"At {int(remaining)}m, {leader} maintains the advantage!",
            ],
            1200: [
                f"{int(remaining)}m to go! The race intensifies!",
                f"At {int(remaining)}m! {leader} controls the tempo!",
            ],
            1000: [
                f"The final kilometer! {leader} leads the charge!",
                f"1000 meters to go! The real racing begins!",
            ],
            800: [
                f"{int(remaining)}m remaining! The stretch approaches!",
                f"At {int(remaining)}m, the pressure is building!",
            ],
            600: [
                f"{int(remaining)}m to go! Into the critical phase!",
                f"At {int(remaining)}m! The drivers ask for more!",
            ],
            400: [
                f"Just {int(remaining)}m left! {leader} is fighting!",
                f"{int(remaining)} meters! The finish line looms!",
            ],
            200: [
                f"Only {int(remaining)}m to go! {leader} is sprinting!",
                f"{int(remaining)} meters! Maximum effort now!",
            ],
            100: [
                f"The final {int(remaining)} meters! {leader} is so close!",
                f"{int(remaining)}m left! Almost there!",
            ],
        }
        
        lines = callouts.get(marker, [])
        return random.choice(lines) if lines else ""
    
    def _get_phase_commentary(self, race_progress: float, leader: str, 
                            positions: List[Tuple[str, float]]) -> str:
        """Phase-based general commentary"""
        if race_progress < 0.15:
            lines = [
                f"{leader} takes the early lead!",
                f"The field settles in behind {leader}!",
                f"{leader} controls the early tempo!",
            ]
        elif race_progress < 0.4:
            lines = [
                f"{leader} maintains a steady trot at the front!",
                f"The field is strung out behind {leader}!",
                f"{leader} looks comfortable in the lead!",
            ]
        elif race_progress < 0.7:
            if len(positions) >= 2:
                second = positions[1][0]
                lines = [
                    f"{leader} still leads with {second} tracking!",
                    f"{second} is poised to challenge {leader}!",
                    f"The race develops between {leader} and {second}!",
                ]
            else:
                lines = [f"{leader} continues to dominate!"]
        elif race_progress < 0.9:
            lines = [
                f"Into the final stages! {leader} leads!",
                f"The finish line approaches! {leader} out front!",
                f"{leader} is being pressed hard!",
            ]
        else:
            lines = [
                f"The final push! {leader} gives everything!",
                f"{leader} is straining for victory!",
                f"Maximum effort from {leader}!",
            ]
        
        return random.choice(lines) if lines else ""
    
    def _get_finish_commentary(self, finished: Set[str], 
                              positions: List[Tuple[str, float]]) -> str:
        """Commentary for horses crossing finish line"""
        # Find newly finished horses
        newly_finished = [horse_id for horse_id, _ in positions if horse_id in finished]
        
        if not newly_finished:
            return ""
        
        horse = newly_finished[0]
        finish_position = list(finished).index(horse) + 1 if horse in finished else 0
        
        if finish_position == 1:
            return random.choice(self.FINISH_LINES_WINNER).format(horse=horse)
        elif finish_position in [2, 3]:
            position_text = "second" if finish_position == 2 else "third"
            return random.choice(self.FINISH_LINES_PLACE).format(
                horse=horse, position=position_text
            )
        else:
            return f"{horse} finishes in {finish_position}th place!"
    
    def reset(self):
        """Reset commentary state for new race"""
        self.last_commentary_time = 0
        self.commentary_history.clear()
        self.distance_callouts_made.clear()
        self.last_incident_time = 0
        self.last_position_time = 0
        self.last_phase_time = 0
        self.gait_breaks_commented.clear()


if __name__ == "__main__":
    print("Harness Racing Commentary Generator loaded")
    
    # Test commentary
    gen = HarnessCommentaryGenerator()
    
    # Simulate race start
    positions = [("Valor Nordic", 50), ("Pride Elite", 48), ("Hope Sprint", 45)]
    commentary = gen.get_commentary(0.5, positions, 2100)
    print("Start:", commentary)
    
    # Mid-race
    positions = [("Valor Nordic", 1200), ("Pride Elite", 1195), ("Hope Sprint", 1180)]
    commentary = gen.get_commentary(60.0, positions, 2100)
    print("Mid-race:", commentary)
    
    # Gait break incident
    incidents = {"Hope Sprint": "gait_break"}
    commentary = gen.get_commentary(65.0, positions, 2100, incidents)
    print("Incident:", commentary)
    
    # Finish
    finished = {"Valor Nordic"}
    positions = [("Valor Nordic", 2105), ("Pride Elite", 2098), ("Hope Sprint", 2085)]
    commentary = gen.get_commentary(120.0, positions, 2100, finished=finished)
    print("Finish:", commentary)
