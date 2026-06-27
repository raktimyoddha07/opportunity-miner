# Reddit Opportunity Miner

Reddit Opportunity Miner is an AI-powered personal research tool that continuously collects Reddit discussions, extracts recurring pain points using LLMs, clusters them into validated opportunities, and generates business/SaaS ideas from strong signals.

The core value of this system is not just generating ideas, but maintaining a growing, fully traceable database of validated customer problems backed by real evidence.

---

## 🎨 How to Use (Core Sections)

The web application is divided into five core sections, designed to take you from configuration to execution and analysis:

### 1. Settings & Config (`/settings`)
* **LLM Setup**: Configure LLM settings using various providers. Select `ollama`, set the model to `qwen2.5:7b-instruct`, and use the default base URL `http://localhost:11434`.
* **Targets**: Add target subreddits (e.g., `selfhosted`, `excel`, `sysadmin`, `productivity`, `sideproject`, `saas`) to scrape.
* **Pipeline Controls**: Adjust scrape depth, comment limits, and duplication thresholds before triggering a run.

### 2. Dashboard & Trends (`/`)
* **Overview**: View your database statistics, including total raw documents collected, active clusters, validated opportunities, and generated ideas.
* **Trend Analysis**: Monitor cluster frequencies over multiple runs to identify emerging customer frustrations early.
* **Breakdown**: Visualize pain points by categories (e.g., `manual_work`, `bad_software`, `automation`).

### 3. Validated Opportunities (`/opportunities`)
* **Ranked List**: View opportunities that passed the validation threshold (e.g., minimum of 10 mentions, 3 unique users, 2 threads, average confidence $\ge$ 2.0).
* **Detailed Breakdown**: Click any opportunity to see its exact problem statement, validation score reasoning, and direct links to evidence and generated ideas.

### 4. Trust Layer: Clusters & Evidence (`/clusters` & `/evidence`)
* **Semantic Clusters**: Examine how raw complaints are grouped using text embedding similarity.
* **Source Traceability**: Every opportunity contains a trust layer where you can view the actual Reddit comments, author names, and direct URLs to the original Reddit threads.

### 5. Business Ideas (`/ideas`)
* **Multi-Format Solutions**: View AI-generated startup concepts targeting validated opportunities.
* **Formats**: Generates ideas spanning `micro_saas`, `ai_agent`, `chrome_extension`, `api_product`, `marketplace`, `service_business`, `internal_tool`, and `workflow_automation`.

---

## 🛠️ Tech Stack

* **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLAlchemy ORM, LangGraph (StateGraph)
* **Database**: PostgreSQL (UUID keys, JSONB metadata, cascading constraints)
* **LLM Integration**: LangChain (factory-driven, provider-agnostic via `factory.py`)
* **Frontend**: Next.js, React, TailwindCSS, Recharts, Shadcn/UI
* **Data Source**: PRAW (Reddit API client)

---

## 🚀 Setup & Installation

### 1. Prerequisites
- **PostgreSQL**: Install and ensure a PostgreSQL server is running. Create a database named `reddit_miner`.
- **Ollama**: Install [Ollama](https://ollama.com) and pull your model of choice in your terminal:
  ```bash
  ollama pull qwen2.5:7b-instruct
  ```

### 2. Backend Setup
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # On Windows
   # source .venv/bin/activate # On macOS/Linux
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file in the `backend/` directory:
   ```ini
   ENV=development
   DEBUG=true
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/reddit_miner
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   OLLAMA_BASE_URL=http://localhost:11434
   ```
5. Start the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```
   The backend will start at `http://localhost:8000` (docs available at `http://localhost:8000/docs`).

### 3. Frontend Setup
1. Navigate to the `frontend/` directory:
   ```bash
   cd ../frontend
   ```
2. Create a `.env` file in the `frontend/` directory:
   ```ini
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```
3. Install dependencies and start the Next.js development server:
   ```bash
   npm install
   npm run dev
   ```
   The frontend will run at `http://localhost:3000`.

---

## 📥 Exports

You can download your opportunities in various formats directly via the browser or API endpoints:
- **JSON**: `http://localhost:8000/export/json` (full nested details)
- **Markdown**: `http://localhost:8000/export/markdown` (formatted report)
- **CSV**: `http://localhost:8000/export/csv` (tabular structure)
