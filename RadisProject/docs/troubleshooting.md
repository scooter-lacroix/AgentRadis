# Troubleshooting Guide

This guide provides solutions for common issues encountered when working with RadisProject, along with debugging strategies and performance optimization tips.

## Table of Contents

- [Common Issues](#common-issues)
  - [Installation Problems](#installation-problems)
  - [GPU Support Issues](#gpu-support-issues)
  - [API Authentication Errors](#api-authentication-errors)
  - [Memory Management](#memory-management)
- [Error Message Interpretation](#error-message-interpretation)
- [Debugging Strategies](#debugging-strategies)
  - [Logging Configuration](#logging-configuration)
  - [Environment Validation](#environment-validation)
- [Performance Optimization](#performance-optimization)

## Common Issues

### Installation Problems

#### Dependency Conflicts

```
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed.
```

**Solution:**
- Try installing with the `--no-dependencies` flag, then install dependencies manually:
  ```bash
  pip install --no-dependencies radisproject
  pip install -r requirements.txt
  ```
- Use a fresh virtual environment:
  ```bash
  conda create -n radis_env python=3.11
  conda activate radis_env
  pip install radisproject
  ```

#### Path Issues

If you encounter `ImportError: No module named 'app'` or similar:

**Solution:**
- Ensure the project root is in your PYTHONPATH:
  ```bash
  export PYTHONPATH=$PYTHONPATH:/path/to/RadisProject
  ```
- Install the package in development mode:
  ```bash
  pip install -e .
  ```

### GPU Support Issues

#### CUDA Availability Warnings

If you see this warning:
```
torch.cuda.amp.GradScaler is enabled, but CUDA is not available. Disabling.
```

**Solutions:**
1. **Verify CUDA Installation:**
   ```bash
   nvidia-smi
   python -c "import torch; print(torch.cuda.is_available())"
   ```

2. **Check Environment Variables:**
   ```bash
   echo $CUDA_HOME
   echo $LD_LIBRARY_PATH
   ```

3. **Install Compatible PyTorch Version:**
   ```bash
   # For CUDA 11.8
   pip install torch==2.0.1+cu118 -f https://download.pytorch.org/whl/torch_stable.html
   
   # For CPU-only
   pip install torch==2.0.1
   ```

#### ROCm Initialization Problems

If using AMD GPUs with ROCm and encountering initialization issues:

**Solutions:**
1. **Verify ROCm Installation:**
   ```bash
   rocminfo
   python -c "import torch; print('ROCm available:', torch.cuda.is_available())"
   ```

2. **Check Compatibility:**
   | ROCm Version | Compatible PyTorch Version |
   |--------------|----------------------------|
   | 5.4.x        | 2.0.1                     |
   | 5.3.x        | 2.0.0                     |
   | 5.2.x        | 1.13.1                    |

3. **Install Compatible PyTorch:**
   ```bash
   pip install torch==2.0.1 -f https://download.pytorch.org/whl/rocm5.4.2
   ```

### API Authentication Errors

#### Invalid API Keys

```
AuthenticationError: API key is invalid or expired
```

**Solutions:**
- Verify your API key is set correctly in the configuration
- Check that the API key is active and not expired
- Ensure the key has the required permissions

#### Connection Timeout Issues

```
ConnectionError: Connection timed out after 30 seconds
```

**Solutions:**
- Check your internet connection
- Verify firewall settings are not blocking the API
- Try using a different network or VPN

### Memory Management

#### Out of Memory Errors

```
RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB
```

**Solutions:**
- Reduce batch size in configuration
- Enable gradient checkpointing:
  ```python
  model.gradient_checkpointing_enable()
  ```
- Implement memory-efficient attention mechanisms
- Use lower precision (e.g., fp16 instead of fp32)

#### Memory Leaks

Signs of memory leaks include gradually increasing memory usage over time.

**Solutions:**
- Ensure tensors are properly deallocated:
  ```python
  del tensor
  torch.cuda.empty_cache()
  ```
- Check for circular references in your code
- Monitor memory usage with tools like `nvidia-smi` (CUDA) or `rocm-smi` (ROCm)

## Error Message Interpretation

| Error Message | Likely Cause | Solution |
|---------------|--------------|----------|
| `FutureWarning: get_tool_registry() will be removed in a future version` | Using deprecated API | Use `app.core.tool_registry.get_tool_registry()` instead |
| `ModuleNotFoundError: No module named 'app.tool'` | Incorrect import path | Update import paths according to the latest package structure |
| `TypeError: 'NoneType' object is not callable` | Calling an uninitialized function | Ensure proper initialization order and check for None values |
| `ValueError: Expected parameter to have defined shape` | Model parameter mismatch | Verify model configuration matches loaded weights |
| `RuntimeError: Expected all tensors to be on the same device` | Mixed device operations | Ensure consistent device usage (CPU vs GPU) |

## Debugging Strategies

### Logging Configuration

RadisProject uses Python's logging module. Enhance debugging by increasing log verbosity:

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)
```

#### Log Levels Guide

| Level | When to Use |
|-------|-------------|
| DEBUG | Detailed information, typically of interest only when diagnosing problems |
| INFO | Confirmation that things are working as expected |
| WARNING | Indication that something unexpected happened, or indicative of some problem |
| ERROR | Due to a more serious problem, the software has not been able to perform some function |
| CRITICAL | A serious error, indicating that the program itself may be unable to continue running |

### Environment Validation

Create a validation script to check your environment:

```python
def validate_environment():
    """Validate the RadisProject environment."""
    import sys
    import torch
    import os
    
    results = {
        "Python Version": sys.version,
        "PyTorch Version": torch.__version__,
        "CUDA Available": torch.cuda.is_available(),
        "GPU Count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "GPU Name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A",
        "Environment Variables": {k: v for k, v in os.environ.items() if k.startswith(('CUDA', 'ROCM', 'PYTHON', 'LD_LIBRARY'))}
    }
    
    for key, value in results.items():
        if key != "Environment Variables":
            print(f"{key}: {value}")
    
    print("\nRelevant Environment Variables:")
    for k, v in results["Environment Variables"].items():
        print(f"  {k}: {v}")
        
    # Check for common misconfigurations
    warnings = []
    if not torch.cuda.is_available() and any(k.startswith('CUDA') for k in os.environ):
        warnings.append("CUDA environment variables are set but CUDA is not available to PyTorch")
    
    if warnings:
        print("\nWarnings:")
        for warning in warnings:
            print(f"  - {warning}")

if __name__ == "__main__":
    validate_environment()
```

Save this script as `validate_env.py` and run it to diagnose environment issues.

#### Dependency Analysis

You can check for package conflicts and versions:

```bash
pip list --format=freeze > requirements_installed.txt
pip check
```

## Performance Optimization

### GPU Memory Efficiency

1. **Gradient Accumulation**
   ```python
   # Instead of updating weights after each batch
   # Accumulate gradients over multiple batches
   optimizer.zero_grad()
   for i, batch in enumerate(dataloader):
       output = model(batch)
       loss = loss_fn(output)
       loss = loss / accumulation_steps  # Scale the loss
       loss.backward()
       if (i + 1) % accumulation_steps == 0:
           optimizer.step()
           optimizer.zero_grad()
   ```

2. **Mixed Precision Training**
   ```python
   from torch.cuda.amp import autocast, GradScaler
   
   scaler = GradScaler()
   for batch in dataloader:
       optimizer.zero_grad()
       with autocast():
           output = model(batch)
           loss = loss_fn(output)
       scaler.scale(loss).backward()
       scaler.step(optimizer)
       scaler.update()
   ```

3. **Model Parallelism Approaches**
   
   | Approach | Best For | Limitations |
   |----------|----------|-------------|
   | DataParallel | Single machine, multiple GPUs | GIL bottleneck |
   | DistributedDataParallel | Multi-node training | More complex setup |
   | Model Sharding | Very large models | Communication overhead |
   | Pipeline Parallelism | Sequential models | Bubble overhead |

### Optimizing Tool Execution

1. **Batch Operation Processing**
   - Group similar operations to reduce context switching
   - Pre-fetch related data when possible

2. **Caching Strategies**
   - Implement LRU caches for expensive operations
   - Use tiered caching for frequently accessed data

3. **Asynchronous Processing**
   ```python
   import asyncio
   
   async def process_tools(tools):
       tasks = [asyncio.create_task(tool.execute()) for tool in tools]
       return await asyncio.gather(*tasks)
   
   # Usage
   results = asyncio.run(process_tools(tool_list))
   ```

### System Optimization Checklist

- [ ] GPU drivers are up-to-date
- [ ] PyTorch is compiled for your specific GPU architecture
- [ ] I/O operations are minimized during processing
- [ ] Batch sizes are optimized for your hardware
- [ ] Unused Python modules are unloaded to free memory
- [ ] CPU and GPU processing are properly coordinated

---

If you're still experiencing issues after trying these troubleshooting steps, please [open an issue](https://github.com/your-org/RadisProject/issues/new) with detailed information about your problem, including the steps to reproduce it and the complete error output.

