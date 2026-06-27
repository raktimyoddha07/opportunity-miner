# Reddit Opportunity Miner

Reddit Opportunity Miner is an AI-powered personal research tool that continuously collects Reddit discussions, extracts recurring pain points using LLMs, clusters them into validated opportunities, and generates business/SaaS ideas from strong signals.

The core value of this system is not just generating ideas, but maintaining a growing, fully traceable database of validated customer problems backed by real evidence.

---

## Architecture & Tech Stack

```
                                  [ Next.js Frontend ]
                                           │
                                           ▼ (REST API)
                                   [ FastAPI Backend ]
                                           │
                                           ▼
                                 [ LangGraph Pipeline ]
  ┌─────────┐     ┌───────┐     ┌─────────┐     ┌────────────┐     ┌─────────┐     ┌───────┐     ┌──────────┐     ┌──────────┐
  │ collect │ ──> │ clean │ ──> │ extract │ ──> │deduplicate │ ──> │ cluster │ ──> │ score │ ──> │ validate │ ──> │ generate │
  └─────────┘     └───────┘     └─────────┘     └────────────┘     └─────────┘     └───────┘     └──────────┘     └──────────┘
       │                              │                                                              │                 │
       ▼ (Save raw)                   ▼ (LLM Extract)                                                ▼ (LLM Validate)  ▼ (LLM Ideas)
  [ Postgres DB ]                [ LLM Providers ]                                              [ LLM Providers ]  [ LLM Providers]
```

- **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLAlchemy ORM
- **Database**: PostgreSQL (UUID keys, JSONB metadata, cascading constraints)
- **Pipeline Orchestration**: LangGraph (StateGraph)
- **LLM Integration**: LangChain (factory-driven, provider-agnostic)
- **Data Source**: PRAW (Reddit API client)
- **Frontend**: Next.js, React, TailwindCSS, Recharts, Radix UI (Shadcn/UI components)

---

## Features

1. **Reddit Collector**: Recursive comment crawler extracting deep context from any list of subreddits across `hot`, `top`, `rising`, and `new` feeds.
2. **Text Filtering**: Discards low-signal comments, meta-discussions, promotional spam, and deleted content.
3. **Structured Extraction**: Extracts validated pain points with intensity, category, and raw quoted evidence.
4. **Deduplication**: Collapses semantically duplicate pain points using configurable embedding similarities.
5. **Clustering & Trend Snapshotting**: Groups pain points by categories and detects emerging trends over time.
6. **Multi-Format Opportunity Validation**: Rejects low-confidence ideas and requires minimum validation thresholds (mentions, users, threads).
7. **Idempotent Idea Generator**: Generates ideas for multiple business types (`micro_saas`, `ai_agent`, `chrome_extension`, etc.) from validated problems.
8. **Auditable Trust Layer**: Complete trace from Opportunity → Cluster → Pain Point → Original Post + Permalinks.

---

## Configuration

Copy `.env.example` in the `frontend/` directory (if configuring the client URL) and configure `.env` in the root or `backend/` directory for the backend server.

### Backend Environment Variables (`backend/.env`)

```ini
# Environment
ENV=development
DEBUG=true

# PostgreSQL Database (Must exist)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/reddit_miner

# Reddit API Credentials
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=RedditOpportunityMiner/0.1
REDDIT_USERNAME=your_reddit_username
REDDIT_PASSWORD=your_reddit_password

# LLM Providers Keys (Optional - depends on selected active provider)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GROQ_API_KEY=your_groq_key
GEMINI_API_KEY=your_gemini_key
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Getting Started

### 1. Setup & Start Backend

Navigate to the `backend/` directory, set up your virtual environment, install requirements, and run the FastAPI server:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app (Automatically creates database tables on startup)
uvicorn main:app --reload --port 8000
```

The server will be available at `http://localhost:8000`. You can visit `http://localhost:8000/docs` to explore interactive Swagger API documentation.

### 2. Setup & Start Frontend

Navigate to the `frontend/` directory, configure your API URL, install packages, and start Next.js:

```bash
cd frontend

# Set the API URL endpoint
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local

# Install and start
npm install
npm run dev
```

The frontend will run at `http://localhost:3000`.

---

## Exports

Export opportunity data via REST endpoints:
- **CSV**: `/export/csv`
- **JSON**: `/export/json`
- **Markdown Report**: `/export/markdown`
