"""
api.py — FastAPI backend for SIH26142
Provides async processing endpoints with DB persistence.
"""
import os
import asyncio
import shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from datetime import datetime

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, SessionLocal, JobRepository, MetricsRepository
from tools import run_super_resolution, compute_metrics, upscale_geotiff, segment_geotiff
from models import MODEL_REGISTRY
from models.bicubic import run_bicubic

# ─── Init ─────────────────────────────────────────────────────────────────────
init_db()
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)

executor = ThreadPoolExecutor(max_workers=2)

app = FastAPI(
    title="SIH26142 Satellite SR API",
    description="Super-Resolution Mapping for Sentinel-2 imagery (NTRO, SIH26142)",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Background worker ────────────────────────────────────────────────────────
def _process_job(job_id: int, input_path: str, model_name: str, scale: float):
    db = SessionLocal()
    job_repo = JobRepository(db)
    met_repo = MetricsRepository(db)
    try:
        out_sr  = f"outputs/sr_{job_id}_{model_name.replace(' ', '_')}.tif"
        out_bic = f"outputs/bic_{job_id}.tif"

        job_repo.update_status(job_id, "running")

        result  = run_super_resolution(input_path, out_sr, model_name=model_name)
        run_bicubic(input_path, out_bic, scale_factor=int(scale))
        metrics = compute_metrics(out_sr, out_bic)

        job_repo.update_status(job_id, "done", output_path=out_sr)
        met_repo.save(
            job_id=job_id,
            psnr=metrics["psnr"],
            ssim=metrics["ssim"],
            inference_time=result["inference_time_sec"],
            output_res_m=MODEL_REGISTRY.get(model_name, {}).get("output_res_m", 5.0),
        )
    except Exception as e:
        job_repo.update_status(job_id, "failed", error_msg=str(e))
    finally:
        db.close()


# ─── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/", summary="Health check")
def root():
    return {"status": "ok", "service": "SIH26142 SR API", "version": "2.0.0"}


@app.get("/models", summary="List available SR models")
def list_models():
    return {
        name: {
            "scale": info["scale"],
            "output_res_m": info["output_res_m"],
            "description": info["description"],
            "physical_bias": info["physical_bias"],
            "paper": info["paper"],
        }
        for name, info in MODEL_REGISTRY.items()
    }


@app.post("/process", summary="Submit a GeoTIFF for SR processing")
async def process(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    model_name: str = Form("DSen2", description="SR model to use"),
):
    if model_name not in MODEL_REGISTRY:
        raise HTTPException(400, f"Unknown model. Choose from: {list(MODEL_REGISTRY.keys())}")

    # Save upload
    input_path = f"uploads/{file.filename}"
    with open(input_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    # Create DB job
    db = SessionLocal()
    job_repo = JobRepository(db)
    minfo = MODEL_REGISTRY[model_name]
    job = job_repo.create(
        filename=file.filename,
        sr_model=model_name,
        scale_factor=float(minfo["scale"]),
        input_path=input_path,
    )
    job_id = job.id
    db.close()

    # Background processing
    background_tasks.add_task(
        _process_job, job_id, input_path, model_name, float(minfo["scale"])
    )

    return {"job_id": job_id, "status": "queued", "model": model_name}


@app.get("/job/{job_id}", summary="Poll job status")
def get_job(job_id: int):
    db = SessionLocal()
    job_repo = JobRepository(db)
    job = job_repo.get(job_id)
    db.close()
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "job_id":       job.id,
        "status":       job.status,
        "model":        job.sr_model,
        "filename":     job.filename,
        "created_at":   job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error":        job.error_msg,
    }


@app.get("/job/{job_id}/download", summary="Download processed GeoTIFF")
def download_job(job_id: int):
    db = SessionLocal()
    job_repo = JobRepository(db)
    job = job_repo.get(job_id)
    db.close()
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != "done":
        raise HTTPException(400, f"Job not done yet (status: {job.status})")
    if not job.output_path or not Path(job.output_path).exists():
        raise HTTPException(404, "Output file not found")
    return FileResponse(job.output_path, media_type="image/tiff",
                        filename=Path(job.output_path).name)


@app.get("/metrics/{job_id}", summary="Get PSNR/SSIM metrics for a job")
def get_metrics(job_id: int):
    db = SessionLocal()
    met_repo = MetricsRepository(db)
    m = met_repo.get_by_job(job_id)
    db.close()
    if not m:
        raise HTTPException(404, "Metrics not found for this job")
    return {
        "job_id":              job_id,
        "psnr_vs_bicubic_db":  m.psnr_vs_bicubic,
        "ssim_vs_bicubic":     m.ssim_vs_bicubic,
        "inference_time_sec":  m.inference_time_sec,
        "output_resolution_m": m.output_resolution_m,
        "hallucination_score": m.hallucination_score,
    }


@app.get("/history", summary="List all processing jobs")
def history(limit: int = 50):
    db = SessionLocal()
    job_repo = JobRepository(db)
    jobs = job_repo.list_all(limit=limit)
    db.close()
    return [
        {
            "job_id":     j.id,
            "filename":   j.filename,
            "status":     j.status,
            "model":      j.sr_model,
            "created_at": j.created_at.isoformat() if j.created_at else None,
        }
        for j in jobs
    ]


# ─── Legacy endpoint ──────────────────────────────────────────────────────────
@app.post("/upscale_and_segment", summary="[Legacy] Upscale + segment in one call")
async def upscale_and_segment(
    file: UploadFile = File(...),
    feature_prompt: str = Form("buildings"),
):
    input_path = f"uploads/tmp_{file.filename}"
    with open(input_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    sr_path  = f"outputs/sr_legacy_{file.filename}"
    seg_path = f"outputs/seg_legacy_{file.filename}"

    upscale_geotiff(input_path, sr_path, scale_factor=2)
    segment_geotiff(sr_path, seg_path, feature_prompt)

    return FileResponse(seg_path, media_type="image/tiff", filename=seg_path)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
