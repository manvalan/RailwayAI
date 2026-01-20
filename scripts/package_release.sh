#!/bin/bash

# RailwayAI Release Packaging Script
# Automates model export and creates a distribution bundle (.tgz)

set -e

PROJECT_ROOT=$(pwd)
RELEASE_DIR="railwayai_release_$(date +%Y%m%d)"
BUNDLE_NAME="${RELEASE_DIR}.tgz"

echo "===================================================="
echo "🚀 Starting RailwayAI Release Packaging"
echo "===================================================="

# 1. Export Models to TorchScript
echo "1. Exporting ML models to TorchScript..."
if [ -f "python/training/export_model.py" ]; then
    export PYTHONPATH=$PYTHONPATH:$(pwd)
    python3 python/training/export_model.py
else
    echo "⚠️ Warning: export_model.py not found. Skipping model export."
fi

# 2. Create Release Directory
echo "2. Creating release directory: $RELEASE_DIR"
mkdir -p "$RELEASE_DIR"

# 3. Copy necessary files
echo "3. Collecting artifacts..."
mkdir -p "$RELEASE_DIR/api"
mkdir -p "$RELEASE_DIR/python"
mkdir -p "$RELEASE_DIR/scripts"

cp -r api/* "$RELEASE_DIR/api/"
cp -r python/* "$RELEASE_DIR/python/"
cp requirements.txt "$RELEASE_DIR/"
cp README.md "$RELEASE_DIR/"
cp STATUS.md "$RELEASE_DIR/"
[ -f ".env.example" ] && cp .env.example "$RELEASE_DIR/.env"

# Copy C++ binaries if they exist (build folder check)
if [ -d "build" ]; then
    echo "   Found build directory, copying C++ binaries..."
    mkdir -p "$RELEASE_DIR/bin"
    find build -maxdepth 2 -executable -type f -not -name "*.so*" -exec cp {} "$RELEASE_DIR/bin/" \;
    # Copy shared libraries
    find build -name "*.so*" -exec cp {} "$RELEASE_DIR/python/" \;
fi

# 4. Create Bundle
echo "4. Creating tarball: $BUNDLE_NAME"
tar -czf "$BUNDLE_NAME" "$RELEASE_DIR"

# 5. Cleanup
echo "5. Cleaning up temporary files..."
rm -rf "$RELEASE_DIR"

echo "===================================================="
echo "✅ Release Bundle Created: $BUNDLE_NAME"
echo "===================================================="
