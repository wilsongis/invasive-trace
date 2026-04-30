import asyncio
import functools
import random
from collections.abc import Callable
from typing import Any

import numpy as np

from app.config import get_settings
from app.services.provenance_logger import ProvenanceLogger


def run_deterministically(model_version: str, **func_kwargs):
    """Decorator to run a function deterministically and log provenance."""

    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> Any:
                settings = get_settings()
                seed = settings.RANDOM_SEED

                # Set random seeds
                random.seed(seed)
                np.random.seed(seed)

                # Attempt PyTorch seed if available
                try:
                    import torch

                    torch.manual_seed(seed)
                except ImportError:
                    pass

                # Combine kwargs for logging
                all_kwargs = {**func_kwargs, **kwargs}

                # Log provenance
                ProvenanceLogger.log_execution(
                    model_version=model_version,
                    parameters={"seed": seed, **all_kwargs},
                    input_data={"args": str(args), "kwargs": str(kwargs)},
                )

                # Execute original function
                result = await func(*args, **kwargs)
                return result

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> Any:
                settings = get_settings()
                seed = settings.RANDOM_SEED

                # Set random seeds
                random.seed(seed)
                np.random.seed(seed)

                # Attempt PyTorch seed if available
                try:
                    import torch

                    torch.manual_seed(seed)
                except ImportError:
                    pass

                # Combine kwargs for logging
                all_kwargs = {**func_kwargs, **kwargs}

                # Log provenance
                ProvenanceLogger.log_execution(
                    model_version=model_version,
                    parameters={"seed": seed, **all_kwargs},
                    input_data={"args": str(args), "kwargs": str(kwargs)},
                )

                # Execute original function
                result = func(*args, **kwargs)
                return result

            return sync_wrapper

    return decorator
