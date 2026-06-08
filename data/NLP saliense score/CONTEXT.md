# Entity Salience Analysis Tool — Context Document

## What This Tool Does
Crawls a domain (and competitors) using Screaming Frog CLI, runs every page through Google Cloud Natural Language API's `analyzeEntities` endpoint to get entity salience scores, clusters pages by shared entities using 3 methods, and outputs CSV analysis + interactive HTML report.

## Project Location
`/Users/george.fakorellis/Desktop/SEO Custom Projects/NLP saliense score/`

## Architecture & Data Flow
```
cli.py run --domain synthesia.io --competitors "loom.com,descript.com"
  │
  ├─► crawl.py
  │     Screaming Frog CLI (headless) → discovers URLs
  │     requests + BeautifulSoup → extracts body text per URL
  │     Text is transient — only passed to NLP, never stored long-term
  │
  ├─► analyze.py
  │     Google Cloud NLP analyzeEntities → extracts entities + salience scores
  │     Results stored in SQLite entities table
  │
  ├─► compare.py
  │     Runs crawl+analyze on each competitor domain
  │     Same entities table, filtered by domain
  │
  ├─► cluster.py
  │     3 methods on entity-salience data:
  │       1. Co-occurrence groups (pages sharing 3+ entities)
  │       2. KMeans on entity-salience vectors (auto K via silhouette)
  │       3. Hierarchical/dendrogram (Ward linkage)
  │     Results in clusters + cluster_pages tables
  │
  ├─► visualize.py
  │     Plotly interactive charts → standalone HTML report
  │     Charts: heatmap, network graph, competitor bars, radar, gaps, treemap, dendrogram
  │
  └─► export.py
        CSV files with analysis results only (no raw content)
```

## Files & Their Roles

| File | Purpose | Key Functions |
|------|---------|--------------|
| `utils.py` | Config, logging, retry, URL cleaning | `load_config()`, `setup_logging()`, `@retry`, `clean_domain()` |
| `db.py` | SQLite schema + CRUD operations | `init_db()`, `upsert_page()`, `upsert_entity()`, `get_entities()` |
| `crawl.py` | Screaming Frog CLI + text extraction | `crawl_domain()`, `extract_text()`, `filter_urls()` |
| `analyze.py` | Google Cloud NLP entity extraction | `analyze_page()`, `analyze_domain()`, `chunk_text()` |
| `cluster.py` | 3 clustering methods | `cooccurrence_clusters()`, `kmeans_clusters()`, `hierarchical_clusters()` |
| `compare.py` | Cross-domain entity comparison | `compare_domains()`, `find_gaps()`, `entity_overlap()` |
| `visualize.py` | Plotly HTML report generation | `build_report()`, various `plot_*()` functions |
| `export.py` | CSV output | `export_entities()`, `export_clusters()`, `export_gaps()` |
| `cli.py` | argparse CLI entry point | Subcommands: crawl, analyze, cluster, compare, report, export, run |
| `config.yaml` | Default settings | Screaming Frog path, thresholds, default domain |

## Database Schema (SQLite — `analysis.db`)

### pages
| Column | Type | Description |
|--------|------|-------------|
| url | TEXT PK | Full page URL |
| domain | TEXT | Domain name |
| status | TEXT | pending → crawled → analyzed |
| crawled_at | TIMESTAMP | When page was crawled |

### entities
| Column | Type | Description |
|--------|------|-------------|
| url | TEXT FK | Page URL |
| entity_name | TEXT | Entity text (e.g., "AI video") |
| entity_type | TEXT | Google NLP type (PERSON, ORG, etc.) |
| salience | REAL | 0.0–1.0, how central to the page |
| mention_count | INT | How many times mentioned |
| domain | TEXT | For cross-domain filtering |
| PK: (url, entity_name) | | |

### clusters
| Column | Type | Description |
|--------|------|-------------|
| method | TEXT | cooccurrence / kmeans / hierarchical |
| cluster_id | INT | Cluster number within method |
| label | TEXT | Auto-generated from top entities |
| top_entities | TEXT | JSON array of top entity names |
| domain | TEXT | Which domain this cluster belongs to |
| PK: (method, cluster_id, domain) | | |

### cluster_pages
| Column | Type | Description |
|--------|------|-------------|
| method | TEXT | Clustering method |
| cluster_id | INT | Cluster number |
| url | TEXT FK | Page URL |
| PK: (method, cluster_id, url) | | |

### runs
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER PK | Auto-increment |
| domain | TEXT | Domain analyzed |
| started_at | TIMESTAMP | Run start time |
| completed_at | TIMESTAMP | Run end time |
| page_count | INT | Pages processed |
| config_snapshot | TEXT | JSON of settings used |

## CLI Usage
```bash
# Full pipeline — one command
python3 cli.py run --domain synthesia.io --competitors "loom.com,descript.com"

# Subfolder only
python3 cli.py run --domain synthesia.io --subfolder /blog/ --limit 50

# Individual steps
python3 cli.py crawl --domain synthesia.io
python3 cli.py analyze --domain synthesia.io
python3 cli.py cluster --domain synthesia.io
python3 cli.py compare --domain synthesia.io --competitors "loom.com"
python3 cli.py report --domain synthesia.io
python3 cli.py export --domain synthesia.io

# Force re-analysis (ignore cache)
python3 cli.py run --domain synthesia.io --force
```

## Dependencies
```
google-cloud-language>=2.13.0   # Google NLP API
plotly>=5.18.0                  # Interactive charts
networkx>=3.2.0                 # Entity network graphs
scikit-learn>=1.4.0             # KMeans clustering
scipy>=1.12.0                   # Hierarchical clustering
beautifulsoup4>=4.12.0          # HTML text extraction
lxml>=5.0.0                     # Fast HTML parser
pyyaml>=6.0.1                   # Config files
python-dotenv>=1.0.0            # .env loading
requests>=2.31.0                # HTTP requests
```

## External Dependencies
- **Screaming Frog SEO Spider** — installed at `/Applications/Screaming Frog SEO Spider.app/`
  - CLI: `ScreamingFrogSEOSpiderLauncher --crawl <url> --headless --output-folder <path>`
  - Requires active license for CLI mode
- **Google Cloud NLP API** — needs service account key at `.credentials/nlp-service-account.json`
  - Enable "Cloud Natural Language API" in GCP Console
  - Pricing: $1/1000 text records (first 5K/month free)

## Setup Instructions
1. `cd "/Users/george.fakorellis/Desktop/SEO Custom Projects/NLP saliense score/"`
2. `python3 -m venv venv && source venv/bin/activate`
3. `pip install -r requirements.txt`
4. Copy GCP service account JSON to `.credentials/nlp-service-account.json`
5. Copy `.env.example` to `.env` and fill in paths
6. `python3 cli.py run --domain synthesia.io --competitors "loom.com"`

## Build Log
- **Step 1**: Created `utils.py`, `config.yaml`, `.env.example`, `requirements.txt`
- **Step 2**: Created `db.py` with full schema and CRUD
- **Step 3**: Created `crawl.py` with SF CLI integration + BS4 text extraction
- **Step 4**: Created `analyze.py` with Google NLP client
- **Step 5**: Created `cluster.py` with 3 clustering methods
- **Step 6**: Created `compare.py` for cross-domain analysis
- **Step 7**: Created `export.py` for CSV output
- **Step 8**: Created `visualize.py` for Plotly HTML report
- **Step 9**: Created `cli.py` wiring everything together
