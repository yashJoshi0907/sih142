"""
api.py — FastAPI backend for SIH26142
All routes are served under /api so the Vite dev proxy (/api → :8000) works
without any path rewriting. Provides async processing endpoints with DB
persistence and SSE progress streaming.
"""
import asyncio
import json
import os
import shutil
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from database import init_db, SessionLocal, JobRepository, MetricsRepository
from tools import run_super_resolution, compute_metrics, upscale_geotiff, segment_geotiff
from models import MODEL_REGISTRY
from models.bicubic import run_bicubic

# ─── Init ─────────────────────────────────────────────────────────────────────
init_db()
os.makedirs("uploads", exist_ok=True)
os.makedirs("outputs", exist_ok=True)
os.makedirs("static/sample_data", exist_ok=True)

SAMPLE_TILE = "static/sample_data/sample_sentinel2.tif"

executor = ThreadPoolExecutor(max_workers=2)

app = FastAPI(
    title="SIH26142 Satellite SR API",
    description="Super-Resolution Mapping for Sentinel-2 imagery (NTRO, SIH26142)",
    version="3.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── SSE job progress registry ─────────────────────────────────────────────────
# Maps job_id → list of (percent | None, stage, message) dicts pending delivery
_job_events: dict[int, list[dict]] = {}
_job_done: dict[int, bool] = {}


def _emit(job_id: int, percent: Optional[float], stage: str, message: str):
    """Push a progress event into the in-memory queue for SSE consumers."""
    if job_id not in _job_events:
        _job_events[job_id] = []
    _job_events[job_id].append({"percent": percent, "stage": stage, "message": message})


# ─── Background worker ─────────────────────────────────────────────────────────
def _process_job(job_id: int, input_path: str, model_name: str, scale: float):
    db = SessionLocal()
    job_repo = JobRepository(db)
    met_repo = MetricsRepository(db)
    try:
        out_sr  = f"outputs/sr_{job_id}_{model_name.replace(' ', '_')}.tif"
        out_bic = f"outputs/bic_{job_id}.tif"

        job_repo.update_status(job_id, "running")
        _emit(job_id, 5, "running", "Reading Sentinel-2 bands…")

        _emit(job_id, 20, "running", "Normalising radiometry…")
        result = run_super_resolution(input_path, out_sr, model_name=model_name)

        _emit(job_id, 65, "running", "Running bicubic baseline…")
        run_bicubic(input_path, out_bic, scale_factor=int(scale))

        _emit(job_id, 85, "running", "Scoring against control…")
        metrics = compute_metrics(out_sr, out_bic)

        _emit(job_id, 95, "running", "Writing GeoTIFF…")
        job_repo.update_status(job_id, "done", output_path=out_sr)
        met_repo.save(
            job_id=job_id,
            psnr=metrics["psnr"],
            ssim=metrics["ssim"],
            inference_time=result["inference_time_sec"],
            output_res_m=MODEL_REGISTRY.get(model_name, {}).get("output_res_m", 5.0),
        )
        _emit(job_id, 100, "done", "Complete.")
    except Exception as e:
        job_repo.update_status(job_id, "failed", error_msg=str(e))
        _emit(job_id, None, "failed", str(e))
    finally:
        _job_done[job_id] = True
        db.close()


def _ensure_sample_tile():
    """Generate the bundled sample tile on first request if it doesn't exist."""
    if not Path(SAMPLE_TILE).exists():
        try:
            from generate_sample_tile import generate_sample_sentinel2
            generate_sample_sentinel2(SAMPLE_TILE)
        except Exception as exc:
            raise HTTPException(500, f"Could not generate sample tile: {exc}")


# ─── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/", summary="Health check")
def root():
    return {"status": "ok", "service": "SIH26142 SR API", "version": "3.0.0"}


# ── Models ────────────────────────────────────────────────────────────────────

@app.get("/api/models", summary="List available SR models")
def list_models():
    return {
        name: {
            "scale":         info["scale"],
            "output_res_m":  info["output_res_m"],
            "description":   info["description"],
            "physical_bias": info["physical_bias"],
            "paper":         info["paper"],
        }
        for name, info in MODEL_REGISTRY.items()
    }


# ── Process ───────────────────────────────────────────────────────────────────

@app.post("/api/process", summary="Submit a GeoTIFF (or the bundled sample) for SR processing")
async def process(
    background_tasks: BackgroundTasks,
    use_sample: Optional[str] = Form(None, description="Set to 'true' to use the bundled sample tile"),
    file: Optional[UploadFile] = File(None),
    model_name: str = Form("DSen2", description="SR model to use"),
):
    if model_name not in MODEL_REGISTRY:
        raise HTTPException(400, f"Unknown model. Choose from: {list(MODEL_REGISTRY.keys())}")

    # Resolve input path
    if use_sample and use_sample.lower() == "true":
        _ensure_sample_tile()
        input_path = SAMPLE_TILE
        filename   = "sample_sentinel2.tif"
    elif file is not None:
        input_path = f"uploads/{file.filename}"
        filename   = file.filename
        with open(input_path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)
    else:
        raise HTTPException(400, "Provide either use_sample=true or a file upload.")

    # Create DB job
    db = SessionLocal()
    job_repo = JobRepository(db)
    minfo = MODEL_REGISTRY[model_name]
    job = job_repo.create(
        filename=filename,
        sr_model=model_name,
        scale_factor=float(minfo["scale"]),
        input_path=input_path,
    )
    job_id = job.id
    db.close()

    # Seed SSE queue
    _job_events[job_id] = []
    _job_done[job_id] = False
    _emit(job_id, 0, "queued", "Reserving job slot…")

    # Background processing
    background_tasks.add_task(
        _process_job, job_id, input_path, model_name, float(minfo["scale"])
    )

    return {"job_id": job_id, "status": "queued", "model": model_name}


# ── Job status & download ─────────────────────────────────────────────────────

@app.get("/api/job/{job_id}", summary="Poll job status")
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


@app.get("/api/job/{job_id}/download", summary="Download processed GeoTIFF")
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
    return FileResponse(
        job.output_path,
        media_type="image/tiff",
        filename=Path(job.output_path).name,
    )


@app.get("/api/job/{job_id}/thumbnail", summary="Render a PNG thumbnail of input or SR output")
def job_thumbnail(job_id: int, kind: str = Query("sr", description="'input' or 'sr'")):
    """
    Returns a simple PNG preview of the requested raster.
    Uses rasterio + Pillow to create an 8-bit RGB composite from bands 3,2,1.
    Falls back to a 1×1 transparent PNG if the file is missing.
    """
    db = SessionLocal()
    job_repo = JobRepository(db)
    job = job_repo.get(job_id)
    db.close()

    if not job:
        raise HTTPException(404, "Job not found")

    if kind == "input":
        tif_path = job.input_path
    else:
        tif_path = job.output_path

    if not tif_path or not Path(tif_path).exists():
        # Return a transparent 1×1 PNG placeholder
        import base64
        EMPTY = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        return StreamingResponse(iter([EMPTY]), media_type="image/png")

    try:
        import rasterio
        import numpy as np
        from PIL import Image
        import io

        with rasterio.open(tif_path) as src:
            count = src.count
            # Read up to 3 bands for RGB preview (use bands 3,2,1 or whatever exists)
            bands_to_read = list(range(1, min(count, 3) + 1))
            data = src.read(bands_to_read)  # (C, H, W) uint16

        # Normalise to uint8
        def norm(band):
            lo, hi = np.percentile(band, 2), np.percentile(band, 98)
            if hi == lo:
                return np.zeros_like(band, dtype=np.uint8)
            return np.clip((band - lo) / (hi - lo) * 255, 0, 255).astype(np.uint8)

        if data.shape[0] >= 3:
            rgb = np.stack([norm(data[2]), norm(data[1]), norm(data[0])], axis=-1)
        else:
            g = norm(data[0])
            rgb = np.stack([g, g, g], axis=-1)

        # Resize to at most 512px on the long edge
        h, w = rgb.shape[:2]
        scale = min(512 / max(h, w), 1.0)
        nh, nw = int(h * scale), int(w * scale)
        img = Image.fromarray(rgb).resize((nw, nh), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")

    except Exception as exc:
        raise HTTPException(500, f"Thumbnail error: {exc}")


# ── SSE progress stream ───────────────────────────────────────────────────────

@app.get("/api/progress/{job_id}", summary="SSE stream of job progress events")
async def progress_stream(job_id: int):
    """
    Server-Sent Events endpoint. Emits `progress` events while the job runs
    and a final `done` event with the JobStatus payload when it finishes.
    """
    async def event_generator():
        yielded = 0
        deadline = time.time() + 600  # 10-minute timeout

        while time.time() < deadline:
            events = _job_events.get(job_id, [])
            # Yield any new events
            while yielded < len(events):
                ev = events[yielded]
                yielded += 1
                yield f"event: progress\ndata: {json.dumps(ev)}\n\n"

            # Check if job is finished
            if _job_done.get(job_id, False):
                # Send the final job status as the `done` event
                db = SessionLocal()
                job = JobRepository(db).get(job_id)
                db.close()
                if job:
                    payload = {
                        "job_id":       job.id,
                        "status":       job.status,
                        "model":        job.sr_model,
                        "filename":     job.filename,
                        "created_at":   job.created_at.isoformat() if job.created_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                        "error":        job.error_msg,
                    }
                    yield f"event: done\ndata: {json.dumps(payload)}\n\n"
                break

            await asyncio.sleep(0.5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ── Metrics ───────────────────────────────────────────────────────────────────

@app.get("/api/metrics/{job_id}", summary="Get PSNR/SSIM metrics for a job")
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


# ── History ───────────────────────────────────────────────────────────────────

@app.get("/api/history", summary="List all processing jobs")
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


# ─── Entrypoint ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
