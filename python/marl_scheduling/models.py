import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple

class ActorNetwork(nn.Module):
    """
    Shared Actor network for any agent.
    Input: Individual agent observation (fixed dim).
    """
    def __init__(self, obs_dim: int, num_actions: int = 3):
        super(ActorNetwork, self).__init__()
        self.fc1 = nn.Linear(obs_dim, 128)
        self.fc2 = nn.Linear(128, 64)
        self.fc3 = nn.Linear(64, num_actions)
        
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = F.relu(self.fc2(x))
        return F.softmax(self.fc3(x), dim=-1)

class CriticNetwork(nn.Module):
    """
    Scenario-agnostic Critic using Mean-Field/Global-Pooling.
    Handles variable number of agents.
    """
    def __init__(self, obs_dim: int):
        super(CriticNetwork, self).__init__()
        self.fc1 = nn.Linear(obs_dim, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, 1)
        
    def forward(self, all_obs: torch.Tensor):
        """
        all_obs: (NumAgents, ObsDim)
        """
        # Embed each agent
        h = F.relu(self.fc1(all_obs))
        h = F.relu(self.fc2(h))
        
        # Mean Pooling to get scenario embedding
        out = torch.mean(h, dim=0, keepdim=True)
        return self.fc3(out)

class GraphConvolutionLayer(nn.Module):
    """
    Simple implementation of a GCN layer without external dependencies.
    H' = sigma( D^-1/2 * A_hat * D^-1/2 * H * W )
    """
    def __init__(self, in_features: int, out_features: int):
        super(GraphConvolutionLayer, self).__init__()
        self.weight = nn.Parameter(torch.FloatTensor(in_features, out_features))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, h, adj):
        """
        h: Node features (N, F)
        adj: Normalized adjacency matrix (N, N)
        """
        support = torch.mm(h, self.weight)
        output = torch.mm(adj, support)
        return output

class MultiAgentPolicy:
    """ Wrapper for managing multiple actors and a centralized critic. """
    def __init__(self, agent_ids: List[str], obs_dim: int, global_obs_dim: int):
        self.actors = {aid: ActorNetwork(obs_dim) for aid in agent_ids}
        self.critic = CriticNetwork(global_obs_dim)
        
    def get_actions(self, observations: Dict[str, np.ndarray]) -> Dict[str, int]:
        actions = {}
        for aid, obs in observations.items():
            # In a real implementation, we'd use torch.no_grad() and sampling
            obs_tensor = torch.FloatTensor(obs).unsqueeze(0)
            probs = self.actors[aid](obs_tensor)
            action = torch.multinomial(probs, 1).item()
            actions[aid] = action
        return actions
