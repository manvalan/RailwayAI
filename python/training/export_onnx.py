"""
Utility per esportare il modello PyTorch in formato ONNX.
Permette l'utilizzo del modello in altri framework o per deploy.
"""

import torch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from models.scheduler_network import SchedulerNetwork


def export_to_onnx(checkpoint_path: str = 'models/scheduler_supervised_best.pth', 
                   onnx_path: str = 'models/scheduler.onnx',
                   input_dim: int = 256,
                   hidden_dim: int = 256,
                   num_trains: int = 50,
                   num_tracks: int = 50,
                   num_stations: int = 30):
    """
    Esporta il modello addestrato in formato ONNX.
    
    Args:
        checkpoint_path: Path al checkpoint .pth
        onnx_path: Path output per il file .onnx
        input_dim, hidden_dim, etc: Parametri architettura
    """
    print(f"Caricamento checkpoint da: {checkpoint_path}")
    
    # Carica modello
    device = torch.device('cpu')  # ONNX export su CPU
    model = SchedulerNetwork(
        input_dim=input_dim,
        hidden_dim=hidden_dim,
        num_trains=num_trains,
        num_tracks=num_tracks,
        num_stations=num_stations
    ).to(device)
    
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()
    
    print(f"✓ Modello caricato (epoch {checkpoint['epoch']})")
    
    # Crea input dummy per tracing
    batch_size = 1
    # Network state ha dimensione 80 (num_tracks + num_stations)
    dummy_network_state = torch.randn(batch_size, 80, device=device)
    dummy_train_states = torch.randn(batch_size, num_trains, 8, device=device)
    
    print("Esportazione in ONNX...")
    
    # Export con TorchScript (più stabile per modelli complessi)
    print("Uso TorchScript per maggiore compatibilità...")
    
    # Prima converti in TorchScript
    traced_model = torch.jit.trace(model, (dummy_network_state, dummy_train_states))
    
    # Poi esporta in ONNX
    torch.onnx.export(
        traced_model,
        (dummy_network_state, dummy_train_states),
        onnx_path,
        export_params=True,
        opset_version=17,  # Versione più recente
        do_constant_folding=True,
        input_names=['network_state', 'train_states'],
        output_names=['output'],
        dynamic_axes={
            'network_state': {0: 'batch_size'},
            'train_states': {0: 'batch_size'},
            'output': {0: 'batch_size'}
        }
    )
    
    print(f"✓ Modello esportato in: {onnx_path}")
    
    # Verifica ONNX
    try:
        import onnx
        onnx_model = onnx.load(onnx_path)
        onnx.checker.check_model(onnx_model)
        print("✓ Modello ONNX verificato correttamente")
    except ImportError:
        print("⚠ onnx non installato, salto verifica")
    except Exception as e:
        print(f"⚠ Errore durante verifica: {e}")


def test_onnx_inference(onnx_path: str,
                       num_trains: int = 50,
                       num_tracks: int = 20,
                       num_stations: int = 10):
    """
    Test di inferenza con il modello ONNX esportato.
    """
    try:
        import onnxruntime as ort
    except ImportError:
        print("⚠ onnxruntime non installato, salto test inferenza")
        return
    
    print("\nTest inferenza ONNX...")
    
    # Crea sessione
    session = ort.InferenceSession(onnx_path)
    
    # Input dummy
    import numpy as np
    network_state = np.random.randn(1, num_tracks * 3 + num_stations * 2).astype(np.float32)
    train_states = np.random.randn(1, num_trains, 8).astype(np.float32)
    
    # Inferenza
    outputs = session.run(
        None,
        {
            'network_state': network_state,
            'train_states': train_states
        }
    )
    
    print(f"✓ Inferenza completata")
    print(f"  Output shapes:")
    print(f"    - time_adjustments: {outputs[0].shape}")
    print(f"    - conflict_priorities: {outputs[1].shape}")
    print(f"    - track_assignments: {outputs[2].shape}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Export PyTorch model to ONNX")
    parser.add_argument('--checkpoint', type=str, default='models/scheduler_supervised_best.pth',
                       help='Path to PyTorch checkpoint')
    parser.add_argument('--output', type=str, default='models/scheduler.onnx',
                       help='Output path for ONNX model')
    parser.add_argument('--test', action='store_true',
                       help='Run inference test after export')
    
    args = parser.parse_args()
    
    # Export
    export_to_onnx(args.checkpoint, args.output)
    
    # Test if requested
    if args.test:
        test_onnx_inference(args.output)
    
    print("\n✓ Esportazione completata con successo!")
