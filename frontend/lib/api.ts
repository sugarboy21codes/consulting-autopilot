/**
 * API client for the Consulting Autopilot FastAPI backend.
 *
 * Handles job submission, polling, and retrieval.
 * Points to localhost:8001 in development, production URL when deployed.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8001";

export interface DiagnosticJob {
  job_id: string;
  status: "queued" | "running" | "complete" | "failed";
  company_url: string;
  problem_statement: string;
  created_at: string;
  completed_at: string | null;
  brief_path: string | null;
  brief_content: string | null;
  error: string | null;
}

export interface DiagnosticRequest {
  company_url: string;
  problem_statement: string;
}

/**
 * Submit a new diagnostic job.
 * Returns immediately with a job ID. The diagnostic runs in the background.
 */
export async function submitDiagnostic(
  request: DiagnosticRequest
): Promise<DiagnosticJob> {
  const res = await fetch(`${API_BASE}/diagnostics`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "ngrok-skip-browser-warning": "true" },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    throw new Error(`Failed to submit diagnostic: ${res.statusText}`);
  }

  return res.json();
}

/**
 * Get a specific diagnostic job by ID.
 */
export async function getDiagnostic(jobId: string): Promise<DiagnosticJob> {
  const res = await fetch(`${API_BASE}/diagnostics/${jobId}`, {
    headers: { "ngrok-skip-browser-warning": "true" },
  });

  if (!res.ok) {
    throw new Error(`Failed to get diagnostic: ${res.statusText}`);
  }

  return res.json();
}

/**
 * List all diagnostic jobs, most recent first.
 */
export async function listDiagnostics(): Promise<DiagnosticJob[]> {
  const res = await fetch(`${API_BASE}/diagnostics`, {
    headers: { "ngrok-skip-browser-warning": "true" },
  });

  if (!res.ok) {
    throw new Error(`Failed to list diagnostics: ${res.statusText}`);
  }

  return res.json();
}

/**
 * Poll a job until it completes or fails.
 * Calls onUpdate with each status change.
 */
export async function pollDiagnostic(
  jobId: string,
  onUpdate: (job: DiagnosticJob) => void,
  intervalMs: number = 3000
): Promise<DiagnosticJob> {
  return new Promise((resolve, reject) => {
    const poll = async () => {
      try {
        const job = await getDiagnostic(jobId);
        onUpdate(job);

        if (job.status === "complete") {
          resolve(job);
        } else if (job.status === "failed") {
          reject(new Error(job.error || "Diagnostic failed"));
        } else {
          setTimeout(poll, intervalMs);
        }
      } catch (err) {
        reject(err);
      }
    };

    poll();
  });
}

/**
 * Check if the API server is healthy.
 */
export async function healthCheck(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE}/health`, {
      headers: { "ngrok-skip-browser-warning": "true" },
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function downloadPdf(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/diagnostics/${jobId}/pdf`, {
    headers: {
      "ngrok-skip-browser-warning": "true",
    },
  });

  if (!response.ok) {
    throw new Error(`PDF download failed: ${response.statusText}`);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `diagnostic_brief_${jobId}.pdf`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}