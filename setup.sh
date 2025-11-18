#!/bin/bash

# Setup script per Railway AI Scheduler
# Configura l'ambiente di sviluppo completo

set -e  # Exit on error

echo "======================================"
echo "Railway AI Scheduler - Setup"
echo "======================================"
echo ""

# ============================================================================
# 1. Verifica requisiti di sistema
# ============================================================================

echo "[1/6] Verifico requisiti di sistema..."

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERRORE: Python 3 non trovato. Installare Python 3.8+ prima di continuare."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "  ✓ Python $PYTHON_VERSION trovato"

# Check CMake
if ! command -v cmake &> /dev/null; then
    echo "ERRORE: CMake non trovato. Installare CMake 3.15+ prima di continuare."
    exit 1
fi

CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
echo "  ✓ CMake $CMAKE_VERSION trovato"

# Check C++ compiler
if command -v g++ &> /dev/null; then
    CXX_COMPILER="g++"
    CXX_VERSION=$(g++ --version | head -n1)
    echo "  ✓ $CXX_VERSION trovato"
elif command -v clang++ &> /dev/null; then
    CXX_COMPILER="clang++"
    CXX_VERSION=$(clang++ --version | head -n1)
    echo "  ✓ $CXX_VERSION trovato"
else
    echo "ERRORE: Nessun compilatore C++ trovato (g++ o clang++)."
    exit 1
fi

echo ""

# ============================================================================
# 2. Crea ambiente virtuale Python
# ============================================================================

echo "[2/6] Creo ambiente virtuale Python..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✓ Ambiente virtuale creato"
else
    echo "  ✓ Ambiente virtuale già esistente"
fi

# Attiva ambiente
source venv/bin/activate

echo "  ✓ Ambiente virtuale attivato"
echo ""

# ============================================================================
# 3. Installa dipendenze Python
# ============================================================================

echo "[3/6] Installo dipendenze Python..."

pip install --upgrade pip setuptools wheel > /dev/null 2>&1
echo "  ✓ pip, setuptools, wheel aggiornati"

pip install -r requirements.txt
echo "  ✓ Dipendenze Python installate"

# Installa pybind11
pip install pybind11[global]
echo "  ✓ pybind11 installato"

echo ""

# ============================================================================
# 4. Compila modulo C++
# ============================================================================

echo "[4/6] Compilo modulo C++..."

# Crea directory build
mkdir -p build
cd build

# Configura con CMake
cmake .. -DCMAKE_BUILD_TYPE=Release
echo "  ✓ Configurazione CMake completata"

# Compila
cmake --build . --config Release -j$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)
echo "  ✓ Compilazione completata"

cd ..
echo ""

# ============================================================================
# 5. Genera dati di training
# ============================================================================

echo "[5/6] Genero dati di training..."

mkdir -p data
mkdir -p models

python3 python/data/data_generator.py
echo "  ✓ Dataset di training generati"

echo ""

# ============================================================================
# 6. Test installazione
# ============================================================================

echo "[6/6] Testo installazione..."

# Test import Python
python3 -c "import torch; print('  ✓ PyTorch:', torch.__version__)"

# Test modulo C++
if [ -f "build/python/railway_cpp$(python3-config --extension-suffix)" ]; then
    echo "  ✓ Modulo C++ compilato correttamente"
    
    # Copia modulo nella directory python per import
    cp build/python/railway_cpp* python/
    
    # Test import
    python3 -c "
import sys
sys.path.insert(0, 'python')
import railway_cpp
print('  ✓ Modulo C++ importabile')
print('  ✓ Versione:', railway_cpp.__version__)
"
else
    echo "  ⚠ Modulo C++ non trovato, potrebbe essere necessaria compilazione manuale"
fi

echo ""

# ============================================================================
# Summary
# ============================================================================

echo "======================================"
echo "Setup completato con successo! 🎉"
echo "======================================"
echo ""
echo "Per iniziare:"
echo "  1. Attiva l'ambiente: source venv/bin/activate"
echo "  2. Genera dati: python python/data/data_generator.py"
echo "  3. Addestra modello: python python/training/train_model.py"
echo "  4. Vedi esempi in: examples/"
echo ""
echo "Per ricompilare il modulo C++:"
echo "  cd build && cmake --build . --config Release"
echo ""
echo "Documentazione completa: README.md"
echo ""
