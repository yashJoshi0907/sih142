"""
models/ldsr_s2.py — LDSR-S2 wrapper (ESAOpenSR)
Physical-Logical trade-off: Balanced (latent diffusion with back-projection constraint).
Uncertainty maps are baked into the model output to flag hallucinated pixels.
Trained specifically on Sentinel-2 RGB+NIR data.
"""
import time
import numpy as np
import rasterio
from rasterio.enums import Resampling
from pathlib import Path


def run_ldsr_s2(input_path: str, output_path: str) -> dict:
    """
    Run LDSR-S2 (ESA Latent Diffusion SR) on a GeoTIFF.
    Returns dict with output_path, uncertainty_path, inference_time_sec.
    Falls back to bicubic if model cannot be loaded.
    """
    start = time.time()
    uncertainty_path = str(Path(output_path).with_suffix(".uncertainty.tif"))

    try:
        from opensr_utils.model_utils.get_models import get_ldsrs2
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = get_ldsrs2(device=device)

        with rasterio.open(input_path) as src:
            # LDSR-S2 expects float32 [0,1] tensor with bands [B, G, R, NIR]
            count = src.count
            if count >= 4:
                # Read first 4 bands: assume B02,B03,B04,B08 ordering
                data = src.read([1, 2, 3, 4]).astype(np.float32)
            else:
                data = src.read().astype(np.float32)
                # Pad to 4 bands by duplicating last band
                while data.shape[0] < 4:
                    data = np.concatenate([data, data[-1:]], axis=0)

            # Normalise to [0, 1] from typical S2 uint16 range [0, 10000]
            max_val = data.max()
            if max_val > 1.0:
                data = data / 10000.0
            data = np.clip(data, 0, 1)

            # Crop to max 512x512 for demo (CPU performance)
            h, w = data.shape[1], data.shape[2]
            crop_h, crop_w = min(h, 512), min(w, 512)
            data_crop = data[:, :crop_h, :crop_w]

            # Model expects (B, C, H, W) tensor
            tensor_in = torch.from_numpy(data_crop).unsqueeze(0).to(device)

            with torch.no_grad():
                result = model(tensor_in)

            # Handle model output (tensor or dict with uncertainty)
            if isinstance(result, dict):
                sr_tensor = result.get("sr", result.get("output", list(result.values())[0]))
                uncertainty = result.get("uncertainty", None)
            else:
                sr_tensor = result
                uncertainty = None

            sr_np = sr_tensor.squeeze(0).cpu().numpy()  # (C, H*4, W*4)
            sr_np = np.clip(sr_np * 10000.0, 0, 65535).astype(np.uint16)

            # Build output profile
            profile = src.profile.copy()
            out_h, out_w = sr_np.shape[1], sr_np.shape[2]
            scale = out_h / crop_h
            profile.update({
                "height": out_h,
                "width": out_w,
                "count": sr_np.shape[0],
                "dtype": "uint16",
                "transform": src.transform * src.transform.scale(
                    (crop_w / out_w), (crop_h / out_h)
                ),
            })
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(sr_np)

            # Write uncertainty map if available
            if uncertainty is not None:
                unc_np = uncertainty.squeeze(0).cpu().numpy()
                unc_profile = profile.copy()
                unc_profile.update({"count": 1, "dtype": "float32"})
                with rasterio.open(uncertainty_path, "w", **unc_profile) as dst:
                    dst.write(unc_np[0:1].astype(np.float32))
            else:
                uncertainty_path = None

        elapsed = time.time() - start
        return {
            "output_path": output_path,
            "uncertainty_path": uncertainty_path,
            "inference_time_sec": elapsed,
            "scale": scale,
            "model": "LDSR-S2",
            "fallback": False,
        }

    except Exception as e:
        print(f"[LDSR-S2] Failed ({e}), falling back to bicubic")
        from .bicubic import run_bicubic
        result = run_bicubic(input_path, output_path, scale_factor=4)
        result["fallback"] = True
        result["fallback_reason"] = str(e)
        return result
