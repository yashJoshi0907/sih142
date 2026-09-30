"""
generate_sample_tile.py
Creates a synthetic Sentinel-2-like GeoTIFF for demonstration purposes.
Simulates a 4-band (B02, B03, B04, B08) scene with realistic value ranges.
Run once: python generate_sample_tile.py
"""
import numpy as np
import rasterio
from rasterio.transform import from_bounds
from rasterio.crs import CRS
from pathlib import Path
import os

def generate_sample_sentinel2(output_path: str = "static/sample_data/sample_sentinel2.tif",
                               size: int = 512):
    """Generate a realistic synthetic Sentinel-2 4-band tile."""
    os.makedirs(Path(output_path).parent, exist_ok=True)
    rng = np.random.default_rng(42)

    # Simulate a mixed scene: urban + vegetation + water bodies
    # All values in S2 uint16 range (0–10000 reflectance units)
    bands = []

    # Create terrain base with coherent spatial structure
    x = np.linspace(0, 4 * np.pi, size)
    y = np.linspace(0, 4 * np.pi, size)
    xx, yy = np.meshgrid(x, y)
    terrain = (np.sin(xx) * np.cos(yy) + 1) / 2  # [0, 1]

    # Add multi-scale texture (simulates urban + vegetation patchwork)
    from scipy.ndimage import gaussian_filter
    noise1 = rng.random((size, size))
    noise2 = rng.random((size, size))
    texture_fine   = gaussian_filter(noise1, sigma=3)
    texture_coarse = gaussian_filter(noise2, sigma=20)
    base = (terrain * 0.4 + texture_coarse * 0.4 + texture_fine * 0.2)

    # Simulate water body (low reflectance in all bands)
    water_mask = (xx > 2 * np.pi) & (xx < 3 * np.pi) & (yy > np.pi) & (yy < 2 * np.pi)

    # B02 (Blue): urban=500-2000, veg=300-800, water=200-600
    b02 = (base * 1500 + 400).astype(np.float32)
    b02[water_mask] = (rng.random(water_mask.sum()) * 400 + 200).astype(np.float32)
    bands.append(np.clip(b02, 0, 10000).astype(np.uint16))

    # B03 (Green): slightly higher than blue for vegetation
    b03 = (base * 1800 + 500).astype(np.float32)
    b03[water_mask] = (rng.random(water_mask.sum()) * 350 + 150).astype(np.float32)
    bands.append(np.clip(b03, 0, 10000).astype(np.uint16))

    # B04 (Red): urban high, vegetation lower
    b04 = (base * 2000 + 300).astype(np.float32)
    b04[water_mask] = (rng.random(water_mask.sum()) * 200 + 100).astype(np.float32)
    bands.append(np.clip(b04, 0, 10000).astype(np.uint16))

    # B08 (NIR): vegetation very high, urban medium, water very low
    b08 = (base * 3500 + 800).astype(np.float32)
    # Boost vegetation areas (NIR signature)
    veg_mask = base > 0.6
    b08[veg_mask] = (base[veg_mask] * 5000 + 2000).astype(np.float32)
    b08[water_mask] = (rng.random(water_mask.sum()) * 150 + 50).astype(np.float32)
    bands.append(np.clip(b08, 0, 10000).astype(np.uint16))

    data = np.stack(bands, axis=0)  # (4, H, W)

    # Geographic transform: 10m pixels over a small region in India (approx NTRO region)
    pixel_size_deg = 10 / 111320  # 10m in degrees
    west, south = 77.0, 28.5     # New Delhi area
    east  = west  + size * pixel_size_deg
    north = south + size * pixel_size_deg

    transform = from_bounds(west, south, east, north, size, size)
    crs = CRS.from_epsg(4326)

    profile = {
        "driver":    "GTiff",
        "dtype":     "uint16",
        "width":     size,
        "height":    size,
        "count":     4,
        "crs":       crs,
        "transform": transform,
        "compress":  "lzw",
    }

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(data)
        dst.update_tags(
            DESCRIPTION="Synthetic Sentinel-2 demo tile (B02/B03/B04/B08)",
            PIXEL_SIZE_M="10",
            SCENE="Synthetic urban+vegetation+water, Delhi region",
        )

    print(f"[OK] Sample tile created: {output_path} ({size}x{size}px, 4 bands, 10m resolution)")
    return output_path


if __name__ == "__main__":
    try:
        from scipy.ndimage import gaussian_filter
        generate_sample_sentinel2()
    except ImportError:
        print("scipy not installed. Run: pip install scipy")
