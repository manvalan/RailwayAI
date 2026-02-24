
import numpy as np
import logging
import json
import os

logger = logging.getLogger(__name__)

class CurriculumManager:
    """
    Manages the transition between different levels of complexity for MARL training.
    """
    
    @staticmethod
    def get_scenario_for_level(level: int) -> dict:
        """
        Generates a scenario based on the difficulty level.
        """
        if level == 1:
            return CurriculumManager._generate_l1()
        elif level == 2:
            return CurriculumManager._generate_l2()
        elif level == 3:
            return CurriculumManager._generate_l3()
        elif level == 4:
            return CurriculumManager._generate_l4()
        else:
            return CurriculumManager._generate_l5()

    @staticmethod
    def _generate_l1():
        """Level 1: 2 trains, 1 track, 2 stations (The Basic Conflict)"""
        return {
            "stations": [
                {"id": 1, "name": "Station A", "num_platforms": 2},
                {"id": 2, "name": "Station B", "num_platforms": 2}
            ],
            "tracks": [
                # Platform tracks at stations
                {"id": 101, "length_km": 1.0, "is_single_track": False, "capacity": 2, "station_ids": [1]},
                {"id": 102, "length_km": 1.0, "is_single_track": False, "capacity": 2, "station_ids": [2]},
                # The single-track line
                {"id": 1, "length_km": 10.0, "is_single_track": True, "capacity": 1, "station_ids": [1, 2]}
            ],
            "trains": [
                {
                    "id": 1, "origin_station": 1, "destination_station": 2, 
                    "scheduled_departure_time": "08:00:00", "velocity_kmh": 100,
                    "position_km": 0, "current_track": 101, "priority": 5, "delay_minutes": 0,
                    "planned_route": [101, 1, 102]
                },
                {
                    "id": 2, "origin_station": 2, "destination_station": 1, 
                    "scheduled_departure_time": "08:08:00", "velocity_kmh": 100,
                    "position_km": 0, "current_track": 102, "priority": 3, "delay_minutes": 0,
                    "planned_route": [102, 1, 101]
                }
            ]
        }

    @staticmethod
    def _generate_l2():
        """Level 2: 4 trains, 3 stations, 2 tracks (Bottleneck Management)"""
        return {
            "stations": [
                {"id": 1, "name": "West", "num_platforms": 2},
                {"id": 2, "name": "Center", "num_platforms": 2},
                {"id": 3, "name": "East", "num_platforms": 2}
            ],
            "tracks": [
                {"id": 1, "length_km": 15.0, "is_single_track": False, "capacity": 2, "station_ids": [1, 2]},
                {"id": 2, "length_km": 10.0, "is_single_track": True, "capacity": 1, "station_ids": [2, 3]}
            ],
            "trains": [
                {"id": i, "origin_station": 1 if i % 2 == 0 else 3, 
                 "destination_station": 3 if i % 2 == 0 else 1,
                 "scheduled_departure_time": f"09:0{i}:00", "velocity_kmh": 120,
                 "position_km": 0 if i % 2 == 0 else 25, 
                 "current_track": 1 if i % 2 == 0 else 2,
                 "priority": 5, "delay_minutes": np.random.randint(0, 5)}
                for i in range(4)
            ]
        }

    @staticmethod
    def _generate_l3():
        """Level 3: Real Topology (Siena-Empoli) - High Traffic Injection"""
        # Load the GROUND TRUTH map
        try:
            with open("scenarios/siena_empoli_real.json", "r") as f:
                scenario = json.load(f)
            
            # Inject dynamic traffic (8 trains)
            # Focus on the single-track bottleneck (Siena-Empoli)
            scenario['trains'] = []
            
            # Inject dynamic traffic (8 trains) using VALID ROUTES
            # We must use RoutePlanner logic (simplified here for curriculum generation)
            # Or assume we have network graph available.
            # Ideally: Import RoutePlanner, but for simplicity in curriculum generator 
            # we rely on pre-calculated key routes or load them dynamically.
            
            # Since importing RoutePlanner inside static method might be tricky with deps,
            # We hardcode valid routes for L3 based on the NEW Siena-Empoli map.
            
            # Corrected FS Track Sequences for Level 3
            # Empoli (0) -> Granaiolo(26) -> ... -> Siena(28)
            # Tracks: 100, 101, 102, 103, 104, 105, 106, 107, 108
            route_empoli_siena = [100, 101, 102, 103, 104, 105, 106, 107, 108] 
            route_siena_empoli = [108, 107, 106, 105, 104, 103, 102, 101, 100]
            
            scenario['trains'] = []
            
            # 4 trains EMPOLI -> SIENA
            for i in range(4):
                scenario['trains'].append({
                    "id": i, 
                    "origin_station": 0,    # Empoli
                    "destination_station": 28, # Siena
                    "scheduled_departure_time": f"08:{i*20:02d}:00", 
                    "velocity_kmh": 100,
                    "position_km": 0.0, 
                    "current_track": route_empoli_siena[0],
                    "planned_route": route_empoli_siena,
                    "route_index": 0,
                    "priority": 5, 
                    "delay_minutes": np.random.randint(0, 10) # Higher variety
                })
                
            # 4 trains SIENA -> EMPOLI
            for i in range(4):
                scenario['trains'].append({
                    "id": i + 4, 
                    "origin_station": 28, # Siena
                    "destination_station": 0,  # Empoli
                    "scheduled_departure_time": f"08:{10 + i*20:02d}:00", 
                    "velocity_kmh": 100,
                    "position_km": 0.0, 
                    "current_track": route_siena_empoli[0],
                    "planned_route": route_siena_empoli,
                    "route_index": 0,
                    "priority": 5, 
                    "delay_minutes": np.random.randint(0, 10)
                })
                
            return scenario
        except Exception as e:
            logger.error(f"Failed to load L3 real map: {e}")
            # Fallback to synthetic hub if file missing
            return CurriculumManager._generate_l2()

    @staticmethod
    def _generate_l4():
        """Level 4: High Congestion on Linear Line"""
        num_stations = 10
        stations = [{"id": i, "name": f"Line {i}", "num_platforms": 2} for i in range(num_stations)]
        tracks = [{"id": i, "length_km": 12.0, "is_single_track": True, "capacity": 1, "station_ids": [i, i+1]} 
                  for i in range(num_stations-1)]
        trains = []
        for i in range(20):
            d = 0 if i < 10 else num_stations-1
            dest = num_stations-1 if i < 10 else 0
            trains.append({
                "id": i, "origin_station": d, "destination_station": dest,
                "scheduled_departure_time": f"15:{i:02d}:00", "velocity_kmh": 110,
                "position_km": 0 if i < 10 else 108, "current_track": 0 if i < 10 else num_stations-2,
                "priority": 5, "delay_minutes": np.random.randint(0, 15)
            })
        return {"stations": stations, "tracks": tracks, "trains": trains}

    @staticmethod
    def _generate_l5():
        """Level 5: Random Grid with many agents"""
        # Load a base from a real scenario but randomize it
        try:
            with open("scenarios/toscana_cleaned.json", "r") as f:
                base = json.load(f)
                # Keep first 20 stations and related tracks/trains
                subset_stations = base['stations'][:20]
                s_ids = {s['id'] for s in subset_stations}
                subset_tracks = [t for t in base['tracks'] if all(sid in s_ids for sid in t['station_ids'])]
                subset_trains = [t for t in base['trains'] if t['origin_station'] in s_ids and t['destination_station'] in s_ids]
                return {"stations": subset_stations, "tracks": subset_tracks, "trains": subset_trains[:50]}
        except:
            return CurriculumManager._generate_l4() # Fallback

    @staticmethod
    def determine_level(episode_reward: float, current_level: int, threshold: float = -100) -> int:
        """
        Stochastic Curriculum: Hard-Switching.
        Instead of waiting for perfect score, try next level occasionally.
        """
        import random
        
        # Soft threshold for exploration (-300 is decent but not perfect)
        exploration_threshold = threshold * 3.0 
        
        if episode_reward > threshold:
            # Solid performance -> Advance permanently
            logger.info(f"Performance target reached ({episode_reward:.1f} > {threshold}). Advancing to Level {current_level + 1}")
            return min(5, current_level + 1)
            
        elif episode_reward > exploration_threshold and current_level < 5:
            # Decent performance -> Try next level 20% of the time (Epsilon-Greedy)
            if random.random() < 0.20:
                logger.info("🎲 Exploring Next Level (20% chance)...")
                return current_level + 1
        
        return current_level
