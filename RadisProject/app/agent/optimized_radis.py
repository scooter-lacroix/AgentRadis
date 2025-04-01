import os
import time
import logging
from typing import List, Optional, Dict, Any
import torch
from torch.cuda import amp
import numpy as np
from pydantic import ValidationError

from app.memory import RollingWindowMemory
from app.metrics import MetricsTracker
from app.tool import BaseTool
from .enhanced_radis import EnhancedRadis
from ..schema.types import ProcessingMetrics
from ..core.exceptions import (
    ROCmNotAvailableError,
    GPUMemoryError,
    BatchProcessingError,
)

logger = logging.getLogger(__name__)


class ROCmOptimizedRadis(EnhancedRadis):
    """
    ROCm-optimized implementation of the RADIS system with GPU acceleration support.
    Includes memory management, batch processing, and performance metrics.
    """

    def __init__(
        self,
        memory: Optional[RollingWindowMemory] = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: str = "",
        metrics_tracker: Optional[MetricsTracker] = None,
        config: Optional[Dict[str, Any]] = None,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
        rocm_device: str = "auto",
    ):
        """Initialize ROCm-optimized Radis instance."""
        super().__init__(
            memory=memory,
            tools=tools,
            system_prompt=system_prompt,
            metrics_tracker=metrics_tracker,
            model=model,
            temperature=temperature,
        )
        self.device = torch.device("cpu")  # Default to CPU
        self.scaler = None  # Will be initialized if ROCm is available
        self.is_rocm_initialized = False
        self.rocm_device = rocm_device
        self.metrics = ProcessingMetrics(
            processing_time=0.0, peak_memory_usage=0.0, device_used="CPU"
        )
        self._initialize_rocm()

    @staticmethod
    def is_rocm_available() -> bool:
        """
        Check if ROCm is available on the system.

        Returns:
            bool: True if ROCm is available, False otherwise
        """
        try:
            return torch.cuda.is_available() and hasattr(torch.version, "hip")
        except Exception as e:
            logger.warning(f"Error checking ROCm availability: {e}")
            return False

    def _initialize_rocm(self) -> None:
        """Initialize ROCm environment if available."""
        if self.is_rocm_available():
            try:
                self.device = torch.device("cuda")
                torch.cuda.init()
                # Initialize GradScaler for ROCm
                try:
                    self.scaler = torch.amp.GradScaler(device_type="cuda")
                    logger.info("GradScaler initialized for ROCm")
                except Exception as e:
                    logger.warning(f"GradScaler initialization failed: {e}")
                    self.scaler = None
                self.is_rocm_initialized = True
                logger.info("ROCm initialization successful")
            except Exception as e:
                logger.error(f"Failed to initialize ROCm: {e}")
                self.fallback_to_cpu()
        else:
            logger.warning("ROCm not available, using CPU")
            self.fallback_to_cpu()

    def clear_gpu_memory(self) -> None:
        """
        Clear GPU memory cache and release unused memory.
        """
        if self.is_rocm_initialized:
            try:
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                current_memory = torch.cuda.memory_allocated()
                logger.debug(
                    f"GPU memory after cleanup: {current_memory / 1024**2:.2f} MB"
                )
            except Exception as e:
                logger.error(f"Error during GPU memory cleanup: {e}")
                raise GPUMemoryError(f"Failed to clear GPU memory: {e}")

    def fallback_to_cpu(self) -> None:
        """
        Fall back to CPU processing when GPU is unavailable or encounters errors.
        """
        self.device = torch.device("cpu")
        self.is_rocm_initialized = False
        logger.info("Switched to CPU processing mode")

    async def process_batch(self, batch_data: List[Any]) -> List[Any]:
        """
        Process a batch of data using ROCm acceleration.

        Args:
            batch_data: List of input data to process

        Returns:
            List[Any]: Processed results

        Raises:
            BatchProcessingError: If batch processing fails
        """
        if not batch_data:
            return []

        try:
            with torch.amp.autocast("cuda", enabled=self.is_rocm_initialized):
                results = []
                start_mem = (
                    torch.cuda.memory_allocated() if self.is_rocm_initialized else 0
                )
                for data in batch_data:
                    tensor_data = torch.tensor(data, device=self.device)
                    processed = await self._process_single_item(tensor_data)
                    results.append(
                        processed
                        if isinstance(processed, np.ndarray)
                        else processed.cpu().numpy()
                    )
                if self.is_rocm_initialized:
                    end_mem = torch.cuda.memory_allocated()
                    self.metrics.peak_memory_usage = max(
                        self.metrics.peak_memory_usage,
                        (end_mem - start_mem) / 1024**2,  # Convert to MB
                    )
                return results
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            raise BatchProcessingError(f"Failed to process batch: {e}")

    async def process_with_metrics(self, data: Any) -> tuple[Any, ProcessingMetrics]:
        """
        Process data and collect performance metrics.

        Args:
            data: Input data to process

        Returns:
            tuple: (processed_result, metrics)
        """
        start_time = time.time()
        peak_memory = 0

        try:
            if self.is_rocm_initialized:
                peak_memory = torch.cuda.max_memory_allocated() / 1024**2  # MB

            result = await self._process_single_item(data)

            processing_time = time.time() - start_time
            metrics = ProcessingMetrics(
                processing_time=processing_time,
                peak_memory_usage=peak_memory,
                device_used="ROCm GPU" if self.is_rocm_initialized else "CPU",
            )

            return result, metrics
        except Exception as e:
            logger.error(f"Processing error: {e}")
            self.clear_gpu_memory()
            raise

    async def process_data(self, data: Any) -> Dict[str, Any]:
        """
        Process a single data item with ROCm acceleration.

        Args:
            data: Input data to process

        Returns:
            Dict[str, Any]: Dictionary containing result and metrics
        """
        try:
            result = await self._process_single_item(data)
            return {
                "result": result,
                "metrics": {
                    "processing_time": self.metrics.processing_time,
                    "peak_memory_usage": self.metrics.peak_memory_usage,
                    "device_used": "cuda" if self.is_rocm_initialized else "cpu",
                },
            }
        except Exception as e:
            logger.error(f"Error in process_data: {e}")
            if self.is_rocm_initialized:
                self.fallback_to_cpu()
                return await self.process_data(data)
            raise

    async def _process_single_item(self, data: Any) -> Any:
        """
        Internal method to process a single item with error handling.

        Args:
            data: Input data to process

        Returns:
            Processed result
        """
        try:
            if isinstance(data, (np.ndarray, torch.Tensor)):
                tensor_data = torch.as_tensor(data, device=self.device)
            else:
                raise ValueError(f"Unsupported data type: {type(data)}")

            result = await self._apply_processing(tensor_data)

            # Convert result back to numpy if needed
            if isinstance(result, torch.Tensor):
                result = result.cpu().numpy()

            return result
        except Exception as e:
            logger.error(f"Error processing item: {e}")
            if self.is_rocm_initialized:
                self.clear_gpu_memory()
                self.fallback_to_cpu()
                return await self._process_single_item(data)
            raise

    async def _apply_processing(self, tensor: torch.Tensor) -> torch.Tensor:
        """
        Apply the actual processing to the tensor.

        Args:
            tensor: Input tensor

        Returns:
            torch.Tensor: Processed tensor
        """
        try:
            with torch.amp.autocast("cuda", enabled=self.is_rocm_initialized):
                # Add your specific tensor processing logic here
                # This is a placeholder implementation that demonstrates ROCm acceleration
                processed = tensor * 2.0
                if self.is_rocm_initialized:
                    processed = self.scaler.scale(processed) if self.scaler is not None else processed
                return processed
        except Exception as e:
            logger.error(f"Tensor processing error: {e}")
            if self.is_rocm_initialized:
                self.fallback_to_cpu()
                return await self._apply_processing(tensor.cpu())
            raise

    async def run(self, text: str) -> str:
        """
        Process input text with ROCm acceleration when available, falling back to CPU processing.

        Args:
            text: Input text to process

        Returns:
            Processed response text
        """
        if not text:
            return ""

        try:
            if self.is_rocm_initialized:
                logger.info("Using ROCm acceleration for processing")
                with torch.amp.autocast("cuda"):
                    response = await super().run(text)
                return response
            else:
                logger.info("ROCm unavailable, falling back to CPU processing")
                return await super().run(text)

        except Exception as e:
            logger.error(f"Error during ROCm processing: {e}")
            logger.info("Falling back to CPU processing due to ROCm error")
            self.fallback_to_cpu()
            return await super().run(text)

    async def step(self, user_input: str) -> Dict[str, Any]:
        """
        Process a single conversation step with ROCm acceleration if available.

        Args:
            user_input: The user's input text

        Returns:
            Dict[str, Any]: Response containing processed result and metadata
        """
        start_time = time.time()

        try:
            # Process the step using the parent class implementation
            response = await super().step(user_input)

            # Add ROCm-specific metrics to the response
            response.update(
                {
                    "metrics": {
                        "processing_time": time.time() - start_time,
                        "peak_memory_usage": (
                            torch.cuda.max_memory_allocated() / 1024**2
                            if self.is_rocm_initialized
                            else 0
                        ),
                        "device_used": (
                            "ROCm GPU" if self.is_rocm_initialized else "CPU"
                        ),
                        "acceleration_enabled": self.is_rocm_initialized,
                    }
                }
            )

            return response

        except Exception as e:
            logger.error(f"Error in ROCm step processing: {e}")
            if self.is_rocm_initialized:
                self.fallback_to_cpu()
                return await self.step(user_input)
            raise

    async def async_setup(self) -> None:
        """
        Asynchronously set up the ROCm environment and initialize necessary components.
        """
        await super().async_setup()  # Call parent setup first

        try:
            if not self.is_rocm_initialized and self.is_rocm_available():
                self._initialize_rocm()
                logger.info("ROCm environment initialized during async setup")

            # Initialize additional ROCm-specific components
            if self.is_rocm_initialized:
                self.scaler = None  # Will be initialized if ROCm is available
                torch.cuda.empty_cache()
                logger.info(f"Using ROCm device: {torch.cuda.get_device_name()}")

        except Exception as e:
            logger.warning(f"Failed to initialize ROCm during async setup: {e}")
            self.fallback_to_cpu()

    async def cleanup(self):
        """Clean up ROCm resources."""
        if self.is_rocm_initialized:
            try:
                self.clear_gpu_memory()
            except Exception as e:
                logger.warning(f"Failed to clean up ROCm resources: {e}")
        await super().cleanup()
