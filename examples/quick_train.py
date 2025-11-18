"""
Training veloce (5 epoche) per validare il sistema.
Per training completo usare python/training/train_model.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'python'))

import torch
import numpy as np
from models.scheduler_network import SchedulerNetwork
from training.train_model import RailwaySchedulingDataset, train_epoch, validate


def quick_train():
    print("\n" + "="*70)
    print("  🚀 QUICK TRAINING - Validazione Sistema")
    print("="*70 + "\n")
    
    # Carica dataset
    print("📊 Caricamento dataset...")
    train_dataset = RailwaySchedulingDataset('../data/training_data.npz')
    val_dataset = RailwaySchedulingDataset('../data/validation_data.npz')
    
    print(f"  • Training samples: {len(train_dataset)}")
    print(f"  • Validation samples: {len(val_dataset)}")
    
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=16, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=16, shuffle=False)
    
    # Inizializza modello (usa dimensione reale dei dati: 80)
    print("\n🧠 Inizializzazione rete neurale...")
    model = SchedulerNetwork(
        input_dim=80,  # Dimensione reale network_state nel dataset
        hidden_dim=128,
        num_trains=50,
        num_tracks=20,
        num_stations=10
    )
    
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = model.to(device)
    print(f"  • Device: {device}")
    print(f"  • Parametri: {sum(p.numel() for p in model.parameters()):,}")
    
    # Optimizer
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.001)
    
    # Training veloce (5 epoche)
    print("\n🏃 Training veloce (5 epoche)...")
    print("="*70)
    
    best_val_loss = float('inf')
    
    for epoch in range(5):
        train_loss = train_epoch(model, train_loader, optimizer, device, epoch)
        val_loss = validate(model, val_loader, device)
        
        # Salva best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'train_loss': train_loss,
                'val_loss': val_loss,
            }, '../models/scheduler_quick.pth')
            marker = " 💾"
        else:
            marker = ""
        
        print(f"Epoca {epoch+1}/5 - Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}{marker}")
    
    print("\n✅ Training completato!")
    print(f"  • Best validation loss: {best_val_loss:.4f}")
    print(f"  • Modello salvato: ../models/scheduler_quick.pth")
    
    # Test predizione
    print("\n🧪 Test predizione...")
    model.eval()
    with torch.no_grad():
        sample_batch = next(iter(val_loader))
        network_state, train_states, conflict_matrix = sample_batch
        network_state = network_state.to(device)
        train_states = train_states.to(device)
        conflict_matrix = conflict_matrix.to(device)
        
        time_adj, track_assign, conflict_prio = model(train_states, network_state, conflict_matrix)
        
        print(f"  • Input shape: {train_states.shape}")
        print(f"  • Time adjustments: {time_adj.shape}")
        print(f"  • Track assignments: {track_assign.shape}")
        print(f"  • Conflict priorities: {conflict_prio.shape}")
        
        # Analizza prima predizione
        first_time_adj = time_adj[0].cpu().numpy()
        print(f"\n  📊 Prima predizione (sample 0):")
        print(f"    • Range aggiustamenti: [{first_time_adj.min():.2f}, {first_time_adj.max():.2f}] minuti")
        print(f"    • Media aggiustamenti: {first_time_adj.mean():.2f} minuti")
        print(f"    • Aggiustamenti significativi (>5min): {(np.abs(first_time_adj) > 5).sum()}/{len(first_time_adj)}")
    
    print("\n" + "="*70)
    print("  ✨ Sistema validato con successo!")
    print("="*70)
    print("\n💡 Prossimi passi:")
    print("  1. Training completo: python python/training/train_model.py")
    print("  2. Aumenta dataset: modifica num_samples in data_generator.py")
    print("  3. Integra C++ engine per ottimizzazione performance")
    print()


if __name__ == "__main__":
    quick_train()
