# European Variation Archive (EVA) Genomic Insights: High-Performance Population Frequency Pipeline

## 1. Problem Statement
The **European Variation Archive (EVA)** hosts massive datasets of genetic variations. For researchers, analyzing population frequencies (e.g., how common a mutation is in Europeans vs. Africans) is a "big data" challenge. Raw VCF/TSV files are often too large to query directly, and traditional Data Warehouses can be overkill or too slow for real-time variant lookups.

**The Goal:** Build an end-to-end, **low-cost**, and **highly reproducible** pipeline to ingest, filter "on-the-fly," and index genomic data. This project enables real-time queries of population frequencies through an interactive dashboard.

---

## 2. Architecture & Design Decisions
To ensure this project is accessible for peer review while maintaining professional standards, the following architectural decisions were made:

* **Orchestration via Bruin:** Instead of heavy tools like Airflow, I used **Bruin**. It allows for SQL and Python-based data asset management with built-in data quality checks, making the pipeline modular and easy to track.
* **Search-Optimized DWH (Manticore Search):** While the course introduces BigQuery, I implemented **Manticore Search** (as a `searchengine` service) as the serving layer. 
    * *Rationale:* Genomics requires ultra-low latency for specific ID lookups. Manticore acts as an "indexed" Data Warehouse, offering sub-second response times that outperform standard SQL scans for this use case.
* **Simulated Data Lake:** To keep the project **Zero-Cost** for reviewers, I use a Docker-mounted volume to simulate a Cloud Data Lake (GCS style), ensuring the project runs entirely within a **GitHub Codespace**.
* **On-the-fly Transformation:** Data is filtered during the download stream. This minimizes disk I/O and avoids storing gigabytes of unnecessary genomic noise.

---

## 3. Technology Stack
| Layer | Tool | Description |
| :--- | :--- | :--- |
| **Orchestration** | [Bruin](https://getbruin.com) | Manages dependencies, ingestion logic, and data validation (service `etl-pipeline`). |
| **Indexing / DWH** | **Manticore Search** | High-performance search engine used for variant indexing (service `search-engine`). |
| **Dashboard** | **Gradio** | Python-based UI for real-time data visualization (service `dashboard`). |
| **Containerization**| **Docker Compose** | Orchestrates the entire stack (`search-engine`, `dashboard`, `etl-pipeline`). |
| **Environment** | **GitHub Codespaces** | Provides a one-click, reproducible development environment. |

---

## 4. The Data Pipeline
The pipeline is managed by **Bruin** and consists of three main stages:

1.  **Ingestion & Filter:** A Python asset streams data from EVA, filters for a specific chromosome (e.g., Chromosome 21), and cleans population metadata.
2.  **Storage:** The cleaned data is persisted as a `.csv` in the local data lake.
3.  **Indexing:** Data is bulk-loaded into Manticore Search. 
    * *Optimization:* Tables are **clustered by Variant ID** and indexed for range queries on genomic positions to ensure maximum performance.

---

## 5. Dashboard Features
The Gradio UI provides two primary tiles for data analysis:
* **Tile 1: Categorical Distribution:** A bar chart visualizing Allele Frequencies across different ethnic populations (e.g., EUR, AFR, AMR, EAS, SAS).
* **Tile 2: Regional Statistics:** A distribution plot showing the density of variations across the genomic region of interest.

---

## 6. How to Reproduce (Peer-Review Guide)
This project is designed to run in a **GitHub Codespace** with zero configuration.

1.  **Launch Codespace:** Click on the "Open in GitHub Codespaces" button in this repository.
2.  **Start Services:** Once the terminal is ready, run:
    ```bash
    ./start-services.sh
    ```
3.  **Run Pipeline:** Execute the Bruin workflow to fetch and index the data:
    ```bash
    ./run-etl-pipeline.sh
    ```
4.  **Access Dashboard:** Open the URL provided by the `dashboard` container (port `7860`) in your browser.

---

## 7. Peer-Review Evaluation Criteria Checklist
* **Cloud/IaC:** Simulated via Docker/Codespaces for cost-efficiency.
* **Workflow Orchestration:** Fully managed by Bruin (End-to-End DAG).
* **Data Warehouse:** Manticore Search used with explicit indexing and clustering for query optimization.
* **Transformations:** Defined in Python/SQL within the Bruin assets.
* **Dashboard:** 2+ tiles built in Gradio.
