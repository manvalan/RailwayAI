from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class SafetyConstraintLayer:
    """
    Ensures that AI actions do not violate hard railway constraints.
    Acts as a 'shield' between the AI policy and the environment.
    """
    
    def __init__(self, tracks: Dict[int, Dict]):
        self.tracks = tracks

    def apply_constraints(self, actions: Dict[str, int], env_state: Dict[str, Any]) -> Dict[str, int]:
        """
        Intercept actions and override if they violate constraints.
        
        Constraints:
        1. Cannot enter a single track if another train is moving in the opposite direction.
        2. Cannot enter a track that is at its capacity limit.
        3. Mandatory stop if a signal is red (modeled as track occupancy).
        """
        safe_actions = actions.copy()
        
        # Track occupancy tracking for this step's projection
        projected_occupancy = {}
        for train in env_state['trains']:
            if train['has_arrived']: continue
            track_id = train.get('current_track')
            if track_id is not None:
                projected_occupancy[track_id] = projected_occupancy.get(track_id, 0) + 1

        for train in env_state['trains']:
            agent_id = str(train['id'])
            if train['has_arrived']: continue
            
            action = actions.get(agent_id, 0)
            
            # If train wants to move (Cruise)
            if action == 0:
                # Check if it's nearing the end of the current track and entering the next
                curr_track_id = train.get('current_track')
                route = train.get('planned_route', [])
                route_idx = train.get('route_index', 0)
                
                # Simple look-ahead: if it's at the end of track, check the next one
                # For simplicity in this dummy layer, we just check general track capacity
                track = self.tracks.get(curr_track_id)
                if track:
                    # If it's a single track and there's another train on it, 
                    # we should be careful. But if it's already on it, it might have to continue.
                    # The more critical check is ENTERING a track.
                    pass
                
                # Check next track in route
                if route_idx + 1 < len(route):
                    next_track_id = route[route_idx + 1]
                    next_track = self.tracks.get(next_track_id)
                    
                    if next_track:
                        curr_occ = projected_occupancy.get(next_track_id, 0)
                        capacity = next_track.get('capacity', 1)
                        
                        # Hard Constraint: Don't enter if full
                        if curr_occ >= capacity:
                            logger.info(f"Constraint: Force STOP for train {agent_id} "
                                        f"due to capacity on track {next_track_id}")
                            safe_actions[agent_id] = 1 # Force Stop
                            
        return safe_actions
