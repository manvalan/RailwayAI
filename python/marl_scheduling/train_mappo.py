import sys
import os
from pathlib import Path

# IMMEDIATE DIAGNOSTIC
print(">>> PYTHON INTERPRETER STARTED", flush=True)

# Limit threads to prevent VPS freeze during torch import/execution
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

import resource
def get_mem():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 # KB on Mac, but usually KB on Linux too
print(f">>> MEMORY USAGE (START): {get_mem():.2f} MB", flush=True)
print(f">>> CWD: {os.getcwd()}", flush=True)
print(f">>> PYTHONPATH: {os.environ.get('PYTHONPATH')}", flush=True)

# Add current directory to sys.path BEFORE any other imports
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

print(f">>> SYS.PATH UPDATED: {sys.path[0]}", flush=True)

print(">>> ATTEMPTING TO IMPORT TORCH (this can take time)...", flush=True)
import torch
print(f">>> TORCH LOADED: {torch.__version__} (Mem: {get_mem():.2f} MB)", flush=True)
import torch.optim as optim
import numpy as np
import argparse
import logging

print(">>> ATTEMPTING LOCAL IMPORTS...", flush=True)
from env import RailwayGymEnv
from scenario_loader import ScenarioLoader
from constraints import SafetyConstraintLayer
from models import ActorNetwork, CriticNetwork

print(">>> ALL IMPORTS SUCCESSFUL", flush=True)

# Force INFO level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)
print("Training script started...") # Direct output for verification
sys.stdout.flush()

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
    parser.add_argument("--background", action="store_true", help="Running in background mode")
    
    args = parser.parse_args()
    train_mappo(args)
