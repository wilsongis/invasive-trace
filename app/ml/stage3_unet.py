"""Stage 3 — UNetTexture (unet-v0.1.0).

PyTorch U-Net wrapper for 512×512 four-channel raster patch hotspot scoring.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

VERSION = "unet-v0.1.0"
ARTIFACT_PATH = Path("models/UNetTexture/unet-v0.1.0/model.pt")
PATCH_SIZE = 512
N_CHANNELS = 4

# Sentinel-2 band order for Stage 3 patch (FR-017b)
SENTINEL2_BANDS = ["B04", "B08", "B03", "B05"]
TARGET_RESOLUTION_M = 10.0
HALF_EXTENT_M = (PATCH_SIZE / 2) * TARGET_RESOLUTION_M  # 2560.0 m from centroid


class UNetTextureArtifactMissingError(FileNotFoundError):
    """Raised when the Stage 3 artifact is absent at the registered path."""


class UNetTexture:
    """PyTorch U-Net texture scorer for 512×512 four-channel raster patches.

    Inference API: infer(patch_tensor)
    Load API     : load()
    """

    VERSION = VERSION
    ARTIFACT_PATH = ARTIFACT_PATH
    PATCH_SIZE = PATCH_SIZE

    def __init__(self) -> None:
        self._model = None

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    def load(self) -> UNetTexture:
        """Load the PyTorch model artifact. Raises UNetTextureArtifactMissingError if absent.

        This check occurs before any DB interaction (fail-fast contract).
        torch is imported lazily to preserve the optional dependency contract.
        """
        if not self.ARTIFACT_PATH.exists():
            raise UNetTextureArtifactMissingError(
                f"Stage 3 artifact missing: {self.ARTIFACT_PATH}. "
                "A pre-trained UNetTexture model.pt must be staged at the registered path."
            )
        import torch  # noqa: PLC0415

        self._model = torch.load(  # noqa: S614
            self.ARTIFACT_PATH,
            map_location="cpu",
            weights_only=False,
        )
        self._model.eval()
        logger.info("stage3_loaded version=%s path=%s", self.VERSION, self.ARTIFACT_PATH)
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def infer(self, patch_tensor: np.ndarray) -> float:
        """Score a 512×512 four-channel raster patch.

        Args:
            patch_tensor: numpy array of shape (4, 512, 512) or (1, 4, 512, 512),
                          or a torch.Tensor of the same shape.

        Returns:
            hotspot_score float. NOT clamped — caller must clamp to [0.0, 1.0].
        """
        if self._model is None:
            raise RuntimeError("UNetTexture must be loaded before infer()")

        import torch  # noqa: PLC0415

        if isinstance(patch_tensor, np.ndarray):
            patch_tensor = torch.from_numpy(patch_tensor).float()

        if patch_tensor.ndim == 3:
            patch_tensor = patch_tensor.unsqueeze(0)  # (1, C, H, W)

        with torch.no_grad():
            output = self._model(patch_tensor)

        score = float(output.squeeze())
        logger.info("stage3_inferred version=%s raw_score=%.4f", self.VERSION, score)
        return score


# ------------------------------------------------------------------
# Patch extraction helpers (FR-017a, FR-017b)
# ------------------------------------------------------------------


async def extract_sentinel2_patch(
    stac_item_id: str,
    lon: float,
    lat: float,
) -> np.ndarray | None:
    """Resolve a Planetary Computer STAC item and extract a 512×512 4-channel patch.

    Bands: B04 (Red), B08 (NIR), B03 (Green), B05 (Red-Edge), all resampled to 10m.
    The patch is centred on (lon, lat). Boundary-short windows are zero-padded (boundless=True).

    Returns None and logs a warning when the STAC asset is unavailable.
    """
    try:
        return await asyncio.to_thread(_extract_patch_sync, stac_item_id, lon, lat)
    except Exception as exc:
        logger.warning(
            "stage3_stac_unavailable stac_item=%s lon=%.6f lat=%.6f error=%s",
            stac_item_id,
            lon,
            lat,
            exc,
        )
        return None


def _extract_patch_sync(stac_item_id: str, lon: float, lat: float) -> np.ndarray | None:
    """Synchronous (thread-safe) Sentinel-2 patch extraction via rasterio COG reads."""
    import planetary_computer  # noqa: PLC0415
    import rasterio  # noqa: PLC0415
    from pystac_client import Client  # noqa: PLC0415
    from rasterio.enums import Resampling  # noqa: PLC0415
    from rasterio.warp import transform as warp_transform  # noqa: PLC0415
    from rasterio.windows import from_bounds as window_from_bounds  # noqa: PLC0415

    from app.services.stac_client import PC_STAC_URL, SENTINEL2_COLLECTION  # noqa: PLC0415

    settings_key: str | None = None
    try:
        from app.config import get_settings  # noqa: PLC0415

        settings_key = get_settings().PC_SDK_SUBSCRIPTION_KEY or None
    except Exception:
        pass

    if settings_key:
        planetary_computer.settings.set_subscription_key(settings_key)

    # Fetch single item by ID via search
    client = Client.open(PC_STAC_URL)
    search = client.search(collections=[SENTINEL2_COLLECTION], ids=[stac_item_id])
    signed_item = None
    for item in search.items():
        signed_item = planetary_computer.sign_inplace(item)
        break

    if signed_item is None:
        logger.warning("stage3_stac_item_not_found stac_item=%s", stac_item_id)
        return None

    band_arrays: list[np.ndarray] = []
    for band_name in SENTINEL2_BANDS:
        asset = signed_item.assets.get(band_name)
        if asset is None:
            logger.warning("stage3_band_missing item=%s band=%s", stac_item_id, band_name)
            return None

        with rasterio.open(asset.href) as src:
            src_crs = src.crs
            (cx,), (cy,) = warp_transform("EPSG:4326", src_crs, [lon], [lat])

            west = cx - HALF_EXTENT_M
            east = cx + HALF_EXTENT_M
            south = cy - HALF_EXTENT_M
            north = cy + HALF_EXTENT_M

            window = window_from_bounds(west, south, east, north, transform=src.transform)
            data = src.read(
                1,
                window=window,
                out_shape=(PATCH_SIZE, PATCH_SIZE),
                resampling=Resampling.bilinear,
                boundless=True,
                fill_value=0,
            ).astype(np.float32)
            band_arrays.append(data)

    return np.stack(band_arrays, axis=0)  # (4, 512, 512)
