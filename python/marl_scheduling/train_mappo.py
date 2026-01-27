import torch
import torch.optim as optim
import numpy as np
from env import RailwayGymEnv
from constraints import SafetyConstraintLayer
from models import ActorNetwork, CriticNetwork
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_mappo(env: RailwayGymEnv, episodes: int = 100):
    """
    Simplified MAPPO training loop.
    """
    agent_ids = env.agent_ids
    obs_dim = 8  # 1 (pos) + 1 (track) + 1 (vel) + 5 (neighbors)
    global_obs_dim = obs_dim * len(agent_ids)
    
    actors = {aid: ActorNetwork(obs_dim) for aid in agent_ids}
    critic = CriticNetwork(global_obs_dim)
    
    actor_opts = {aid: optim.Adam(actors[aid].parameters(), lr=1e-3) for aid in agent_ids}
    critic_opt = optim.Adam(critic.parameters(), lr=1e-3)
    
    safety_layer = SafetyConstraintLayer(env.raw_tracks)
    
    for episode in range(episodes):
        obs, _ = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            # 1. Collect actions from actors
            actions = {}
            action_log_probs = {}
            
            for aid in agent_ids:
                # Prepare observation
                o = obs[aid]
                # Flatten the observation dict into a vector
                o_vec = np.concatenate([o['position'], [o['current_track']], o['velocity'], o['neighbor_occupancy']])
                o_tensor = torch.FloatTensor(o_vec).unsqueeze(0)
                
                probs = actors[aid](o_tensor)
                dist = torch.distributions.Categorical(probs)
                action = dist.sample()
                
                actions[aid] = action.item()
                action_log_probs[aid] = dist.log_prob(action)
            
            # 2. Apply Safety Constraints
            safe_actions = safety_layer.apply_constraints(actions, {"trains": env.trains})
            
            # 3. Environment Step
            next_obs, rewards, done, truncated, info = env.step(safe_actions)
            
            # 4. Centralized Critic Evaluation
            # Concatenate all observations for global state
            obs_vecs = []
            for aid in agent_ids:
                o = obs[aid]
                obs_vecs.append(np.concatenate([o['position'], [o['current_track']], o['velocity'], o['neighbor_occupancy']]))
            global_obs = torch.FloatTensor(np.concatenate(obs_vecs)).unsqueeze(0)
            
            value = critic(global_obs)
            
            # 5. Update Networks (Simplified PPO Step)
            # This is a placeholder for the actual PPO loss calculation
            # involving advantages, ratios, and clipping.
            
            # Mock update logic
            total_reward = sum(rewards.values())
            episode_reward += total_reward
            
            # Update obs
            obs = next_obs
            if truncated:
                done = True
                
        if episode % 10 == 0:
            logger.info(f"Episode {episode}: Total Reward = {episode_reward:.2f}, Conflicts = {info.get('conflicts', 0)}")

if __name__ == "__main__":
    # Mock data for demonstration
    mock_tracks = [
        {'id': 1, 'station_ids': [101, 102], 'length_km': 10, 'capacity': 1, 'is_single_track': True},
        {'id': 2, 'station_ids': [102, 103], 'length_km': 15, 'capacity': 2, 'is_single_track': False}
    ]
    mock_stations = [{'id': 101, 'name': 'A'}, {'id': 102, 'name': 'B'}, {'id': 103, 'name': 'C'}]
    mock_trains = [
        {'id': 1, 'planned_route': [1, 2], 'velocity_kmh': 120},
        {'id': 2, 'planned_route': [2, 1], 'velocity_kmh': 100} # Potential conflict on track 1
    ]
    
    env = RailwayGymEnv(mock_tracks, mock_stations, mock_trains)
    train_mappo(env, episodes=50)
