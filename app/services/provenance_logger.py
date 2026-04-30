import hashlib
import json
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)


class ProvenanceLogger:
    @staticmethod
    def log_execution(
        model_version: str, parameters: dict[str, Any], input_data: Any = None
    ) -> str:
        """Log pipeline execution and return a provenance trace ID."""
        trace_id = hashlib.sha256(str(time.time()).encode()).hexdigest()[:8]

        input_hash = None
        if input_data is not None:
            try:
                input_str = json.dumps(input_data, sort_keys=True, default=str)
                input_hash = hashlib.sha256(input_str.encode()).hexdigest()
            except Exception:
                input_hash = "unhashable"

        log_data = {
            "trace_id": trace_id,
            "model_version": model_version,
            "hyperparameters": parameters,
            "input_hash": input_hash,
        }

        logger.info(f"PROVENANCE RECORD: {json.dumps(log_data)}")
        return trace_id
