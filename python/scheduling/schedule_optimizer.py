"""
Schedule Optimizer using Genetic Algorithm

Optimizes train departure times to achieve target capacity utilization
while minimizing conflicts and ensuring good temporal distribution.
"""

from typing import Dict, List, Optional, Tuple
import random
import logging
from datetime import datetime, timedelta
from copy import deepcopy

logger = logging.getLogger(__name__)


class ScheduleOptimizer:
    """Optimizes train schedules using genetic algorithm"""
    
    def __init__(self, 
                 network_metrics: Dict,
                 trains: List[Dict],
                 time_window: Dict,
                 target_utilization: float,
                 route_planner,
                 temporal_simulator):
        """
        Initialize schedule optimizer.
        
        Args:
            network_metrics: Output from NetworkAnalyzer
            trains: List of trains to schedule
            time_window: Dict with 'start' and 'end' times (HH:MM:SS)
            target_utilization: Target capacity utilization (0.0-1.0)
            route_planner: RoutePlanner instance
            temporal_simulator: TemporalSimulator instance
        """
        self.network_metrics = network_metrics
        self.trains = trains
        self.time_window = time_window
        self.target_utilization = target_utilization
        self.route_planner = route_planner
        self.temporal_simulator = temporal_simulator
        
        # Parse time window
        self.start_minutes = self._time_to_minutes(time_window['start'])
        self.end_minutes = self._time_to_minutes(time_window['end'])
        self.window_duration = self.end_minutes - self.start_minutes
        
        logger.info(f"ScheduleOptimizer initialized: {len(trains)} trains, "
                   f"window={time_window['start']}-{time_window['end']}, "
                   f"target={target_utilization:.2%}")
    
    def optimize(self, 
                 max_iterations: int = 1000,
                 population_size: int = 50,
                 mutation_rate: float = 0.1) -> Dict:
        """
        Run genetic algorithm to find optimal schedule.
        
        Args:
            max_iterations: Maximum number of generations
            population_size: Number of schedules in each generation
            mutation_rate: Probability of mutation (0.0-1.0)
        
        Returns:
            Dict with optimized schedule and metrics
        """
        logger.info(f"Starting optimization: max_iter={max_iterations}, "
                   f"pop_size={population_size}, mutation={mutation_rate}")
        
        # Initialize population
        population = self._initialize_population(population_size)
        best_fitness = -float('inf')
        best_schedule = None
        generations_without_improvement = 0
        
        for iteration in range(max_iterations):
            # Evaluate fitness for all schedules
            fitness_scores = []
            for schedule in population:
                fitness = self._evaluate_fitness(schedule)
                fitness_scores.append(fitness)
                
                if fitness > best_fitness:
                    best_fitness = fitness
                    best_schedule = deepcopy(schedule)
                    generations_without_improvement = 0
                    logger.info(f"Generation {iteration}: New best fitness = {fitness:.4f}")
            
            # Check convergence
            generations_without_improvement += 1
            if generations_without_improvement > 50:
                logger.info(f"Converged after {iteration} generations")
                break
            
            # Selection
            parents = self._select_parents(population, fitness_scores, population_size // 2)
            
            # Crossover and mutation
            offspring = self._create_offspring(parents, population_size, mutation_rate)
            
            # Next generation (elitism: keep best 10%)
            elite_count = max(1, population_size // 10)
            elite_indices = sorted(range(len(fitness_scores)), 
                                 key=lambda i: fitness_scores[i], 
                                 reverse=True)[:elite_count]
            elite = [population[i] for i in elite_indices]
            
            population = elite + offspring[:population_size - elite_count]
        
        # Format result
        return self._format_result(best_schedule, iteration, best_fitness)
    
    def _initialize_population(self, size: int) -> List[List[Dict]]:
        """
        Create initial population of random schedules.
        
        Args:
            size: Population size
        
        Returns:
            List of schedules (each schedule is a list of train dicts with departure times)
        """
        population = []
        
        for _ in range(size):
            schedule = []
            for train in self.trains:
                train_copy = deepcopy(train)
                # Random departure time within window
                departure_minutes = random.uniform(self.start_minutes, self.end_minutes)
                train_copy['scheduled_departure_time'] = self._minutes_to_time(departure_minutes)
                train_copy['departure_minutes'] = departure_minutes  # For easier calculation
                schedule.append(train_copy)
            population.append(schedule)
        
        return population
    
    def _evaluate_fitness(self, schedule: List[Dict]) -> float:
        """
        Evaluate fitness of a schedule.
        
        Components:
        1. Capacity utilization (how close to target)
        2. Number of conflicts (minimize)
        3. Temporal distribution (uniformity)
        
        Args:
            schedule: List of trains with departure times
        
        Returns:
            Fitness score (higher is better)
        """
        # Weights for different objectives
        w_utilization = 0.4
        w_conflicts = 0.4
        w_distribution = 0.2
        
        # 1. Capacity utilization score
        utilization = self._calculate_utilization(schedule)
        utilization_score = 1.0 - abs(utilization - self.target_utilization)
        
        # 2. Conflict score
        conflicts = self._count_conflicts(schedule)
        conflict_score = 1.0 / (1.0 + conflicts)
        
        # 3. Temporal distribution score
        distribution_score = self._temporal_distribution_score(schedule)
        
        # Combined fitness
        fitness = (w_utilization * utilization_score + 
                  w_conflicts * conflict_score + 
                  w_distribution * distribution_score)
        
        return fitness
    
    def _calculate_utilization(self, schedule: List[Dict]) -> float:
        """Calculate average network utilization for this schedule."""
        # Simplified: count trains per time slot
        time_slots = [0] * (self.window_duration // 60 + 1)  # Hourly slots
        
        for train in schedule:
            slot = int((train['departure_minutes'] - self.start_minutes) // 60)
            if 0 <= slot < len(time_slots):
                time_slots[slot] += 1
        
        # Average utilization
        max_capacity = len(self.trains) / len(time_slots)
        avg_utilization = sum(time_slots) / len(time_slots) / max_capacity if max_capacity > 0 else 0
        
        return min(avg_utilization, 1.0)
    
    def _count_conflicts(self, schedule: List[Dict]) -> int:
        """
        Count conflicts in the schedule using temporal simulation.
        
        Args:
            schedule: List of trains with departure times
        
        Returns:
            Number of conflicts
        """
        try:
            # Use temporal simulator to detect conflicts
            conflicts = self.temporal_simulator.detect_future_conflicts(
                schedule,
                time_horizon_minutes=self.window_duration,
                time_step_minutes=5.0  # Check every 5 minutes
            )
            return len(conflicts)
        except Exception as e:
            logger.warning(f"Error counting conflicts: {e}")
            return 999  # High penalty for invalid schedules
    
    def _temporal_distribution_score(self, schedule: List[Dict]) -> float:
        """
        Score how evenly trains are distributed over time.
        
        Returns:
            Score 0.0-1.0 (1.0 = perfectly uniform)
        """
        # Divide time window into bins
        num_bins = 10
        bin_size = self.window_duration / num_bins
        bins = [0] * num_bins
        
        for train in schedule:
            bin_idx = int((train['departure_minutes'] - self.start_minutes) / bin_size)
            if 0 <= bin_idx < num_bins:
                bins[bin_idx] += 1
        
        # Calculate variance
        mean = len(schedule) / num_bins
        variance = sum((count - mean) ** 2 for count in bins) / num_bins
        
        # Convert to score (lower variance = higher score)
        max_variance = mean ** 2  # Worst case: all trains in one bin
        score = 1.0 - (variance / max_variance) if max_variance > 0 else 1.0
        
        return score
    
    def _select_parents(self, population: List, fitness_scores: List[float], num_parents: int) -> List:
        """
        Select parents using tournament selection.
        
        Args:
            population: Current population
            fitness_scores: Fitness scores for each individual
            num_parents: Number of parents to select
        
        Returns:
            List of selected parents
        """
        parents = []
        tournament_size = 3
        
        for _ in range(num_parents):
            # Tournament selection
            tournament = random.sample(list(zip(population, fitness_scores)), tournament_size)
            winner = max(tournament, key=lambda x: x[1])
            parents.append(deepcopy(winner[0]))
        
        return parents
    
    def _create_offspring(self, parents: List, offspring_size: int, mutation_rate: float) -> List:
        """
        Create offspring through crossover and mutation.
        
        Args:
            parents: Selected parents
            offspring_size: Number of offspring to create
            mutation_rate: Probability of mutation
        
        Returns:
            List of offspring schedules
        """
        offspring = []
        
        while len(offspring) < offspring_size:
            # Select two random parents
            parent1, parent2 = random.sample(parents, 2)
            
            # Crossover
            child = self._crossover(parent1, parent2)
            
            # Mutation
            if random.random() < mutation_rate:
                child = self._mutate(child)
            
            offspring.append(child)
        
        return offspring
    
    def _crossover(self, parent1: List[Dict], parent2: List[Dict]) -> List[Dict]:
        """
        Perform crossover between two parents.
        
        Uses uniform crossover: randomly select departure time from either parent.
        """
        child = []
        
        for train1, train2 in zip(parent1, parent2):
            train_copy = deepcopy(train1 if random.random() < 0.5 else train2)
            child.append(train_copy)
        
        return child
    
    def _mutate(self, schedule: List[Dict]) -> List[Dict]:
        """
        Mutate a schedule by randomly changing some departure times.
        """
        mutated = deepcopy(schedule)
        
        # Mutate 1-3 random trains
        num_mutations = random.randint(1, min(3, len(mutated)))
        trains_to_mutate = random.sample(range(len(mutated)), num_mutations)
        
        for idx in trains_to_mutate:
            # New random departure time
            new_departure = random.uniform(self.start_minutes, self.end_minutes)
            mutated[idx]['scheduled_departure_time'] = self._minutes_to_time(new_departure)
            mutated[idx]['departure_minutes'] = new_departure
        
        return mutated
    
    def _format_result(self, schedule: List[Dict], iterations: int, fitness: float) -> Dict:
        """Format optimization result."""
        # Calculate final metrics
        utilization = self._calculate_utilization(schedule)
        conflicts = self._count_conflicts(schedule)
        distribution = self._temporal_distribution_score(schedule)
        
        return {
            'schedule': schedule,
            'metrics': {
                'average_capacity_utilization': utilization,
                'total_conflicts': conflicts,
                'temporal_distribution_score': distribution,
                'fitness': fitness
            },
            'iterations': iterations,
            'convergence': fitness
        }
    
    def _time_to_minutes(self, time_str: str) -> float:
        """Convert HH:MM:SS to minutes since midnight."""
        h, m, s = map(int, time_str.split(':'))
        return h * 60 + m + s / 60.0
    
    def _minutes_to_time(self, minutes: float) -> str:
        """Convert minutes since midnight to HH:MM:SS."""
        h = int(minutes // 60)
        m = int(minutes % 60)
        s = int((minutes % 1) * 60)
        return f"{h:02d}:{m:02d}:{s:02d}"
