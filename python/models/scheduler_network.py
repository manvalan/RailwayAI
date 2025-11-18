"""
Neural Network per lo scheduling ferroviario.
Gestisce l'ottimizzazione degli orari per evitare conflitti su binari.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class SchedulerNetwork(nn.Module):
    """
    Rete neurale per la previsione e l'ottimizzazione degli orari ferroviari.
    
    Input:
        - Stato corrente della rete ferroviaria
        - Posizioni e orari dei treni
        - Configurazione binari (singolo/doppio)
    
    Output:
        - Aggiustamenti temporali proposti
        - Priorità di risoluzione conflitti
    """
    
    def __init__(self, 
                 input_dim: int = 256,
                 hidden_dim: int = 512,
                 num_trains: int = 50,
                 num_tracks: int = 20,
                 num_stations: int = 10):
        """
        Args:
            input_dim: Dimensione dell'input encoding
            hidden_dim: Dimensione layer nascosti
            num_trains: Numero massimo di treni simultanei
            num_trains: Numero di binari nella rete
            num_stations: Numero di stazioni
        """
        super(SchedulerNetwork, self).__init__()
        
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.num_trains = num_trains
        self.num_tracks = num_tracks
        self.num_stations = num_stations
        
        # Encoder per lo stato della rete
        self.network_encoder = nn.Sequential(
            nn.Linear(num_tracks + num_stations, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 256)
        )
        
        # Encoder per i treni (LSTM per catturare sequenze temporali)
        self.train_encoder = nn.LSTM(
            input_size=8,  # [pos, velocity, delay, priority, track, destination, time_to_station, is_delayed]
            hidden_size=128,
            num_layers=2,
            batch_first=True,
            dropout=0.2
        )
        
        # Attention mechanism per focus su conflitti critici
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_dim,
            num_heads=8,
            dropout=0.1
        )
        
        # Main processing layers
        self.fc1 = nn.Linear(256 + 128, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim)
        self.fc3 = nn.Linear(hidden_dim, hidden_dim // 2)
        
        # Output heads
        # 1. Predizione aggiustamenti temporali per ogni treno
        self.time_adjustment_head = nn.Linear(hidden_dim // 2, num_trains)
        
        # 2. Predizione priorità di risoluzione conflitti
        self.conflict_priority_head = nn.Linear(hidden_dim // 2, num_trains * num_trains)
        
        # 3. Track assignment (per rotte alternative)
        self.track_assignment_head = nn.Linear(hidden_dim // 2, num_trains * num_tracks)
        
        # Normalizzazione
        self.layer_norm1 = nn.LayerNorm(hidden_dim)
        self.layer_norm2 = nn.LayerNorm(hidden_dim)
        
    def forward(self, network_state, train_states, train_mask=None):
        """
        Forward pass della rete.
        
        Args:
            network_state: Tensor [batch, num_tracks + num_stations]
            train_states: Tensor [batch, num_trains, 8] 
            train_mask: Tensor [batch, num_trains] (1 per treni attivi, 0 per padding)
            
        Returns:
            dict con:
                - time_adjustments: [batch, num_trains]
                - conflict_priorities: [batch, num_trains, num_trains]
                - track_assignments: [batch, num_trains, num_tracks]
        """
        batch_size = network_state.size(0)
        
        # Encode network state
        network_encoded = self.network_encoder(network_state)  # [batch, 256]
        
        # Encode train states con LSTM
        train_encoded, (hn, cn) = self.train_encoder(train_states)  # [batch, num_trains, 128]
        # Usa l'ultimo hidden state
        train_encoded = hn[-1]  # [batch, 128]
        
        # Combina encodings
        combined = torch.cat([network_encoded, train_encoded], dim=-1)  # [batch, 384]
        
        # Main processing
        x = F.relu(self.fc1(combined))
        x = self.layer_norm1(x)
        x = F.relu(self.fc2(x))
        x = self.layer_norm2(x)
        x = F.relu(self.fc3(x))
        
        # Output heads
        time_adjustments = self.time_adjustment_head(x)  # [batch, num_trains]
        time_adjustments = torch.tanh(time_adjustments) * 30  # Limita a ±30 minuti
        
        conflict_priorities = self.conflict_priority_head(x)  # [batch, num_trains * num_trains]
        conflict_priorities = conflict_priorities.view(batch_size, self.num_trains, self.num_trains)
        conflict_priorities = torch.softmax(conflict_priorities, dim=-1)
        
        track_assignments = self.track_assignment_head(x)  # [batch, num_trains * num_tracks]
        track_assignments = track_assignments.view(batch_size, self.num_trains, self.num_tracks)
        track_assignments = torch.softmax(track_assignments, dim=-1)
        
        # Applica mask se fornita
        if train_mask is not None:
            train_mask = train_mask.unsqueeze(-1)  # [batch, num_trains, 1]
            time_adjustments = time_adjustments * train_mask.squeeze(-1)
            track_assignments = track_assignments * train_mask
        
        return {
            'time_adjustments': time_adjustments,
            'conflict_priorities': conflict_priorities,
            'track_assignments': track_assignments
        }
    
    def compute_loss(self, predictions, targets, conflict_matrix):
        """
        Calcola la loss per il training.
        
        Args:
            predictions: Output del forward pass
            targets: Target values {time_adjustments, track_assignments}
            conflict_matrix: [batch, num_trains, num_trains] binario (1 = conflitto)
            
        Returns:
            total_loss, loss_dict
        """
        # Loss per time adjustments (MSE)
        time_loss = F.mse_loss(
            predictions['time_adjustments'], 
            targets['time_adjustments']
        )
        
        # Loss per track assignments (CrossEntropy)
        track_loss = F.cross_entropy(
            predictions['track_assignments'].view(-1, self.num_tracks),
            targets['track_assignments'].view(-1)
        )
        
        # Loss per risoluzione conflitti (penalizza conflitti non risolti)
        conflict_loss = self._compute_conflict_loss(
            predictions, 
            conflict_matrix
        )
        
        # Combinazione pesata
        total_loss = time_loss + 2.0 * track_loss + 3.0 * conflict_loss
        
        loss_dict = {
            'total': total_loss.item(),
            'time': time_loss.item(),
            'track': track_loss.item(),
            'conflict': conflict_loss.item()
        }
        
        return total_loss, loss_dict
    
    def _compute_conflict_loss(self, predictions, conflict_matrix):
        """
        Penalizza soluzioni che non risolvono conflitti.
        """
        # Estrai le priorità predette
        priorities = predictions['conflict_priorities']
        
        # Calcola quanti conflitti rimangono dopo le priorità assegnate
        # (semplificazione: assumiamo che priorità più alta risolva il conflitto)
        unresolved = conflict_matrix * (1.0 - priorities)
        conflict_loss = unresolved.sum() / (conflict_matrix.sum() + 1e-8)
        
        return conflict_loss


class ConflictDetector(nn.Module):
    """
    Rete ausiliaria per detection di conflitti potenziali.
    """
    
    def __init__(self, input_dim=16, hidden_dim=128):
        super(ConflictDetector, self).__init__()
        
        self.fc1 = nn.Linear(input_dim, hidden_dim)
        self.fc2 = nn.Linear(hidden_dim, hidden_dim // 2)
        self.fc3 = nn.Linear(hidden_dim // 2, 1)
        
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, train_pair_features):
        """
        Predice probabilità di conflitto tra coppie di treni.
        
        Args:
            train_pair_features: [batch, num_pairs, 16]
                Features: [train1_state (8), train2_state (8)]
        
        Returns:
            conflict_probs: [batch, num_pairs]
        """
        x = F.relu(self.fc1(train_pair_features))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = torch.sigmoid(self.fc3(x))
        
        return x.squeeze(-1)
