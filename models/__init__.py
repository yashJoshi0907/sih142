"""
models/__init__.py
Model registry for satellite-specific super-resolution.
"""
from .ldsr_s2 import run_ldsr_s2
from .dsen2 import run_dsen2
from .bicubic import run_bicubic

MODEL_REGISTRY = {
    "LDSR-S2 (ESA)": {
        "fn": run_ldsr_s2,
        "scale": 4,
        "output_res_m": 2.5,
        "description": "ESA's Latent Diffusion SR for Sentinel-2. Best quality, includes uncertainty maps.",
        "physical_bias": "Balanced",
        "paper": "ESAOpenSR (2024)",
    },
    "DSen2": {
        "fn": run_dsen2,
        "scale": 2,
        "output_res_m": 5.0,
        "description": "Deep Sentinel-2 SR (ISPRS 2020). Physics-first, radiometrically consistent.",
        "physical_bias": "Physical",
        "paper": "Lanaras et al. ISPRS 2020",
    },
    "Bicubic Baseline": {
        "fn": run_bicubic,
        "scale": 2,
        "output_res_m": 5.0,
        "description": "Classical bicubic resampling. Always available, zero hallucination.",
        "physical_bias": "Physical",
        "paper": "Classical",
    },
}
