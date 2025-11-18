"""
Script di training per la rete neurale di scheduling.
"""

import torch
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import os
import sys
from pathlib import Path
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from models.scheduler_network import SchedulerNetwork, ConflictDetector


class RailwaySchedulingDataset(Dataset):
    """Dataset per il training."""
    
    def __init__(self, data_path: str):
        """
        Args:
            data_path: Path al file .npz con i dati
        """
        data = np.load(data_path)
        self.network_states = torch.FloatTensor(data['network_states'])
        self.train_states = torch.FloatTensor(data['train_states'])
        self.conflict_matrices = torch.FloatTensor(data['conflict_matrices'])
        
        print(f"Dataset caricato: {len(self)} campioni")
        
    def __len__(self):
        return len(self.network_states)
    
    def __getitem__(self, idx):
        return {
            'network_state': self.network_states[idx],
            'train_states': self.train_states[idx],
            'conflict_matrix': self.conflict_matrices[idx]
        }


def create_targets(batch, model):
    """
    Crea target labels per il training supervisionato.
    In un sistema reale, questi verrebbero da soluzioni ottimali pre-calcolate.
    Per ora usiamo euristiche.
    """
    batch_size = batch['network_state'].size(0)
    num_trains = batch['train_states'].size(1)
    num_tracks = 20
    
    # Target per time adjustments: risolvi conflitti dando precedenza
    time_targets = torch.zeros(batch_size, num_trains)
    
    for b in range(batch_size):
        conflicts = batch['conflict_matrix'][b]
        train_states = batch['train_states'][b]
        
        for i in range(num_trains):
            for j in range(i+1, num_trains):
                if conflicts[i, j] > 0:
                    # Conflitto: dai ritardo al treno a priorità minore
                    priority_i = train_states[i, 3]  # priority è al index 3
                    priority_j = train_states[j, 3]
                    
                    if priority_i < priority_j:
                        time_targets[b, i] += 5.0  # +5 minuti di ritardo
                    else:
                        time_targets[b, j] += 5.0
    
    # Target per track assignments: mantieni track corrente se possibile
    track_targets = batch['train_states'][:, :, 4].long()  # current_track al index 4
    track_targets = torch.clamp(track_targets, 0, num_tracks - 1)
    
    return {
        'time_adjustments': time_targets,
        'track_assignments': track_targets
    }


def train_epoch(model, dataloader, optimizer, device, epoch):
    """Training per una epoch."""
    model.train()
    total_loss = 0
    total_batches = 0
    
    loss_components = {'time': 0, 'track': 0, 'conflict': 0}
    
    for batch_idx, batch in enumerate(dataloader):
        # Sposta dati su device
        network_state = batch['network_state'].to(device)
        train_states = batch['train_states'].to(device)
        conflict_matrix = batch['conflict_matrix'].to(device)
        
        # Forward pass
        predictions = model(network_state, train_states)
        
        # Crea targets
        targets = create_targets(batch, model)
        targets = {k: v.to(device) for k, v in targets.items()}
        
        # Calcola loss
        loss, loss_dict = model.compute_loss(predictions, targets, conflict_matrix)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        
        # Gradient clipping per stabilità
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        
        optimizer.step()
        
        # Accumula metriche
        total_loss += loss.item()
        total_batches += 1
        
        for key in loss_components:
            loss_components[key] += loss_dict[key]
        
        # Log periodico
        if batch_idx % 50 == 0:
            print(f"  Batch {batch_idx}/{len(dataloader)} - Loss: {loss.item():.4f}")
    
    # Medie
    avg_loss = total_loss / total_batches
    avg_components = {k: v / total_batches for k, v in loss_components.items()}
    
    return avg_loss, avg_components


def validate(model, dataloader, device):
    """Validazione del modello."""
    model.eval()
    total_loss = 0
    total_batches = 0
    
    loss_components = {'time': 0, 'track': 0, 'conflict': 0}
    
    with torch.no_grad():
        for batch in dataloader:
            network_state = batch['network_state'].to(device)
            train_states = batch['train_states'].to(device)
            conflict_matrix = batch['conflict_matrix'].to(device)
            
            predictions = model(network_state, train_states)
            targets = create_targets(batch, model)
            targets = {k: v.to(device) for k, v in targets.items()}
            
            loss, loss_dict = model.compute_loss(predictions, targets, conflict_matrix)
            
            total_loss += loss.item()
            total_batches += 1
            
            for key in loss_components:
                loss_components[key] += loss_dict[key]
    
    avg_loss = total_loss / total_batches
    avg_components = {k: v / total_batches for k, v in loss_components.items()}
    
    return avg_loss, avg_components


def train_model(config: dict):
    """
    Training completo del modello.
    
    Args:
        config: Dizionario con parametri di training
    """
    # Setup device
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Training su device: {device}")
    
    # Carica dataset
    train_dataset = RailwaySchedulingDataset(config['train_data_path'])
    val_dataset = RailwaySchedulingDataset(config['val_data_path'])
    
    train_loader = DataLoader(
        train_dataset,
        batch_size=config['batch_size'],
        shuffle=True,
        num_workers=config['num_workers']
    )
    
    val_loader = DataLoader(
        val_dataset,
        batch_size=config['batch_size'],
        shuffle=False,
        num_workers=config['num_workers']
    )
    
    # Inizializza modello
    model = SchedulerNetwork(
        input_dim=config['input_dim'],
        hidden_dim=config['hidden_dim'],
        num_trains=config['num_trains'],
        num_tracks=config['num_tracks'],
        num_stations=config['num_stations']
    ).to(device)
    
    print(f"Modello inizializzato: {sum(p.numel() for p in model.parameters())} parametri")
    
    # Optimizer e scheduler
    optimizer = optim.AdamW(
        model.parameters(),
        lr=config['learning_rate'],
        weight_decay=config['weight_decay']
    )
    
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode='min',
        factor=0.5,
        patience=5,
        verbose=True
    )
    
    # Training loop
    best_val_loss = float('inf')
    training_history = []
    
    print(f"\nInizio training per {config['num_epochs']} epochs\n")
    
    for epoch in range(config['num_epochs']):
        print(f"Epoch {epoch + 1}/{config['num_epochs']}")
        print("-" * 50)
        
        # Training
        train_loss, train_components = train_epoch(
            model, train_loader, optimizer, device, epoch
        )
        
        print(f"Train Loss: {train_loss:.4f}")
        print(f"  Time: {train_components['time']:.4f}, "
              f"Track: {train_components['track']:.4f}, "
              f"Conflict: {train_components['conflict']:.4f}")
        
        # Validation
        val_loss, val_components = validate(model, val_loader, device)
        
        print(f"Val Loss: {val_loss:.4f}")
        print(f"  Time: {val_components['time']:.4f}, "
              f"Track: {val_components['track']:.4f}, "
              f"Conflict: {val_components['conflict']:.4f}")
        
        # Learning rate scheduling
        scheduler.step(val_loss)
        
        # Salva metriche
        training_history.append({
            'epoch': epoch + 1,
            'train_loss': train_loss,
            'val_loss': val_loss,
            'train_components': train_components,
            'val_components': val_components,
            'lr': optimizer.param_groups[0]['lr']
        })
        
        # Salva best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            checkpoint = {
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'config': config
            }
            torch.save(checkpoint, config['checkpoint_path'])
            print(f"✓ Nuovo best model salvato (val_loss: {val_loss:.4f})")
        
        print()
    
    # Salva training history
    history_path = config['checkpoint_path'].replace('.pth', '_history.json')
    with open(history_path, 'w') as f:
        json.dump(training_history, f, indent=2)
    
    print(f"\nTraining completato!")
    print(f"Best validation loss: {best_val_loss:.4f}")
    print(f"Modello salvato in: {config['checkpoint_path']}")
    print(f"History salvata in: {history_path}")


def main():
    """Main training script."""
    
    # Configurazione training
    config = {
        # Data
        'train_data_path': '../../data/training_data.npz',
        'val_data_path': '../../data/validation_data.npz',
        
        # Model
        'input_dim': 256,
        'hidden_dim': 512,
        'num_trains': 50,
        'num_tracks': 20,
        'num_stations': 10,
        
        # Training
        'batch_size': 32,
        'num_epochs': 100,
        'learning_rate': 0.001,
        'weight_decay': 0.0001,
        'num_workers': 4,
        
        # Output
        'checkpoint_path': '../../models/scheduler_best.pth',
    }
    
    # Crea directory per modelli se non esiste
    os.makedirs(os.path.dirname(config['checkpoint_path']), exist_ok=True)
    
    # Stampa configurazione
    print("=" * 60)
    print("RAILWAY AI SCHEDULER - TRAINING")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nConfigurazione:")
    for key, value in config.items():
        print(f"  {key}: {value}")
    print("=" * 60)
    print()
    
    # Avvia training
    train_model(config)


if __name__ == "__main__":
    main()
