"""@bruin
name: raw.download_frequencies
@bruin"""

import os
import subprocess

import pandas as pd


def materialize(number_of_variants: int):
    # If using Bruin, the variable defined in pipeline.yml is passed directly to materialize.
    # Alternatively, you can use **kwargs to capture all variables.
    print(f"Starting EVA VCF Stream using bcftools (limiting to {number_of_variants} variants)...")

    # --- RAW LAYER: /data/raw ---
    os.makedirs('/data/raw', exist_ok=True)
    raw_path = '/data/raw/freq-subset.vcf.gz'

    bash_script = f"""
    curl -s https://ftp.ncbi.nih.gov/snp/population_frequency/latest_release/freq.vcf.gz | \\
    bcftools view | head -n {number_of_variants + 100} | bcftools view -Oz -o {raw_path}
    """

    print("Executing bcftools and awk pipeline (FTP → raw)...")
    process = subprocess.run(
        ["bash", "-c", bash_script], capture_output=True, text=True)

    if process.returncode != 0:
        print(f"Error executing bash pipeline:\n{process.stderr}")
        raise RuntimeError("Bash pipeline failed.")

    print(f"Raw data saved to {raw_path}")

    return pd.DataFrame([{"status": "download_complete"}])


