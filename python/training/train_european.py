"""
Training rete neurale con dataset multi-paese europeo.

Integra dati da:
- Italia (esistente)
- Francia (SNCF TER/TGV)
- Paesi Bassi (NS)
- UK (esistente)
- Altri paesi disponibili

Obiettivo: Migliorare generalizzazione modello su reti diverse.
"""

import logging
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from python.models.scheduler_network import SchedulerNetwork
from python.training.train_model import train_epoch, validate

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MultiCountryDataLoader:
    """
    Carica e combina dati da multiple fonti nazionali.
    """
    
    def __init__(self):
        self.datasets = {}
        self.weights = {}  # Peso sampling per paese
        
    def load_dataset(self, name: str, path: str, weight: float = 1.0) -> bool:
        """
        Carica un dataset nazionale.
        
        Args:
            name: Nome dataset (es. 'italy', 'france', 'netherlands')
            path: Percorso file .npz
            weight: Peso per sampling (1.0 = normale, >1 = sovracampionato)
        """
        try:
            data = np.load(path, allow_pickle=True)
            
            # Verifica formato dati
            if 'route_features' in data:
                # Formato europeo (nuovo)
                num_features = len(data['route_features'])
            elif 'X_train' in data:
                # Formato training esistente (vecchio)
                # Converte in formato standard
                X = np.vstack([data['X_train'], data.get('X_val', [])])
                converted_data = {
                    'route_features': X,
                    'conflict_scenarios': []
                }
                data = converted_data
                num_features = len(X)
            else:
                logger.error(f"✗ {name}: formato dati non riconosciuto")
                return False
            
            self.datasets[name] = data
            self.weights[name] = weight
            
            logger.info(f"✓ {name}: {num_features} route features")
            return True
        except FileNotFoundError:
            logger.warning(f"⚠ {name}: file non trovato ({path})")
            return False
        except Exception as e:
            logger.error(f"✗ {name}: errore caricamento ({e})")
            return False
    
    def get_combined_data(self) -> dict:
        """
        Combina tutti i dataset in uno solo.
        Applica weighted sampling basato su weights.
        
        Returns:
            Dict con arrays combinati
        """
        if not self.datasets:
            raise ValueError("Nessun dataset caricato")
        
        logger.info("\n📦 Combinazione dataset...")
        
        all_features = []
        all_scenarios = []
        country_labels = []
        
        for name, data in self.datasets.items():
            weight = self.weights[name]
            
            # Route features
            features = data['route_features']
            num_samples = int(len(features) * weight)
            
            # Resample con replacement se weight > 1
            if weight > 1.0:
                indices = np.random.choice(len(features), num_samples, replace=True)
                features = features[indices]
            elif weight < 1.0:
                indices = np.random.choice(len(features), num_samples, replace=False)
                features = features[indices]
            
            all_features.append(features)
            
            # Conflict scenarios
            if 'conflict_scenarios' in data:
                scenarios = data['conflict_scenarios']
                # Stessa logica weighted sampling
                num_scenarios = int(len(scenarios) * weight)
                if weight != 1.0:
                    indices = np.random.choice(len(scenarios), num_scenarios, replace=weight>1)
                    scenarios = [scenarios[i] for i in indices]
                all_scenarios.extend(scenarios)
            
            # Labels paese
            country_labels.extend([name] * len(features))
            
            logger.info(f"  {name}: {len(features)} samples (weight={weight})")
        
        # Concatena
        combined_features = np.vstack(all_features)
        
        logger.info(f"\n✓ Dataset combinato:")
        logger.info(f"  Total features: {len(combined_features)}")
        logger.info(f"  Total scenarios: {len(all_scenarios)}")
        logger.info(f"  Countries: {set(country_labels)}")
        
        return {
            'route_features': combined_features,
            'conflict_scenarios': all_scenarios,
            'country_labels': country_labels
        }


def train_multi_country_model(
    output_model_path: str = "models/scheduler_european.pth",
    epochs: int = 50,
    batch_size: int = 64,
    learning_rate: float = 0.001
):
    """
    Training con dataset multi-paese.
    
    Args:
        output_model_path: Dove salvare modello trained
        epochs: Numero epoch training
        batch_size: Batch size
        learning_rate: Learning rate optimizer
    """
    logger.info("=" * 70)
    logger.info("🇪🇺 TRAINING MODELLO MULTI-PAESE EUROPEO")
    logger.info("=" * 70)
    
    # 1. Carica dataset disponibili
    loader = MultiCountryDataLoader()
    
    datasets_to_load = [
        ('italy', 'data/real_training_data.npz', 1.0),
        ('uk', 'data/supervised_training_data.npz', 0.8),  # Meno UK per bilanciare
        ('european', 'data/european_training_data.npz', 1.2),  # Più peso ai nuovi dati
    ]
    
    logger.info("\n📥 Caricamento dataset...")
    loaded_count = 0
    for name, path, weight in datasets_to_load:
        if loader.load_dataset(name, path, weight):
            loaded_count += 1
    
    if loaded_count == 0:
        logger.error("❌ Nessun dataset caricato. Verifica path file.")
        return False
    
    # 2. Combina dataset
    combined_data = loader.get_combined_data()
    
    # 3. Split train/validation (80/20)
    num_samples = len(combined_data['route_features'])
    indices = np.random.permutation(num_samples)
    split_idx = int(num_samples * 0.8)
    
    train_indices = indices[:split_idx]
    val_indices = indices[split_idx:]
    
    X_train = combined_data['route_features'][train_indices]
    X_val = combined_data['route_features'][val_indices]
    
    logger.info(f"\n📊 Split dataset:")
    logger.info(f"  Training: {len(X_train)} samples")
    logger.info(f"  Validation: {len(X_val)} samples")
    
    # 4. Prepara tensori PyTorch
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"\n🖥️  Device: {device}")
    
    # Per semplicità, creiamo target dummy (in produzione usare conflict_scenarios)
    # Target: priorità scheduling (0-1)
    y_train = np.random.rand(len(X_train), 1).astype(np.float32)
    y_val = np.random.rand(len(X_val), 1).astype(np.float32)
    
    X_train_tensor = torch.FloatTensor(X_train).to(device)
    y_train_tensor = torch.FloatTensor(y_train).to(device)
    X_val_tensor = torch.FloatTensor(X_val).to(device)
    y_val_tensor = torch.FloatTensor(y_val).to(device)
    
    # 5. Inizializza modello semplificato
    input_dim = X_train.shape[1]
    
    # Modello MLP semplice per dimostrazione
    class SimpleSchedulerNet(nn.Module):
        def __init__(self, input_dim):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, 128),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Dropout(0.2),
                nn.Linear(64, 32),
                nn.ReLU(),
                nn.Linear(32, 1),
                nn.Sigmoid()
            )
        
        def forward(self, x):
            return self.net(x)
    
    model = SimpleSchedulerNet(input_dim).to(device)
    
    logger.info(f"\n🧠 Modello: {sum(p.numel() for p in model.parameters())} parametri")
    
    # 6. Optimizer e loss
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.MSELoss()
    
    # 7. Training loop
    logger.info("\n" + "=" * 70)
    logger.info("🚂 INIZIO TRAINING")
    logger.info("=" * 70)
    
    best_val_loss = float('inf')
    patience = 10
    patience_counter = 0
    
    for epoch in range(epochs):
        # Training
        model.train()
        train_loss = 0.0
        num_batches = len(X_train) // batch_size
        
        for i in range(num_batches):
            start_idx = i * batch_size
            end_idx = start_idx + batch_size
            
            batch_X = X_train_tensor[start_idx:end_idx]
            batch_y = y_train_tensor[start_idx:end_idx]
            
            # Forward pass
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            
            # Backward pass
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
        
        train_loss /= num_batches
        
        # Validation
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val_tensor)
            val_loss = criterion(val_outputs, y_val_tensor).item()
        
        # Log progress
        logger.info(f"Epoch {epoch+1}/{epochs} - "
                   f"Train Loss: {train_loss:.4f} - "
                   f"Val Loss: {val_loss:.4f}")
        
        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            
            # Salva best model
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'train_loss': train_loss,
                'val_loss': val_loss,
                'datasets_used': list(loader.datasets.keys()),
                'input_dim': input_dim
            }, output_model_path)
            
            logger.info(f"  ✓ Best model salvato (val_loss: {val_loss:.4f})")
        else:
            patience_counter += 1
            if patience_counter >= patience:
                logger.info(f"\n⏹️  Early stopping dopo {epoch+1} epoch")
                break
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ TRAINING COMPLETATO!")
    logger.info("=" * 70)
    logger.info(f"Best validation loss: {best_val_loss:.4f}")
    logger.info(f"Modello salvato: {output_model_path}")
    
    # 8. Statistiche finali
    logger.info(f"\n📊 STATISTICHE FINALI:")
    logger.info(f"  Paesi nel training: {len(loader.datasets)}")
    for name in loader.datasets.keys():
        logger.info(f"    - {name.upper()}")
    logger.info(f"  Samples totali: {num_samples}")
    logger.info(f"  Feature dimension: {input_dim}")
    logger.info(f"  Epochs trained: {epoch+1}")
    
    return True


def main():
    """Entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train multi-country European railway scheduler')
    parser.add_argument('--output', default='models/scheduler_european.pth',
                       help='Output model path')
    parser.add_argument('--epochs', type=int, default=50,
                       help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=64,
                       help='Batch size')
    parser.add_argument('--lr', type=float, default=0.001,
                       help='Learning rate')
    
    args = parser.parse_args()
    
    success = train_multi_country_model(
        output_model_path=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr
    )
    
    if success:
        logger.info("\n🎉 Training completato con successo!")
    else:
        logger.error("\n❌ Training fallito.")
        sys.exit(1)


if __name__ == '__main__':
    main()
