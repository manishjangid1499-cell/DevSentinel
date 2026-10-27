<div align="center">

# 🛡️ DevSentinel
### Autonomous AI Software Engineering &amp; CI/CD Review Platform with Human-in-the-Loop Controls

[![CI Pipeline](https://img.shields.io/badge/CI-GitHub_Actions-brightgreen?logo=github-actions&style=for-the-badge)](.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&style=for-the-badge)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688?logo=fastapi&style=for-the-badge)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&style=for-the-badge)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&style=for-the-badge)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br/>

<p align="center">
  <strong>An end-to-end AI software engineering agent that diagnoses repository issues, synthesizes reproduction unit tests, applies surgical code patches in an isolated candidate staging workspace, and enforces strict Human-in-the-Loop (HITL) developer review before touching the working tree.</strong>
</p>

---

### 🖥️ Live Platform Dashboard Preview

<img src="docs/assets/dashboard-preview.svg" alt="DevSentinel Platform Dashboard" width="100%"/>

</div>

---

## 📌 Executive Summary

Modern AI code generation models frequently hallucinate syntax errors, miss subtle edge cases, or introduce security regressions because they lack runtime execution feedback.

**DevSentinel** bridges the gap between raw LLMs and production engineering standards:
1. **Isolated Candidate Staging (Working Tree Protection)**: Candidate patches and reproduction tests are generated and executed strictly within a temporary staging copy of the repository. The original working tree and production branch remain **100% untouched** until an engineer explicitly clicks **Approve & Merge**.
2. **Ground-Truth Process Exit Code Verification**: DevSentinel never substitutes invented pass counts or strings. It requires the synthesized reproduction test to fail initially (asserting non-zero exit code), and after patching, requires the entire test suite to pass with process exit code 0.
3. **Environment Sanitization & Process-Tree Isolation**: Controlled runner strips host API keys, cloud credentials, and sensitive environment variables (`OPENAI_*`, `GEMINI_*`, `AWS_*`, `TOKEN`) before executing child test processes, with cross-platform tree termination (`taskkill /F /T` on Windows, `killpg` on POSIX).
4. **Path Traversal Containment**: Every target path from model generation is canonicalized and verified against the workspace root, rejecting `../` directory escapes.

---

## 🏗️ System Architecture

```mermaid
flowchart TD
    subgraph Client ["Frontend Presentation Layer"]
        UI["React 19 Dashboard<br/>(Vite + Tailwind CSS + Lucide)"]
        HITL["Human-in-the-Loop Review Bar<br/>(Approve / Reject / Revise)"]
    end

    subgraph Server ["FastAPI Backend Services"]
        API["REST API Router<br/>(/api/jobs, /api/stats, /api/demo)"]
        DB[(SQLAlchemy ORM<br/>SQLite / PostgreSQL)]
    end

    subgraph Agent ["Agentic AI Core Engine"]
        Engine["DevSentinel Multi-Stage Agent"]
        LLM["LLM Gateway<br/>(OpenAI / Gemini / Offline Demo Fixture)"]
        Sandbox["Controlled Sandbox Runner<br/>(Env Sanitization & Tree Kill)"]
    end

    subgraph Staging ["Isolated Candidate Staging Workspace"]
        TempRepo["Staged Copy of Source Code"]
        Pytest["Synthesized Tests (pytest)"]
        Diff["Unified Git Diff"]
    end

    subgraph Target ["Original Target Codebase"]
        OriginalRepo["Original Source Code (Untouched until Approval)"]
    end

    UI --> API
    HITL -->|"Approve & Merge"| API
    API -->|"Apply Patched Files"| OriginalRepo
    API --> DB
    API --> Engine
    Engine --> LLM
    Engine --> Sandbox
    Sandbox --> TempRepo
    Sandbox --> Pytest
    Engine --> Diff
    Diff --> UI
```

<div align="center">
  <img src="docs/assets/architecture.svg" alt="DevSentinel Architecture Diagram" width="90%"/>
</div>

---

## 🚀 Core Engineering Capabilities

### 1. Multi-Stage Iterative Agentic Workflow
Unlike single-prompt chatbots, DevSentinel runs an autonomous 5-stage engineering loop:
- **Stage 1 (Reconnaissance)**: Scans candidate files, AST symbols, and test configurations.
- **Stage 2 (Test Synthesis)**: Synthesizes a dedicated reproduction unit test (`test_devsentinel_reproduce.py`) asserting the bug before touching any source code.
- **Stage 3 (Baseline Execution)**: Executes `pytest` in isolation and verifies the defect manifests (non-zero process exit code).
- **Stage 4 (Surgical Remediation)**: Modifies only the vulnerable functions in the isolated staging workspace.
- **Stage 5 (Regression Verification)**: Re-runs the full test suite in the sandbox, verifying exit code 0.

### 2. Surgical Git Diff Viewer & Code Remediation
Every patch is captured as a unified Git diff with syntax highlighting:

<div align="center">
  <img src="docs/assets/diff-preview.svg" alt="DevSentinel Git Diff Preview" width="90%"/>
</div>

### 3. Human-in-the-Loop (HITL) Review Drawer
- **Trajectory Timeline**: Step-by-step thought chain inspection for every decision.
- **Security Audit Scoring**: Algorithmic security scoring (0–100) assessing vulnerability mitigation.
- **One-Click Actions**: Single-click `[Approve & Merge]`, `[Request Revision with Notes]`, or `[Reject]`.

---

## 📂 Repository Structure

```bash
DevSentinel/
├── .github/workflows/
│   └── ci.yml               # Automated CI/CD pipeline (Pytest + Vite Build)
├── backend/
│   ├── app/
│   │   ├── agent/           # Agentic loop, sandbox runner, and LLM abstraction
│   │   │   ├── engine.py    # Multi-stage agent loop with candidate workspace isolation
│   │   │   ├── sandbox.py   # Sanitized execution runner with process-tree termination
│   │   │   └── llm.py       # LLM provider with explicit demo fixture mode
│   │   ├── api/             # FastAPI REST endpoints
│   │   │   └── routes.py    # Job dispatch, state-transition validation, and approval
│   │   ├── core/            # Config, database engine, settings, CORS policy
│   │   ├── models/job.py    # SQLAlchemy ORM models (verification status & audit trails)
│   │   └── schemas/job.py   # Pydantic request/response schemas with Enum validation
│   ├── tests/               # Backend Pytest test suite (100% passing)
│   ├── Dockerfile           # Backend container definition
│   └── requirements.txt     # Python dependencies
├── frontend/
│   ├── src/                 # React 19 application
│   │   ├── App.jsx          # Interactive HITL Review Workspace & Dashboard
│   │   ├── App.css          # Dark-theme engineering UI stylesheet
│   │   └── main.jsx         # Vite entrypoint
│   ├── Dockerfile           # Multi-stage Nginx container build
│   └── package.json         # Node.js dependencies
├── docs/assets/             # Architecture and platform preview visuals
├── sample_repos/
│   └── audio_transcoder/    # Realistic target project (Audio DSP + SQL logging)
├── docker-compose.yml       # Full-stack container orchestration
├── run_dev.ps1              # One-click Windows development launcher
└── README.md                # Documentation & Architecture Guide
```

---

## ⚡ Quickstart Guide

### Option 1: Native Local Setup

#### Prerequisites
- **Python**: 3.10+ (tested on Python 3.12)
- **Node.js**: 18+ (tested on Node.js 24)

#### 1. Backend Setup
```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload --port 8000
```
Backend API will be live at: `http://localhost:8000` (Interactive Swagger docs at `http://localhost:8000/docs`).

#### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Frontend UI will be live at: `http://localhost:5173`.

---

### Option 2: Docker Compose (Full Stack)

```bash
docker compose up --build
```
Access the application dashboard at `http://localhost:3000`.

---

## 🧪 Live Demonstration Scenario (Shure Audio DSP)

1. Open the dashboard at `http://localhost:5173`.
2. Click **"Run Shure Audio Demo"** in the top-right header.
3. DevSentinel will automatically:
   - Create an isolated staging copy of the sample audio transcoder repository.
   - Detect **CWE-120** (buffer overrun) and **CWE-89** (SQL injection in track logger).
   - Synthesize a reproduction pytest suite.
   - Execute tests in sandbox, verify non-zero failure exit code, and apply a surgical parameterized fix.
   - Re-verify tests (verifying clean exit code 0).
   - Present the patch diff and security score for **Human-in-the-Loop review**.
4. Review the diff and click **"Approve & Merge"** to copy the verified fix into the primary repository.

---

## 📋 Running Automated Tests

Run the backend unit, integration, and security test suite:

```bash
# Set PYTHONPATH to project root:
# Windows PowerShell:
$env:PYTHONPATH = (Get-Location).Path
.\backend\.venv\Scripts\pytest backend/tests/ -v

# Linux/macOS:
# export PYTHONPATH=$(pwd)
# pytest backend/tests/ -v
```

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
