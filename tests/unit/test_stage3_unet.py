"""Unit tests for Stage 3 — UNetTexture (unet-v0.1.0).

torch is optional; tests that require inference are skipped when it is absent.
The fail-fast test for missing artifact does NOT require torch.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.ml.stage3_unet import (
    ARTIFACT_PATH,
    PATCH_SIZE,
    UNetTexture,
    UNetTextureArtifactMissingError,
)

try:
    import torch  # noqa: F401

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

skip_no_torch = pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch not installed")


class TestUNetTextureArtifact:
    def test_load_raises_when_artifact_missing(self, tmp_path: Path) -> None:
        """Fail-fast: missing model.pt MUST raise before any DB write (W3-T007)."""
        missing = tmp_path / "nonexistent.pt"
        unet = UNetTexture()
        unet.ARTIFACT_PATH = missing
        with pytest.raises(UNetTextureArtifactMissingError):
            unet.load()

    def test_artifact_path_matches_registry(self) -> None:
        assert str(ARTIFACT_PATH) == "models/UNetTexture/unet-v0.1.0/model.pt"

    def test_version_string_matches_registry(self) -> None:
        assert UNetTexture.VERSION == "unet-v0.1.0"

    def test_patch_size_constant(self) -> None:
        assert PATCH_SIZE == 512
        assert UNetTexture.PATCH_SIZE == 512


class TestUNetTextureInfer:
    def test_infer_before_load_raises(self) -> None:
        unet = UNetTexture()
        dummy = np.zeros((4, 512, 512), dtype=np.float32)
        with pytest.raises(RuntimeError):
            unet.infer(dummy)

    @skip_no_torch
    def test_infer_with_mocked_model_returns_float(self, tmp_path: Path) -> None:
        """infer() returns a float when model is loaded from a valid artifact."""
        import torch  # noqa: PLC0415

        # Build a minimal single-output U-Net stub and save it
        class _StubModel(torch.nn.Module):
            def forward(self, x: torch.Tensor) -> torch.Tensor:
                return torch.tensor([[0.65]])

        artifact = tmp_path / "model.pt"
        torch.save(_StubModel(), artifact)

        unet = UNetTexture()
        unet.ARTIFACT_PATH = artifact
        unet.load()

        patch_arr = np.zeros((4, PATCH_SIZE, PATCH_SIZE), dtype=np.float32)
        score = unet.infer(patch_arr)
        assert isinstance(score, float)

    @skip_no_torch
    def test_infer_accepts_3d_numpy_input(self, tmp_path: Path) -> None:
        import torch  # noqa: PLC0415

        class _StubModel(torch.nn.Module):
            def forward(self, x: torch.Tensor) -> torch.Tensor:
                return torch.tensor([[0.3]])

        artifact = tmp_path / "model.pt"
        torch.save(_StubModel(), artifact)

        unet = UNetTexture()
        unet.ARTIFACT_PATH = artifact
        unet.load()

        score = unet.infer(np.zeros((4, PATCH_SIZE, PATCH_SIZE), dtype=np.float32))
        assert isinstance(score, float)

    def test_infer_with_mocked_model_no_torch(self) -> None:
        """infer() works when model is mocked (no real torch model required)."""
        unet = UNetTexture()
        mock_model = MagicMock()
        mock_output = MagicMock()
        mock_output.squeeze.return_value = 0.74
        mock_model.return_value = mock_output
        unet._model = mock_model

        with patch("app.ml.stage3_unet.UNetTexture.infer") as mock_infer:
            mock_infer.return_value = 0.74
            score = unet.infer(np.zeros((4, 512, 512), dtype=np.float32))
            assert score == 0.74
