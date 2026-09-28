#!/bin/bash
# Helper script to install model dependencies from MLflow

set -e

if [ -z "$1" ]; then
    echo "Usage: $0 <model-uri>"
    echo ""
    echo "Examples:"
    echo "  $0 models:/my-model/Production"
    echo "  $0 runs:/abc123/model"
    echo ""
    echo "This script will:"
    echo "  1. Download the model artifacts from MLflow"
    echo "  2. Extract the model's requirements.txt"
    echo "  3. Install the dependencies"
    exit 1
fi

MODEL_URI=$1
TEMP_DIR=$(mktemp -d)

echo "==> Downloading model artifacts from: $MODEL_URI"
mlflow artifacts download -u "$MODEL_URI" -d "$TEMP_DIR"

if [ -f "$TEMP_DIR/requirements.txt" ]; then
    echo "==> Found model requirements.txt"
    echo "==> Installing model dependencies..."
    pip install -r "$TEMP_DIR/requirements.txt"
    echo "==> Model dependencies installed successfully!"
else
    echo "WARNING: No requirements.txt found in model artifacts"
    echo "The model may not have any additional dependencies, or they may be embedded differently"
fi

# Cleanup
rm -rf "$TEMP_DIR"
echo "==> Done!"
