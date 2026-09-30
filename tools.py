"""
tools.py — Unified SR engine + metrics computation for SIH26142
Handles: band extraction, model dispatch, PSNR/SSIM computation,
         segmentation (LangSAM), and GeoTIFF I/O.
"""
import os
import time
import numpy as np
import rasterio
from rasterio.enums import Resampling
from pathlib import Path
from typing import Optional


# ─── SR Dispatch ──────────────────────────────────────────────────────────────

def run_super_resolution(input_path: str, output_path: str,
                         model_name: str = "DSen2") -> dict:
    """
    Dispatch to the selected satellite-specific SR model.
    Returns result dict from the model wrapper.
    """
    from models import MODEL_REGISTRY
    from models.bicubic import run_bicubic

    entry = MODEL_REGISTRY.get(model_name)
    if entry is None:
        print(f"[tools] Unknown model '{model_name}', using Bicubic.")
        return run_bicubic(input_path, output_path)

    fn     = entry["fn"]
    scale  = entry["scale"]

    try:
        if model_name == "Bicubic Baseline":
            return fn(input_path, output_path, scale_factor=scale)
        else:
            return fn(input_path, output_path)
    except Exception as e:
        print(f"[tools] {model_name} raised {e}, falling back to bicubic.")
        result = run_bicubic(input_path, output_path, scale_factor=scale)
        result["fallback"] = True
        result["fallback_reason"] = str(e)
        return result


# ─── Metrics ──────────────────────────────────────────────────────────────────

def compute_metrics(sr_path: str, bicubic_path: str) -> dict:
    """
    Compute PSNR and SSIM between SR output and bicubic reference.
    Both are compared at the same resolution (SR output resolution).
    Returns: {"psnr": float, "ssim": float}
    """
    try:
        from skimage.metrics import peak_signal_noise_ratio, structural_similarity

        with rasterio.open(sr_path) as sr_src:
            sr_data = sr_src.read().astype(np.float32)

        with rasterio.open(bicubic_path) as bic_src:
            bic_data = bic_src.read(
                out_shape=(sr_data.shape[0], sr_data.shape[1], sr_data.shape[2]),
                resampling=Resampling.cubic,
            ).astype(np.float32)

        # Normalise to [0, 1]
        sr_norm  = sr_data  / sr_data.max()  if sr_data.max()  > 0 else sr_data
        bic_norm = bic_data / bic_data.max() if bic_data.max() > 0 else bic_data

        # Use first 3 bands for perceptual metrics
        sr_rgb  = np.moveaxis(sr_norm[:3],  0, -1)
        bic_rgb = np.moveaxis(bic_norm[:3], 0, -1)

        psnr = peak_signal_noise_ratio(bic_rgb, sr_rgb, data_range=1.0)
        ssim = structural_similarity(
            bic_rgb, sr_rgb,
            multichannel=True, data_range=1.0, channel_axis=-1
        )
        return {"psnr": round(float(psnr), 2), "ssim": round(float(ssim), 4)}

    except Exception as e:
        print(f"[tools] Metrics computation failed: {e}")
        return {"psnr": None, "ssim": None}


# ─── Legacy helpers (kept for API backward compatibility) ─────────────────────

def upscale_geotiff(input_path: str, output_path: str,
                    scale_factor: int = 2) -> str:
    """Legacy wrapper — delegates to bicubic baseline."""
    from models.bicubic import run_bicubic
    run_bicubic(input_path, output_path, scale_factor=scale_factor)
    return output_path


def segment_geotiff(input_path: str, output_path: str,
                    text_prompt: str) -> str:
    """
    Sub-pixel segmentation via LangSAM (segment-geospatial).
    Falls back to a copy of the input if LangSAM is unavailable.
    """
    try:
        from samgeo import LangSAM
        sam = LangSAM()
        sam.predict(input_path, text_prompt,
                    box_threshold=0.24, text_threshold=0.24)
        sam.show_anns(
            cmap="Greens", box_color="red",
            title="Segmentation Results", blend=True,
            output=output_path,
        )
    except ImportError as e:
        print(f"[tools] LangSAM unavailable ({e}). Copying input as fallback.")
        import shutil
        shutil.copy(input_path, output_path)
    return output_path


# ─── Thumbnail helper for Streamlit display ───────────────────────────────────

def geotiff_to_png(tif_path: str, png_path: str,
                   bands: tuple = (1, 2, 3)) -> Optional[str]:
    """
    Extract selected bands from a GeoTIFF and save as a PNG for display.
    Returns png_path on success, None on failure.
    """
    try:
        from PIL import Image

        with rasterio.open(tif_path) as src:
            available = src.count
            read_bands = [b for b in bands if b <= available]
            if not read_bands:
                read_bands = [1]

            data = src.read(read_bands).astype(np.float32)

        # Percentile stretch to [0, 255]
        p2, p98 = np.percentile(data, 2), np.percentile(data, 98)
        if p98 > p2:
            data = np.clip((data - p2) / (p98 - p2), 0, 1)
        else:
            data = data / (data.max() + 1e-8)

        data = (data * 255).astype(np.uint8)

        if data.shape[0] == 1:
            img = Image.fromarray(data[0], mode="L").convert("RGB")
        elif data.shape[0] >= 3:
            img = Image.fromarray(np.moveaxis(data[:3], 0, -1), mode="RGB")
        else:
            img = Image.fromarray(data[0], mode="L").convert("RGB")

        img.save(png_path)
        return png_path

    except Exception as e:
        print(f"[tools] geotiff_to_png failed: {e}")
        return None
