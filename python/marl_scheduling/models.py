import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from typing import Dict, List, Tuple

class MultiHeadAttention(nn.Module):
    def __init__(self, embed_dim: int, num_heads: int = 4):
        super(MultiHeadAttention, self).__init__()
        self.mha = nn.MultiheadAttention(embed_dim, num_heads, batch_first=True)
        
    def forward(self, x):
        # x: (Batch, NumAgents, EmbedDim)
        attn_output, _ = self.mha(x, x, x)
        return attn_output

class ActorNetwork(nn.Module):
    """
    Advanced Actor with Self-Attention.
    Allows the agent to perceive the state of other agents and their relative importance.
    """
    def __init__(self, obs_dim: int, num_actions: int = 3, embed_dim: int = 64):
        super(ActorNetwork, self).__init__()
        self.encoder = nn.Linear(obs_dim, embed_dim)
        self.attention = MultiHeadAttention(embed_dim)
        self.fc1 = nn.Linear(embed_dim, 128)
        self.fc2 = nn.Linear(128, num_actions)
        
    def forward(self, x):
        """
        x: (Batch, NumAgents, ObsDim) or (Batch, ObsDim)
        """
        if x.dim() == 2:
            x = x.unsqueeze(0) # Add agent dimension
            
        h = F.relu(self.encoder(x))
        h_attn = self.attention(h)
        # Use first agent or aggregate? For individual actor, we take the target agent's feature
        # but the feature now contains context from others.
        x = F.relu(self.fc1(h_attn))
        return F.softmax(self.fc2(x), dim=-1)

class CriticNetwork(nn.Module):
    """
    Centralized Critic with Attention Pooling.
    Aggregates global information to estimate the scenario's value.
    """
    def __init__(self, obs_dim: int, embed_dim: int = 128):
        super(CriticNetwork, self).__init__()
        self.encoder = nn.Linear(obs_dim, embed_dim)
        self.attention = MultiHeadAttention(embed_dim, num_heads=8)
        self.fc1 = nn.Linear(embed_dim, 256)
        self.fc2 = nn.Linear(256, 128)
        self.fc3 = nn.Linear(128, 1)
        
    def forward(self, all_obs: torch.Tensor):
        """
        all_obs: (Batch, NumAgents, ObsDim)
        """
        if all_obs.dim() == 2:
            all_obs = all_obs.unsqueeze(0)
            
        h = F.relu(self.encoder(all_obs))
        h = self.attention(h)
        
        # Weighted Global Pooling
        global_h = torch.mean(h, dim=1) # (Batch, EmbedDim)
        
        x = F.relu(self.fc1(global_h))
        x = F.relu(self.fc2(x))
        return self.fc3(x)

class GraphConvolutionLayer(nn.Module):
    """
    GCN layer to integrate network topology.
    """
    def __init__(self, in_features: int, out_features: int):
        super(GraphConvolutionLayer, self).__init__()
        self.weight = nn.Parameter(torch.FloatTensor(in_features, out_features))
        nn.init.xavier_uniform_(self.weight)

    def forward(self, h, adj):
        support = torch.mm(h, self.weight)
        output = torch.mm(adj, support)
        return output
