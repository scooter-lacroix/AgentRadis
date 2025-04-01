# RadisProject Installation Guide

This guide provides detailed instructions on how to install RadisProject.

## Prerequisites

*   Python 3.11+
*   Conda (recommended)

## Installation Steps

1.  **Create a Conda Environment:**

    ```bash
    conda create -n radis python=3.11
    conda activate radis
    ```

2.  **Clone the Repository:**

    ```bash
    git clone https://example.com/RadisProject.git
    cd RadisProject
    ```

3.  **Install RadisProject with Dependencies:**

    ```bash
    pip install -e ".[gpu]"  # For GPU support
    # Or, for specific GPU support:
    pip install -e ".[rocm]" # For AMD GPUs (ROCm)
    pip install -e ".[cuda]" # For NVIDIA GPUs (CUDA)
    ```

    *   `pip install -e ".[gpu]"`: Installs RadisProject in editable mode along with core dependencies and GPU support.
    *   `pip install -e ".[rocm]"`: Installs RadisProject with ROCm support for AMD GPUs.
    *   `pip install -e ".[cuda]"`: Installs RadisProject with CUDA support for NVIDIA GPUs.

## Verification

After installation, you can verify the installation by running the unit tests:

```bash
pytest
```

## Troubleshooting

If you encounter any issues during installation, please consult the [Troubleshooting Guide](troubleshooting.md) or report the issue on the [GitHub issue tracker](https://example.com/RadisProject/issues).
