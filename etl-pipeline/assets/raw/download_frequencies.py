"""@bruin
name: raw.download_frequencies
@bruin"""

import os
import subprocess
import sys
import pandas as pd

def materialize(number_of_variants=None):
    if number_of_variants is None:
        # Fetch from Bruin context if available, else environment variable, else default
        number_of_variants = int(os.getenv('BRUIN_VAR_NUMBER_OF_VARIANTS', os.getenv('number_of_variants', 100)))

    print(f"Starting EVA VCF Stream using bcftools (limiting to {number_of_variants} variants)...")

    # --- RAW LAYER: /data/raw ---
    os.makedirs('/data/raw', exist_ok=True)
    raw_path = '/data/raw/freq-subset.vcf.gz'

    # Note: We omit 'set -o pipefail' here because 'head' gracefully closes the pipe 
    # and we want to ignore the SIGPIPE (141) from upstream bcftools.
    bash_script = f"""
    set -e
    echo "Downloading and filtering VCF data from NCBI (approx. {number_of_variants} variants)..."
    curl -s https://ftp.ncbi.nih.gov/snp/population_frequency/latest_release/freq.vcf.gz | \
    bcftools view | head -n {number_of_variants + 100} | bcftools view -Oz -o {raw_path} || [ $? -eq 141 ]
    """

    print("Executing bcftools pipeline (FTP → raw)...")
    process = subprocess.run(
        ["bash", "-c", bash_script], capture_output=True, text=True)

    # Note: stderr may contain warnings about contigs not in header; we only care about real failures
    if process.returncode != 0 and process.returncode != 141:
        print(f"Error executing bash pipeline (Exit {process.returncode}):\n{process.stderr}")
        raise RuntimeError(f"Bash pipeline failed with exit code {process.returncode}")

    if not os.path.exists(raw_path) or os.path.getsize(raw_path) == 0:
        raise RuntimeError(f"Failed to create raw data file at {raw_path} or file is empty.")

    print(f"Raw data successfully saved to {raw_path} ({os.path.getsize(raw_path)} bytes)")

    return pd.DataFrame([{"status": "download_complete"}])

if __name__ == "__main__":
    materialize()


