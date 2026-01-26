"""
Conflict Resolver using Genetic Algorithm

Resolves train conflicts by finding optimal departure time adjustments
that minimize total delay while avoiding cascading conflicts.
"""

from typing import Dict, List, Tuple
import random
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)


class ConflictResolver:
    """Resolves conflicts using genetic algorithm optimization"""
    
    def __init__(self, temporal_simulator, route_planner):
        """
        Initialize conflict resolver.
        
        Args:
            temporal_simulator: TemporalSimulator instance
            route_planner: RoutePlanner instance
        """
        self.temporal_simulator = temporal_simulator
        self.route_planner = route_planner
    
    def resolve_conflicts(self,
                         trains: List[Dict],
                         time_horizon_minutes: float = 120.0,
                         max_iterations: int = 100,
                         population_size: int = 30) -> Dict:
        """
        Resolve conflicts using genetic algorithm.
        
        Args:
            trains: List of train dictionaries
            time_horizon_minutes: Time horizon for conflict detection
            max_iterations: Maximum GA iterations
            population_size: GA population size
        
        Returns:
            Dict with resolutions and metrics
        """
        logger.info(f"Starting conflict resolution for {len(trains)} trains")
        
        # Detect initial conflicts
        initial_conflicts = self.temporal_simulator.detect_future_conflicts(
            trains,
            time_horizon_minutes=time_horizon_minutes,
            time_step_minutes=1.0
        )
        
        if not initial_conflicts:
            logger.info("No conflicts detected")
            return {
                'resolutions': [],
                'total_delay': 0.0,
                'conflicts_resolved': 0,
                'iterations': 0
            }
        
        logger.info(f"Detected {len(initial_conflicts)} initial conflicts")
        
        # Initialize population of solutions
        population = self._initialize_population(trains, initial_conflicts, population_size)
        
        best_solution = None
        best_fitness = -float('inf')
        
        logger.info(f"GA running: pop_size={population_size}, max_iter={max_iterations}")
        
        for iteration in range(max_iterations):
            # Evaluate fitness
            fitness_scores = []
            for solution in population:
                fitness = self._evaluate_fitness(solution, trains, time_horizon_minutes)
                fitness_scores.append(fitness)
                
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_solution = deepcopy(solution)
            
            # Check if we found a perfect solution
            if best_fitness >= 1.0:
                logger.info(f"Found perfect solution at iteration {iteration}")
                break
            
            # Selection
            parents = self._select_parents(population, fitness_scores, population_size // 2)
            
            # Crossover and mutation
            offspring = self._create_offspring(parents, population_size)
            
            # Elitism: keep best 20%
            elite_count = max(1, population_size // 5)
            elite_indices = sorted(range(len(fitness_scores)),
                                 key=lambda i: fitness_scores[i],
                                 reverse=True)[:elite_count]
            elite = [population[i] for i in elite_indices]
            
            population = elite + offspring[:population_size - elite_count]
        
        # Format result
        return self._format_result(best_solution, trains, iteration, best_fitness)
    
    def _initialize_population(self, trains: List[Dict], conflicts: List[Dict], size: int) -> List[Dict]:
        """
        Initialize population of solutions.
        
        Each solution is a dict: {train_id: {'departure_delay': float, 'dwell_delays': [float, ...]}}
        """
        population = []
        
        # Get unique train IDs involved in conflicts
        conflict_train_ids = set()
        for conflict in conflicts:
            conflict_train_ids.add(conflict['train1_id'])
            conflict_train_ids.add(conflict['train2_id'])
        
        for p_idx in range(size):
            solution = {}
            for train_id in conflict_train_ids:
                train = next((t for t in trains if t['id'] == train_id), None)
                if not train: continue
                
                # Use 'or []' because key might be None in the dict
                planned_route = train.get('planned_route') or []
                num_intermediate_stations = max(0, len(planned_route) - 1)
                
                # First solution is always zero delay (baseline)
                if p_idx == 0:
                    solution[train_id] = {
                        'departure_delay': 0.0,
                        'dwell_delays': [0.0] * num_intermediate_stations
                    }
                else:
                    # Random delays
                    solution[train_id] = {
                        'departure_delay': random.uniform(0, 60),
                        'dwell_delays': [random.uniform(0, 15) for _ in range(num_intermediate_stations)]
                    }
            population.append(solution)
        
        return population
    
    def _evaluate_fitness(self, solution: Dict, trains: List[Dict], time_horizon: float) -> float:
        """Evaluate fitness of a multi-parameter solution."""
        # Apply delays to trains
        adjusted_trains = []
        for train in trains:
            train_copy = deepcopy(train)
            if train['id'] in solution:
                params = solution[train['id']]
                dep_delay = params['departure_delay']
                
                # Apply departure delay
                if 'scheduled_departure_time' in train_copy:
                    h, m, s = map(int, train_copy['scheduled_departure_time'].split(':'))
                    total_minutes = h * 60 + m + dep_delay
                    new_h = int(total_minutes // 60) % 24
                    new_m = int(total_minutes % 60)
                    train_copy['scheduled_departure_time'] = f"{new_h:02d}:{new_m:02d}:{s:02d}"
                train_copy['delay_minutes'] = train_copy.get('delay_minutes', 0) + dep_delay
                
                # Apply dwell delays
                train_copy['dwell_delays'] = params['dwell_delays']
                
            adjusted_trains.append(train_copy)
        
        # Detect conflicts with adjusted schedule
        try:
            conflicts = self.temporal_simulator.detect_future_conflicts(
                adjusted_trains,
                time_horizon_minutes=time_horizon,
                time_step_minutes=1.0
            )
        except Exception as e:
            logger.warning(f"Error in conflict detection: {e}")
            return -10000.0
        
        # Calculate fitness components
        num_conflicts = len(conflicts)
        
        total_dep_delay = sum(s['departure_delay'] for s in solution.values())
        total_dwell_delay = sum(sum(s['dwell_delays']) for s in solution.values())
        total_delay = total_dep_delay + total_dwell_delay
        
        max_delay = 0
        if solution:
            max_delay = max(s['departure_delay'] + sum(s['dwell_delays']) for s in solution.values())
        
        # Extreme penalty for conflicts
        conflict_penalty = num_conflicts * 2000.0
        
        # Fitness: maximize (closer to 0 is better)
        # We value resolving conflicts significantly more than saving minutes
        fitness = -(conflict_penalty + (total_delay * 0.1) + (max_delay * 0.5))
        
        return fitness
    
    def _create_offspring(self, parents: List[Dict], offspring_size: int) -> List[Dict]:
        """Create offspring with deep crossover and mutation."""
        offspring = []
        
        while len(offspring) < offspring_size and len(parents) >= 2:
            parent1, parent2 = random.sample(parents, 2)
            
            # Crossover: per-train basis
            child = {}
            all_train_ids = set(parent1.keys()) | set(parent2.keys())
            for tid in all_train_ids:
                if random.random() < 0.5:
                    child[tid] = deepcopy(parent1.get(tid, {'departure_delay': 0, 'dwell_delays': []}))
                else:
                    child[tid] = deepcopy(parent2.get(tid, {'departure_delay': 0, 'dwell_delays': []}))
            
            # Mutation
            if random.random() < 0.4:
                if child:
                    tid = random.choice(list(child.keys()))
                    # Mutate departure delay OR one dwell delay
                    if random.random() < 0.5:
                        child[tid]['departure_delay'] = max(0, child[tid]['departure_delay'] + random.uniform(-10, 10))
                    else:
                        dd = child[tid]['dwell_delays']
                        if dd:
                            idx = random.randrange(len(dd))
                            dd[idx] = max(0, dd[idx] + random.uniform(-5, 5))
            
            offspring.append(child)
        
        return offspring
    
    def _format_result(self, solution: Dict, trains: List[Dict], iterations: int, fitness: float) -> Dict:
        """Format the result including dwell delay details."""
        resolutions = []
        
        for train_id, params in solution.items():
            dep_delay = params['departure_delay']
            dwell_delays = params['dwell_delays']
            
            # Check if there's any adjustment
            if dep_delay > 0.1 or any(d > 0.1 for d in dwell_delays):
                resolutions.append({
                    'train_id': train_id,
                    'time_adjustment_min': dep_delay,
                    'dwell_delays': dwell_delays,
                    'confidence': 1.0 if fitness > -100 else 0.8
                })
        
        total_delay = sum(s['departure_delay'] + sum(s['dwell_delays']) for s in solution.values())
        
        return {
            'resolutions': resolutions,
            'total_delay': total_delay,
            'conflicts_resolved': len(resolutions),
            'iterations': iterations,
            'fitness': fitness
        }
