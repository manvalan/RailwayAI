import torch
import torch.optim as optim
import numpy as np
import argparse
import os
from env import RailwayGymEnv
from scenario_loader import ScenarioLoader
from constraints import SafetyConstraintLayer
from models import ActorNetwork, CriticNetwork
import logging

# Force INFO level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)
print("Training script started...") # Direct output for verification

def train_mappo(args):
    """
    MAPPO training with scenario scaling and checkpointing.
    """
    # Load Scenario
    scenario_abs_path = os.path.abspath(args.scenario)
    logger.info(f"Attempting to load scenario from: {scenario_abs_path}")
    scenario = ScenarioLoader.load_scenario(args.scenario)
    env = RailwayGymEnv(scenario['tracks'], scenario['stations'], scenario['trains'])
    
    agent_ids = env.agent_ids
    obs_dim = 8  # 1 (pos) + 1 (track) + 1 (vel) + 5 (neighbors)
    
    # Universal Policy (Shared Weights)
    actor = ActorNetwork(obs_dim)
    critic = CriticNetwork(obs_dim)
    
    # Load checkpoint if exists
    if args.checkpoint and os.path.exists(args.checkpoint):
        logger.info(f"Loading checkpoint from {args.checkpoint}")
        ckpt = torch.load(args.checkpoint)
        critic.load_state_dict(ckpt['critic'])
        actor.load_state_dict(ckpt['actor'])
    
    actor_opt = optim.Adam(actor.parameters(), lr=args.lr)
    critic_opt = optim.Adam(critic.parameters(), lr=args.lr)
    
    safety_layer = SafetyConstraintLayer(env.raw_tracks)
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    for episode in range(args.episodes):
        obs, _ = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            actions = {}
            all_o_tensors = []
            
            for aid in agent_ids:
                o = obs[aid]
                o_vec = np.concatenate([o['position'], [o['current_track']], o['velocity'], o['neighbor_occupancy']])
                o_tensor = torch.FloatTensor(o_vec).unsqueeze(0)
                all_o_tensors.append(o_tensor)
                
                probs = actor(o_tensor)
                dist = torch.distributions.Categorical(probs)
                action = dist.sample()
                actions[aid] = action.item()
            
            # Critic processing (Mean Field)
            batch_obs = torch.cat(all_o_tensors, dim=0)
            value = critic(batch_obs)
            
            # Constraint Layer (Safety)
            safe_actions = safety_layer.apply_constraints(actions, {"trains": env.trains})
            
            # Environment STEP (Accelerated by C++ if HAS_CPP)
            next_obs, rewards, done, truncated, info = env.step(safe_actions)
            
            total_reward = sum(rewards.values())
            episode_reward += total_reward
            obs = next_obs
            if truncated: done = True
                
        if episode % 1 == 0:  # Log every episode for smoother real-time dashboard updates
            logger.info(f"Episode {episode}: Reward = {episode_reward:.2f}, Conflicts = {info.get('conflicts', 0)}")
            
        # Checkpoint
        if episode > 0 and episode % args.save_interval == 0:
            ckpt_path = os.path.join(args.out_dir, f"mappo_universal_ep{episode}.pth")
            torch.save({
                'critic': critic.state_dict(),
                'actor': actor.state_dict(),
                'episode': episode
            }, ckpt_path)
            logger.info(f"Saved checkpoint: {ckpt_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str, required=True, help="Path to JSON scenario")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--save_interval", type=int, default=50)
    parser.add_argument("--checkpoint", type=str, default=None)
    parser.add_argument("--out_dir", type=str, default="checkpoints")
    
    args = parser.parse_args()
    train_mappo(args)
