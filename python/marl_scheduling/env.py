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

    def __init__(self, tracks: List[Dict], stations: List[Dict], trains: List[Dict], active_agent_ids: Optional[List[int]] = None):
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
            t.setdefault('is_background', False)
            
        self.initial_trains = deepcopy(trains)
        self.trains = deepcopy(trains)
        
        # Determine which trains are active agents
        if active_agent_ids is not None:
            self.agent_ids = [str(aid) for aid in active_agent_ids]
            # Mark others as background
            for t in self.trains:
                if t['id'] not in active_agent_ids:
                    t['is_background'] = True
        else:
            self.agent_ids = [str(t['id']) for t in trains]
        
        # Build network graph for neighbor occupancy calculation
        self.graph = nx.Graph()
        for t_id, t in self.raw_tracks.items():
            s_ids = t['station_ids']
            if len(s_ids) >= 2:
                self.graph.add_edge(s_ids[0], s_ids[1], id=t_id, length=t['length_km'], 
                                   capacity=t['capacity'], is_single=t.get('is_single_track', True))
        
        # Observation space: 15 dimensions (pos, track, vel, 12 neighbors)
        self.observation_space = spaces.Dict({
            agent_id: spaces.Dict({
                "position": spaces.Box(low=0, high=1000, shape=(1,), dtype=np.float32),
                "current_track": spaces.Discrete(10000), 
                "velocity": spaces.Box(low=0, high=300, shape=(1,), dtype=np.float32),
                "neighbor_occupancy": spaces.Box(low=0, high=10, shape=(12,), dtype=np.float32),
            }) for agent_id in self.agent_ids
        })
        
        # Action Space: Discrete(4) (0: Normal, 1: Slow, 2: Wait, 3: Fast)
        self.action_space = spaces.Dict({
            agent_id: spaces.Discrete(4) for agent_id in self.agent_ids
        })
        
        self.current_step = 0
        self.time_step_min = 1.0 
        self.max_steps = 150 # Increased horizon for larger scenarios like Roma
        self.active_ids_int = [int(aid) for aid in self.agent_ids]

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
                t['last_position'] = t.get('position_km', 0.0)
                t['last_route_index'] = 0
                
        return self._get_obs(), {}

    def step(self, actions: Dict[str, int]):
        if HAS_CPP:
            cpp_actions = {}
            for aid_str, act in actions.items():
                tid = int(aid_str)
                # Find the train to modulate its velocity
                train_ref = next((t for t in self.trains if t['id'] == tid), None)
                
                if act == 0: # Normal
                    cpp_actions[tid] = 0
                    if train_ref: train_ref['velocity_kmh'] = 100.0
                elif act == 1: # Slow
                    cpp_actions[tid] = 0 # Still moving
                    if train_ref: train_ref['velocity_kmh'] = 40.0
                elif act == 2: # Wait
                    cpp_actions[tid] = 1 # Stop (C++ Action 1)
                    if train_ref: train_ref['velocity_kmh'] = 0.0
                elif act == 3: # Fast
                    cpp_actions[tid] = 0
                    if train_ref: train_ref['velocity_kmh'] = 140.0
                
                # Sync velocity to C++
                if train_ref:
                    self.cpp_scheduler.update_train_state(tid, train_ref['position_on_track'], train_ref['velocity_kmh'], train_ref.get('is_delayed', False))
            
            # Background trains (missing from actions) use default logic (Action 0 = Speed)
            for t in self.trains:
                tid = t['id']
                if tid not in cpp_actions:
                    cpp_actions[tid] = 0 # Background continues at normal speed
                    
            self.cpp_scheduler.step(cpp_actions, self.time_step_min)
            
            # Refresh local train states from C++ backend
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
            num_conflicts = 0 
            pass

        rewards = {agent_id: 0.0 for agent_id in self.agent_ids}
        terminated = {agent_id: False for agent_id in self.agent_ids}
        
        for train in self.trains:
            tid = str(train['id'])
            if tid not in self.agent_ids:
                continue # No reward calculations for background traffic
                
            if train['has_arrived']:
                arrival_bonus = 200.0
                delay_penalty = min(150.0, train['delay_min'] * 2.5) # Stronger penalty for background isolation
                terminated[tid] = True
                rewards[tid] += (arrival_bonus - delay_penalty)
            else:
                progress = train['position_on_track'] - train.get('last_position', 0.0)
                if train['route_index'] > train.get('last_route_index', 0):
                    progress += 5.0 
                
                rewards[tid] += progress * 10.0
                
                # --- PROGRESSIVE PENALTY SHAPING (Anti-Pigrizia) ---
                # Softened quadratic penalty: Small delays tolerated to solve conflicts.
                delay_factor = max(0.0, train['delay_min'] / 100.0)
                # Reduced power from 2.5 to 2.0 to avoid overwhelming the conflict penalty
                rewards[tid] -= (delay_factor ** 2.0) * 60.0
                
                # Standstill Penalty (Dynamic)
                if progress < 0.001:
                    # Penalty for not moving
                    rewards[tid] -= 2.0 
                # ---------------------------------------------------
                
                train['last_position'] = train['position_on_track']
                train['last_route_index'] = train['route_index']
        
        if HAS_CPP:
            for c in conflicts:
                t1, t2 = str(c.train1_id), str(c.train2_id)
                # DRAMATIC INCREASE: Penalty for conflict must dominate the delay reward
                # Increased from 150 to 1000 per agent involved
                if t1 in rewards: rewards[t1] -= 1000.0 
                if t2 in rewards: rewards[t2] -= 1000.0

        self.current_step += 1
        truncated = self.current_step >= self.max_steps
        env_terminated = all(terminated.values())
        
        observations = self._get_obs()
        return observations, rewards, env_terminated, truncated, {"conflicts": num_conflicts}

    def _get_obs(self):
        obs = {}
        # Track occupancy includes ALL trains (active + background obstacles)
        track_occupancy = {}
        for t in self.trains:
            if not t['has_arrived']:
                cid = t.get('current_track', 1)
                track_occupancy[cid] = track_occupancy.get(cid, 0) + 1

        for train in self.trains:
            agent_id = str(train['id'])
            if agent_id not in self.agent_ids:
                continue # Only generate observations for active agents
                
            curr_track_id = train.get('current_track', 1)
            neighbor_occ = [0.0] * 12
            
            # Slot 0: Current track occupancy (excluding self)
            neighbor_occ[0] = max(0, track_occupancy.get(curr_track_id, 0) - 1)
            
            # Slots 1-11: Occupancy on connected tracks (BFS search up to depth 2)
            try:
                visited_tracks = {curr_track_id}
                tracked_stations = set()
                
                curr_track_data = self.raw_tracks.get(curr_track_id)
                if curr_track_data:
                    tracked_stations.update(curr_track_data['station_ids'])
                
                idx = 1
                for s_id in tracked_stations:
                    if idx >= 12: break
                    for _, _, edge_data in self.graph.edges(s_id, data=True):
                        other_track_id = edge_data['id']
                        if other_track_id not in visited_tracks:
                            neighbor_occ[idx] = track_occupancy.get(other_track_id, 0)
                            visited_tracks.add(other_track_id)
                            idx += 1
                            if idx >= 12: break
                            
                # Fill remaining by searching neighbors of neighbors if possible
                # (Omitted complex BFS for speed, just zero padding is fine)
            except Exception:
                pass
                
            # Slot 12: Weighted Approach Velocity
            approach_vel = 0.0
            for neighbor_tid in self.trains:
                if neighbor_tid['id'] == train['id'] or neighbor_tid['has_arrived']: continue
                if neighbor_tid['current_track'] in visited_tracks:
                    rel_v = (neighbor_tid['velocity_kmh'] - train['velocity_kmh']) / 200.0
                    approach_vel += rel_v
            
            # Slot 13: Station Awareness (Can I safely wait here?)
            curr_track_data = self.raw_tracks.get(curr_track_id)
            is_station = 1.0 if (curr_track_data and curr_track_data.get('capacity', 1) > 1) else 0.0
            
            # Slot 14: Route Lookahead (Is the path ahead blocked?)
            lookahead_danger = 0.0
            route = train.get('planned_route', [])
            curr_idx = train.get('route_index', 0)
            # Look 4 segments ahead in our own planned path
            for nt_id in route[curr_idx + 1 : curr_idx + 5]:
                if track_occupancy.get(nt_id, 0) > 0:
                    lookahead_danger += 1.0

            # --- NEW STRATEGIC NEURONS (v3: Hierarchy & Urgency) ---
            # Slot 15-16: Own Stats
            self_priority = train.get('priority', 5) / 10.0
            self_delay = min(1.0, train.get('delay_min', 0.0) / 60.0)
            
            # Slot 17: Distance to next station/safe-point
            dist_to_station = 1.0 # Default if no station ahead
            remaining_route = route[curr_idx:]
            acc_dist = 0
            for idx, r_id in enumerate(remaining_route):
                tr_data = self.raw_tracks.get(r_id)
                if not tr_data: continue
                
                if idx == 0:
                    acc_dist += max(0, tr_data['length_km'] - train.get('position_on_track', 0.0))
                else:
                    acc_dist += tr_data['length_km']
                
                if tr_data.get('capacity', 1) > 1:
                    dist_to_station = min(1.0, acc_dist / 20.0) # Normalized to 20km
                    break
            
            # Slot 18: Hierarchy Awareness (Who is around me?)
            max_neighbor_prio = 0.0
            for neighbor in self.trains:
                if neighbor['id'] == train['id'] or neighbor['has_arrived']: continue
                if neighbor['current_track'] in visited_tracks:
                    max_neighbor_prio = max(max_neighbor_prio, neighbor.get('priority', 5) / 10.0)

            obs[agent_id] = {
                "position": np.array([train.get('position_on_track', 0.0) / 10.0], dtype=np.float32),
                "current_track": curr_track_id, 
                "velocity": np.array([train.get('velocity_kmh', 120.0) / 200.0], dtype=np.float32),
                "neighbor_occupancy": np.array(neighbor_occ, dtype=np.float32),
                "approach_vector": np.array([approach_vel], dtype=np.float32),
                "station_lookahead": np.array([is_station, lookahead_danger], dtype=np.float32),
                "strategic_stats": np.array([self_priority, self_delay, dist_to_station, max_neighbor_prio], dtype=np.float32)
            }
        return obs
