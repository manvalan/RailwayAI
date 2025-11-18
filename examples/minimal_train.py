"""
Training minimale senza complessità per validare il sistema end-to-end.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'python'))

import torch
import torch.nn as nn
import numpy as np
from tqdm import tqdm


class SimpleSchedulerNetwork(nn.Module):
    """Rete semplificata per test rapidi."""
    
    def __init__(self, network_dim=80, train_dim=8, hidden=128, num_trains=50):
        super().__init__()
        self.num_trains = num_trains
        
        # Encoder per network state
        self.net_encoder = nn.Sequential(
            nn.Linear(network_dim, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden//2)
        )
        
        # Encoder per train states
        self.train_encoder = nn.LSTM(train_dim, hidden//2, batch_first=True)
        
        # Decoder per aggiustamenti temporali
        self.time_predictor = nn.Sequential(
            nn.Linear(hidden, hidden),
            nn.ReLU(),
            nn.Linear(hidden, num_trains)
        )
    
    def forward(self, network_state, train_states):
        batch_size = network_state.size(0)
        
        # Encode network
        net_enc = self.net_encoder(network_state)  # [batch, 64]
        
        # Encode trains
        train_enc, _ = self.train_encoder(train_states)  # [batch, num_trains, 64]
        train_enc = train_enc.mean(dim=1)  # [batch, 64] - average pooling
        
        # Combina
        combined = torch.cat([net_enc, train_enc], dim=1)  # [batch, 128]
        
        # Predici aggiustamenti
        time_adj = self.time_predictor(combined)  # [batch, num_trains]
        
        return time_adj


def main():
    print("\n" + "="*70)
    print("  🚀 TRAINING MINIMALE - Sistema Semplificato")
    print("="*70 + "\n")
    
    # Carica dati
    print("📊 Caricamento dataset...")
    train_data = np.load('../data/training_data.npz')
    val_data = np.load('../data/validation_data.npz')
    
    X_train_net = torch.FloatTensor(train_data['network_states'])
    X_train_trains = torch.FloatTensor(train_data['train_states'])
    X_val_net = torch.FloatTensor(val_data['network_states'])
    X_val_trains = torch.FloatTensor(val_data['train_states'])
    
    print(f"  • Training: {len(X_train_net)} samples")
    print(f"  • Validation: {len(X_val_net)} samples")
    print(f"  • Network state dim: {X_train_net.shape[1]}")
    print(f"  • Train state dim: {X_train_trains.shape[1:]}")
    
    # Crea target semplici (min delay necessario per risolvere conflitti)
    # Per ora: target = piccoli aggiustamenti casuali come placeholder
    y_train = torch.randn(len(X_train_net), 50) * 2  # [-6, +6] minuti
    y_val = torch.randn(len(X_val_net), 50) * 2
    
    # Modello
    print("\n🧠 Inizializzazione modello semplificato...")
    model = SimpleSchedulerNetwork(
        network_dim=80,
        train_dim=8,
        hidden=128,
        num_trains=50
    )
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    
    params = sum(p.numel() for p in model.parameters())
    print(f"  • Device: {device}")
    print(f"  • Parametri: {params:,}")
    
    # Training setup
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.MSELoss()
    
    # Training loop
    print("\n🏃 Training (5 epoche)...")
    print("="*70)
    
    batch_size = 16
    best_val_loss = float('inf')
    
    for epoch in range(5):
        # Training
        model.train()
        train_loss = 0
        num_batches = 0
        
        for i in range(0, len(X_train_net), batch_size):
            batch_net = X_train_net[i:i+batch_size].to(device)
            batch_trains = X_train_trains[i:i+batch_size].to(device)
            batch_y = y_train[i:i+batch_size].to(device)
            
            optimizer.zero_grad()
            pred = model(batch_net, batch_trains)
            loss = criterion(pred, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            num_batches += 1
        
        train_loss /= num_batches
        
        # Validation
        model.eval()
        val_loss = 0
        num_val_batches = 0
        
        with torch.no_grad():
            for i in range(0, len(X_val_net), batch_size):
                batch_net = X_val_net[i:i+batch_size].to(device)
                batch_trains = X_val_trains[i:i+batch_size].to(device)
                batch_y = y_val[i:i+batch_size].to(device)
                
                pred = model(batch_net, batch_trains)
                loss = criterion(pred, batch_y)
                
                val_loss += loss.item()
                num_val_batches += 1
        
        val_loss /= num_val_batches
        
        # Salva best model
        marker = ""
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'train_loss': train_loss,
                'val_loss': val_loss,
            }, '../models/scheduler_minimal.pth')
            marker = " 💾 SAVED"
        
        print(f"Epoca {epoch+1}/5 - Train: {train_loss:.4f} | Val: {val_loss:.4f}{marker}")
    
    # Test
    print("\n🧪 Test predizione...")
    model.eval()
    with torch.no_grad():
        test_net = X_val_net[:1].to(device)
        test_trains = X_val_trains[:1].to(device)
        pred = model(test_net, test_trains)
        
        print(f"  • Input shape: {test_trains.shape}")
        print(f"  • Output shape: {pred.shape}")
        print(f"  • Predizioni (primi 10 treni): {pred[0, :10].cpu().numpy()}")
        print(f"  • Range: [{pred.min():.2f}, {pred.max():.2f}] minuti")
    
    print("\n✅ Training completato!")
    print(f"  • Best val loss: {best_val_loss:.4f}")
    print(f"  • Modello salvato: ../models/scheduler_minimal.pth")
    
    print("\n" + "="*70)
    print("  ✨ Sistema validato!")
    print("="*70)
    print("\n💡 Prossimi passi:")
    print("  1. Integra C++ engine: usa railway_cpp per risoluzione")
    print("  2. Target realistici: calcola soluzioni ottimali vere")
    print("  3. Rete completa: usa SchedulerNetwork con attention")
    print("  4. Più dati: genera 1000+ scenari diversificati")
    print()


if __name__ == "__main__":
    main()
