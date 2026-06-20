"use client";

import { useState, useEffect, useCallback } from "react";
import {
  submitDiagnostic,
  listDiagnostics,
  pollDiagnostic,
  healthCheck,
  DiagnosticJob,
} from "@/lib/api";

/**
 * Status badge colors and labels
 */
function StatusBadge({ status }: { status: DiagnosticJob["status"] }) {
  const config = {
    queued: { bg: "bg-yellow-100 text-yellow-800", label: "Queued" },
    running: { bg: "bg-blue-100 text-blue-800", label: "Running..." },
    complete: { bg: "bg-green-100 text-green-800", label: "Complete" },
    failed: { bg: "bg-red-100 text-red-800", label: "Failed" },
  };

  const { bg, label } = config[status] || config.queued;

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${bg}`}>
      {status === "running" && (
        <span className="mr-1.5 h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
      )}
      {label}
    </span>
  );
}

/**
 * Form for submitting a new diagnostic
 */
function DiagnosticForm({ onSubmit, isSubmitting }: {
  onSubmit: (url: string, problem: string) => void;
  isSubmitting: boolean;
}) {
  const [url, setUrl] = useState("");
  const [problem, setProblem] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim() && problem.trim()) {
      onSubmit(url.trim(), problem.trim());
      setUrl("");
      setProblem("");
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        New Diagnostic
      </h2>
      <div className="space-y-4">
        <div>
          <label htmlFor="url" className="block text-sm font-medium text-gray-700 mb-1">
            Company URL
          </label>
          <input
            id="url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com"
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-gray-900 text-sm"
            disabled={isSubmitting}
          />
        </div>
        <div>
          <label htmlFor="problem" className="block text-sm font-medium text-gray-700 mb-1">
            Problem Statement
          </label>
          <textarea
            id="problem"
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
            placeholder="Describe the challenge this company is facing..."
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-gray-900 text-sm"
            disabled={isSubmitting}
          />
        </div>
        <button
          onClick={handleSubmit}
          disabled={isSubmitting || !url.trim() || !problem.trim()}
          className="w-full bg-gray-900 text-white py-2.5 px-4 rounded-md text-sm font-medium hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isSubmitting ? "Submitting..." : "Generate Diagnostic Brief"}
        </button>
      </div>
    </div>
  );
}

/**
 * List of diagnostic jobs
 */
function JobList({ jobs, selectedId, onSelect }: {
  jobs: DiagnosticJob[];
  selectedId: string | null;
  onSelect: (job: DiagnosticJob) => void;
}) {
  if (jobs.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">
          Diagnostics
        </h2>
        <p className="text-sm text-gray-500">
          No diagnostics yet. Submit one above to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">
          Diagnostics ({jobs.length})
        </h2>
      </div>
      <ul className="divide-y divide-gray-200">
        {jobs.map((job) => {
          const companyName = job.company_url
            .replace("https://", "")
            .replace("http://", "")
            .split("/")[0];
          const isSelected = job.job_id === selectedId;

          return (
            <li
              key={job.job_id}
              onClick={() => onSelect(job)}
              className={`p-4 cursor-pointer transition-colors ${
                isSelected
                  ? "bg-gray-50 border-l-2 border-gray-900"
                  : "hover:bg-gray-50 border-l-2 border-transparent"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm font-medium text-gray-900">
                  {companyName}
                </span>
                <StatusBadge status={job.status} />
              </div>
              <p className="text-xs text-gray-500 truncate">
                {job.problem_statement}
              </p>
              <p className="text-xs text-gray-400 mt-1">
                {new Date(job.created_at).toLocaleString()}
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/**
 * Brief viewer for completed diagnostics
 */
function BriefViewer({ job }: { job: DiagnosticJob | null }) {
  if (!job) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 flex items-center justify-center min-h-[400px]">
        <p className="text-sm text-gray-400">
          Select a diagnostic to view its brief
        </p>
      </div>
    );
  }

  if (job.status === "queued" || job.status === "running") {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8 flex flex-col items-center justify-center min-h-[400px]">
        <div className="h-8 w-8 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin mb-4" />
        <p className="text-sm text-gray-600 font-medium">
          {job.status === "queued"
            ? "Diagnostic queued, waiting to start..."
            : "Agents are researching and analyzing..."}
        </p>
        <p className="text-xs text-gray-400 mt-2">
          This typically takes 2-5 minutes
        </p>
      </div>
    );
  }

  if (job.status === "failed") {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <h3 className="text-sm font-medium text-red-800">
            Diagnostic Failed
          </h3>
          <p className="text-sm text-red-700 mt-1">
            {job.error || "An unknown error occurred."}
          </p>
        </div>
      </div>
    );
  }

  const handleDownload = () => {
    if (!job.brief_content) return;

    const blob = new Blob([job.brief_content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const companyName = job.company_url
      .replace("https://", "")
      .replace("http://", "")
      .split("/")[0];
    a.href = url;
    a.download = `diagnostic_brief_${companyName}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Diagnostic Brief
          </h2>
          <p className="text-xs text-gray-500 mt-0.5">
            Completed {job.completed_at ? new Date(job.completed_at).toLocaleString() : ""}
          </p>
        </div>
        <button
          onClick={handleDownload}
          className="inline-flex items-center px-3 py-1.5 bg-gray-900 text-white text-sm font-medium rounded-md hover:bg-gray-800 transition-colors"
        >
          Download .md
        </button>
      </div>
      <div className="p-6 prose prose-sm max-w-none overflow-auto max-h-[600px]">
        <pre className="whitespace-pre-wrap font-sans text-sm text-gray-800 leading-relaxed">
          {job.brief_content || "No content available."}
        </pre>
      </div>
    </div>
  );
}

/**
 * Main dashboard page
 */
export default function Dashboard() {
  const [jobs, setJobs] = useState<DiagnosticJob[]>([]);
  const [selectedJob, setSelectedJob] = useState<DiagnosticJob | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [apiConnected, setApiConnected] = useState<boolean | null>(null);

  // Check API health on mount
  useEffect(() => {
    healthCheck().then(setApiConnected);
  }, []);

  // Load existing jobs on mount
  useEffect(() => {
    listDiagnostics()
      .then(setJobs)
      .catch(() => setJobs([]));
  }, []);

  // Refresh job list periodically if any jobs are running
  useEffect(() => {
    const hasActiveJobs = jobs.some(
      (j) => j.status === "queued" || j.status === "running"
    );

    if (!hasActiveJobs) return;

    const interval = setInterval(async () => {
      try {
        const updated = await listDiagnostics();
        setJobs(updated);

        // Update selected job if it changed
        if (selectedJob) {
          const updatedSelected = updated.find(
            (j) => j.job_id === selectedJob.job_id
          );
          if (updatedSelected) {
            setSelectedJob(updatedSelected);
          }
        }
      } catch {
        // Silently fail on poll errors
      }
    }, 3000);

    return () => clearInterval(interval);
  }, [jobs, selectedJob]);

  const handleSubmit = useCallback(
    async (url: string, problem: string) => {
      setIsSubmitting(true);
      try {
        const job = await submitDiagnostic({
          company_url: url,
          problem_statement: problem,
        });

        setJobs((prev) => [job, ...prev]);
        setSelectedJob(job);

        // Start polling this job
        pollDiagnostic(job.job_id, (updated) => {
          setJobs((prev) =>
            prev.map((j) => (j.job_id === updated.job_id ? updated : j))
          );
          setSelectedJob((prev) =>
            prev?.job_id === updated.job_id ? updated : prev
          );
        }).catch(() => {
          // Poll failure handled via status update
        });
      } catch (err) {
        console.error("Submit failed:", err);
      } finally {
        setIsSubmitting(false);
      }
    },
    []
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">
                Consulting Autopilot
              </h1>
              <p className="text-sm text-gray-500">
                by King Makers
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <span
                className={`h-2 w-2 rounded-full ${
                  apiConnected === true
                    ? "bg-green-500"
                    : apiConnected === false
                    ? "bg-red-500"
                    : "bg-yellow-500"
                }`}
              />
              <span className="text-xs text-gray-500">
                {apiConnected === true
                  ? "API Connected"
                  : apiConnected === false
                  ? "API Offline"
                  : "Checking..."}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* API Offline Warning */}
      {apiConnected === false && (
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 mt-4">
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-sm text-red-800">
              The API server is not running. Start it with:{" "}
              <code className="bg-red-100 px-1.5 py-0.5 rounded text-xs">
                uvicorn api:app --reload --port 8001
              </code>
            </p>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Form + Job List */}
          <div className="lg:col-span-4 space-y-6">
            <DiagnosticForm
              onSubmit={handleSubmit}
              isSubmitting={isSubmitting}
            />
            <JobList
              jobs={jobs}
              selectedId={selectedJob?.job_id || null}
              onSelect={setSelectedJob}
            />
          </div>

          {/* Right Column: Brief Viewer */}
          <div className="lg:col-span-8">
            <BriefViewer job={selectedJob} />
          </div>
        </div>
      </main>
    </div>
  );
}
