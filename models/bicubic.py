"""
models/bicubic.py — Bicubic resampling baseline
Physical-Logical trade-off: Fully Physical (zero hallucination).
Used as:
  1. Always-available fallback for other models
  2. Reference image for PSNR/SSIM computation
  3. Stand-alone "Bicubic Baseline" model selection
"""
import time
import numpy as np
import rasterio
from rasterio.enums import Resampling


def run_bicubic(input_path: str, output_path: str, scale_factor: int = 2) -> dict:
    """
    Bicubic resampling of a GeoTIFF with full CRS/transform preservation.
    Args:
        input_path:    Input GeoTIFF path
        output_path:   Output GeoTIFF path
        scale_factor:  Integer upscale factor (default 2 → 10m→5m)
    Returns:
        dict with output metadata
    """
    start = time.time()

    with rasterio.open(input_path) as src:
        new_h = int(src.height * scale_factor)
        new_w = int(src.width  * scale_factor)

        data = src.read(
            out_shape=(src.count, new_h, new_w),
            resampling=Resampling.cubic,
        )

        new_transform = src.transform * src.transform.scale(
            (src.width  / new_w),
            (src.height / new_h),
        )

        profile = src.profile.copy()
        profile.update({
            "height":    new_h,
            "width":     new_w,
            "transform": new_transform,
        })

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(data)

    elapsed = time.time() - start
    return {
        "output_path":        output_path,
        "uncertainty_path":   None,
        "inference_time_sec": elapsed,
        "scale":              scale_factor,
        "model":              "Bicubic",
        "fallback":           False,
    }
