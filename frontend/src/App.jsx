import React, { useState, useEffect } from "react";
import { 
  ShieldCheck, 
  Terminal, 
  GitPullRequest, 
  Play, 
  CheckCircle2, 
  XCircle, 
  AlertTriangle, 
  Plus, 
  Activity, 
  Cpu, 
  Clock, 
  DollarSign, 
  FileCode, 
  RefreshCw 
} from "lucide-react";
import "./App.css";

const API_BASE = "http://localhost:8000/api";

export default function App() {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [stats, setStats] = useState({
    total_jobs: 0,
    approved_jobs: 0,
    rejected_jobs: 0,
    pending_review: 0,
    acceptance_rate: 0,
    total_cost_usd: 0,
    avg_security_score: 0
  });
  const [activeTab, setActiveTab] = useState("trajectory"); // trajectory, diff, tests
  const [reviewerNotes, setReviewerNotes] = useState("");
  const [isSeeding, setIsSeeding] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [newJob, setNewJob] = useState({
    repo_name: "Audio Signal Parser",
    repo_path: "sample_repos/audio_transcoder",
    issue_description: "Fix memory boundary violation and prevent raw SQL queries."
  });

  const fetchData = async () => {
    try {
      const [jobsRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/jobs`),
        fetch(`${API_BASE}/stats`)
      ]);
      if (jobsRes.ok) {
        const jobsData = await jobsRes.json();
        setJobs(jobsData);
        if (!selectedJob && jobsData.length > 0) {
          setSelectedJob(jobsData[0]);
        } else if (selectedJob) {
          const updated = jobsData.find((j) => j.id === selectedJob.id);
          if (updated) setSelectedJob(updated);
        }
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
      }
    } catch (err) {
      console.error("Failed to connect to DevSentinel backend:", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, [selectedJob?.id]);

  const handleSeedDemo = async () => {
    setIsSeeding(true);
    try {
      const res = await fetch(`${API_BASE}/demo/seed`, { method: "POST" });
      if (res.ok) {
        const seeded = await res.json();
        setSelectedJob(seeded);
        fetchData();
      }
    } catch (err) {
      console.error("Demo seed error:", err);
    } finally {
      setIsSeeding(false);
    }
  };

  const handleHumanDecision = async (decision) => {
    if (!selectedJob) return;
    try {
      const res = await fetch(`${API_BASE}/jobs/${selectedJob.id}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          decision: decision,
          feedback: reviewerNotes || `Action: ${decision} by Engineering Reviewer`
        })
      });
      if (res.ok) {
        const updated = await res.json();
        setSelectedJob(updated);
        setReviewerNotes("");
        fetchData();
      }
    } catch (err) {
      console.error("Error submitting review:", err);
    }
  };

  const handleCreateJobSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await fetch(`${API_BASE}/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newJob)
      });
      if (res.ok) {
        const created = await res.json();
        setSelectedJob(created);
        setShowModal(false);
        fetchData();
      }
    } catch (err) {
      console.error("Error creating job:", err);
    }
  };

  const renderDiffLines = (diffText) => {
    if (!diffText) return <span style={{ color: "var(--text-muted)" }}>No code changes generated yet.</span>;
    return diffText.split("\n").map((line, idx) => {
      let className = "";
      if (line.startsWith("+") && !line.startsWith("+++")) className = "diff-line-add";
      else if (line.startsWith("-") && !line.startsWith("---")) className = "diff-line-del";
      return (
        <span key={idx} className={className}>
          {line}
          {"\n"}
        </span>
      );
    });
  };

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">DS</div>
          <div>
            <div className="brand-title">DevSentinel</div>
            <div className="brand-subtitle">Autonomous AI Software Engineering & CI/CD Platform</div>
          </div>
        </div>

        <div className="header-actions">
          <button className="btn-secondary" onClick={handleSeedDemo} disabled={isSeeding}>
            <Play size={14} />
            {isSeeding ? "Launching Agent..." : "Run Shure Audio DSP Demo"}
          </button>
          <button className="btn-primary" onClick={() => setShowModal(true)}>
            <Plus size={14} />
            New Audit Task
          </button>
        </div>
      </header>

      {/* Real-Time Metrics Strip */}
      <div className="metrics-bar">
        <div className="metric-item">
          <span className="metric-label">Total Jobs</span>
          <span className="metric-value">{stats.total_jobs}</span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Human Acceptance</span>
          <span className="metric-value" style={{ color: "var(--accent-green)" }}>
            {stats.acceptance_rate}%
          </span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Awaiting Review</span>
          <span className="metric-value" style={{ color: "var(--accent-amber)" }}>
            {stats.pending_review}
          </span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Avg Security Score</span>
          <span className="metric-value" style={{ color: "var(--accent-cyan)" }}>
            {stats.avg_security_score}/100
          </span>
        </div>
        <div className="metric-item">
          <span className="metric-label">Total Token Spend</span>
          <span className="metric-value">${stats.total_cost_usd}</span>
        </div>
      </div>

      {/* Main Split Layout */}
      <div className="main-workspace">
        {/* Left Sidebar: Jobs List */}
        <aside className="jobs-sidebar">
          <div className="sidebar-header">
            <span className="sidebar-title">Audit Pipeline</span>
            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>{jobs.length} tasks</span>
          </div>

          <div className="jobs-list">
            {jobs.length === 0 ? (
              <div style={{ padding: "24px", textAlign: "center", color: "var(--text-muted)", fontSize: "13px" }}>
                No audit tasks yet. Click "Run Shure Audio DSP Demo" above to start an agent run.
              </div>
            ) : (
              jobs.map((j) => (
                <div
                  key={j.id}
                  className={`job-card ${selectedJob?.id === j.id ? "active" : ""}`}
                  onClick={() => setSelectedJob(j)}
                >
                  <div className="job-card-header">
                    <span className="job-repo-name">{j.repo_name}</span>
                    <span className={`status-badge ${j.status}`}>{j.status.replace("_", " ")}</span>
                  </div>
                  <div className="job-desc">{j.issue_description}</div>
                  <div className="job-card-footer">
                    <span>Sec: {j.security_score}/100</span>
                    <span>Cost: ${j.cost_usd}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* Right Main Panel: Human-in-the-Loop Review Workspace */}
        <main className="workspace-content">
          {selectedJob ? (
            <>
              <div className="workspace-header">
                <div className="workspace-title-box">
                  <div className="workspace-title">{selectedJob.repo_name}</div>
                  <div className="workspace-meta">
                    <span>Task ID: {selectedJob.id.slice(0, 8)}</span>
                    <span>•</span>
                    <span>Status: <strong style={{ color: "var(--accent-cyan)" }}>{selectedJob.status}</strong></span>
                    <span>•</span>
                    <span>Runtime: {selectedJob.execution_time_seconds}s</span>
                  </div>
                </div>

                <div style={{ display: "flex", gap: "16px", alignItems: "center" }}>
                  <div className="score-badge">
                    <ShieldCheck size={18} />
                    <span>Security Audit: {selectedJob.security_score}/100</span>
                  </div>
                </div>
              </div>

              {/* Navigation Tabs */}
              <div className="tabs-navigation">
                <button
                  className={`tab-btn ${activeTab === "trajectory" ? "active" : ""}`}
                  onClick={() => setActiveTab("trajectory")}
                >
                  <Activity size={15} />
                  Agent Trajectory ({selectedJob.trajectory?.length || 0} Steps)
                </button>
                <button
                  className={`tab-btn ${activeTab === "diff" ? "active" : ""}`}
                  onClick={() => setActiveTab("diff")}
                >
                  <GitPullRequest size={15} />
                  Proposed Git Diff
                </button>
                <button
                  className={`tab-btn ${activeTab === "tests" ? "active" : ""}`}
                  onClick={() => setActiveTab("tests")}
                >
                  <Terminal size={15} />
                  Sandbox Verification Logs
                </button>
              </div>

              {/* Tab Contents */}
              <div className="tab-content">
                {activeTab === "trajectory" && (
                  <div className="timeline">
                    {selectedJob.trajectory?.length === 0 ? (
                      <div style={{ color: "var(--text-muted)" }}>Agent execution initializing...</div>
                    ) : (
                      selectedJob.trajectory.map((step, idx) => (
                        <div key={idx} className="timeline-step">
                          <div className="step-marker">
                            <div className="step-circle">{step.step_index}</div>
                            {idx < selectedJob.trajectory.length - 1 && <div className="step-line" />}
                          </div>
                          <div className="step-card">
                            <div className="step-header">
                              <span className="step-stage">{step.stage}</span>
                              <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                                Action: {step.action}
                              </span>
                            </div>
                            <div className="step-thought">{step.thought}</div>
                            <div className="code-box">{step.observation}</div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                )}

                {activeTab === "diff" && (
                  <div>
                    <div style={{ marginBottom: "12px", fontSize: "13px", color: "var(--text-secondary)" }}>
                      Unified patch ready for developer verification:
                    </div>
                    <pre className="diff-container">{renderDiffLines(selectedJob.patch_diff)}</pre>
                  </div>
                )}

                {activeTab === "tests" && (
                  <div>
                    <div style={{ marginBottom: "12px", fontSize: "13px", color: "var(--text-secondary)" }}>
                      Isolated Pytest Sandbox Output:
                    </div>
                    <div className="code-box" style={{ minHeight: "220px", color: "#4ade80" }}>
                      {selectedJob.test_output || "Running tests inside sandbox..."}
                    </div>
                  </div>
                )}
              </div>

              {/* Human-in-the-Loop Decision Drawer (Matches Shure JD) */}
              <footer className="human-decision-bar">
                <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "12px" }}>
                  <ShieldCheck size={20} color="var(--accent-cyan)" />
                  <input
                    type="text"
                    style={{ flex: 1 }}
                    placeholder="Enter human code reviewer feedback or approval notes..."
                    value={reviewerNotes}
                    onChange={(e) => setReviewerNotes(e.target.value)}
                  />
                </div>

                <div className="decision-actions">
                  <button className="btn-approve" onClick={() => handleHumanDecision("APPROVED")}>
                    <CheckCircle2 size={16} />
                    Approve & Merge
                  </button>
                  <button className="btn-revise" onClick={() => handleHumanDecision("REVISION_REQUESTED")}>
                    <AlertTriangle size={16} />
                    Request Revision
                  </button>
                  <button className="btn-reject" onClick={() => handleHumanDecision("REJECTED")}>
                    <XCircle size={16} />
                    Reject
                  </button>
                </div>
              </footer>
            </>
          ) : (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", color: "var(--text-muted)" }}>
              Select a task from the left pipeline or click "Run Shure Audio DSP Demo".
            </div>
          )}
        </main>
      </div>

      {/* New Task Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: "18px", fontWeight: 700 }}>Dispatch New AI Audit Task</h3>
            <form onSubmit={handleCreateJobSubmit} style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Repository Name
                </label>
                <input
                  style={{ width: "100%" }}
                  value={newJob.repo_name}
                  onChange={(e) => setNewJob({ ...newJob, repo_name: e.target.value })}
                  required
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Repository Path
                </label>
                <input
                  style={{ width: "100%" }}
                  value={newJob.repo_path}
                  onChange={(e) => setNewJob({ ...newJob, repo_path: e.target.value })}
                  required
                />
              </div>
              <div>
                <label style={{ display: "block", fontSize: "12px", color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Issue Description & Requirements
                </label>
                <textarea
                  style={{ width: "100%", minHeight: "80px" }}
                  value={newJob.issue_description}
                  onChange={(e) => setNewJob({ ...newJob, issue_description: e.target.value })}
                  required
                />
              </div>
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "12px", marginTop: "12px" }}>
                <button type="button" className="btn-secondary" onClick={() => setShowModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary">
                  Dispatch Agent
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
