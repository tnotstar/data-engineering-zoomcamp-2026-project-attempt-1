# AGENTS.md

This document describes the various agents and components that work together in the Genomic Data Pipeline for Data Engineering Zoomcamp 2026.

## Overview

This project implements an end-to-end data engineering pipeline for ingesting, processing, and serving genomic variant data from the European Variation Archive (EVA). The system consists of four main agents that coordinate through Docker Compose.

---

## Agents

### 1. EVA Ingestion Agent

**Location**: `etl-pipeline/assets/ingest_eva.py`

**Purpose**: Simulates data ingestion from the European Variation Archive FTP server and generates synthetic genomic variant data focused on Chromosome 21.

**Responsibilities**:
- Connects to EBI's FTP server (`ftp.ebi.ac.uk`) to access EVA database
- Generates realistic variant records with population frequency data
- Filters variants for Chromosome 21 (positions 1000000-2000000)
- Creates 5,000 simulated variant records with fields:
  - `variant_id`: Unique identifier (rs1000+)
  - `chr`: Chromosome number
  - `pos`: Genomic position
  - `ref`: Reference allele
  - `alt`: Alternate allele
  - `eur_freq`, `afr_freq`, `amr_freq`: Population allele frequencies
- Validates data quality:
  - Ensures `variant_id` is unique and not null
- Outputs data to shared volume at `/data/eva_filtered.csv`

**Technology Stack**:
- Python 3.11
- Pandas for data manipulation
- ftplib for FTP connection
- Bruin orchestration

**Triggers**: Run by Bruin pipeline as first step in the DAG

---

### 2. Manticore Loading Agent

**Location**: `etl-pipeline/assets/load_to_manticore.py`

**Purpose**: Bulk loads the filtered variant data from CSV into Manticore Search engine for fast querying and indexing.

**Responsibilities**:
- Reads CSV output from EVA Ingestion Agent (`/data/eva_filtered.csv`)
- Transforms data into NDJSON format for Manticore Bulk API
- Bulk inserts 5,000 variant records into `eva_variants` index
- Handles connection retries (up to 3 attempts) with exponential backoff
- Maps data fields to Manticore document structure
- Provides status reporting and error handling

**Technology Stack**:
- Python 3.11
- Pandas for data processing
- Requests library for HTTP calls to Manticore API
- Bruin orchestration

**Dependencies**: Requires `ingest_eva` to complete successfully

**Triggers**: Run by Bruin pipeline as second step after ingestion

---

### 3. Search Engine Agent

**Location**: Docker service `search-engine` in `docker-compose.yaml`

**Purpose**: Acts as the data warehouse and search engine, providing fast full-text search and structured querying capabilities for genomic variants.

**Responsibilities**:
- Maintains the `eva_variants` index with variant records
- Supports full-text search on variant IDs
- Provides RESTful API for querying (port 9308)
- Supports SQL-like queries via SphinxQL (port 9306)
- Serves data to the Gradio Web Interface
- Persists data to `/data` volume

**Technology Stack**:
- Manticore Search (latest)
- Docker containerization

**API Endpoints**:
- `http://localhost:9308/bulk` - Bulk insert/update operations
- `http://localhost:9308/search` - Search queries
- Port 9308 - HTTP API
- Port 9306 - SphinxQL protocol

**Dependencies**: None (independent service)

---

### 4. Dashboard Agent

**Location**: `dashboard/main.py`

**Purpose**: Provides a user-friendly web interface for searching and visualizing genomic variant data stored in Manticore.

**Responsibilities**:
- Variant Search:
  - Accepts variant ID input (e.g., "rs100", "rs150")
  - Queries Manticore Search for matching records
  - Displays variant details (position, ref/alt alleles)
  - Generates interactive bar chart showing population frequencies (EUR, AFR, AMR)

- Distribution Analysis:
  - Retrieves up to 5,000 variant records
  - Creates histogram showing variant distribution across chromosome segment
  - Allows real-time refresh of density plot

- User Interface:
  - Responsive Gradio web UI
  - Interactive visualizations using Plotly
  - Status messages and error handling

**Technology Stack**:
- Python 3.11
- Gradio 4.0+ for web interface
- Plotly for interactive charts
- Pandas for data manipulation
- manticoresearch client library

**Web Interface**:
- URL: `http://localhost:7860`
- Two main views:
  1. Search by Variant ID with population frequency bar chart
  2. Chromosome distribution histogram

**Dependencies**: Requires Manticore Search to be running and populated

---

## Pipeline Orchestration

### Bruin Pipeline Engine

**Location**: `etl-pipeline/` directory

**Purpose**: Orchestrates the ETL workflow, managing dependencies between agents.

**Pipeline Definition**: `etl-pipeline/pipeline.yml`

**DAG Structure**:
```
ingest_eva → load_to_manticore
```

**Workflow**:
1. Bruin executes `ingest_eva` asset
   - Generates and validates variant data
   - Saves to `/data/eva_filtered.csv`
2. Upon successful completion, Bruin triggers `load_to_manticore`
   - Reads CSV and bulk loads to Manticore
   - Verifies data is indexed and queryable
3. Web interface becomes available for querying

**Environment Configuration**:
- Default environment: `etl-pipeline/environments/default.yml`
- DuckDB connection for intermediate storage
- Supports multiple deployment environments

---

## Communication Flow

```
User → Gradio Web UI → Manticore Search API → Returns variant data
                         ↑
                         |
                         Bulk Load
                         |
EVA Ingestion → CSV File → Manticore Loading Agent → Manticore Search
                         (orchestrated by Bruin)
```

**Data Flow Summary**:
1. **Ingestion Phase**: EVA Ingestion Agent → CSV file (shared volume)
2. **Loading Phase**: Manticore Loading Agent → Manticore Search (bulk API)
3. **Serving Phase**: Gradio Web UI → Manticore Search (search API) → User visualizations

---

## Shared Infrastructure

### Docker Compose

**Location**: `docker-compose.yaml`

**Purpose**: Manages all services as containers with proper networking and volume sharing.

**Services**:
- `search-engine`: Search engine and data warehouse
- `dashboard`: Web interface
- `etl-pipeline`: Pipeline orchestration environment

**Shared Volumes**:
- `./data`: Shared data directory for CSV files and Manticore persistence
- `./etl-pipeline`: Pipeline code (mounted to etl container)
- `./dashboard`: Gradio application code (mounted to dashboard container)

**Networking**:
- All services on default Docker network
- Service names used as hostnames (e.g., `http://search-engine:9308`)

---

## Development Environment

### Dev Container

**Location**: `.devcontainer/devcontainer.json`

**Purpose**: Provides a reproducible development environment for the project.

**Features**:
- Python 3.11 base image
- Docker-in-Docker support for running Docker Compose
- VS Code extensions: Python, Docker
- Port forwarding: 7860 (Gradio), 9308 (Manticore API)
- Automatic setup via `setup.sh` script

---

## Data Quality

### Validation Checks

**EVA Ingestion Agent**:
- Unique constraint on `variant_id`
- Not-null constraint on `variant_id`

**Manticore Loading Agent**:
- Connection retry logic (3 attempts with 2s delay)
- HTTP response validation (expects 200 status)
- Data type enforcement (integer for pos, float for frequencies)

---

## Scalability Considerations

- **Manticore Search**: Can handle millions of records with sub-second queries
- **Gradio**: Stateless application; can scale horizontally
- **Bruin**: Designed for local execution, but supports GitHub Actions for CI/CD
- **Data Volume**: Currently 5,000 records for demo; can be increased to full EVA dataset

---

## Security Notes

- Environment variables used for sensitive configuration (MANTICORE_URL)
- No hardcoded credentials
- FTP connection is read-only
- Gradio runs without authentication (intended for local/demo use)
- Manticore runs without authentication (should be secured for production)

---

## Monitoring and Observability

**Logging**:
- Each agent prints status messages to stdout
- Bruin logs to `etl-pipeline/logs/` directory
- Docker Compose captures all container logs

**Health Checks**:
- EVA Agent: Validates unique/not-null constraints
- Loading Agent: Verifies Manticore response status
- Web UI: Provides status messages to user

---

## Future Enhancements

Potential improvements to the agent system:

1. **Real-time Ingestion**: Replace simulated data with actual VCF parsing from EVA FTP
2. **Additional Populations**: Add more population frequencies (EAS, SAS, etc.)
3. **Batch Processing**: Support incremental updates instead of full reloads
4. **Authentication**: Add user authentication to Gradio interface
5. **API Extensions**: Expose REST API for programmatic access
6. **Data Versioning**: Track different versions of the variant dataset
7. **Caching**: Add caching layer for frequently queried variants
8. **Alerting**: Notify on pipeline failures or data anomalies
9. **Multi-chromosome Support**: Extend beyond Chromosome 21
10. **Genomic Annotations**: Add gene context, functional impact data
