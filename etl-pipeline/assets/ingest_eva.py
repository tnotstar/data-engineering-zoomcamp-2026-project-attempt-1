"""@bruin
name: main.ingest_eva
@bruin"""

import subprocess
import os
import pandas as pd

def materialize():
    print("Starting EVA VCF Stream using bcftools...")

    # --- RAW LAYER: /data/raw ---
    os.makedirs('/data/raw', exist_ok=True)
    raw_path = '/data/raw/freq-subset.vcf.gz'

    # --- SILVER LAYER: /data/silver ---
    os.makedirs('/data/silver', exist_ok=True)
    silver_path = '/data/silver/variantes_poblaciones.tsv'

    bash_script = f"""
    curl -s https://ftp.ncbi.nih.gov/snp/population_frequency/latest_release/freq.vcf.gz | \\
    bcftools view | head -n 1000100 | bcftools view -Oz -o {raw_path}

    # Generate samples header
    samples=$(bcftools query -l {raw_path} | tr '\\n' '\\t')
    echo -e "variant_id\\tCHROM\\tpos\\tref\\talt\\t$samples" > {silver_path}

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
        print(f"Error executing bash pipeline:\n{process.stderr}")
        raise RuntimeError("Bash pipeline failed.")

    print(f"Raw data saved to {raw_path}")
    print(f"Silver data saved to {silver_path}")

    return pd.DataFrame([{"status": "ingest_complete"}])

materialize()
