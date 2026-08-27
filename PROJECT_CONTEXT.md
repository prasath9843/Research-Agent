# DeepResearch Studio — Complete Project Context & Handoff Guide

## 1. Project Overview & Objective
**DeepResearch Studio** is an autonomous, publication-grade academic research engine with a full interactive web UI.
- **Repository**: `prasath9843/Research-Agent`
- **Main Branch**: `main` (hosted locally and deployed to Render at `https://deepresearch-studio.onrender.com`)
- **Backend**: FastAPI (Python), SQLite database (`research_agent.db`), Uvicorn server on `http://127.0.0.1:8000`.
- **Frontend**: Full-screen academic studio UI (Vanilla HTML/CSS/JS with FontAwesome, Markdown rendering, live telemetry, interactive tabs, PDF export).

---

## 2. Core Architecture & Pipeline (10-Stage Process)
When a user launches a research task (`POST /api/research`):
1. **Stage 1 (Query Planning)**: Decomposes query into 3–5 sub-questions (`SubQuestion`) with categories (`core`, `nuance`, `counter_argument`).
2. **Stage 2 (Search Execution)**: Parallel web searches with 2.5s fast non-blocking timeout per query.
3. **Stage 3 (Scraping & Scoring)**: Fetches page contents, cleans HTML with Trafilatura, and computes domain credibility score (0.0 to 1.0).
4. **Stage 4 (Claims Extraction)**: Extracts atomic factual claims into the local SQLite evidence store.
5. **Stage 5 (Gap Analysis)**: Autonomous loop that assesses if further rounds are needed.
6. **Stage 6 (Contradiction / Consensus)**: Discovers agreement & disagreement patterns across collected sources.
7. **Stage 7 (Grounded Synthesis)**: Generates a 15-section publication-ready Markdown report with strict tables and `[source_N]` citations.
8. **Stage 8 (Citation Verification)**: Programmatic verification of all cited references against the evidence store.
9. **Stage 9 (Report Assembly)**: Appends formatted References and Credibility index.
10. **Stage 10 (AI Quality Audit)**: Evaluates the report with an instant Rigor score stamp (e.g. 9.4/10 Rigor Stamped).

---

## 3. Active Models & AI Configuration
- **NVIDIA NIM API**:
  - `NVIDIA_BASE_URL`: `https://integrate.api.nvidia.com/v1`
  - Active Fast & Strong Model: **`meta/llama-3.2-11b-vision-instruct`**
  *(Note: `meta/llama-3.1-*` and `meta/llama-3.2-3b-instruct` reached end-of-life on NVIDIA NIM and were fully migrated to `meta/llama-3.2-11b-vision-instruct` with 3x connection retry backoff).*

---

## 4. Authentication & Security Setup
- **Email Verification / OTP System**:
  - Verification codes and password reset tokens are sent **exclusively to the user's Gmail inbox** via SMTP.
  - Development OTP codes (`dev_code`) are completely removed from UI and API responses for privacy.
- **Gmail SMTP Configuration** (Configured in `.env`):
  - `SMTP_SERVER=smtp.gmail.com`
  - `SMTP_PORT=587`
  - `SMTP_USER=prasathsubramani8098@gmail.com`
  - `SMTP_PASS`: Configured in local `.env` (Gmail App Password)
  - `SMTP_FROM=prasathsubramani8098@gmail.com`
- **Google OAuth 2.0 Integration** (Configured in `.env`):
  - `GOOGLE_CLIENT_ID`: Configured in local `.env`
  - `GOOGLE_CLIENT_SECRET`: Configured in local `.env`
  - Endpoint: `GET /api/auth/google/login` & `GET /api/auth/google/callback`

---

## 5. Key Files & Structure
- `main.py`: FastAPI server, authentication routes, research launch endpoint, status polling, report export.
- `pipeline.py`: Orchestrates the 10-stage autonomous research pipeline (`ResearchPipeline`).
- `llm_client.py`: Client for NVIDIA NIM completions with JSON schema repair, fallback routing, and connection retries.
- `evidence_store.py`: SQLite evidence persistence layer (`sessions`, `sources`, `claims`, `reports`, `session_logs`).
- `models.py`: Pydantic data schemas (`QueryPlannerOutput`, `AtomicClaim`, `CitationVerificationResult`, `ResearchRequest`).
- `search_engine.py`: Search execution layer with fast non-blocking timeouts.
- `scraper.py`: Web scraper using Trafilatura for clean article text extraction.
- `email_service.py`: Dispatches HTML verification emails via Gmail SMTP.
- `templates/index.html`: Complete DeepResearch Studio web UI (top navbar badges, depth cards, white academic paper canvas, red PDF buttons, chat bar).
- `static/js/app.js` & `static/css/style.css`: Client-side logic and styles.

---

## 6. How to Run Locally
```bash
# In the workspace root: c:\Users\prasa\OneDrive\Desktop\Research Agent
.\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Open **`http://localhost:8000`** in the browser.

---

## 7. Recent Fixes Accomplished
1. **NVIDIA NIM End-of-Life Model Rotation Fixed**: Fully migrated all prompt stages and configuration to active `meta/llama-3.2-11b-vision-instruct`.
2. **Schema & Verification Bugs Fixed**: Resolved `AtomicClaim.source_url` and `CitationVerificationResult` missing field validation errors.
3. **Speed & Latency**: Added 2.5s search timeouts so Turbo mode runs in ~15 seconds without stalling.
4. **Resilient Connection Retries**: Added auto-retry logic with exponential backoff on transient OpenAI network errors.
5. **Pixel-Perfect Studio UI Restored**: Top navbar badges, depth speed cards, 4-tab views, and red PDF download buttons restored and synced with GitHub `main`.
