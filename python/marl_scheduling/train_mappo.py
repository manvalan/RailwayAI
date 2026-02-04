import sys
import os
from pathlib import Path

# Limit threads and force stability for background training
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["MKL_SERVICE_FORCE_INTEL"] = "1"
os.environ["OMP_PROC_BIND"] = "FALSE"
os.environ["TORCH_NUM_THREADS"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "" 
os.environ["MKL_THREADING_LAYER"] = "SEQUENTIAL" 

import numpy as np
import argparse
import logging

# Add current directory to sys.path
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Force INFO level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

def train_mappo(args):
    """
    MAPPO training with scenario scaling and checkpointing.
    Supports Curriculum Learning.
    """
    # Heavy imports inside to ensure quick process startup signal
    import torch
    import torch.optim as optim
    import torch.nn.functional as F
    from env import RailwayGymEnv
    from scenario_loader import ScenarioLoader
    from constraints import SafetyConstraintLayer
    from models import ActorNetwork, CriticNetwork
    from curriculum import CurriculumManager

    current_level = args.level
    
    def setup_level(level):
        if args.curriculum:
            logger.info(f"Setting up Curriculum Level {level}...")
            scenario = CurriculumManager.get_scenario_for_level(level)
            ScenarioLoader._inject_default_routes(scenario)
        else:
            logger.info(f"Loading static scenario: {args.scenario}")
            scenario = ScenarioLoader.load_scenario(args.scenario)
        
        env = RailwayGymEnv(scenario['tracks'], scenario['stations'], scenario['trains'])
        return env, scenario

    env, scenario = setup_level(current_level)
    
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
    
    running_reward = 0
    window_size = 5
    
    # Buffer for PPO
    obs_buffer = []
    action_buffer = []
    log_prob_buffer = []
    reward_buffer = []
    value_buffer = []
    mask_buffer = []
    
    ppo_epochs = 4
    mini_batch_size = 64
    gamma = 0.99
    gae_lambda = 0.95
    clip_param = 0.2
    
    for episode in range(args.episodes):
        obs, _ = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            actions = {}
            log_probs = {}
            values = {}
            
            current_agent_ids = env.agent_ids
            curr_obs_list = []
            curr_action_list = []
            curr_log_prob_list = []
            
            for aid in current_agent_ids:
                o = obs.get(aid)
                if o is None: continue
                o_vec = np.concatenate([o['position'], [o['current_track']], o['velocity'], o['neighbor_occupancy']])
                o_tensor = torch.FloatTensor(o_vec).unsqueeze(0)
                
                with torch.no_grad():
                    probs = actor(o_tensor)
                    dist = torch.distributions.Categorical(probs)
                    action = dist.sample()
                    log_prob = dist.log_prob(action)
                
                actions[aid] = action.item()
                log_probs[aid] = log_prob
                curr_obs_list.append(o_vec)
                curr_action_list.append(action.item())
                curr_log_prob_list.append(log_prob.item())
            
            if not curr_obs_list:
                break

            # Centralized Critic
            with torch.no_grad():
                batch_obs_tensor = torch.FloatTensor(np.array(curr_obs_list))
                val = critic(batch_obs_tensor)
                # We use the same central value for all agents in this step (simplified MAPPO)
                step_value = val.item()

            # Constraint Layer (Safety)
            safe_actions = safety_layer.apply_constraints(actions, {"trains": env.trains})
            
            # Environment STEP
            next_obs, rewards, done, truncated, info = env.step(safe_actions)
            
            total_reward = sum(rewards.values())
            episode_reward += total_reward
            
            # Store in buffer
            obs_buffer.append(curr_obs_list)
            action_buffer.append(curr_action_list)
            log_prob_buffer.append(curr_log_prob_list)
            reward_buffer.append(total_reward)
            value_buffer.append(step_value)
            mask_buffer.append(1.0 - float(done or truncated))
            
            obs = next_obs
            if truncated: done = True
                
        # Update Logic (Every Episode for simplicity in background)
        if len(reward_buffer) > 0:
            # Compute Returns and Advantages (GAE)
            returns = []
            advantages = []
            gae = 0
            next_value = 0 # Assume 0 for terminal
            
            for i in reversed(range(len(reward_buffer))):
                delta = reward_buffer[i] + gamma * next_value * mask_buffer[i] - value_buffer[i]
                gae = delta + gamma * gae_lambda * mask_buffer[i] * gae
                advantages.insert(0, gae)
                next_value = value_buffer[i]
                returns.insert(0, advantages[0] + value_buffer[i])
            
            adv_tensor = torch.FloatTensor(advantages)
            ret_tensor = torch.FloatTensor(returns)
            
            # PPO Update
            adv_tensor = (adv_tensor - adv_tensor.mean()) / (adv_tensor.std() + 1e-8)
            
            for _ in range(ppo_epochs):
                indices = np.arange(len(obs_buffer))
                np.random.shuffle(indices)
                
                for start in range(0, len(obs_buffer), mini_batch_size):
                    end = start + mini_batch_size
                    mb_indices = indices[start:end]
                    
                    for i in mb_indices:
                        o_t = torch.FloatTensor(np.array(obs_buffer[i]))
                        a_t = torch.LongTensor(np.array(action_buffer[i]))
                        old_lp = torch.FloatTensor(np.array(log_prob_buffer[i]))
                        
                        # Actor Loss
                        probs = actor(o_t)
                        dist = torch.distributions.Categorical(probs)
                        new_lp = dist.log_prob(a_t)
                        entropy = dist.entropy().mean()
                        
                        ratio = torch.exp(new_lp - old_lp)
                        surr1 = ratio * adv_tensor[i]
                        surr2 = torch.clamp(ratio, 1.0 - clip_param, 1.0 + clip_param) * adv_tensor[i]
                        actor_loss = -torch.min(surr1, surr2).mean() - 0.01 * entropy
                        
                        # Critic Loss
                        val_pred = critic(o_t)
                        critic_loss = F.mse_loss(val_pred, ret_tensor[i].view(1, 1))
                        
                        # Optimize
                        actor_opt.zero_grad()
                        actor_loss.backward()
                        actor_opt.step()
                        
                        critic_opt.zero_grad()
                        critic_loss.backward()
                        critic_opt.step()
            
            # Clear buffers
            obs_buffer, action_buffer, log_prob_buffer, reward_buffer, value_buffer, mask_buffer = [], [], [], [], [], []

        # Curriculum update logic
        running_reward = 0.9 * running_reward + 0.1 * episode_reward if episode > 0 else episode_reward
        
        if episode % 1 == 0:
            logger.info(f"Episode {episode} (L{current_level}): Reward = {episode_reward:.2f}, Conflicts = {info.get('conflicts', 0)}")
            
        if args.curriculum and episode > 0 and episode % window_size == 0:
            new_level = CurriculumManager.determine_level(running_reward, current_level, threshold=-10.0 * current_level)
            if new_level != current_level:
                current_level = new_level
                env, scenario = setup_level(current_level)
                safety_layer = SafetyConstraintLayer(env.raw_tracks)
                logger.info(f"Network complexity increased to Level {current_level}")

        # Checkpoint
        if episode > 0 and episode % args.save_interval == 0:
            ckpt_path = os.path.join(args.out_dir, f"mappo_curriculum_l{current_level}_ep{episode}.pth")
            torch.save({
                'critic': critic.state_dict(),
                'actor': actor.state_dict(),
                'episode': episode,
                'level': current_level
            }, ckpt_path)
            logger.info(f"Saved checkpoint: {ckpt_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str, default="scenarios/toscana_cleaned.json")
    parser.add_argument("--curriculum", action="store_true", help="Use progressive complexity")
    parser.add_argument("--level", type=int, default=1, help="Start level for curriculum (1-5)")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--save_interval", type=int, default=50)
    parser.add_argument("--checkpoint", type=str, default=None)
    parser.add_argument("--out_dir", type=str, default="checkpoints")
    parser.add_argument("--background", action="store_true", help="Running in background mode")
    
    args = parser.parse_args()
    train_mappo(args)

