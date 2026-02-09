#!/usr/bin/env python3
"""
Imitation Learning Trainer

Train neural network from expert (GA) demonstrations.
Much faster than pure RL - network learns from good solutions directly.
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, random_split
import logging
from tqdm import tqdm
import json

from python.marl_scheduling.models import ActorNetwork

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExpertDataset(Dataset):
    """Dataset from expert demonstrations"""
    
    def __init__(self, dataset_path: str):
        logger.info(f"Loading dataset from {dataset_path}...")
        data = torch.load(dataset_path)
        
        self.states = data["states"]
        self.actions = data["actions"]
        self.metadata = {k: v for k, v in data.items() if k not in ["states", "actions"]}
        
        logger.info(f"✓ Loaded {len(self.states)} examples")
        logger.info(f"  Scenarios used: {self.metadata.get('scenarios_used', 'unknown')}")
        logger.info(f"  Success rate: {self.metadata.get('success_rate', 0):.2%}")
    
    def __len__(self):
        return len(self.states)
    
    def __getitem__(self, idx):
        return self.states[idx], self.actions[idx]

def train_imitation(
    dataset_path: str,
    output_dir: str = "models/imitation",
    epochs: int = 50,
    batch_size: int = 256,
    lr: float = 3e-4,
    val_split: float = 0.1
):
    """Train network using imitation learning"""
    
    logger.info("="*70)
    logger.info("  🎓 IMITATION LEARNING FROM GA EXPERT")
    logger.info("="*70)
    
    # Setup
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Device: {device}")
    
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load dataset
    dataset = ExpertDataset(dataset_path)
    
    # Split train/val
    val_size = int(len(dataset) * val_split)
    train_size = len(dataset) - val_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    logger.info(f"Train: {train_size} | Val: {val_size}")
    
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=4)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=4)
    
    # Model
    obs_dim = dataset.states.shape[1]
    model = ActorNetwork(obs_dim, num_actions=4).to(device)  # 4 actions: wait, slow, normal, fast
    
    params = sum(p.numel() for p in model.parameters())
    logger.info(f"Model parameters: {params:,}")
    
    # Optimizer
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    
    # Training loop
    best_val_acc = 0.0
    history = {"train_loss": [], "train_acc": [], "val_loss": [], "val_acc": []}
    
    logger.info("\n" + "="*70)
    logger.info("Starting training...")
    logger.info("="*70 + "\n")
    
    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0
        train_correct = 0
        train_total = 0
        
        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")
        for states, actions in pbar:
            states = states.to(device)
            actions = actions.to(device)
            
            optimizer.zero_grad()
            
            # Forward
            logits = model(states.unsqueeze(0)).squeeze(0)  # Add batch dim for attention
            
            # Cross-entropy loss
            loss = F.cross_entropy(logits, actions)
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            
            # Metrics
            train_loss += loss.item()
            pred = logits.argmax(dim=1)
            train_correct += (pred == actions).sum().item()
            train_total += actions.size(0)
            
            pbar.set_postfix({
                'loss': f'{loss.item():.4f}',
                'acc': f'{100*train_correct/train_total:.1f}%'
            })
        
        train_loss /= len(train_loader)
        train_acc = 100 * train_correct / train_total
        
        # Validation
        model.eval()
        val_loss = 0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for states, actions in val_loader:
                states = states.to(device)
                actions = actions.to(device)
                
                logits = model(states.unsqueeze(0)).squeeze(0)
                loss = F.cross_entropy(logits, actions)
                
                val_loss += loss.item()
                pred = logits.argmax(dim=1)
                val_correct += (pred == actions).sum().item()
                val_total += actions.size(0)
        
        val_loss /= len(val_loader)
        val_acc = 100 * val_correct / val_total
        
        scheduler.step()
        
        # Save best model
        marker = ""
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            
            checkpoint = {
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_acc': val_acc,
                'val_loss': val_loss,
                'obs_dim': obs_dim
            }
            
            torch.save(checkpoint, output_dir / "best_imitation_model.pth")
            marker = " 💾"
        
        # History
        history["train_loss"].append(train_loss)
        history["train_acc"].append(train_acc)
        history["val_loss"].append(val_loss)
        history["val_acc"].append(val_acc)
        
        logger.info(
            f"Epoch {epoch+1:3d} | "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc:.1f}% | "
            f"Val Loss: {val_loss:.4f} Acc: {val_acc:.1f}%{marker}"
        )
        
        # Early stopping
        if epoch > 10 and val_acc < best_val_acc - 5:
            logger.info("\n⚠️  Early stopping - validation accuracy declining")
            break
    
    # Save final model
    torch.save({
        'epoch': epoch,
        'model_state_dict': model.state_dict(),
        'history': history,
        'best_val_acc': best_val_acc,
        'obs_dim': obs_dim
    }, output_dir / "final_imitation_model.pth")
    
    # Save history
    with open(output_dir / "training_history.json", 'w') as f:
        json.dump(history, f, indent=2)
    
    # Summary
    logger.info("\n" + "="*70)
    logger.info("  ✅ TRAINING COMPLETED")
    logger.info("="*70)
    logger.info(f"Best validation accuracy: {best_val_acc:.2f}%")
    logger.info(f"Epochs completed: {epoch+1}")
    logger.info(f"Model saved to: {output_dir}")
    logger.info("\nNext steps:")
    logger.info("1. Fine-tune with reinforcement learning:")
    logger.info(f"   python python/marl_scheduling/train_mappo.py --checkpoint {output_dir}/best_imitation_model.pth")
    logger.info("2. Or deploy directly for inference")
    
    return model, history

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, required=True, help="Path to expert dataset (.pt)")
    parser.add_argument("--output", type=str, default="models/imitation", help="Output directory")
    parser.add_argument("--epochs", type=int, default=50, help="Number of epochs")
    parser.add_argument("--batch-size", type=int, default=256, help="Batch size")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    args = parser.parse_args()
    
    train_imitation(
        dataset_path=args.dataset,
        output_dir=args.output,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr
    )
