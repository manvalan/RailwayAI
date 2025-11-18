"""
Training supervisionato con target realistici dal C++ engine.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import numpy as np
from tqdm import tqdm
from models.scheduler_network import SchedulerNetwork


class SupervisedDataset(Dataset):
    """Dataset con target realistici."""
    
    def __init__(self, data_path):
        data = np.load(data_path)
        self.network_states = torch.FloatTensor(data['network_states'])
        self.train_states = torch.FloatTensor(data['train_states'])
        self.conflict_matrices = torch.FloatTensor(data['conflict_matrices'])
        self.time_targets = torch.FloatTensor(data['time_targets'])
        self.track_targets = torch.LongTensor(data['track_targets'].astype(np.int64))
    
    def __len__(self):
        return len(self.network_states)
    
    def __getitem__(self, idx):
        return {
            'network_state': self.network_states[idx],
            'train_states': self.train_states[idx],
            'conflict_matrix': self.conflict_matrices[idx],
            'time_target': self.time_targets[idx],
            'track_target': self.track_targets[idx]
        }


def train_supervised(
    train_path='data/supervised_training_data.npz',
    val_path='data/supervised_validation_data.npz',
    epochs=100,
    batch_size=32,
    lr=0.0001,
    device=None
):
    """Training supervisionato completo."""
    
    print(f"\n{'='*70}")
    print(f"  🚀 TRAINING SUPERVISIONATO")
    print(f"{'='*70}\n")
    
    # Device
    if device is None:
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"📱 Device: {device}\n")
    
    # Carica dataset
    print("📊 Caricamento dataset...")
    train_dataset = SupervisedDataset(train_path)
    val_dataset = SupervisedDataset(val_path)
    
    train_size = len(train_dataset)
    val_size = len(val_dataset)
    
    print(f"  • Training: {train_size} samples")
    print(f"  • Validation: {val_size} samples\n")
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    # Modello
    print("🧠 Inizializzazione rete neurale...")
    # Note: SchedulerNetwork usa num_tracks + num_stations per network_encoder
    # Ma il nostro dataset ha network_state di dim 80 (variabile)
    # Dobbiamo usare un modello compatibile o modificare l'architettura
    model = SchedulerNetwork(
        input_dim=256,  # Non usato direttamente
        hidden_dim=256,
        num_trains=50,
        num_tracks=50,  # Usa dimensione maggiore per accogliere padding
        num_stations=30  # 50+30=80 match con network_state
    ).to(device)
    
    params = sum(p.numel() for p in model.parameters())
    print(f"  • Parametri: {params:,}\n")
    
    # Optimizer e loss
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-5)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=10
    )
    
    time_criterion = nn.MSELoss()
    track_criterion = nn.CrossEntropyLoss()
    
    # Training loop
    print(f"🏃 Training ({epochs} epoche)...")
    print("="*70 + "\n")
    
    best_val_loss = float('inf')
    history = {'train_loss': [], 'val_loss': []}
    
    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0
        train_time_loss = 0
        train_track_loss = 0
        
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")
        for batch in pbar:
            network_state = batch['network_state'].to(device)
            train_states = batch['train_states'].to(device)
            conflict_matrix = batch['conflict_matrix'].to(device)
            time_target = batch['time_target'].to(device)
            track_target = batch['track_target'].to(device)
            
            optimizer.zero_grad()
            
            # Forward (nota: il modello attuale non usa conflict_matrix)
            # Per ora usiamo solo network_state e train_states
            outputs = model(network_state, train_states)
            
            # Loss sui time adjustments
            # outputs è un dict o tupla? Verifica il modello
            if isinstance(outputs, dict):
                time_pred = outputs['time_adjustments']
            else:
                time_pred = outputs[0]  # Assume tupla (time, track, conflict)
            
            loss_time = time_criterion(time_pred, time_target)
            
            # Per ora solo time loss (track assignment richiede modifica modello)
            loss = loss_time
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            
            train_loss += loss.item()
            train_time_loss += loss_time.item()
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        train_loss /= len(train_loader)
        train_time_loss /= len(train_loader)
        
        # Validation
        model.eval()
        val_loss = 0
        val_time_loss = 0
        
        with torch.no_grad():
            for batch in val_loader:
                network_state = batch['network_state'].to(device)
                train_states = batch['train_states'].to(device)
                time_target = batch['time_target'].to(device)
                
                outputs = model(network_state, train_states)
                
                if isinstance(outputs, dict):
                    time_pred = outputs['time_adjustments']
                else:
                    time_pred = outputs[0]
                
                loss_time = time_criterion(time_pred, time_target)
                loss = loss_time
                
                val_loss += loss.item()
                val_time_loss += loss_time.item()
        
        val_loss /= len(val_loader)
        val_time_loss /= len(val_loader)
        
        # Scheduler step
        scheduler.step(val_loss)
        
        # Salva best model
        marker = ""
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'train_loss': train_loss,
                'val_loss': val_loss,
                'config': {
                    'input_dim': 256,
                    'hidden_dim': 256,
                    'num_trains': 50,
                    'num_tracks': 50,
                    'num_stations': 30
                }
            }, 'models/scheduler_supervised_best.pth')
            marker = " 💾"
        
        history['train_loss'].append(train_loss)
        history['val_loss'].append(val_loss)
        
        print(f"Epoch {epoch+1:3d} | Train: {train_loss:.4f} | Val: {val_loss:.4f}{marker}")
        
        # Early stopping
        if epoch > 20 and val_loss > best_val_loss * 1.1:
            print("\n⚠️  Early stopping - validation loss non migliora")
            break
    
    # Summary
    print(f"\n{'='*70}")
    print(f"  ✅ TRAINING COMPLETATO")
    print(f"{'='*70}\n")
    print(f"📊 Risultati finali:")
    print(f"  • Best validation loss: {best_val_loss:.4f}")
    print(f"  • Epoche completate: {epoch+1}")
    print(f"  • Modello salvato: models/scheduler_supervised_best.pth")
    print()
    
    return model, history


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--train', type=str, default='data/supervised_training_data.npz')
    parser.add_argument('--val', type=str, default='data/supervised_validation_data.npz')
    parser.add_argument('--epochs', type=int, default=100)
    parser.add_argument('--batch-size', type=int, default=32)
    parser.add_argument('--lr', type=float, default=0.0001)
    args = parser.parse_args()
    
    train_supervised(
        train_path=args.train,
        val_path=args.val,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr
    )
