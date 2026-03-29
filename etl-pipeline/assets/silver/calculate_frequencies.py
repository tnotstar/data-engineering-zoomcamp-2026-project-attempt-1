"""@bruin
name: silver.calculate_frequencies
depends:
  - raw.download_frequencies
@bruin"""

import subprocess
import os
import pandas as pd

def materialize():
    print("Starting EVA VCF Stream using bcftools...")

    # --- RAW LAYER: /data/raw ---
    os.makedirs('/data/raw', exist_ok=True)
    raw_path = '/data/raw/freq-subset.vcf.gz'

    if not os.path.exists(raw_path):
        # List files in /data/raw for debugging
        try:
            files = os.listdir('/data/raw')
            print(f"Files in /data/raw: {files}")
        except:
            pass
        raise FileNotFoundError(f"Missing {raw_path}. Did the raw layer run successfully?")

    # --- SILVER LAYER: /data/silver ---
    os.makedirs('/data/silver', exist_ok=True)
    silver_path = '/data/silver/variantes_poblaciones.tsv'

    bash_script = f"""
    set -eo pipefail
    echo "Generating samples header from {raw_path}..."
    samples=$(bcftools query -l {raw_path} | tr '\\n' '\\t')
    echo -e "variant_id\\tchrom\\tpos\\tref\\talt\\t$samples" > {silver_path}

    echo "Extracting AC and AN and computing frequencies..."
    # Extract AC and AN recursively and compute frequencies using awk
    bcftools query -f '%ID\\t%CHROM\\t%POS\\t%REF\\t%ALT[\\t%AC\\t%AN]\\n' {raw_path} | \\
    awk 'BEGIN {{FS="\\t"; OFS="\\t"}} {{
        for (i=6; i<=NF; i+=2) {{
            ac = $i; an = $(i+1);
            if (an != "." && an > 0 && ac != ".") {{
                $i = ac/an;
            }} else {{
                $i = "NULL";
            }}
        }}
        print $1,$2,$3,$4,$5,$6,$8,$10,$12,$14,$16,$18,$20,$22,$24,$26,$28
    }}' >> {silver_path}
    """

    print("Executing bcftools and awk pipeline (raw → silver)...")
    process = subprocess.run(["bash", "-c", bash_script], capture_output=True, text=True)

    if process.returncode != 0:
        print(f"Error executing bash pipeline (Exit {process.returncode}):\n{process.stderr}")
        raise RuntimeError(f"Bash pipeline failed: {process.stderr}")

    if not os.path.exists(silver_path) or os.path.getsize(silver_path) == 0:
        raise RuntimeError(f"Failed to create silver data file at {silver_path} or file is empty.")

    print(f"Silver data successfully saved to {silver_path} ({os.path.getsize(silver_path)} bytes)")

    return pd.DataFrame([{"status": "calculate_frequencies_complete"}])

if __name__ == "__main__":
    materialize()
