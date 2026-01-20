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
    
    # Initialize model (parameters should match the trained model)
    # These are example parameters, in a real scenario we'd load them from a config
    model = SchedulerNetwork(
        input_size=10, 
        hidden_size=64, 
        num_layers=2, 
        output_size=5
    )
    
    # Load state dict
    try:
        model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
        model.eval()
        print("Model loaded successfully.")
    except Exception as e:
        print(f"Error loading model: {e}")
        return False

    # Create dummy input for tracing
    # Shape: (batch_size, sequence_length, input_size)
    dummy_input = torch.randn(1, 10, 10)
    
    print(f"Tracing model...")
    try:
        traced_script_module = torch.jit.trace(model, dummy_input)
        
        # Save the traced model
        traced_script_module.save(output_path)
        print(f"✅ Model successfully exported to TorchScript: {output_path}")
        return True
    except Exception as e:
        print(f"Error tracing model: {e}")
        return False

if __name__ == "__main__":
    # Example usage
    model_dir = Path("python/models")
    best_model = model_dir / "scheduler_real_world.pth"
    output_model = model_dir / "scheduler_real_world.pt"
    
    if best_model.exists():
        export_to_torchscript(str(best_model), str(output_model))
    else:
        print(f"Model file not found: {best_model}")
        print("Please ensure you have trained the model first.")
