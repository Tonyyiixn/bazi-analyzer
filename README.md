# AI-Driven Bazi Astrology Assistant

**Live:** [bazi-analyzer-rose.vercel.app](https://bazi-analyzer-rose.vercel.app) — the backend runs on a free tier that sleeps when idle, so the first request after a quiet spell can take up to a minute.

A full-stack web application that grounds traditional Chinese Bazi (Four Pillars of Destiny) astrology in **deterministic Python calculation**, then layers a Claude-powered chat agent on top for natural-language readings — instead of letting an LLM freehand-reason about a chart, every structural fact (pillars, Ten Gods, interactions, strength) is computed by pure functions and handed to the agent as tools.

## Key Features

**Deterministic chart engine**
* Four Pillars, Da Yun (10-year luck cycles), and Five Elements balance, with True Solar Time correction based on birth city.
* Ten Gods (十神) for every pillar's stem *and* full hidden-stem (藏干) breakdown per branch — not just the dominant main qi.
* Branch interactions: clashes, combinations, three-harmonies, punishments, harms, and breaks (沖合刑害破).
* Heavenly Stem combinations (天干五合), including season-support heuristics for true transformation.
* Day Master strength (身強/身弱) via the 扶抑 (Support/Suppress) method — explicitly documented as one of several valid traditional approaches, not an uncontested truth.
* Liu Nian (流年, annual) and Liu Yue (流月, monthly) pillars, read together against the natal chart for "how am I doing right now" questions.

**AI chat agent**
* Claude + [MCP](https://modelcontextprotocol.io/) tool-use loop: the agent calls the chart engine as tools rather than inventing chart facts from training data.
* RAG over a curated Bazi principles library, with feature-keyed retrieval — search queries are built from the chart's own computed Ten Gods/strength/interactions, not just the agent's free-text wording.
* Skill-based personas (career, relationship, health, yearly forecast, general) that switch the agent's system prompt/lens.
* A rule-based **consistency gate** that flags replies contradicting the chart's computed facts (e.g. claiming "strong" when the tool said "weak").
* A **high-stakes-question guardrail** that detects self-harm, mortality, medical-diagnosis, and major-irreversible-decision questions and injects safety-specific instructions before the agent responds.
* AI-assisted birth-hour rectification (Claude reasons over MBTI-style personality answers to estimate a missing birth hour).
* Session-based chat history, persisted per user with a sidebar to revisit past conversations.

**Frontend**
* Ink & Jade design system (Tailwind CSS v4), with an iOS-style scrolling wheel picker for birth date/time entry.
* Hover/tap tooltips on every Ten God label, explaining what it means in plain language.
* Saved-chart "Vault" per user, with the full deterministic breakdown (interactions, strength, hidden stems, current period) rendered for both freshly-calculated and previously-saved charts.

## Tech Stack
* **Frontend:** React 19, Vite, React Router, Tailwind CSS v4
* **Backend:** Python 3.12, FastAPI, SQLAlchemy + Alembic (Postgres in production, SQLite locally), Pydantic, JWT auth
* **AI / LLM:** Anthropic Claude API, Model Context Protocol (MCP), scikit-learn (TF-IDF retrieval)
* **Infrastructure:** Docker, Render (backend), Neon (Postgres), Vercel (frontend)
* **Testing:** pytest — 100+ tests, split into VERIFIED (checked against independently-confirmable traditional theory, e.g. the 60-year sexagenary cycle epoch or the standard Ten God table) vs. REGRESSION BASELINE (pins current output, not a correctness proof) vs. hand-tallied algorithm self-consistency checks for genuinely contested judgment calls (like Day Master strength)

---

## Project Structure
```
bazi-analyzer/
├── main.py                   # FastAPI app: auth, chart calculation, chat, saved charts, /health
├── core/
│   ├── bazi_math.py          # Pillars, Ten Gods, hidden stems (pure calculation)
│   ├── bazi_interactions.py  # Branch/stem interactions, Liu Nian/Liu Yue
│   ├── bazi_strength.py      # Day Master strength (扶抑 method)
│   ├── time_engine.py        # True Solar Time correction
│   ├── mcp_server.py         # MCP tools exposing the chart engine to the agent
│   ├── agent/orchestrator.py # Claude tool-use loop + system persona
│   ├── consistency_gate.py   # Flags replies contradicting computed facts
│   ├── guardrails.py         # High-stakes-question detection
│   ├── rag.py                # TF-IDF retrieval over principle docs
│   ├── database.py           # SQLAlchemy engine, driven by DATABASE_URL
│   ├── models.py             # ORM tables (users, saved charts, chat sessions/messages)
│   ├── skills/               # Career/relationship/health/yearly-forecast lenses
│   └── knowledge/principles/ # Curated Bazi theory reference docs
├── alembic/                  # Schema migrations (versions/ holds the history)
├── tests/                    # pytest suite
├── frontend/                 # React/Vite app
│   └── src/api.js            # Single source of the backend URL (VITE_API_URL)
├── Dockerfile                # Multi-stage image the backend deploys as
├── render.yaml               # Render Blueprint for the backend service
└── .env.example              # Every backend env var, documented
```

## Deployment
Both halves auto-deploy from `main`.

| Piece | Where | Notes |
|---|---|---|
| Frontend | **Vercel** (static Vite build) | `VITE_API_URL` env var points it at the backend |
| Backend | **Render** (Docker web service, free tier) | Built from the repo's `Dockerfile` via `render.yaml`; health check on `/health` |
| Database | **Neon** (managed Postgres, free tier) | Same region as the backend (us-east-2) |

The backend keeps a long-lived process (it spawns the MCP tool server as a subprocess at startup), which is why it runs as a container on Render rather than as serverless functions. On the free tier Render spins the service down after ~15 minutes idle, so the first request after a quiet spell takes ~30-60s while the container and MCP handshake come back up.

**Configuration** is entirely via environment variables - see `.env.example` (backend) and `frontend/.env.example`. `JWT_SECRET_KEY` and `DATABASE_URL` are required; the app refuses to start without the former and falls back to a local SQLite file without the latter.

**Schema changes** go through Alembic. Migrations are deliberately not run on container startup (instances would race); run them against the database before deploying the code that needs them:

```bash
DATABASE_URL=<postgres url> alembic upgrade head
```

---

## Local Installation & Setup

You'll need two terminals — one for the backend, one for the frontend.

### 1. Clone the Repository
```bash
git clone https://github.com/Tonyyiixn/bazi-analyzer.git
cd bazi-analyzer
```

### 2. Backend Setup (FastAPI)
Requires Python 3.10+ (3.12 is what's verified and deployed). From the repo root:

```bash
python3 -m venv venv          # Windows: py -3.12 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

**Environment variables.** Copy `.env.example` to `.env` and fill in the two required values:

```env
ANTHROPIC_API_KEY=sk-ant-...
JWT_SECRET_KEY=...            # python -c "import secrets; print(secrets.token_urlsafe(48))"
```

`DATABASE_URL` and `CORS_ORIGINS` can stay unset locally — the app falls back to a SQLite file and the Vite dev server's origin.

**Create the database.** Tables are managed by Alembic, not created on startup, so this step is required once on a fresh clone:

```bash
alembic upgrade head
```

Start the backend server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
*The API will be running at `http://localhost:8000/docs`*

### 3. Frontend Setup (React/Vite)
Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```
*The UI will be running at `http://localhost:5173`*, calling the local backend by default. To point it elsewhere, set `VITE_API_URL` — see `frontend/.env.example`.

### 4. Run with Docker (optional)
The same image that deploys to Render:

```bash
docker build -t bazi-backend .
docker run -p 8080:8080 --env-file .env bazi-backend
```

### 5. Run the Tests
From the repo root, with the virtualenv active:

```bash
pytest tests/ -v
```
