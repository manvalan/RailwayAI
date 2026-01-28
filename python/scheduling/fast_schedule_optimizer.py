
"""
Fast Schedule Generator using Genetic Algorithm.
Optimized for speed (sub-second execution) to define routes and hourly cadence.
"""

from typing import Dict, List, Tuple
import random
import time
import math
from dataclasses import dataclass, asdict

# Lightweight data structures for speed
@dataclass
class FastStation:
    id: int
    neighbors: List[int]

@dataclass
class FastTrainSpec:
    origin: int
    destination: int
    cadence_minutes: int  # e.g., 60 for every hour
    start_offset: int     # e.g., 15 for XX:15 departures

class FastScheduleOptimizer:
    def __init__(self, stations: List[Dict], tracks: List[Dict]):
        # Pre-process graph for O(1) lookups
        self.station_map = {s['id']: FastStation(s['id'], []) for s in stations}
        self.tracks = tracks
        
        # Build adjacency list from tracks
        for track in tracks:
            s_ids = track['station_ids']
            if len(s_ids) >= 2:
                u, v = s_ids[0], s_ids[1]
                if u in self.station_map and v in self.station_map:
                    self.station_map[u].neighbors.append(v)
                    self.station_map[v].neighbors.append(u)
        
        # Note: parent_hub_id is stored in station metadata for:
        # - Identifying HUB stations (for visualization and priority)
        # - Emergency routing scenarios
        # But we do NOT create automatic neighbors between hub stations
        # to keep network types (AV, Regional) physically separated.

    def generate_plan(self, 
                     target_trains_count: int = 5, 
                     time_window_hours: int = 24, 
                     max_generations: int = 50,
                     population_size: int = 20) -> Dict:
        """
        Generates a route plan and cadence quickly.
        """
        start_time = time.time()
        
        # 1. Identify key terminals (leaf nodes or high degree nodes)
        terminals = self._identify_terminals()
        if len(terminals) < 2:
            return {"error": "Network too small"}

        # 2. Genetic Algorithm
        # Chromosome: List of FastTrainSpec (Route + Cadence)
        population = self._init_population(population_size, terminals, target_trains_count)
        
        best_solution = None
        best_fitness = -1.0
        
        for gen in range(max_generations):
            # Check elapsed time (strict budget 200ms for responsiveness)
            if time.time() - start_time > 0.5: 
                break
                
            # Evaluate
            fitnesses = [(self._fitness(ind), ind) for ind in population]
            fitnesses.sort(key=lambda x: x[0], reverse=True)
            
            current_best = fitnesses[0]
            if current_best[0] > best_fitness:
                best_fitness = current_best[0]
                best_solution = current_best[1]
            
            # Selection & Crossover (Elitism)
            survivors = fitnesses[:population_size // 2]
            parents = [p[1] for p in survivors]
            
            new_pop = list(parents) # Keep best half
            
            # Fill rest with offspring
            while len(new_pop) < population_size:
                p1, p2 = random.sample(parents, 2)
                child = self._crossover(p1, p2)
                if random.random() < 0.1: # 10% mutation
                    self._mutate(child, terminals)
                new_pop.append(child)
                
            population = new_pop

        # 3. Format Output
        return self._format_output(best_solution, time_window_hours)

    def _identify_terminals(self) -> List[int]:
        """Finds stations suitable for Origin/Destination (end of lines or hubs)."""
        leaves = []
        hubs = []
        for sid, node in self.station_map.items():
            degree = len(node.neighbors)
            if degree == 1:
                leaves.append(sid)
            elif degree > 2:
                hubs.append(sid)
        
        candidates = leaves if leaves else []
        candidates.extend(hubs)
        
        # Fallback: if we found fewer than 2 interesting nodes, use ALL stations
        if len(candidates) < 2:
            return list(self.station_map.keys())
            
        return list(set(candidates))

    def _init_population(self, size, terminals, n_specs):
        pop = []
        for _ in range(size):
            ind = []
            for _ in range(n_specs):
                o, d = random.sample(terminals, 2)
                cadence = random.choice([30, 60, 120]) # Minutes
                offset = random.choice([0, 15, 30, 45])
                ind.append(FastTrainSpec(o, d, cadence, offset))
            pop.append(ind)
        return pop

    def _get_full_path(self, start: int, end: int) -> List[int]:
        """Simple BFS to find the actual path between two stations. Returns [] if no path."""
        if start == end: return [start]
        queue = [(start, [start])]
        visited = {start}
        while queue:
            node, path = queue.pop(0)
            if node == end: return path
            for neighbor in self.station_map[node].neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        return []

    def _fitness(self, individual: List[FastTrainSpec]) -> float:
        """
        Fitness function with Full Path Interchange Awareness.
        """
        score = 0.0
        covered_stations = set()
        stations_served_by_line = [] # List of sets
        
        # Identify hubs
        hubs = {sid for sid, node in self.station_map.items() if len(node.neighbors) > 2}
        
        for spec in individual:
            path = self._get_full_path(spec.origin, spec.destination)
            
            if not path:
                score -= 100 # Heavy penalty for impossible routes
                continue
                
            dist = len(path) - 1
            if dist == 0:
                score -= 20
                continue

            # Valid route reward - reward complexity and length
            score += 30 + (dist * 3)
            
            # Coverage using the FULL PATH
            path_set = set(path)
            covered_stations.update(path_set)
            stations_served_by_line.append(path_set)
            
            # Hub traversal reward: lines that pass through hubs are more valuable
            hubs_traversed = path_set.intersection(hubs)
            score += len(hubs_traversed) * 15

        # --- Interchange Reward (Full Path) ---
        station_service_count = {}
        for line_path_set in stations_served_by_line:
            for sid in line_path_set:
                station_service_count[sid] = station_service_count.get(sid, 0) + 1
        
        for sid, count in station_service_count.items():
            if count > 1:
                # Multiple lines pass through this station
                is_hub = sid in hubs
                multiplier = 25 if is_hub else 10 # High reward for hub interchanges
                score += (count - 1) * multiplier
        
        # Global coverage reward
        score += len(covered_stations) * 5.0
        
        return score

    def _crossover(self, p1, p2):
        cut = len(p1) // 2
        return p1[:cut] + p2[cut:]

    def _mutate(self, ind, terminals):
        idx = random.randrange(len(ind))
        # Mutate one gene
        choice = random.random()
        if choice < 0.33:
            ind[idx].origin = random.choice(terminals)
        elif choice < 0.66:
            ind[idx].cadence_minutes = random.choice([30, 60, 120])
        else:
            ind[idx].start_offset = random.choice([0, 15, 30, 45])

    def _format_output(self, solution: List[FastTrainSpec], window_hours):
        if not solution:
            return {
                "proposed_lines": [],
                "schedule_preview": []
            }

        result = {
            "proposed_lines": [],
            "schedule_preview": []
        }
        
        # Generate proposed lines
        for i, spec in enumerate(solution):
            line_id = f"L{i+1}"
            
            # Get the full path including intermediate stations
            full_path = self._get_full_path(spec.origin, spec.destination)
            
            result["proposed_lines"].append({
                "id": line_id,
                "origin": spec.origin,
                "destination": spec.destination,
                "stops": full_path, # Added intermediate stations
                "frequency": f"Every {spec.cadence_minutes} min",
                "first_departure_minute": spec.start_offset
            })
            
            # Generate concrete trains for preview (first 2 hours)
            current_min = spec.start_offset
            while current_min < 120: # 2 hour preview
                h = current_min // 60
                m = current_min % 60
                time_str = f"{h:02d}:{m:02d}:00"
                result["schedule_preview"].append({
                    "line": line_id,
                    "departure": time_str,
                    "origin": spec.origin,
                    "destination": spec.destination,
                    "stops": full_path # Also helpful in preview
                })
                current_min += spec.cadence_minutes
                
        return result
