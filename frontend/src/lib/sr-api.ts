/**
 * Client for the SR ground-segment API.
 *
 * The backend is the FastAPI service at /api (proxied to :8000 in dev).
 * Every function degrades gracefully: the console renders fine with the
 * backend down, it just shows honest empty states.
 */

export interface ModelInfo {
  name: string;
  scale: number;
  output_res_m: number;
  description: string;
  physical_bias: string;
  paper: string;
}

export interface JobStatus {
  job_id: number;
  status: "queued" | "running" | "done" | "failed";
  model: string;
  filename: string;
  created_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface JobMetrics {
  job_id: number;
  psnr_vs_bicubic_db: number | null;
  ssim_vs_bicubic: number | null;
  inference_time_sec: number | null;
  output_resolution_m: number | null;
  hallucination_score: number | null;
}

export interface HistoryEntry {
  job_id: number;
  filename: string;
  status: string;
  model: string;
  created_at: string | null;
}

export interface ProgressEvent {
  /** 0..100, or null when the stage is indeterminate. */
  percent: number | null;
  stage: string;
  message: string;
}

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `Request failed (${res.status})`;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") message = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(message, res.status);
  }
  return (await res.json()) as T;
}

export async function fetchModels(): Promise<ModelInfo[]> {
  const raw = await fetch("/api/models").then((r) =>
    unwrap<Record<string, Omit<ModelInfo, "name">>>(r),
  );
  return Object.entries(raw).map(([name, info]) => ({ name, ...info }));
}

export async function submitSampleJob(modelName: string): Promise<{ job_id: number }> {
  const form = new FormData();
  form.set("use_sample", "true");
  form.set("model_name", modelName);
  return unwrap<{ job_id: number }>(await fetch("/api/process", { method: "POST", body: form }));
}

export async function submitFileJob(file: File, modelName: string): Promise<{ job_id: number }> {
  const form = new FormData();
  form.set("file", file);
  form.set("model_name", modelName);
  return unwrap<{ job_id: number }>(await fetch("/api/process", { method: "POST", body: form }));
}

export async function fetchJob(jobId: number): Promise<JobStatus> {
  return unwrap<JobStatus>(await fetch(`/api/job/${jobId}`));
}

export async function fetchMetrics(jobId: number): Promise<JobMetrics> {
  return unwrap<JobMetrics>(await fetch(`/api/metrics/${jobId}`));
}

export async function fetchHistory(limit = 50): Promise<HistoryEntry[]> {
  return unwrap<HistoryEntry[]>(await fetch(`/api/history?limit=${limit}`));
}

export function downloadUrl(jobId: number): string {
  return `/api/job/${jobId}/download`;
}

/**
 * Streams a job's progress over SSE, falling back to polling the status
 * endpoint if the stream errors before completion. `onEvent` fires per
 * progress tick; the promise resolves with the final job status.
 */
export function streamJob(jobId: number, onEvent: (e: ProgressEvent) => void): Promise<JobStatus> {
  return new Promise((resolve, reject) => {
    const es = new EventSource(`/api/progress/${jobId}`);
    let settled = false;

    const cleanup = () => {
      es.close();
    };

    es.addEventListener("progress", (ev) => {
      try {
        onEvent(JSON.parse((ev as MessageEvent<string>).data) as ProgressEvent);
      } catch {
        /* malformed tick — ignore, next tick or status will recover */
      }
    });

    es.addEventListener("done", (ev) => {
      settled = true;
      cleanup();
      try {
        resolve(JSON.parse((ev as MessageEvent<string>).data) as JobStatus);
      } catch {
        resolve(fetchJob(jobId));
      }
    });

    es.onerror = () => {
      if (settled) return;
      cleanup();
      // Stream died (proxy hiccup, backend restart). Poll to completion
      // rather than leaving the console hanging on a dead connection.
      pollJob(jobId, onEvent).then(resolve).catch(reject);
    };
  });
}

async function pollJob(jobId: number, onEvent: (e: ProgressEvent) => void): Promise<JobStatus> {
  for (;;) {
    const job = await fetchJob(jobId).catch(() => null);
    if (!job) throw new ApiError("Lost contact with the job", 503);
    if (job.status === "running") {
      onEvent({ percent: null, stage: "processing", message: "Model running…" });
    }
    if (job.status === "done" || job.status === "failed") return job;
    await new Promise((r) => setTimeout(r, 2000));
  }
}
