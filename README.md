# Opportunity Miner

Opportunity Miner is an AI-powered personal research tool that continuously collects Reddit discussions, extracts recurring pain points using LLMs, clusters them into validated opportunities, and generates business/SaaS ideas from strong signals.

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
* **Ranked List**: View opportunities that passed the full validation pipeline (internal thresholds + LLM judgement + external market signals).
* **Detailed Breakdown**: Click any opportunity to see its exact problem statement, validation score reasoning, and direct links to evidence and generated ideas.

### 4. Trust Layer: Clusters & Evidence (`/clusters` & `/evidence`)
* **Semantic Clusters**: Examine how raw complaints are grouped using `all-MiniLM-L6-v2` text embedding similarity.
* **Source Traceability**: Every opportunity contains a trust layer where you can view the actual Reddit comments, author names, and direct URLs to the original Reddit threads.

### 5. Business Ideas (`/ideas`)
* **Multi-Format Solutions**: View AI-generated startup concepts targeting validated opportunities.
* **Formats**: Generates ideas spanning `micro_saas`, `ai_agent`, `chrome_extension`, `api_product`, `marketplace`, `service_business`, `internal_tool`, and `workflow_automation`.

---

## ⚙️ Implementation Process

This section explains exactly how the system transforms raw Reddit posts into validated business opportunities. The pipeline is orchestrated by **LangGraph** as a stateful directed graph.

### Pipeline Overview

```
collect → clean → enrich → extract → deduplicate → cluster → score → validate → generate → END
```

Each node has a strict single responsibility. No node can abort the entire run — all errors are caught, logged, and the pipeline continues.

---

### Stage 1 — Collect

**What it does:** Scrapes the configured subreddits via the Reddit API (PRAW).

- Collects from all four feeds per subreddit: `hot`, `top`, `rising`, `new` (up to 100 posts each)
- Recursively collects comments to a configurable depth
- Saves every raw post/comment to the `source_documents` table **before** any processing (Rule: never process before saving)
- All data is converted to a source-agnostic `SourceDocument` format, keeping the system extensible to other sources (GitHub Issues, Hacker News, G2 reviews, etc.)

---

### Stage 2 — Clean

**What it does:** Removes low-quality, off-topic, or non-meaningful content.

Discards documents matching any of these conditions:
- Content is `[deleted]` or `[removed]`
- Length under 40 characters
- Meta discussions ("rate my idea", "roast my SaaS")
- Self-promotion or product links
- Low-signal replies ("lol", "same", "thanks", "good idea")

---

### Stage 3 — Enrich *(Urgency Scorer + Entity Extraction)*

**What it does:** Scores each post for urgency/purchase intent, extracts mentioned tools/products, and drops zero-signal posts before they reach the LLM.

#### Urgency / Willingness-to-Pay Keyword Pre-Scorer
A weighted keyword scoring function runs on each post's raw text before any LLM call. Phrases like:

| Phrase | Weight |
|---|---|
| "would pay" / "paying for" | +3 |
| "switched from" / "anyone built" / "wish someone would" | +2 |
| "hours every week" / "my whole team" / "every single time" | +2 |
| "can't believe" / "so frustrating" / "still no way to" | +1 |

Posts with `urgency_score = 0` **and** length < 100 characters are skipped entirely — no LLM call wasted on them. The `urgency_score` is stored as metadata on every document.

#### spaCy Entity Extraction
Using the `en_core_web_sm` spaCy model, each post is scanned for named entities with labels `ORG`, `PRODUCT`, and `WORK_OF_ART`. This creates a competitor gap map — e.g., knowing that 30 posts all complain about **Notion** or **Zapier** is a direct positioning signal. Entities are stored in document metadata.

---

### Stage 4 — Extract *(LLM Pain Point Detection)*

**What it does:** Sends each enriched document to the LLM (via `factory.py`) to determine if a genuine, recurring pain point exists.

The LLM returns a structured JSON with:

| Field | Description |
|---|---|
| `has_pain_point` | True/False — does this text contain a real recurring frustration? |
| `summary` | One-sentence description of the core problem |
| `category` | One of 12 fixed categories (e.g., `bad_software`, `integration_gap`, `manual_work`) |
| `emotion` | One of 8 emotion labels (see below) |
| `intensity` | 1–5 scale of how severely the user is affected |
| `quoted_evidence` | Exact quote from the original text |
| `confidence` | 0–100 LLM confidence score |

#### Emotion Taxonomy
Instead of raw sentiment, the LLM classifies each pain point into a business-actionable emotion:

| Label | Meaning |
|---|---|
| `paying_for_bad_tool` | User pays money for something that fails them — direct monetization signal |
| `frustrated_with_workaround` | User is doing manual steps to fix a broken process |
| `asking_for_missing_feature` | User wants something that doesn't exist yet |
| `abandoned_by_vendor` | Tool raised prices, killed a feature, or shut down |
| `time_wasted` | Task takes far longer than it should |
| `data_loss_fear` | User experienced or fears losing data/work |
| `onboarding_confusion` | User cannot figure out how to use a tool |
| `integration_broken` | Two tools don't work together properly |

All LLM calls use a max of **3 retry attempts** with error isolation per document.

---

### Stage 5 — Deduplicate *(Semantic Similarity Clustering)*

**What it does:** Groups near-identical pain points using embedding similarity so the same complaint posted in multiple threads is counted as one signal with a higher frequency weight.

#### Embedding Model: `all-MiniLM-L6-v2`
Uses the `sentence-transformers` library to load `all-MiniLM-L6-v2` — a 384-dimension model purpose-built for semantic similarity tasks. It runs **fully on CPU** with no API key or internet required. This model is significantly better than generic embeddings for short complaint texts.

- Cosine similarity is computed pairwise across all pain point summaries
- Groups with similarity ≥ 0.82 are merged into a single master entry
- Each master keeps a `duplicate_count` and `duplicate_ids` — the chain of evidence is never discarded

---

### Stage 6 — Cluster

**What it does:** Groups deduplicated pain points into named thematic clusters using keyword and category overlap.

Each cluster gets:
- A descriptive name and summary
- A category label
- A list of all contributing pain point evidence

---

### Stage 7 — Score

**What it does:** Computes a composite opportunity score for each cluster using four independent signals.

```
Score = Frequency × Intensity × Diversity × Persistence   (normalized 0–100)
```

| Signal | How it's computed |
|---|---|
| **Frequency** | mentions in this cluster / total mentions across all clusters |
| **Intensity** | average pain intensity rating (1–5) across cluster members |
| **Diversity** | number of unique subreddits mentioning the cluster (saturates at 5) |
| **Persistence** | fraction of distinct calendar days spanned by the evidence (saturates at 3 days) |

---

### Stage 8 — Validate *(Internal + External)*

**What it does:** The gatekeeper stage. An opportunity must pass **both** hard thresholds and an LLM judgement call. Passing opportunities also receive external market signal enrichment.

#### Internal Hard Thresholds (Rule 7)
| Check | Minimum Required |
|---|---|
| Unique mentions | ≥ 3 |
| Unique users | ≥ 2 |
| Unique threads | ≥ 1 |
| Average LLM confidence | ≥ 1.5 / 5.0 |

> **Rule 7**: Bad opportunities are worse than missing ones. When in doubt, reject.

#### LLM Validation
The LLM reviews the cluster summary and top 25 quoted evidence snippets and answers:
- Is this a real recurring problem?
- Are users actively frustrated?
- Would businesses pay for a solution?

Final decision = `LLM says valid` **AND** `thresholds pass`.

#### External Market Validation (Upgrade 5)
For every cluster that passes internally, three free public signals are checked automatically:

| Signal | Source | What it measures |
|---|---|---|
| **Google Trends** | `pytrends` | 12-month search interest trend; flags if rising in last 3 months |
| **HN Mentions** | Hacker News Algolia API (free, no auth) | How many HN comments discuss this topic |
| **Product Hunt** | Public search scrape | How many existing products exist (competition level) |

These combine into an `external_confidence` score:
```
external_confidence = internal_confidence
                    + 2  (if Google Trends rising)
                    + 1  (if HN mentions > 5)
                    + 3  (if Product Hunt count = 0  ← untapped market)
                    - 1  (if Product Hunt count > 10 ← saturated market)
```

---

### Stage 9 — Generate

**What it does:** For every validated opportunity, the LLM generates concrete business ideas across multiple formats.

Each opportunity gets ideas of types: `micro_saas`, `ai_agent`, `chrome_extension`, `api_product`, `marketplace`, `service_business`, `internal_tool`, `workflow_automation`.

All ideas are linked back to their parent opportunity, cluster, pain points, and original Reddit URLs — the full evidence chain is always intact.

---

## 🛠️ Tech Stack

* **Backend**: Python 3.11+, FastAPI, Uvicorn, SQLAlchemy ORM, LangGraph (StateGraph)
* **Database**: PostgreSQL (UUID keys, JSONB metadata, cascading constraints)
* **LLM Integration**: LangChain (factory-driven, provider-agnostic via `factory.py`) — supports Ollama, OpenAI, Anthropic, Groq, Gemini, OpenRouter
* **NLP / Embeddings**: spaCy `en_core_web_sm` (entity extraction), `all-MiniLM-L6-v2` via sentence-transformers (semantic deduplication)
* **External Signals**: pytrends (Google Trends), HN Algolia API, Product Hunt search
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
4. Download the spaCy English model (required for entity extraction):
   ```bash
   python -m spacy download en_core_web_sm
   ```
5. Create a `.env` file in the `backend/` directory:
   ```ini
   ENV=development
   DEBUG=true
   DATABASE_URL=postgresql://postgres:postgres@localhost:5432/reddit_miner
   REDDIT_CLIENT_ID=your_reddit_client_id
   REDDIT_CLIENT_SECRET=your_reddit_client_secret
   OLLAMA_BASE_URL=http://localhost:11434
   ```
6. Start the FastAPI server:
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
