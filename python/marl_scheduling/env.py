import gymnasium as gym
from gymnasium import spaces
import numpy as np
import networkx as nx
from typing import Dict, List, Optional, Tuple, Any
import logging
from copy import deepcopy
import sys
import os

# Add build/python to path for railway_cpp
sys.path.append(os.path.join(os.path.dirname(__file__), '../../build/python'))

try:
    import railway_cpp
    HAS_CPP = True
    logger.info("Railway C++ backend loaded successfully.")
except ImportError:
    HAS_CPP = False
    logger.warning("Railway C++ backend not found. Falling back to Python simulation.")

logger = logging.getLogger(__name__)

class RailwayGymEnv(gym.Env):
    """
    Multi-Agent Gymnasium Environment for Railway Conflict Resolution.
    
    Agents: Individual trains.
    State: Graph-based topology with train positions and track occupancy.
    Actions: 0: Cruise, 1: Stop/Wait, 2: Deviate (Switch Track).
    """
    
    metadata = {"render_modes": ["human"], "name": "railway_marl_v1"}

    def __init__(self, tracks: List[Dict], stations: List[Dict], trains: List[Dict]):
        super().__init__()
        
        self.raw_tracks = {t['id']: t for t in tracks}
        self.raw_stations = {s['id']: s for s in stations}
        self.initial_trains = deepcopy(trains)
        self.trains = deepcopy(trains)
        
        # Build network graph
        self.graph = nx.Graph()
        for t_id, t in self.raw_tracks.items():
            s1, s2 = t['station_ids']
            self.graph.add_edge(s1, s2, id=t_id, length=t['length_km'], 
                                capacity=t['capacity'], is_single=t.get('is_single_track', True),
                                occupancy=0)
        
        self.agent_ids = [str(t['id']) for t in trains]
        
        # Action Space: Discrete(3) for each agent
        # 0: Cruise, 1: Stop/Wait, 2: Deviate
        self.action_space = spaces.Dict({
            agent_id: spaces.Discrete(3) for agent_id in self.agent_ids
        })
        
        # Observation Space: This will be a graph representation.
        # For RL libraries, we often need to flatten this or use a custom obs format.
        # Here we'll provide a dict containing node features, edge features, and agent states.
        self.observation_space = spaces.Dict({
            agent_id: spaces.Dict({
                "position": spaces.Box(low=0, high=1000, shape=(1,), dtype=np.float32),
                "current_track": spaces.Discrete(len(tracks) + 1), # +1 for null
                "velocity": spaces.Box(low=0, high=300, shape=(1,), dtype=np.float32),
                "neighbor_occupancy": spaces.Box(low=0, high=1, shape=(5,), dtype=np.float32), # simplified local view
            }) for agent_id in self.agent_ids
        })
        
        self.current_step = 0
        self.time_step_min = 1.0 # 1 minute per step
        self.max_steps = 120 # 2 hours simulation

        if HAS_CPP:
            self.cpp_scheduler = railway_cpp.RailwayScheduler(len(tracks), len(stations))
            # Convert dicts to C++ objects if necessary, but bindings usually handle lists of dicts
            # Actually, pybind11 might need explicit conversion or the C++ side expects list of struct.
            # We'll see.
            cpp_tracks = []
            for t in tracks:
                ct = railway_cpp.Track()
                ct.id = t['id']
                ct.length_km = t['length_km']
                ct.is_single_track = t.get('is_single_track', True)
                ct.capacity = t.get('capacity', 1)
                ct.station_ids = t['station_ids']
                cpp_tracks.append(ct)
            
            cpp_stations = []
            for s in stations:
                cs = railway_cpp.Station()
                cs.id = s['id']
                cs.name = s['name']
                cs.num_platforms = s.get('num_platforms', 2)
                cpp_stations.append(cs)
                
            self.cpp_scheduler.initialize_network(cpp_tracks, cpp_stations)
            
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.trains = deepcopy(self.initial_trains)
        self.current_step = 0
        
        # Initialize train states
        for train in self.trains:
            train['position_km'] = 0.0
            train['has_arrived'] = False
            train['delay_min'] = 0.0
            
        observations = self._get_obs()
        info = {}
        return observations, info

    def step(self, actions: Dict[str, int]):
        """
        Execute one step in the environment.
        actions: Dict mapping agent_id (str) -> action (int)
        """
        if HAS_CPP:
            # Convert actions to C++ map (int -> int)
            cpp_actions = {int(k): v for k, v in actions.items()}
            self.cpp_scheduler.step(cpp_actions, self.time_step_min)
            
            # Map back state from C++ to self.trains
            # This is optional if we only use C++ for obs generation too
            state = self.cpp_scheduler.get_network_state()
            # Update self.trains with information from state.trains
            for cpp_train in state.trains:
                for t in self.trains:
                    if t['id'] == cpp_train.id:
                        t['position_on_track'] = cpp_train.position_on_track
                        t['current_track'] = cpp_train.current_track
                        t['route_index'] = cpp_train.route_index
                        t['has_arrived'] = cpp_train.has_arrived
                        t['delay_min'] = cpp_train.delay_minutes
                        break
            
            conflicts = self.cpp_scheduler.detect_conflicts()
            num_conflicts = len(conflicts)
        else:
            # Python Fallback
            # ... existing logic ...
            num_conflicts = 0 # Placeholder for brevity in chunk
            pass

        # Calculate rewards (common logic or C++ integrated)
        rewards = {agent_id: 0.0 for agent_id in self.agent_ids}
        terminated = {agent_id: False for agent_id in self.agent_ids}
        
        for train in self.trains:
            tid = str(train['id'])
            if train['has_arrived']:
                terminated[tid] = True
                rewards[tid] += 100.0
            else:
                rewards[tid] -= 0.1 # Small step penalty
        
        # Conflict penalties
        if HAS_CPP:
            for c in conflicts:
                t1 = str(c.train1_id)
                t2 = str(c.train2_id)
                if t1 in rewards: rewards[t1] -= 50.0
                if t2 in rewards: rewards[t2] -= 50.0

        self.current_step += 1
        truncated = self.current_step >= self.max_steps
        env_terminated = all(terminated.values())
        
        observations = self._get_obs()
        return observations, rewards, env_terminated, truncated, {"conflicts": num_conflicts}

    def _move_train(self, train: Dict, distance: float):
        """Move train along its planned route."""
        route = train.get('planned_route', [])
        if not route:
            train['has_arrived'] = True
            return

        curr_track_idx = train.get('route_index', 0)
        curr_track_pos = train.get('position_on_track', 0.0)
        
        remaining_dist = distance
        while remaining_dist > 0 and curr_track_idx < len(route):
            track_id = route[curr_track_idx]
            track = self.raw_tracks.get(track_id)
            if not track: break
            
            track_length = track['length_km']
            dist_to_end = track_length - curr_track_pos
            
            if remaining_dist < dist_to_end:
                curr_track_pos += remaining_dist
                remaining_dist = 0
            else:
                remaining_dist -= dist_to_end
                curr_track_pos = 0.0
                curr_track_idx += 1
                
        if curr_track_idx >= len(route):
            train['has_arrived'] = True
            train['route_index'] = len(route) - 1
            train['position_on_track'] = track_length if 'track_length' in locals() else 0.0
        else:
            train['route_index'] = curr_track_idx
            train['position_on_track'] = curr_track_pos
            train['current_track'] = route[curr_track_idx]

    def _handle_deviate(self, train: Dict):
        """Handle deviation action: look for alternative routes from current station."""
        # This requires more complex route planning integration
        # For now, it's a placeholder.
        pass

    def _get_obs(self) -> Dict[str, Any]:
        """Generate graph-based observations for each agent."""
        # Update edge occupancy in graph
        for u, v, d in self.graph.edges(data=True):
            d['occupancy'] = 0
            
        for train in self.trains:
            if not train['has_arrived']:
                track_id = train.get('current_track')
                # Find edge corresponding to track_id
                for u, v, d in self.graph.edges(data=True):
                    if d['id'] == track_id:
                        d['occupancy'] += 1
                        break
        
        obs = {}
        # Convert graph state to numeric features for NN
        # For simplicity, we provide local context: current track info + neighbors
        for train in self.trains:
            tid = str(train['id'])
            curr_track_id = train.get('current_track', -1)
            
            # Neighboring tracks occupancy
            neighbors = []
            if curr_track_id in self.raw_tracks:
                s_ids = self.raw_tracks[curr_track_id]['station_ids']
                for s in s_ids:
                    for neighbor_station in self.graph.neighbors(s):
                        edge_data = self.graph.get_edge_data(s, neighbor_station)
                        neighbors.append(edge_data['occupancy'])
            
            # Pad or truncate neighbors to fixed size (e.g., 5)
            neighbor_feats = np.zeros(5, dtype=np.float32)
            for i, occ in enumerate(neighbors[:5]):
                neighbor_feats[i] = occ
                
            obs[tid] = {
                "position": np.array([train.get('position_on_track', 0.0)], dtype=np.float32),
                "current_track": curr_track_id if curr_track_id != -1 else 0,
                "velocity": np.array([train.get('velocity_kmh', 120.0)], dtype=np.float32),
                "neighbor_occupancy": neighbor_feats,
            }
        return obs

    def _detect_conflicts(self) -> List[Dict]:
        """Detect actual conflicts based on track capacity and occupancy."""
        conflicts = []
        track_occupancy = {}
        
        for train in self.trains:
            if train['has_arrived']: continue
            tid = train['id']
            track_id = train.get('current_track')
            if track_id is None: continue
            
            if track_id not in track_occupancy:
                track_occupancy[track_id] = []
            track_occupancy[track_id].append(train)
            
        for track_id, trains_on_track in track_occupancy.items():
            track = self.raw_tracks.get(track_id)
            if not track: continue
            
            capacity = track.get('capacity', 1)
            is_single = track.get('is_single_track', True)
            
            if len(trains_on_track) > capacity:
                # Collision or capacity overflow
                # Simple logic: all pairs on this track are in conflict if capacity exceeded
                for i in range(len(trains_on_track)):
                    for j in range(i + 1, len(trains_on_track)):
                        conflicts.append({
                            'train1_id': trains_on_track[i]['id'],
                            'train2_id': trains_on_track[j]['id'],
                            'track_id': track_id
                        })
                        
        return conflicts

    def render(self):
        pass
