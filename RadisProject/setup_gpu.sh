#!/bin/bash

# Set ROCm device order and visibility
export ROCR_VISIBLE_DEVICES="0,1"
export HIP_VISIBLE_DEVICES="0,1"
export GPU_DEVICE_ORDINAL="0,1"

# Set compute mode preferences
export HSA_ENABLE_SDMA=1
export HSA_JOBS_PER_GPU=8

# Optimize memory management
export HSA_ENABLE_VM=1
export HIP_FORCE_P2P_HOST=1

# Set performance preferences
export ROCM_AGENT_ENUM="GPU"
export HSA_ENABLE_QUEUE_PROFILING=0

# Apply power management settings
if command -v rocm-smi &> /dev/null; then
    # Set power limits
    rocm-smi --setpoweroverdrive 230 -d 0
    rocm-smi --setpoweroverdrive 330 -d 1
    
    # Set performance level to high
    rocm-smi --setperflevel high -d 0,1
    
    # Disable GPU2 (iGPU)
    rocm-smi --resetclocks -d 2
    rocm-smi --setperflevel low -d 2
fi

echo "GPU configuration applied. Current status:"
rocm-smi

