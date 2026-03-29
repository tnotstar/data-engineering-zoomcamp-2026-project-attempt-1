"""@bruin
name: main.ingest_eva
@bruin"""

import subprocess
import os
import pandas as pd

def materialize():
    print("Starting EVA VCF Stream using bcftools...")
    
    # Ensure local path exists (Shared Volume)
    os.makedirs('/data', exist_ok=True)
    out_path = '/data/variantes_poblaciones.tsv'
    
    # Using the user-provided bash pipeline with 10,000 lines for testing
    bash_script = """
    curl -s https://ftp.ncbi.nih.gov/snp/population_frequency/latest_release/freq.vcf.gz | \\
    bcftools view | head -n 10000 | bcftools view -Oz -o /data/freq-subset.vcf.gz

    # Generate samples header
    samples=$(bcftools query -l /data/freq-subset.vcf.gz | tr '\\n' '\\t')
    echo -e "variant_id\\tCHROM\\tpos\\tref\\talt\\t$samples" > /data/variantes_poblaciones.tsv

    # Extract AC and AN recursively and compute frequencies using awk
    bcftools query -f '%ID\\t%CHROM\\t%POS\\t%REF\\t%ALT[\\t%AC\\t%AN]\\n' /data/freq-subset.vcf.gz | \\
    awk 'BEGIN {FS="\\t"; OFS="\\t"} {
        for (i=6; i<=NF; i+=2) {
            ac = $i; an = $(i+1);
            if (an != "." && an > 0 && ac != ".") {
                $i = ac/an;
            } else {
                $i = "NULL";
            }
        }
        # Esto elimina la columna AN sobrante para dejar solo la de frecuencia
        print $1,$2,$3,$4,$5, $6,$8,$10,$12,$14,$16,$18,$20,$22,$24,$26,$28
    }' >> /data/variantes_poblaciones.tsv
    """
    
    print("Executing bcftools and awk pipeline...")
    process = subprocess.run(["bash", "-c", bash_script], capture_output=True, text=True)
    
    if process.returncode != 0:
        print(f"Error executing bash pipeline:\\n{process.stderr}")
        raise RuntimeError("Bash pipeline failed.")
        
    print(f"Bash pipeline completed. Output saved to {out_path}.")
    
    # Return a basic status as there is no need to push pandas dataframe to next asset
    return pd.DataFrame([{"status": "ingest_complete"}])
