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
            
            # If train wants to move (Cruise (0), Slow (1), Fast (3))
            if action in [0, 1, 3]:
                curr_track_id = train.get('current_track')
                route = train.get('planned_route', [])
                route_idx = train.get('route_index', 0)
                
                # Check next track in route
                if route_idx + 1 < len(route):
                    next_track_id = route[route_idx + 1]
                    next_track = self.tracks.get(next_track_id)
                    
                    if next_track:
                        # 1. Capacity Check
                        curr_occ = projected_occupancy.get(next_track_id, 0)
                        capacity = next_track.get('capacity', 1)
                        if curr_occ >= capacity:
                            logger.debug(f"Constraint: Force STOP for train {agent_id} "
                                        f"due to capacity on track {next_track_id}")
                            safe_actions[agent_id] = 2 # Force Wait (Stop)
                            continue

                        # 2. SINGLE TRACK RECURSIVE CHECK
                        if next_track.get('is_single_track', False):
                            # Look ahead for the entire single-track chain
                            chain = []
                            for i in range(route_idx + 1, len(route)):
                                t_id = route[i]
                                tr_data = self.tracks.get(t_id)
                                if tr_data and tr_data.get('is_single_track', False):
                                    chain.append(t_id)
                                else:
                                    break # Chain ends at double track or station
                            
                            # If anyone else is on this chain, WAIT at the gateway
                            danger = False
                            for t_id in chain:
                                if projected_occupancy.get(t_id, 0) > 0:
                                    danger = True
                                    break
                            
                            if danger:
                                logger.info(f"🛡️ SAFETY: Blocking train {agent_id} entry to single-track chain {chain} (Occupied)")
                                safe_actions[agent_id] = 2
                            
        return safe_actions
