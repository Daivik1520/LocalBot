#!/bin/bash

# Configuration
MODEL_PATH="models/gemma-2-2b-it-Q4_K_M.gguf"
PORT=8080
API_KEY=$(grep LLAMA_API_KEY .env | cut -d '=' -f2)

# Optimization: Detect physical CPU cores (better than logical for LLMs)
# For macOS (Darwin) use sysctl, for Linux use nproc or lscpu
if [[ "$OSTYPE" == "darwin"* ]]; then
    CORES=$(sysctl -n hw.physicalcpu)
else
    CORES=$(grep -c ^processor /proc/cpuinfo)
    # Use half of logical cores if physical detection is tricky on some Linux distros
    CORES=$((CORES / 2)) 
fi

if [ -z "$API_KEY" ]; then
    echo "Error: LLAMA_API_KEY not found in .env"
    exit 1
fi

echo "Starting llama-server on CPU with $CORES threads..."
echo "Model: Gemma 2 2B Instruct (Q4_K_M)"
echo "Using --mlock to prevent RAM swapping (improves speed)..."

# Run llama-server optimized for CPU
# -t: Set threads to physical core count
# --mlock: Lock model in RAM (prevents slow disk swapping)
./llama.cpp/llama-server \
    -m "$MODEL_PATH" \
    -t "$CORES" \
    --mlock \
    --port "$PORT" \
    --api-key "$API_KEY" \
    --no-jinja \
    --chat-template gemma \
    --host 0.0.0.0
