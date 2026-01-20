import torch
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from python.models.scheduler_network import SchedulerNetwork

def export_to_torchscript(model_path, output_path):
    """
    Exports a trained PyTorch model to TorchScript format for C++ inference.
    """
    print(f"Loading model from {model_path}...")
    
    # Load data first to get config
    try:
        data = torch.load(model_path, map_location=torch.device('cpu'))
        if 'config' in data:
            config = data['config']
            input_dim = config.get('input_dim', 256)
            hidden_dim = config.get('hidden_dim', 512)
            num_trains = config.get('num_trains', 50)
            num_tracks = config.get('num_tracks', 20)
            num_stations = config.get('num_stations', 10)
            print(f"Using parameters from checkpoint: hidden={hidden_dim}, trains={num_trains}, tracks={num_tracks}, stations={num_stations}")
        else:
            # Fallback for old models or raw state dicts
            input_dim = 256
            hidden_dim = 512
            num_trains = 50
            num_tracks = 20
            num_stations = 10
            print("Warning: No config found in checkpoint, using defaults.")
            
        model = SchedulerNetwork(
            input_dim=input_dim,
            hidden_dim=hidden_dim,
            num_trains=num_trains,
            num_tracks=num_tracks,
            num_stations=num_stations
        )
        
        if 'model_state_dict' in data:
            model.load_state_dict(data['model_state_dict'])
        else:
            model.load_state_dict(data)
            
        model.eval()
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

    # Create dummy inputs for tracing (use parameters from model instance)
    dummy_network = torch.randn(1, model.num_tracks + model.num_stations)
    dummy_trains = torch.randn(1, model.num_trains, 8)
    
    print(f"Tracing model...")
    try:
        # Trace with multiple inputs
        traced_script_module = torch.jit.trace(model, (dummy_network, dummy_trains), strict=False)
        
        # Save the traced model
        traced_script_module.save(output_path)
        print(f"✅ Model successfully exported to TorchScript: {output_path}")
        return True
    except Exception as e:
        print(f"Error tracing model: {e}")
        return False

if __name__ == "__main__":
    # Example usage
    model_dir = Path("models")
    best_model = model_dir / "scheduler_real_world.pth"
    output_model = model_dir / "scheduler_real_world.pt"
    
    if best_model.exists():
        export_to_torchscript(str(best_model), str(output_model))
    else:
        # Try best_supervised if real_world is missing
        best_model = model_dir / "scheduler_supervised_best.pth"
        if best_model.exists():
            export_to_torchscript(str(best_model), str(output_model))
        else:
            print(f"Model file not found in {model_dir}")
            print("Please ensure you have trained the model first.")
