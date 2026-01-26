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
        
        # Add a "no delay" solution to the population as a baseline
        population[0] = {train['id']: 0.0 for train in trains}
        
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
        Initialize population of delay solutions.
        
        Each solution is a dict: {train_id: delay_minutes}
        """
        population = []
        
        # Get unique train IDs involved in conflicts
        conflict_train_ids = set()
        for conflict in conflicts:
            conflict_train_ids.add(conflict['train1_id'])
            conflict_train_ids.add(conflict['train2_id'])
        
        for _ in range(size):
            solution = {}
            for train_id in conflict_train_ids:
                # Random delay between 0 and 60 minutes
                solution[train_id] = random.uniform(0, 60)
            population.append(solution)
        
        return population
    
    def _evaluate_fitness(self, solution: Dict, trains: List[Dict], time_horizon: float) -> float:
        """
        Evaluate fitness of a solution.
        
        Fitness components:
        1. Number of conflicts (minimize)
        2. Total delay (minimize)
        3. Max delay for single train (minimize)
        
        Returns:
            Fitness score (higher is better, 1.0 = perfect)
        """
        # Apply delays to trains
        adjusted_trains = []
        for train in trains:
            train_copy = deepcopy(train)
            if train['id'] in solution:
                delay = solution[train['id']]
                # Adjust scheduled_departure_time
                if 'scheduled_departure_time' in train_copy:
                    h, m, s = map(int, train_copy['scheduled_departure_time'].split(':'))
                    total_minutes = h * 60 + m + delay
                    new_h = int(total_minutes // 60) % 24
                    new_m = int(total_minutes % 60)
                    train_copy['scheduled_departure_time'] = f"{new_h:02d}:{new_m:02d}:{s:02d}"
                train_copy['delay_minutes'] = train_copy.get('delay_minutes', 0) + delay
            adjusted_trains.append(train_copy)
        
        # Detect conflicts with adjusted schedule
        try:
            conflicts = self.temporal_simulator.detect_future_conflicts(
                adjusted_trains,
                time_horizon_minutes=time_horizon,
                time_step_minutes=1.0  # Finer evaluation
            )
        except Exception as e:
            logger.warning(f"Error in conflict detection: {e}")
            return -1000.0
        
        # Calculate fitness components
        num_conflicts = len(conflicts)
        total_delay = sum(solution.values())
        max_delay = max(solution.values()) if solution else 0
        
        # HEAVY penalty for conflicts
        # Each conflict costs as much as 1000 minutes of delay
        conflict_penalty = num_conflicts * 1000.0
        
        # Fitness is negative - we want to maximize it (bring it closer to 0)
        # We want 0 conflicts AND minimum delay
        fitness = -(conflict_penalty + (total_delay * 0.1) + (max_delay * 0.5))
        
        return fitness
    
    def _select_parents(self, population: List[Dict], fitness_scores: List[float], num_parents: int) -> List[Dict]:
        """Tournament selection"""
        parents = []
        tournament_size = 3
        
        for _ in range(num_parents):
            tournament = random.sample(list(zip(population, fitness_scores)), tournament_size)
            winner = max(tournament, key=lambda x: x[1])
            parents.append(deepcopy(winner[0]))
        
        return parents
    
    def _create_offspring(self, parents: List[Dict], offspring_size: int) -> List[Dict]:
        """Create offspring through crossover and mutation"""
        offspring = []
        
        while len(offspring) < offspring_size:
            if len(parents) < 2:
                break
            
            parent1, parent2 = random.sample(parents, 2)
            
            # Crossover
            child = {}
            all_keys = set(parent1.keys()) | set(parent2.keys())
            for key in all_keys:
                if random.random() < 0.5:
                    child[key] = parent1.get(key, 0)
                else:
                    child[key] = parent2.get(key, 0)
            
            # Mutation (40% chance of mutation - higher for better exploration)
            if random.random() < 0.4:
                if child:
                    mutate_key = random.choice(list(child.keys()))
                    # Randomly change delay: either a small tweak or a completely new random value
                    if random.random() < 0.7:
                        child[mutate_key] = max(0, child[mutate_key] + random.uniform(-15, 15))
                    else:
                        child[mutate_key] = random.uniform(0, 90)
            
            offspring.append(child)
        
        return offspring
    
    def _format_result(self, solution: Dict, trains: List[Dict], iterations: int, fitness: float) -> Dict:
        """Format the result"""
        resolutions = []
        
        for train_id, delay in solution.items():
            if delay > 0.5:  # Only include significant delays
                resolutions.append({
                    'train_id': train_id,
                    'time_adjustment_min': delay,
                    'track_assignment': None,  # Will be filled by caller
                    'confidence': fitness
                })
        
        total_delay = sum(solution.values())
        
        return {
            'resolutions': resolutions,
            'total_delay': total_delay,
            'conflicts_resolved': len(resolutions),
            'iterations': iterations,
            'fitness': fitness
        }
