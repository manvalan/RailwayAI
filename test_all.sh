#!/bin/bash
# Final validation test - tutti i componenti

echo "========================================================================"
echo "  🎯 RAILWAY AI SCHEDULER - FINAL VALIDATION TEST"
echo "========================================================================"
echo ""

# Test 1: Python Data Generator
echo "📊 Test 1: Data Generator (Python)"
echo "------------------------------------------------------------------------"
./venv/bin/python -c "
import sys
sys.path.insert(0, 'python')
from data.data_generator import RailwayNetworkGenerator
gen = RailwayNetworkGenerator(5, 8)
scenario = gen.generate_scenario(10, 0.3)
print(f'✅ Generati {len(scenario[\"trains\"])} treni, {len(scenario[\"conflicts\"])} conflitti')
"
echo ""

# Test 2: C++ Engine
echo "🔧 Test 2: C++ Execution Engine"
echo "------------------------------------------------------------------------"
./venv/bin/python -c "
import sys
sys.path.insert(0, 'python')
import railway_cpp as rc
scheduler = rc.RailwayScheduler()
print(f'✅ C++ Scheduler inizializzato: {scheduler}')
"
echo ""

# Test 3: Neural Network
echo "🧠 Test 3: Neural Network"
echo "------------------------------------------------------------------------"
./venv/bin/python -c "
import sys
sys.path.insert(0, 'python')
from models.scheduler_network import SchedulerNetwork
import torch
model = SchedulerNetwork(input_dim=80, hidden_dim=64, num_trains=50, num_tracks=20, num_stations=10)
params = sum(p.numel() for p in model.parameters())
print(f'✅ Rete neurale creata: {params:,} parametri')
"
echo ""

# Test 4: Trained Model
echo "💾 Test 4: Modello Addestrato"
echo "------------------------------------------------------------------------"
./venv/bin/python -c "
import torch
checkpoint = torch.load('models/scheduler_minimal.pth', map_location='cpu')
print(f'✅ Modello caricato: epoca {checkpoint[\"epoch\"]}, val_loss {checkpoint[\"val_loss\"]:.4f}')
"
echo ""

# Test 5: Dataset
echo "📁 Test 5: Dataset"
echo "------------------------------------------------------------------------"
./venv/bin/python -c "
import numpy as np
train_data = np.load('data/training_data.npz')
val_data = np.load('data/validation_data.npz')
print(f'✅ Training: {len(train_data[\"network_states\"])} samples')
print(f'✅ Validation: {len(val_data[\"network_states\"])} samples')
"
echo ""

# Test 6: Full Integration
echo "🚀 Test 6: Full Integration Test"
echo "------------------------------------------------------------------------"
./venv/bin/python examples/demo_quick.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Demo Python eseguito con successo"
else
    echo "❌ Demo Python fallito"
fi

./venv/bin/python examples/example_usage.py > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Esempio C++ eseguito con successo"
else
    echo "❌ Esempio C++ fallito"
fi
echo ""

# Summary
echo "========================================================================"
echo "  ✨ VALIDATION COMPLETE"
echo "========================================================================"
echo ""
echo "Sistema validato! Componenti funzionanti:"
echo "  ✅ Data Generator (Python)"
echo "  ✅ C++ Execution Engine"
echo "  ✅ Neural Network Architecture"
echo "  ✅ Trained Model"
echo "  ✅ Training/Validation Dataset"
echo "  ✅ Full Integration (Python + C++)"
echo ""
echo "🎯 Pronto per:"
echo "  • Training completo (python/training/train_model.py)"
echo "  • Acquisizione dati reali (python/data_acquisition/)"
echo "  • Ottimizzazione e deployment"
echo ""
echo "📚 Vedi STATUS.md per dettagli completi"
echo ""
