import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
from copy import deepcopy
import sys
import os
import networkx as nx

# The railway_cpp backend should be installed in site-packages or available via PYTHONPATH

try:
    import railway_cpp
    HAS_CPP = True
    logging.info("Railway C++ backend loaded successfully.")
except ImportError:
    HAS_CPP = False
    logging.warning("Railway C++ backend not found. Falling back to Python simulation.")

logger = logging.getLogger(__name__)

class RailwayGymEnv(gym.Env):
    """
    Multi-agent environment for railway conflict resolution.
    Each train is an agent.
    """
    metadata = {"render_modes": ["human"], "name": "railway_marl_v1"}

    def __init__(self, tracks: List[Dict], stations: List[Dict], trains: List[Dict]):
        super().__init__()
        
        self.raw_tracks = {t['id']: t for t in tracks}
        self.raw_stations = {s['id']: s for s in stations}
        
        # Ensure trains have all necessary fields from loader
        for t in trains:
            t.setdefault('planned_route', [])
            t.setdefault('route_index', 0)
            t.setdefault('position_on_track', 0.0)
            t.setdefault('has_arrived', False)
            t.setdefault('delay_min', 0.0)
            
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
        self.action_space = spaces.Dict({
            agent_id: spaces.Discrete(3) for agent_id in self.agent_ids
        })
        
        self.observation_space = spaces.Dict({
            agent_id: spaces.Dict({
                "position": spaces.Box(low=0, high=1000, shape=(1,), dtype=np.float32),
                "current_track": spaces.Discrete(1000), # Support more tracks
                "velocity": spaces.Box(low=0, high=300, shape=(1,), dtype=np.float32),
                "neighbor_occupancy": spaces.Box(low=0, high=10, shape=(5,), dtype=np.float32),
            }) for agent_id in self.agent_ids
        })
        
        self.current_step = 0
        self.time_step_min = 1.0 
        self.max_steps = 120 

        if HAS_CPP:
            self.cpp_scheduler = railway_cpp.RailwayScheduler(len(tracks), len(stations))
            
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
        
        if HAS_CPP:
            # Re-add trains to C++
            for t in self.trains:
                ct = railway_cpp.Train()
                ct.id = t['id']
                ct.current_track = t.get('current_track', 0)
                ct.position_km = t.get('position_km', 0.0)
                ct.velocity_kmh = t.get('velocity_kmh', 120.0)
                ct.planned_route = t.get('planned_route', [])
                ct.route_index = 0
                ct.has_arrived = False
                self.cpp_scheduler.add_train(ct)
                
        return self._get_obs(), {}

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
            state = self.cpp_scheduler.get_network_state()
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
            # Python Fallback (legacy)
            num_conflicts = 0 
            pass

        rewards = {agent_id: 0.0 for agent_id in self.agent_ids}
        terminated = {agent_id: False for agent_id in self.agent_ids}
        
        for train in self.trains:
            tid = str(train['id'])
            if train['has_arrived']:
                terminated[tid] = True
                rewards[tid] += 100.0
            else:
                rewards[tid] -= 0.1 
        
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

    def _get_obs(self):
        obs = {}
        for train in self.trains:
            agent_id = str(train['id'])
            
            # Local topology from graph
            curr_track = train.get('current_track', 0)
            neighbor_occ = [0.0] * 5
            
            # Simple local view: occupancy of connected edges
            if self.graph.has_node(curr_track): # Dummy mapping for now
                pass
                
            obs[agent_id] = {
                "position": np.array([train.get('position_on_track', 0.0)], dtype=np.float32),
                "current_track": train.get('current_track', 0),
                "velocity": np.array([train.get('velocity_kmh', 120.0)], dtype=np.float32),
                "neighbor_occupancy": np.array(neighbor_occ, dtype=np.float32)
            }
        return obs
