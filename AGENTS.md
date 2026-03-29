# AGENTS.md

**Version**: 2.0
**Last Updated**: March 29, 2026
**Architecture**: Medallion (Ingest → Process → Serve)

This document describes the various agents and components that work together in the Genomic Data Pipeline for Data Engineering Zoomcamp 2026.

## Overview

This project implements an end-to-end data engineering pipeline for ingesting, processing, and serving genomic variant data from the NCBI ALFA (Allele Frequency Aggregator) project. The system consists of four main agents that coordinate through Docker Compose, following a **Medallion Architecture** pattern.

## Medallion Architecture

The pipeline follows a **Medallion Architecture** with three distinct layers:

### 1. Raw Layer (`/data/raw`)
- **Purpose**: Ingest raw VCF data from external sources
- **Format**: GZIP-compressed VCF files
- **Content**: Original variant call format data with allele counts
- **Agent**: EVA Ingestion Agent

### 2. Silver Layer (`/data/silver`)
- **Purpose**: Transform raw VCF data into structured, queryable format
- **Format**: Tab-separated values (TSV)
- **Content**: Variant ID, chromosome, position, ref/alt alleles, and 12 population frequencies
- **Agent**: Manticore Loading Agent (transformation step)
- **Populations**: AFR, AMR, EAS, EUR, SAS, AJ, FIPA, CAU, OTH, APL, ASN, AMR_CAU

### 3. Gold Layer (Manticore Search)
- **Purpose**: Serve indexed, searchable variant data for fast querying
- **Format**: Full-text search index with structured fields
- **Content**: Optimized search index with real-time availability
- **Agent**: Search Engine Agent
- **Access**: REST API (port 9308), SQL protocol (port 9306)

**Architecture Flow**:
```
Raw (VCF.gz) → Silver (TSV) → Gold (Manticore Index)
      ↓               ↓                ↓
  Ingest        Transform        Serve
```

---

## Agents

### 1. EVA Ingestion Agent

**Location**: `etl-pipeline/assets/ingest_eva.py`

**Purpose**: Ingests real genomic variant data from NCBI ALFA project using VCF format, transforming it into a structured format for downstream processing.

**Responsibilities**:
- Downloads VCF data from NCBI FTP (`https://ftp.ncbi.nih.gov/snp/population_frequency/latest_release/freq.vcf.gz`)
- Processes VCF files using `bcftools` for efficient variant extraction
- Filters data to extract relevant variant information (first 1,000,100 records)
- Computes allele frequencies from AC (Allele Count) and AN (Allele Number) fields
- Transforms raw VCF format into structured tabular format
- Handles 12 population samples from ALFA project
- Outputs compressed VCF file to `/data/raw/freq-subset.vcf.gz`
- Creates processed TSV file at `/data/silver/variantes_poblaciones.tsv`

**Data Fields**:
- `variant_id`: Unique identifier (rs... or .id format)
- `CHROM`: Chromosome number
- `pos`: Genomic position
- `ref`: Reference allele
- `alt`: Alternate allele
- `SAMN10492695` through `SAMN10492705`: 12 population frequencies (AFR, AMR, EAS, EUR, SAS, AJ, FIPA, CAU, OTH, APL, ASN, AMR_CAU)

**Technology Stack**:
- Python 3.11
- bcftools for VCF processing
- Subprocess execution for bash pipeline
- AWK for frequency calculation
- Bruin orchestration

**Triggers**: Run by Bruin pipeline as first step in the DAG

---

### 2. Manticore Loading Agent

**Location**: `etl-pipeline/assets/load_to_manticore.py`

**Purpose**: Transforms and bulk loads variant data from the Silver layer into Manticore Search engine for fast querying and indexing.

**Responsibilities**:
- Reads TSV output from EVA Ingestion Agent (`/data/silver/variantes_poblaciones.tsv`)
- Handles NULL values and missing data
- Drops invalid records (those without variant IDs)
- Transforms sample column names to population frequency fields
- Drops and recreates Manticore table to match schema (12 populations)
- Transforms data into NDJSON format for Manticore Bulk API
- Bulk inserts variant records into `eva_variants` index with REPLACE mode
- Implements chunked loading (5,000 records per chunk) to avoid timeouts
- Handles connection retries (up to 3 attempts) with 2s backoff
- Maps TSV columns to Manticore document structure
- Provides status reporting and error handling

**Population Mapping**:
| TSV Column | Manticore Field | Population |
|------------|------------------|------------|
| SAMN10492695 | afr_freq | African |
| SAMN10492696 | amr_freq | American (Admixed) |
| SAMN10492697 | eas_freq | East Asian |
| SAMN10492698 | eur_freq | European |
| SAMN10492699 | sas_freq | South Asian |
| SAMN10492700 | aj_freq | Admixed Jewish |
| SAMN10492701 | fipa_freq | Fijian/Pacific |
| SAMN10492702 | cau_freq | Caucasian |
| SAMN11605645 | oth_freq | Other |
| SAMN10492703 | apl_freq | Andean Pacific |
| SAMN10492704 | asn_freq | Asian |
| SAMN10492705 | amr_cau_freq | American Caucasian |

**Technology Stack**:
- Python 3.11
- Pandas for data manipulation
- Requests library for HTTP calls to Manticore API
- Bruin orchestration

**Dependencies**: Requires `main.ingest_eva` to complete successfully

**Triggers**: Run by Bruin pipeline as second step after ingestion

---

### 3. Search Engine Agent

**Location**: Docker service `search-engine` in `docker-compose.yaml`

**Purpose**: Acts as the data warehouse and search engine in the Gold layer, providing fast full-text search and structured querying capabilities for genomic variants.

**Responsibilities**:
- Maintains the `eva_variants` index with variant records
- Supports full-text search on variant IDs (text field)
- Provides RESTful API for querying (port 9308)
- Supports SQL-like queries via SphinxQL (port 9306)
- Serves data to the Gradio Web Interface
- Persists data to `/data` volume for durability
- Handles bulk insert operations efficiently
- Supports real-time querying and indexing

**Schema**:
```
eva_variants (
  variant_id TEXT,          -- Full-text searchable
  pos INTEGER,               -- Genomic position
  ref STRING,                -- Reference allele
  alt STRING,                -- Alternate allele
  afr_freq FLOAT,             -- African frequency
  amr_freq FLOAT,            -- American (Admixed) frequency
  eas_freq FLOAT,            -- East Asian frequency
  eur_freq FLOAT,            -- European frequency
  sas_freq FLOAT,            -- South Asian frequency
  aj_freq FLOAT,             -- Admixed Jewish frequency
  fipa_freq FLOAT,           -- Fijian/Pacific frequency
  cau_freq FLOAT,            -- Caucasian frequency
  oth_freq FLOAT,            -- Other frequency
  apl_freq FLOAT,            -- Andean Pacific frequency
  asn_freq FLOAT,            -- Asian frequency
  amr_cau_freq FLOAT         -- American Caucasian frequency
)
```

**Technology Stack**:
- Manticore Search (latest)
- Docker containerization

**API Endpoints**:
- `http://localhost:9308/bulk` - Bulk insert/update operations
- `http://localhost:9308/sql` - SQL queries
- `http://localhost:9308/search` - Search queries
- Port 9308 - HTTP API
- Port 9306 - SphinxQL protocol

**Dependencies**: None (independent service)

---

### 4. Dashboard Agent

**Location**: `dashboard/main.py`

**Purpose**: Provides a user-friendly web interface for searching and visualizing genomic variant data stored in Manticore, with support for 12 population frequencies.

**Responsibilities**:
- **Variant Search**:
  - Dropdown with 20 sample variant IDs for easy access
  - Allows custom variant ID entry (rs... format)
  - Queries Manticore Search for matching records
  - Displays variant details (position, ref/alt alleles)
  - Generates interactive bar chart showing all 12 population frequencies (AFR, AMR, EAS, EUR, SAS, AJ, FIPA, CAU, OTH, APL, ASN, AMR_CAU)
  - Autoscales Y-axis to fit data range (no fixed [0, 1.0] limit)

- **Distribution Analysis**:
  - Retrieves up to 5,000 variant records
  - Creates histogram showing variant distribution across chromosome segment
  - Allows real-time refresh of density plot

- **User Interface**:
  - Responsive Gradio web UI
  - Dropdown with sample variant IDs (auto-populated on load)
  - "Refresh Sample List" button to reload variants
  - Interactive visualizations using Plotly
  - Status messages and error handling

**Technology Stack**:
- Python 3.11
- Gradio 4.0+ for web interface
- Plotly for interactive charts with autoscaling
- Pandas for data manipulation
- manticoresearch client library

**Web Interface**:
- URL: `http://localhost:7860`
- Three main features:
  1. Search by Variant ID with 12-population frequency bar chart (autoscaled)
  2. Chromosome distribution histogram
  3. Sample variant dropdown with 20 pre-loaded options

**Dependencies**: Requires Manticore Search to be running and populated

---

## Pipeline Orchestration

### Bruin Pipeline Engine

**Location**: `etl-pipeline/` directory

**Purpose**: Orchestrates the ETL workflow, managing dependencies between agents and ensuring data flows correctly through Medallion layers.

**Pipeline Definition**: `etl-pipeline/pipeline.yml`

**DAG Structure**:
```
main.ingest_eva → main.load_to_manticore
```

**Workflow**:
1. Bruin executes `main.ingest_eva` asset
   - Downloads VCF data from NCBI ALFA
   - Processes with bcftools
   - Saves to `/data/raw/freq-subset.vcf.gz` (Raw Layer)
   - Transforms to `/data/silver/variantes_poblaciones.tsv` (Silver Layer)
2. Upon successful completion, Bruin triggers `main.load_to_manticore`
   - Reads TSV from Silver Layer
   - Transforms and bulk loads to Manticore (Gold Layer)
   - Verifies data is indexed and queryable
3. Web interface becomes available for querying from Gold Layer

**Environment Configuration**:
- Default environment: `etl-pipeline/environments/default.yml`
- No DuckDB connection (uses file-based Medallion layers)
- Supports multiple deployment environments

---

## Communication Flow

```
User → Gradio Web UI → Manticore Search API → Returns variant data (Gold Layer)
                         ↑
                         |
                         Bulk Load
                         |
EVA Ingestion → TSV File → Manticore Loading Agent → Manticore Search (Gold Layer)
  (Raw Layer)      (Silver Layer)              (orchestrated by Bruin)
```

**Data Flow Summary**:
1. **Ingestion Phase (Raw → Silver)**: EVA Ingestion Agent downloads VCF data from NCBI ALFA and transforms it to TSV format
2. **Loading Phase (Silver → Gold)**: Manticore Loading Agent transforms TSV and bulk loads to Manticore index
3. **Serving Phase (Gold → User)**: Gradio Web UI queries Manticore Search for real-time variant visualization

---

## Shared Infrastructure

### Docker Compose

**Location**: `docker-compose.yaml`

**Purpose**: Manages all services as containers with proper networking and volume sharing across Medallion layers.

**Services**:
- `search-engine`: Search engine and data warehouse (Gold Layer)
- `dashboard`: Web interface
- `etl-pipeline`: Pipeline orchestration environment

**Shared Volumes**:
- `./data`: Shared data directory for Medallion layers
  - `/data/raw` - Raw VCF files
  - `/data/silver` - Processed TSV files
  - Manticore persistence
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
- Manual setup (no automatic `setup.sh` execution)
- Lightweight startup for faster codespace initialization

---

## Data Quality

### Validation Checks

**EVA Ingestion Agent**:
- Variant ID uniqueness and validity checks
- Allele frequency calculations (AC/AN) with NULL handling
- VCF format validation via bcftools

**Manticore Loading Agent**:
- Connection retry logic (3 attempts with 2s delay)
- HTTP response validation (expects 200 status)
- Data type enforcement (integer for pos, float for frequencies)
- NULL value handling and conversion to 0.0
- Invalid record filtering (drops records without variant IDs)

---

## Scalability Considerations

- **Manticore Search**: Can handle millions of records with sub-second queries
- **Gradio**: Stateless application; can scale horizontally
- **Bruin**: Designed for local execution, but supports GitHub Actions for CI/CD
- **Data Volume**: Currently ~1.6M records (ALFA subset); can be increased to full dataset
- **Medallion Layers**: Each layer can be independently scaled and optimized
- **Chunked Loading**: Prevents memory issues and timeouts during bulk inserts

---

## Security Notes

- Environment variables used for sensitive configuration (MANTICORE_URL)
- No hardcoded credentials
- FTP connection is read-only
- Gradio runs without authentication (intended for local/demo use)
- Manticore runs without authentication (should be secured for production)
- VCF data is from public NCBI ALFA repository

---

## Monitoring and Observability

**Logging**:
- Each agent prints status messages to stdout
- Bruin logs to `etl-pipeline/logs/` directory
- Docker Compose captures all container logs

**Health Checks**:
- EVA Agent: Validates VCF download and bcftools processing
- Loading Agent: Verifies Manticore response status
- Web UI: Provides status messages to user

---

## Future Enhancements

Potential improvements to the agent system:

1. **Incremental Updates**: Support delta updates instead of full reloads
2. **Additional Data Sources**: Integrate other genomic databases (gnomAD, 1000 Genomes)
3. **Authentication**: Add user authentication to Gradio interface
4. **API Extensions**: Expose REST API for programmatic access
5. **Data Versioning**: Track different versions of the variant dataset
6. **Caching**: Add caching layer for frequently queried variants
7. **Alerting**: Notify on pipeline failures or data anomalies
8. **Multi-chromosome Support**: Extend beyond current chromosome subset
9. **Genomic Annotations**: Add gene context, functional impact data
10. **Advanced Search**: Support range queries, complex filters, and faceted search
11. **Real-time Streaming**: Implement change data capture for live data updates
12. **Medallion Expansion**: Add Bronze/Gold+ layers for advanced analytics
